"""Controlled corpus-ingestion API.

This service accepts only structured, review-labelled legal chunks. It never
scrapes public sources and it never marks content authoritative on its own.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.embedders.embedding_generator import embedding_generator
from src.transaction_manager import DualStoreConsistencyError, TransactionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="IP-SAKTI controlled ingestion", version="1.0.0")
transaction_manager = TransactionManager()


class SourceChunk(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    section: str = Field(min_length=1, max_length=500)
    clause: str | None = Field(default=None, max_length=500)
    source_id: str = Field(min_length=1, max_length=500)
    citation_label: str | None = Field(default=None, max_length=1_000)


class IngestionRequest(BaseModel):
    data: list[SourceChunk] = Field(min_length=1, max_length=10_000)
    metadata: dict[str, Any]
    jurisdiction: Literal["in", "india", "intl", "international"]
    domain: str = Field(pattern=r"^[a-z0-9_]+$")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        for field in ("source", "source_url", "retrieved_date", "review_status"):
            if not str(value.get(field, "")).strip():
                raise ValueError(f"metadata.{field} is required")
        if value["review_status"] not in {"pending_review", "approved", "rejected"}:
            raise ValueError("metadata.review_status must be pending_review, approved, or rejected")
        if value["review_status"] == "rejected":
            raise ValueError("rejected corpus content cannot be ingested")
        return value


class IngestionResponse(BaseModel):
    status: Literal["completed"]
    chunks_processed: int
    qdrant_points: int
    elasticsearch_docs: int
    corpus_version: str
    transaction_id: str


def _normalise(request: IngestionRequest) -> list[dict[str, Any]]:
    """Create immutable provenance before embeddings are generated."""
    base = dict(request.metadata)
    source_id = str(base.get("source_id") or hashlib.sha256(f"{base['source']}|{base['source_url']}".encode()).hexdigest()[:24])
    prepared: list[dict[str, Any]] = []
    for ordinal, item in enumerate(request.data):
        content = item.text.strip()
        section, clause = item.section.strip(), (item.clause or "not_applicable").strip() or "not_applicable"
        version_hash = hashlib.sha256((content + "|" + source_id + "|" + section + "|" + clause).encode("utf-8")).hexdigest()
        prepared.append({
            "content": content,
            "metadata": {**base, "source_id": item.source_id.strip() or source_id, "section": section, "clause": clause,
                         "version_hash": version_hash, "chunk_ordinal": ordinal, "citation_label": item.citation_label or f"{section}, {clause}"},
        })
    return embedding_generator.generate_embeddings(prepared)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    stores = transaction_manager.health_check()
    model = embedding_generator.get_model_info()
    healthy = stores["transaction_manager"] and model["status"] == "loaded"
    return {"status": "healthy" if healthy else "degraded", "service": "ingestion", "components": {**stores, "embeddings": model["status"]}}


@app.post("/ingest", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest(request: IngestionRequest) -> IngestionResponse:
    try:
        chunks = _normalise(request)
        version = hashlib.sha256("".join(chunk["metadata"]["version_hash"] for chunk in chunks).encode()).hexdigest()
        result = transaction_manager.ingest_chunks(chunks, version, request.jurisdiction, request.domain)
        return IngestionResponse(status="completed", chunks_processed=len(chunks), qdrant_points=result.qdrant_points,
                                 elasticsearch_docs=result.elasticsearch_docs, corpus_version=version, transaction_id=result.transaction_id)
    except (ValueError, DualStoreConsistencyError) as error:
        logger.error("Ingestion refused: %s", error)
        raise HTTPException(status_code=409, detail="Ingestion was not committed; inspect the operator logs and dual-store alert.") from error
    except Exception as error:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Ingestion failed without publishing partial results.") from error
