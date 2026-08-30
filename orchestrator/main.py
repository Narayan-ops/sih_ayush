"""
IP-SAKTI Sahayak Orchestrator Service
Main entry point for the orchestrator service
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import components
from src.classifiers.formulation_classifier import formulation_classifier
from src.retrieval.hybrid_retriever import HybridRetriever
from src.citation.citation_engine import CitationEngine
from src.llm.config import llm_config
from src.llm.provider_abstraction import LLMProviderFactory
from src.embeddings.query_embedder import query_embedder
from src.retrieval.reranker import _extract_explicit_reference, RerankedResult

app = FastAPI(title="IP-SAKTI Orchestrator", version="0.1.0")

# Initialize components
hybrid_retriever = HybridRetriever()
citation_engine = CitationEngine()

# Get LLM provider (default: self_hosted per ADR-001)
default_provider = os.getenv("LLM_DEFAULT_PROVIDER", "self_hosted")


class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str
    jurisdiction: str = "in"  # "in" for India, "intl" for International
    formulation_type: Optional[str] = None
    provider: Optional[str] = None  # Override default LLM provider
    include_citations: bool = True
    include_confidence: bool = True


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    answer: str
    citations: List[Dict[str, Any]]
    confidence_score: Optional[float]
    formulation_type: Optional[str]
    jurisdiction: str
    model_used: str
    provider_used: str


@app.get("/health")
async def health_check():
    """Health check endpoint - actually checks component health"""
    # Check retrieval components
    retrieval_health = hybrid_retriever.health_check()
    
    # Check LLM provider
    llm_healthy = False
    try:
        provider = llm_config.get_provider(default_provider)
        llm_healthy = await provider.health_check()
    except Exception as e:
        logger.warning(f"LLM provider health check failed: {e}")
    
    # Citation engine always healthy if initialized
    citation_healthy = True
    
    # Classifier always healthy if initialized
    classifier_healthy = True
    
    all_healthy = all([
        retrieval_health.get('dense_retriever', False),
        retrieval_health.get('sparse_retriever', False),
        retrieval_health.get('reranker', False),
        llm_healthy,
        citation_healthy,
        classifier_healthy
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "orchestrator",
        "components": {
            "llm_provider": "healthy" if llm_healthy else "unhealthy",
            "classifier": "healthy" if classifier_healthy else "unhealthy",
            "retrieval": retrieval_health,
            "citation": "healthy" if citation_healthy else "unhealthy"
        }
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Main query endpoint - orchestrates retrieval, classification, and generation
    Flow: formulation_classifier → hybrid_retriever → llm_provider → citation_engine → confidence_scorer
    """
    try:
        logger.info(f"Received query: {request.query[:100]}... (jurisdiction: {request.jurisdiction})")
        
        # Step 1: Classify formulation type
        classification_result = await formulation_classifier.classify(
            user_input=request.query,
            session_context={"jurisdiction": request.jurisdiction}
        )
        
        formulation_type = classification_result.get("formulation_class")
        logger.info(f"Classification result: {formulation_type}")
        
        # Step 2: Retrieve relevant documents using hybrid retriever
        # Generate real query embedding using the same model as ingestion
        query_embedding = query_embedder.generate_embedding(request.query)
        
        # Get available collections for the jurisdiction
        jurisdiction = "india" if request.jurisdiction == "in" else "international"
        jurisdiction_prefix = "in_" if jurisdiction == "india" else "intl_"
        
        # Query Qdrant for available collections with the jurisdiction prefix
        try:
            from qdrant_client import QdrantClient
            qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
            all_collections = qdrant_client.get_collections()
            available_domains = [
                collection.name.replace(jurisdiction_prefix, "")
                for collection in all_collections.collections
                if collection.name.startswith(jurisdiction_prefix)
            ]
            
            logger.info(f"Available domains for {jurisdiction}: {available_domains}")
            
            # Domain-hint mapping for lightweight routing (boost, not filter)
            DOMAIN_HINTS = {
                # GI domain
                "gi": ["geographical indication", "gi", "geographical", "regional identity", "regional product", "origin product"],
                # Copyright domain  
                "copyright": ["copyright", "copyright act", "literary work", "artistic work", "musical work", "cinematograph"],
                # Trademarks domain
                "trademarks": ["trademark", "trade mark", "brand", "brand name", "logo", "service mark", "certification mark"],
                # Patents domain
                "patents": ["patent", "invention", "patentable", "novel", "non-obvious", "industrial application"],
                # Designs domain
                "designs": ["design", "industrial design", "visual design", "ornamental design", "aesthetic design"],
                # Plant variety domain
                "plant_variety": ["plant variety", "variety protection", "plant breeder", "farmers rights", "plant varieties"],
                # BDA domain
                "bda_abs": ["biodiversity", "biological diversity", "access benefit sharing", "abs", "genetic resource", "biological resource", "traditional knowledge digital library", "tkdl"],
                # Drugs and cosmetics domain
                "drugs_cosmetics": ["drug", "cosmetic", "ayurvedic medicine", "siddha medicine", "unani medicine", "formulation", "medicine", "pharmaceutical"],
                # FSSAI domain
                "fssai": ["fssai", "food safety", "ayurveda aahar", "nutraceutical", "food regulation", "food standard"],
            }
            
            # Detect domain hints from query
            query_lower = request.query.lower()
            boosted_domains = set()
            for domain, keywords in DOMAIN_HINTS.items():
                if domain in available_domains:
                    for keyword in keywords:
                        if keyword in query_lower:
                            boosted_domains.add(domain)
                            logger.info(f"Domain hint detected: '{keyword}' -> {domain} (boost 3x)")
                            break
            
            if not boosted_domains:
                logger.info("No domain hints detected, using default retrieval (all domains equal weight)")
                logger.info(f"FALLBACK: Keyword routing did not match any domain - query: '{request.query[:100]}...'")
            else:
                logger.info(f"Boosted domains: {list(boosted_domains)}")
            
            # Retrieve from all available domains with domain-aware boost
            all_retrieval_results = []
            for domain in available_domains:
                logger.info(f"Retrieving from domain: {domain}")
                domain_results = hybrid_retriever.retrieve(
                    query=request.query,
                    query_embedding=query_embedding,
                    jurisdiction=jurisdiction,
                    domain=domain,
                    top_k=10,
                    enable_rerank=False  # Disabled cross-encoder reranking, using dense/sparse fusion instead
                )
                
                # Apply domain-hint boost (3x) to results from boosted domains
                if domain in boosted_domains:
                    for result in domain_results:
                        if hasattr(result, 'rerank_score'):
                            result.rerank_score *= 3.0
                            logger.info(f"Domain boost applied: domain={domain}, chunk_id={result.chunk_id[:8]}..., original_score={result.rerank_score/3.0:.4f}, boosted_score={result.rerank_score:.4f}")
                
                all_retrieval_results.extend(domain_results)
                logger.info(f"Retrieved {len(domain_results)} results from {domain}")
            
            logger.info(f"Total results from all domains: {len(all_retrieval_results)}")
            
            # Check for explicit clause/section reference and force include via direct lookup
            explicit_ref = _extract_explicit_reference(request.query)
            if explicit_ref:
                logger.info(f"Query contains explicit reference: {explicit_ref}")
                logger.info(f"Running direct lookup for clause/section: {explicit_ref}")
                
                from qdrant_client import QdrantClient
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
                
                # Scope direct lookup to boosted domains if hints detected, otherwise all domains
                lookup_domains = boosted_domains if boosted_domains else available_domains
                logger.info(f"Direct lookup scoped to domains: {list(lookup_domains)}")
                
                # Direct lookup in scoped domains for the explicit reference
                for domain in lookup_domains:
                    collection_name = f"{jurisdiction_prefix}{domain}"
                    try:
                        # Try clause match first
                        filter_clause = Filter(
                            must=[FieldCondition(
                                key="clause",
                                match=MatchValue(value=explicit_ref)
                            )]
                        )
                        
                        search_results = qdrant_client.search(
                            collection_name=collection_name,
                            query_vector=query_embedding,
                            query_filter=filter_clause,
                            limit=5,
                            with_payload=True
                        )
                        
                        if search_results:
                            logger.info(f"Direct lookup found {len(search_results)} results for clause={explicit_ref} in {collection_name}")
                            for result in search_results:
                                payload = result.payload
                                # Create RerankedResult with high score to ensure inclusion
                                direct_result = RerankedResult(
                                    chunk_id=result.id,
                                    source_id=payload.get('source_id', ''),
                                    section=payload.get('section', ''),
                                    article=payload.get('article', ''),
                                    content=payload.get('content', ''),
                                    original_score=0.0,
                                    rerank_score=999.0,  # Force high score for inclusion (sentinel value, not a real similarity score)
                                    version_hash=payload.get('version_hash', ''),
                                    jurisdiction=payload.get('jurisdiction', jurisdiction),
                                    domain=payload.get('domain', domain),
                                    metadata=payload.get('metadata', {}),
                                    clause=payload.get('clause', '')
                                )
                                all_retrieval_results.append(direct_result)
                                logger.info(f"  Force-included chunk_id={result.id[:8]}..., clause={payload.get('clause', '')}, score=999.0")
                    except Exception as e:
                        logger.warning(f"Direct lookup failed for {collection_name}: {e}")
                
                logger.info(f"Total results after direct lookup: {len(all_retrieval_results)}")
            
            # Sort all results by rerank_score (if available) or score
            def get_sort_key(result):
                if hasattr(result, 'rerank_score'):
                    return result.rerank_score
                elif hasattr(result, 'score'):
                    return result.score
                else:
                    return 0.0
            
            # Per-domain guaranteed slots with reserved slots for boosted domains
            # Instead of pooling all domains and taking global top-10, reserve slots for boosted domain
            domain_results_map = {}  # domain -> list of results
            for result in all_retrieval_results:
                domain = result.domain if hasattr(result, 'domain') else result.get('domain', 'unknown')
                if domain not in domain_results_map:
                    domain_results_map[domain] = []
                domain_results_map[domain].append(result)
            
            # Sort each domain's results by score
            for domain in domain_results_map:
                domain_results_map[domain].sort(key=get_sort_key, reverse=True)
            
            final_candidates = []
            min_score_floor = 0.5  # Minimum relevance floor
            
            # Extract the term being defined for "What is X" queries
            definition_term = None
            definition_term_normalized = None
            import re
            definition_match = re.search(r'what\s+is\s+(?:a\s+)?(.+?)(?:\s+under|$)', request.query, re.IGNORECASE)
            if definition_match:
                definition_term = definition_match.group(1).strip().lower()
                # Normalize: replace spaces with underscores for clause matching
                definition_term_normalized = definition_term.replace(' ', '_')
                logger.info(f"Definition query detected, looking for clause matching term: '{definition_term}' (normalized: '{definition_term_normalized}')")
            
            # RESERVE 3 slots for boosted domain (if it has results)
            if boosted_domains:
                for domain in boosted_domains:
                    if domain in domain_results_map:
                        domain_results = domain_results_map[domain]
                        
                        # For definition queries, force-include matching clause if found
                        if definition_term:
                            for result in domain_results:
                                clause = result.clause if hasattr(result, 'clause') else result.get('clause', '')
                                clause_lower = clause.lower()
                                # Match both space-separated and underscore-separated versions
                                if (definition_term in clause_lower or 
                                    definition_term_normalized in clause_lower) and get_sort_key(result) >= min_score_floor:
                                    if result not in final_candidates:
                                        final_candidates.append(result)
                                        logger.info(f"Boosted domain {domain}: FORCE-INCLUDED definition clause={clause}, score={get_sort_key(result):.4f}")
                                else:
                                    # Debug: log why it didn't match
                                    logger.debug(f"Clause match check: clause='{clause_lower}', term='{definition_term}', norm='{definition_term_normalized}', match=False")
                        
                        # Take top 3 from boosted domain (reserved slots), excluding already-added
                        boosted_top = []
                        for r in domain_results[:5]:  # Look at top 5 to find 3 valid ones
                            if r not in final_candidates and get_sort_key(r) >= min_score_floor:
                                boosted_top.append(r)
                                if len(boosted_top) >= 3:
                                    break
                        
                        final_candidates.extend(boosted_top)
                        logger.info(f"Boosted domain {domain}: RESERVED {len(boosted_top)} additional slots (top from above floor {min_score_floor})")
            
            # Take top-1 from each non-boosted domain to fill remaining slots
            for domain, results in domain_results_map.items():
                if domain not in boosted_domains:
                    # Take top 1 from each other domain
                    domain_top = [r for r in results[:1] if get_sort_key(r) >= min_score_floor and r not in final_candidates]
                    final_candidates.extend(domain_top)
                    logger.info(f"Domain {domain}: took {len(domain_top)} result (top 1 above floor {min_score_floor})")
            
            # Sort all candidates globally and cap at 10
            final_candidates.sort(key=get_sort_key, reverse=True)
            retrieval_results = final_candidates[:10]
            logger.info(f"Final top-10 after per-domain selection: {len(retrieval_results)} results from {len(domain_results_map)} domains")
        except Exception as e:
            logger.error(f"Error querying Qdrant for available collections: {e}")
            # Fallback to patents domain if Qdrant query fails
            logger.warning("Falling back to patents domain")
            retrieval_results = hybrid_retriever.retrieve(
                query=request.query,
                query_embedding=query_embedding,
                jurisdiction=jurisdiction,
                domain="patents",
                top_k=10,
                enable_rerank=False
            )
        
        logger.info(f"Retrieved {len(retrieval_results)} documents")
        logger.info(f"Retrieval result types: {[type(r).__name__ for r in retrieval_results[:3]]}")
        for i, r in enumerate(retrieval_results[:3]):
            logger.info(f"  Result {i}: type={type(r).__name__}, has_rerank_score={hasattr(r, 'rerank_score')}, has_score={hasattr(r, 'score')}")
            if hasattr(r, 'rerank_score'):
                logger.info(f"    rerank_score={r.rerank_score:.4f}")
            if hasattr(r, 'score'):
                logger.info(f"    score={r.score:.4f}")
        
        # Step 3: If no results found, return abstention response
        if not retrieval_results:
            logger.warning("No retrieval results found - returning abstention response")
            return QueryResponse(
                answer="I could not find relevant information in the corpus to answer your question. This may be because the topic is outside the current scope, or the specific information is not available in the indexed documents. Please try rephrasing your question or contact the appropriate regulatory authority directly.",
                citations=[],
                confidence_score=0.0,
                formulation_type=formulation_type,
                jurisdiction=request.jurisdiction,
                model_used="N/A",
                provider_used=request.provider or default_provider
            )
        
        # Deduplicate retrieval results by chunk_id
        logger.info(f"Before dedup: {len(retrieval_results)} results")
        for i, result in enumerate(retrieval_results):
            chunk_id = result.chunk_id if hasattr(result, 'chunk_id') else result.get('chunk_id', 'N/A')
            clause = result.clause if hasattr(result, 'clause') else result.get('clause', 'N/A')
            logger.info(f"  Before dedup {i}: chunk_id={chunk_id[:8] if chunk_id != 'N/A' else 'N/A'}..., clause={clause}")
        
        seen_chunk_ids = set()
        deduplicated_results = []
        for result in retrieval_results:
            chunk_id = result.chunk_id if hasattr(result, 'chunk_id') else result.get('chunk_id', '')
            if chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                deduplicated_results.append(result)
        
        logger.info(f"After dedup: {len(deduplicated_results)} unique chunks")
        for i, result in enumerate(deduplicated_results):
            chunk_id = result.chunk_id if hasattr(result, 'chunk_id') else result.get('chunk_id', 'N/A')
            clause = result.clause if hasattr(result, 'clause') else result.get('clause', 'N/A')
            logger.info(f"  After dedup {i}: chunk_id={chunk_id[:8] if chunk_id != 'N/A' else 'N/A'}..., clause={clause}")
        
        # Step 4: Generate answer using LLM provider
        provider_name = request.provider or default_provider
        llm_provider = llm_config.get_provider(provider_name)
        
        # Build context from retrieved documents with clause/section metadata
        context = "\n\n".join([
            f"Section {result.section}, Clause {result.clause}: {result.content}"
            for result in deduplicated_results[:5]
        ])
        
        logger.info(f"Context built from {len(deduplicated_results[:5])} chunks")
        logger.info(f"Context text:\n{context}")
        
        prompt = f"""Answer the user's question directly using the provided context.
Each document includes its section/clause identifier in parentheses.
Provide a clear, concise answer without introductory phrases like "Based on the context" or "According to the documents".
Only say "answer not in context" if no document contains relevant information for the question.

Context:
{context}

Question: {request.query}

Answer:"""
        
        logger.info(f"Full prompt sent to LLM:\n{prompt}")
        
        llm_response = await llm_provider.generate(prompt)
        generated_answer = llm_response.content
        
        logger.info(f"Generated answer using {provider_name}")
        logger.info(f"Raw LLM answer: {generated_answer}")
        
        # Step 5: Process through citation engine
        retrieved_chunks = [
            {
                "source_id": result.source_id,
                "content": result.content,
                "metadata": result.metadata,
                "chunk_id": result.chunk_id,
                "section": result.section,
                "article": result.article,
                "version_hash": result.version_hash,
                "clause": result.clause,
                "rerank_score": result.rerank_score  # Include rerank_score for confidence scoring
            }
            for result in deduplicated_results
        ]
        
        logger.info(f"Passing {len(retrieved_chunks)} chunks to citation engine")
        for i, chunk in enumerate(retrieved_chunks[:5]):
            logger.info(f"  Chunk {i}: chunk_id={chunk['chunk_id'][:8] if chunk.get('chunk_id') else 'N/A'}..., content='{chunk['content'][:100]}...'")
        
        citation_result = citation_engine.process_response(
            generated_text=generated_answer,
            retrieved_chunks=retrieved_chunks
        )
        
        # Step 6: Check if response should be rejected due to citation requirements
        if citation_result['should_reject']:
            logger.warning(f"Response rejected: {citation_result['reject_reason']}")
            abstention_message = citation_engine.confidence_scorer.get_abstention_message(
                citation_result['confidence_score']
            )
            return QueryResponse(
                answer=abstention_message,
                citations=[],
                confidence_score=citation_result['confidence_score'].overall_confidence,
                formulation_type=formulation_type,
                jurisdiction=request.jurisdiction,
                model_used=llm_response.model,
                provider_used=provider_name
            )
        
        # Step 7: Annotate response with citations
        final_answer = citation_engine.annotate_response(
            generated_text=generated_answer,
            processed_result=citation_result
        )
        
        # Step 8: Build citation list for response
        citations_list = []
        for mapping in citation_result['citation_mappings']:
            if mapping.is_supported and mapping.citations:
                for citation in mapping.citations:
                    citations_list.append({
                        "source_id": citation.source_id,
                        "section": citation.section,
                        "article": citation.article,
                        "confidence": citation.confidence
                    })
        
        return QueryResponse(
            answer=final_answer,
            citations=citations_list,
            confidence_score=citation_result['confidence_score'].overall_confidence,
            formulation_type=formulation_type,
            jurisdiction=request.jurisdiction,
            model_used=llm_response.model,
            provider_used=provider_name
        )
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: QueryRequest):
    """
    Chat endpoint - streaming variant of query for conversational interface
    """
    # TODO: Implement streaming chat endpoint
    return {"message": "Streaming chat endpoint not yet implemented"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
