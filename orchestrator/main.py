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
from src.security.prompt_template import prompt_template
import re

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


class ClassificationRequest(BaseModel):
    """Request model for classification endpoint"""
    user_input: str
    existing_state: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None


class ClassificationResponse(BaseModel):
    """Response model for classification endpoint"""
    formulation_class: Optional[str]
    status: str  # "classified", "needs_clarification", "escalated", "incomplete", "suspicious_input"
    current_step: Optional[str] = None
    clarifying_question: Optional[str] = None
    collected_slots: Optional[Dict[str, Any]] = None
    requires_escalation: bool
    escalation_reason: Optional[str] = None
    flags: Optional[List[str]] = None
    failed_slot: Optional[str] = None


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


def _extract_entities(text: str) -> set:
    """
    Extract only factual entities that must be preserved exactly in Pass 2.
    Returns a set of normalized entities for safety comparison.
    
    Focuses on: citation brackets and numbers only.
    NOT: proper nouns, common words, or general NLP entities.
    """
    entities = set()
    
    # Extract citation brackets verbatim - these must appear exactly unchanged
    # Matches: [Section 1-11, Clause 2(1)(m)] or similar patterns
    citation_brackets = re.findall(r'\[[^\]]+\]', text)
    entities.update(citation_brackets)
    
    # Extract all numbers (including section numbers like 3(p), years like 1970, etc.)
    numbers = re.findall(r'\b\d+\b', text)
    entities.update(numbers)
    
    return entities


async def rewrite_pass2(
    original_answer: str,
    user_query: str,
    llm_provider
) -> str:
    """
    Pass 2: Rewrite for plain-language clarity without altering facts.
    
    If the rewrite introduces new entities/claims not in the original,
    return the original answer unchanged (safety fallback).
    """
    original_entities = _extract_entities(original_answer)
    
    # Extract citation brackets from original for verification
    original_citations = re.findall(r'\[[^\]]+\]', original_answer)
    
    rewrite_prompt = f"""You are rewriting a legal information answer for clarity. Your audience is AYUSH startup founders, practitioners, and MSME owners.

ORIGINAL ANSWER (do not change facts):
{original_answer}

USER QUESTION:
{user_query}

REWRITE INSTRUCTIONS:
- Restructure to start with a direct answer in 1-2 plain-language sentences, then follow with the citation-backed explanation.
- Rephrase for plain-language clarity — explain legal jargon naturally.
- DO NOT add any new factual claims, numbers, or legal citations not present in the original answer.
- DO NOT remove any factual claims or citations from the original answer.
- Keep all citation brackets [like this] exactly as they appear in the original answer — do not modify them.

Rewritten answer:"""
    
    try:
        rewrite_response = await llm_provider.generate(rewrite_prompt)
        rewritten_answer = rewrite_response.content
        
        # Safety check: extract entities from rewritten answer
        rewritten_entities = _extract_entities(rewritten_answer)
        
        # Check for new entities (hallucination detection)
        new_entities = rewritten_entities - original_entities
        
        # Check for missing entities (removal detection)
        missing_entities = original_entities - rewritten_entities
        
        # Check if citation brackets are preserved verbatim
        rewritten_citations = re.findall(r'\[[^\]]+\]', rewritten_answer)
        citations_match = set(original_citations) == set(rewritten_citations)
        
        if new_entities:
            logger.warning(f"Pass 2 introduced new entities, discarding rewrite: {new_entities}")
            return original_answer
        
        if missing_entities:
            logger.warning(f"Pass 2 removed entities, discarding rewrite: {missing_entities}")
            return original_answer
        
        if not citations_match:
            logger.warning(f"Pass 2 modified citation brackets, discarding rewrite. Original: {original_citations}, Rewritten: {rewritten_citations}")
            return original_answer
        
        logger.info("Pass 2 rewrite accepted")
        return rewritten_answer
        
    except Exception as e:
        logger.error(f"Pass 2 rewrite failed: {e}, using original answer")
        return original_answer


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Main query endpoint - orchestrates retrieval, classification, and generation
    Flow: formulation_classifier → hybrid_retriever → llm_provider → citation_engine → confidence_scorer
    """
    try:
        logger.info(f"Received query: {request.query[:100]}... (jurisdiction: {request.jurisdiction})")
        
        # Step 1: Classify formulation type
        # Use provided formulation_type if available (from gateway multi-turn classification)
        # Otherwise, run classification inline
        if request.formulation_type:
            formulation_type = request.formulation_type
            logger.info(f"Using provided formulation_type: {formulation_type}")
        else:
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
                # International domains
                "trips": ["trips", "trips agreement", "wto trips", "trade-related intellectual property rights"],
                "pct": ["pct", "patent cooperation treaty", "international patent application"],
                "budapest": ["budapest", "budapest treaty", "microorganism", "biological material deposit"],
                "madrid": ["madrid", "madrid system", "international trademark registration"],
                "hague": ["hague", "hague system", "industrial design registration"],
                "cbd_nagoya": ["cbd", "nagoya", "nagoya protocol", "genetic resources", "access benefit sharing"],
                "wipo_gratk": ["gratk", "traditional knowledge", "genetic resources", "traditional knowledge expressions"],
                "herbal_market_access": ["herbal", "traditional herbal", "herbal medicine", "eu herbal directive"],
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
            
            # Extract the term being defined for "What is X" queries (do this early for use in retrieval)
            definition_term = None
            definition_term_normalized = None
            import re
            # Only match "What is X" or "What is a X", not "What are X"
            definition_match = re.search(r'what\s+is\s+(?:a\s+)?([a-z_]+(?:\s+[a-z_]+)?)(?:\s+under|$)', request.query, re.IGNORECASE)
            if definition_match:
                definition_term = definition_match.group(1).strip().lower()
                # Normalize: replace spaces with underscores for clause matching
                definition_term_normalized = definition_term.replace(' ', '_')
                # Only proceed if the term looks like a single concept (1-2 words)
                if len(definition_term.split()) <= 2:
                    logger.info(f"Definition query detected, looking for clause matching term: '{definition_term}' (normalized: '{definition_term_normalized}')")
                else:
                    # Reset if it's a complex phrase (like "patentability criteria")
                    definition_term = None
                    definition_term_normalized = None
            
            # Retrieve from all available domains with domain-aware boost
            all_retrieval_results = []
            for domain in available_domains:
                logger.info(f"Retrieving from domain: {domain}")
                try:
                    domain_results = hybrid_retriever.retrieve(
                        query=request.query,
                        query_embedding=query_embedding,
                        jurisdiction=jurisdiction,
                        domain=domain,
                        top_k=10,
                        enable_rerank=False  # Disabled cross-encoder reranking, using dense/sparse fusion instead
                    )
                    logger.info(f"Successfully retrieved {len(domain_results)} results from domain {domain}")
                except Exception as e:
                    logger.error(f"Exception while retrieving from domain {domain}: {e}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    domain_results = []
                
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
            
            # Dedupe each domain's results by chunk_id AND content before selecting top-N
            for domain in domain_results_map:
                seen_chunk_ids = set()
                seen_content = set()
                deduped_results = []
                for result in domain_results_map[domain]:
                    chunk_id = result.chunk_id if hasattr(result, 'chunk_id') else result.get('chunk_id', '')
                    content = result.content if hasattr(result, 'content') else result.get('content', '')
                    content_normalized = content.strip()[:100]  # Use first 100 chars for comparison
                    if chunk_id not in seen_chunk_ids and content_normalized not in seen_content:
                        seen_chunk_ids.add(chunk_id)
                        seen_content.add(content_normalized)
                        deduped_results.append(result)
                original_count = len(domain_results_map[domain])
                domain_results_map[domain] = deduped_results
                logger.info(f"Domain {domain}: deduped from {original_count} to {len(deduped_results)} unique chunks")
            
            # Sort each domain's results by score
            for domain in domain_results_map:
                domain_results_map[domain].sort(key=get_sort_key, reverse=True)
            
            final_candidates = []
            min_score_floor = 0.5  # Minimum relevance floor
                

            
            # RESERVE 3 slots for boosted domain (if it has results)
            if boosted_domains:
                for domain in boosted_domains:
                    if domain in domain_results_map:
                        domain_results = domain_results_map[domain]
                        
                        # Force-include for definition queries: look for chunk with matching clause
                        # Search through all results, not just top ones
                        # Only apply if we have a valid single-concept definition term
                        if definition_term and definition_term_normalized and len(definition_term.split()) <= 2 and domain_results:
                            definition_match = None
                            for r in domain_results:
                                clause = r.clause if hasattr(r, 'clause') else r.get('clause', '')
                                clause_lower = clause.lower()
                                logger.info(f"Checking clause: '{clause}' (lower: '{clause_lower}') against term: '{definition_term_normalized}'")
                                # Check if clause contains the normalized definition term
                                if definition_term_normalized in clause_lower:
                                    definition_match = r
                                    logger.info(f"Boosted domain {domain}: FOUND definition chunk with clause={clause} matching term '{definition_term_normalized}'")
                                    break
                            
                            if definition_match and definition_match not in final_candidates:
                                final_candidates.append(definition_match)
                                logger.info(f"Boosted domain {domain}: FORCE-INCLUDED definition chunk, clause={definition_match.clause if hasattr(definition_match, 'clause') else definition_match.get('clause', '')}, score={get_sort_key(definition_match):.4f}")
                            else:
                                logger.info(f"Boosted domain {domain}: No definition chunk found for term '{definition_term_normalized}'")
                        
                        # Take top 3 from boosted domain (reserved slots), excluding already-added
                        boosted_top = []
                        for r in domain_results[:5]:  # Look at top 5 to find 3 valid ones
                            if r not in final_candidates and get_sort_key(r) >= min_score_floor:
                                boosted_top.append(r)
                                if len(boosted_top) >= 3:
                                    break
                        
                        final_candidates.extend(boosted_top)
                        logger.info(f"Boosted domain {domain}: RESERVED {len(boosted_top)} slots (top from above floor {min_score_floor})")
            
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
        # Include top 10 chunks to provide more surrounding context for better explanation
        context = "\n\n".join([
            f"Section {result.section}, Clause {result.clause}: {result.content}"
            for result in deduplicated_results[:10]
        ])
        
        logger.info(f"Context built from {len(deduplicated_results[:10])} chunks")
        logger.info(f"Context text:\n{context}")
        
        # Use the prompt template for generation
        prompt = prompt_template.build_prompt(
            "generation",
            user_input=request.query,
            context=context
        )
        
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
        
        # Step 9: Pass 2 rewrite for plain-language clarity
        final_answer = await rewrite_pass2(
            original_answer=final_answer,
            user_query=request.query,
            llm_provider=llm_provider
        )
        
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


@app.post("/classify")
async def classify(request: ClassificationRequest):
    """
    Formulation classification endpoint
    Supports multi-turn classification with session state
    
    Args:
        request: Classification request with user input and optional existing state
    
    Returns:
        Classification result with formulation class or clarifying question
    """
    try:
        logger.info(f"Received classification request: user_input='{request.user_input}', existing_state={request.existing_state}")
        
        # Call formulation classifier
        session_context = request.session_context or {}
        result = await formulation_classifier.classify(
            user_input=request.user_input,
            session_context=session_context,
            existing_state=request.existing_state
        )
        
        logger.info(f"Classification result: status={result.get('status')}, formulation_class={result.get('formulation_class')}")
        
        return ClassificationResponse(**result)
        
    except Exception as e:
        logger.error(f"Classification failed: {e}")
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
