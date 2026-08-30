"""
IP-SAKTI Sahayak Ingestion Service
Main entry point for the ingestion pipeline
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import ingestion components
from src.parsers.statute_parser import statute_parser
from src.chunkers.legal_chunker import legal_chunker
from src.embedders.embedding_generator import embedding_generator
from src.transaction_manager import TransactionManager

app = FastAPI(title="IP-SAKTI Ingestion", version="0.1.0")

# Initialize components
transaction_manager = TransactionManager()


class IngestionRequest(BaseModel):
    """Request model for ingestion endpoint"""
    data_source: str  # "json" or "raw_text"
    data: List[Dict[str, Any]]  # Either structured JSON or raw text data
    metadata: Dict[str, Any]
    jurisdiction: str = "india"
    domain: str = "statutes"


class IngestionResponse(BaseModel):
    """Response model for ingestion endpoint"""
    status: str
    chunks_processed: int
    qdrant_points: int
    elasticsearch_docs: int
    corpus_version: str
    errors: List[str]


@app.get("/health")
async def health_check():
    """Health check endpoint - actually checks component health"""
    # Check transaction manager (includes Qdrant and Elasticsearch)
    health_status = transaction_manager.health_check()
    
    # Check embedding generator
    embedding_healthy = True  # Always healthy if initialized
    
    # Check parser
    parser_healthy = True  # Always healthy if initialized
    
    # Check chunker
    chunker_healthy = True  # Always healthy if initialized
    
    all_healthy = all([
        health_status.get("qdrant", False),
        health_status.get("elasticsearch", False),
        embedding_healthy,
        parser_healthy,
        chunker_healthy
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "ingestion",
        "components": {
            "qdrant": "healthy" if health_status.get("qdrant") else "unhealthy",
            "elasticsearch": "healthy" if health_status.get("elasticsearch") else "unhealthy",
            "embeddings": "healthy" if embedding_healthy else "unhealthy",
            "parsers": "healthy" if parser_healthy else "unhealthy",
            "chunkers": "healthy" if chunker_healthy else "unhealthy",
            "transaction_manager": "healthy" if health_status.get("transaction_manager") else "degraded"
        }
    }


@app.post("/ingest", response_model=IngestionResponse)
async def ingest(request: IngestionRequest):
    """
    Main ingestion endpoint - full pipeline: parse → chunk → embed → write to Qdrant+Elasticsearch
    """
    try:
        logger.info(f"Starting ingestion for {request.data_source} from {request.jurisdiction}")
        
        errors = []
        
        # Step 1: Parse data based on source type
        if request.data_source == "json":
            # Use structured JSON parsing
            parsed_chunks = statute_parser.parse_json(request.data, request.metadata)
        elif request.data_source == "raw_text":
            # Use raw text parsing
            # Expect data to be list of {"text": "..."} objects
            raw_texts = [item.get("text", "") for item in request.data]
            parsed_chunks = []
            for i, text in enumerate(raw_texts):
                chunks = statute_parser.parse(text, {**request.metadata, "doc_index": i})
                parsed_chunks.extend(chunks)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported data_source: {request.data_source}")
        
        logger.info(f"Parsed {len(parsed_chunks)} chunks")
        
        if not parsed_chunks:
            return IngestionResponse(
                status="completed",
                chunks_processed=0,
                qdrant_points=0,
                elasticsearch_docs=0,
                corpus_version=request.metadata.get("version", "1.0"),
                errors=["No chunks parsed from input data"]
            )
        
        # Step 2: Chunk the parsed data
        chunked_data = legal_chunker.chunk(parsed_chunks)
        
        # Add citation metadata
        enhanced_chunks = legal_chunker.add_citation_metadata(
            chunked_data,
            {
                **request.metadata,
                "jurisdiction": request.jurisdiction,
                "domain": request.domain
            }
        )
        
        logger.info(f"Chunked into {len(enhanced_chunks)} enhanced chunks")
        
        # Step 3: Generate embeddings
        embedded_chunks = embedding_generator.generate_embeddings(enhanced_chunks)
        
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
        
        # Debug: Check first chunk structure
        if embedded_chunks:
            first_chunk = embedded_chunks[0]
            logger.info(f"First chunk keys: {first_chunk.keys()}")
            logger.info(f"First chunk has 'embedding': {'embedding' in first_chunk}")
            if 'embedding' in first_chunk:
                logger.info(f"First chunk embedding length: {len(first_chunk['embedding'])}")
            else:
                logger.error(f"First chunk missing 'embedding' key!")
        
        # Step 4: Transactional write to Qdrant and Elasticsearch
        corpus_version = request.metadata.get("version", "1.0")
        
        try:
            qdrant_points, elasticsearch_docs = await transaction_manager.ingest_chunks(
                chunks=embedded_chunks,
                corpus_version=corpus_version,
                jurisdiction=request.jurisdiction,
                domain=request.domain
            )
            
            logger.info(f"Successfully wrote {qdrant_points} points to Qdrant and {elasticsearch_docs} docs to Elasticsearch")
            
            return IngestionResponse(
                status="completed",
                chunks_processed=len(embedded_chunks),
                qdrant_points=qdrant_points,
                elasticsearch_docs=elasticsearch_docs,
                corpus_version=corpus_version,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            errors.append(f"Transaction failed: {str(e)}")
            
            return IngestionResponse(
                status="failed",
                chunks_processed=len(embedded_chunks),
                qdrant_points=0,
                elasticsearch_docs=0,
                corpus_version=corpus_version,
                errors=errors
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-single")
async def ingest_single_text(text: str, metadata: Dict[str, Any]):
    """
    Convenience endpoint for ingesting a single text document
    """
    request = IngestionRequest(
        data_source="raw_text",
        data=[{"text": text}],
        metadata=metadata
    )
    return await ingest(request)


@app.get("/corpus/{version}")
async def get_corpus_info(version: str):
    """
    Get information about a specific corpus version
    """
    try:
        info = await transaction_manager.get_corpus_info(version)
        return info
    except Exception as e:
        logger.error(f"Failed to get corpus info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
