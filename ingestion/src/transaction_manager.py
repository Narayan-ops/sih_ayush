"""Verified, recoverable dual-store ingestion for IP-SAKTI.

Qdrant and Elasticsearch have no shared transaction.  This module therefore
uses deterministic ids, post-write verification, and compensation that deletes
only records created by the failed operation. A compensation failure is raised
as a critical operational error instead of being reported as success.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from elasticsearch import Elasticsearch, helpers
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

logger = logging.getLogger(__name__)
_NAME = re.compile(r"^(in|intl)_[a-z0-9_]+$")


class DualStoreConsistencyError(RuntimeError):
    """A write cannot be proven present in both retrieval stores."""


@dataclass(frozen=True)
class IngestionResult:
    qdrant_points: int
    elasticsearch_docs: int
    transaction_id: str


class TransactionManager:
    """Write immutable corpus chunks consistently to Qdrant and Elasticsearch."""

    def __init__(self, qdrant_client: QdrantClient | None = None, elasticsearch_client: Elasticsearch | None = None):
        self.qdrant_client = qdrant_client or QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"), api_key=os.getenv("QDRANT_API_KEY")
        )
        if elasticsearch_client:
            self.elasticsearch_client = elasticsearch_client
        else:
            endpoint = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            username, password = os.getenv("ELASTICSEARCH_USERNAME"), os.getenv("ELASTICSEARCH_PASSWORD")
            self.elasticsearch_client = Elasticsearch([endpoint], basic_auth=(username, password)) if username and password else Elasticsearch([endpoint])

    @staticmethod
    def collection_name(jurisdiction: str, domain: str) -> str:
        prefix = {"india": "in", "in": "in", "international": "intl", "intl": "intl"}.get(jurisdiction.lower())
        name = f"{prefix}_{domain.lower().replace('-', '_')}" if prefix else ""
        if not _NAME.fullmatch(name):
            raise ValueError("jurisdiction must be India/in or International/intl and domain must be a safe identifier")
        return name

    @staticmethod
    def _id(chunk: dict[str, Any]) -> str:
        metadata = chunk["metadata"]
        value = "|".join(str(metadata[key]) for key in ("source_id", "section", "clause", "version_hash", "chunk_ordinal"))
        return str(uuid.uuid5(uuid.NAMESPACE_URL, value))

    def _ensure_stores(self, collection: str, dimension: int) -> None:
        collections = {item.name for item in self.qdrant_client.get_collections().collections}
        if collection not in collections:
            self.qdrant_client.create_collection(collection_name=collection, vectors_config=VectorParams(size=dimension, distance=Distance.COSINE, on_disk=True))
        if not self.elasticsearch_client.indices.exists(index=collection):
            self.elasticsearch_client.indices.create(index=collection, mappings={"dynamic": "strict", "properties": {
                "chunk_id": {"type": "keyword"}, "content": {"type": "text"}, "source_id": {"type": "keyword"},
                "section": {"type": "keyword"}, "clause": {"type": "keyword"}, "version_hash": {"type": "keyword"},
                "review_status": {"type": "keyword"}, "jurisdiction": {"type": "keyword"}, "domain": {"type": "keyword"},
                "corpus_version": {"type": "keyword"}, "ingested_at": {"type": "date"}, "metadata": {"type": "object", "enabled": False},
            }})

    def _existing_qdrant_ids(self, collection: str, ids: list[str]) -> set[str]:
        return {str(point.id) for point in self.qdrant_client.retrieve(collection_name=collection, ids=ids, with_payload=False, with_vectors=False)}

    def _existing_es_ids(self, collection: str, ids: list[str]) -> set[str]:
        response = self.elasticsearch_client.mget(index=collection, docs=[{"_id": item} for item in ids])
        return {item["_id"] for item in response["docs"] if item.get("found")}

    def _delete_qdrant(self, collection: str, ids: Iterable[str]) -> None:
        values = list(ids)
        if values:
            self.qdrant_client.delete(collection_name=collection, points_selector=PointIdsList(points=values), wait=True)

    def _delete_es(self, collection: str, ids: Iterable[str]) -> None:
        actions = [{"_op_type": "delete", "_index": collection, "_id": item} for item in ids]
        if actions:
            helpers.bulk(self.elasticsearch_client, actions, raise_on_error=True, refresh="wait_for")

    def _verify(self, collection: str, ids: list[str]) -> None:
        wanted = set(ids)
        qdrant_ids, es_ids = self._existing_qdrant_ids(collection, ids), self._existing_es_ids(collection, ids)
        if qdrant_ids != wanted or es_ids != wanted:
            raise DualStoreConsistencyError(
                f"CRITICAL dual-store inconsistency collection={collection} missing_qdrant={sorted(wanted-qdrant_ids)} missing_elasticsearch={sorted(wanted-es_ids)}"
            )

    def ingest_chunks(self, chunks: list[dict[str, Any]], corpus_version: str, jurisdiction: str, domain: str) -> IngestionResult:
        if not chunks:
            return IngestionResult(0, 0, "empty")
        collection, transaction_id = self.collection_name(jurisdiction, domain), str(uuid.uuid4())
        ids = [self._id(chunk) for chunk in chunks]
        if len(ids) != len(set(ids)):
            raise ValueError("input contains duplicate deterministic chunk identities")
        dimensions = {len(chunk.get("embedding", [])) for chunk in chunks}
        if len(dimensions) != 1 or not next(iter(dimensions)):
            raise ValueError("each chunk must have a non-empty embedding of the same dimension")
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            required = ("source_id", "section", "clause", "version_hash", "chunk_ordinal", "review_status")
            if any(not str(metadata.get(key, "")).strip() for key in required):
                raise ValueError("every chunk requires source_id, section, clause, version_hash, chunk_ordinal and review_status")

        self._ensure_stores(collection, next(iter(dimensions)))
        q_before, es_before = self._existing_qdrant_ids(collection, ids), self._existing_es_ids(collection, ids)
        if q_before != es_before:
            raise DualStoreConsistencyError(f"CRITICAL pre-existing inconsistency in {collection}; repair before ingesting")
        new = [(chunk, chunk_id) for chunk, chunk_id in zip(chunks, ids) if chunk_id not in q_before]
        if not new:
            self._verify(collection, ids)
            return IngestionResult(0, 0, transaction_id)

        created_ids, now = [chunk_id for _, chunk_id in new], datetime.now(timezone.utc).isoformat()
        try:
            points = [PointStruct(id=chunk_id, vector=chunk["embedding"], payload={
                "chunk_id": chunk_id, "content": chunk["content"], "source_id": chunk["metadata"]["source_id"],
                "section": chunk["metadata"]["section"], "clause": chunk["metadata"]["clause"],
                "version_hash": chunk["metadata"]["version_hash"], "review_status": chunk["metadata"]["review_status"],
                "jurisdiction": collection.split("_", 1)[0], "domain": domain, "corpus_version": corpus_version, "metadata": chunk["metadata"],
            }) for chunk, chunk_id in new]
            self.qdrant_client.upsert(collection_name=collection, points=points, wait=True)
            actions = [{"_op_type": "create", "_index": collection, "_id": chunk_id, "_source": {
                "chunk_id": chunk_id, "content": chunk["content"], "source_id": chunk["metadata"]["source_id"],
                "section": chunk["metadata"]["section"], "clause": chunk["metadata"]["clause"], "version_hash": chunk["metadata"]["version_hash"],
                "review_status": chunk["metadata"]["review_status"], "jurisdiction": collection.split("_", 1)[0], "domain": domain,
                "corpus_version": corpus_version, "ingested_at": now, "metadata": chunk["metadata"],
            }} for chunk, chunk_id in new]
            helpers.bulk(self.elasticsearch_client, actions, raise_on_error=True, refresh="wait_for")
            self._verify(collection, ids)
            logger.info("dual-store transaction committed id=%s collection=%s chunks=%s", transaction_id, collection, len(new))
            return IngestionResult(len(new), len(new), transaction_id)
        except Exception as error:
            rollback_errors: list[str] = []
            for name, rollback in (("elasticsearch", self._delete_es), ("qdrant", self._delete_qdrant)):
                try:
                    rollback(collection, created_ids)
                except Exception as rollback_error:
                    rollback_errors.append(f"{name}: {rollback_error}")
            message = f"dual-store transaction {transaction_id} failed: {error}"
            if rollback_errors:
                logger.critical("%s; rollback failures: %s", message, rollback_errors)
                raise DualStoreConsistencyError(f"{message}; rollback failures: {rollback_errors}") from error
            logger.error("%s; compensating rollback completed", message)
            raise

    def health_check(self) -> dict[str, bool]:
        try:
            self.qdrant_client.get_collections(); qdrant = True
        except Exception:
            qdrant = False
        try:
            elasticsearch = bool(self.elasticsearch_client.ping())
        except Exception:
            elasticsearch = False
        return {"qdrant": qdrant, "elasticsearch": elasticsearch, "transaction_manager": qdrant and elasticsearch}
