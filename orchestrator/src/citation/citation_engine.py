"""
Citation Engine - Main orchestration for citation and confidence
Per AGENTS.md constraint #1: No answer without citable source
"""

import logging
from typing import List, Dict, Optional
from .claim_extractor import ClaimExtractor, Claim
from .citation_mapper import CitationMapper, CitationMapping
from .confidence_scorer import ConfidenceScorer, ConfidenceScore

logger = logging.getLogger(__name__)


class CitationEngine:
    """
    Main citation engine orchestrating claim extraction, mapping, and confidence scoring
    
    Per AGENTS.md #1: This engine rejects unmapped sentences - never bypassed
    Per ARCHITECTURE.md: Implements safe abstention when confidence is insufficient
    """

    def __init__(
        self,
        claim_extractor: Optional[ClaimExtractor] = None,
        citation_mapper: Optional[CitationMapper] = None,
        confidence_scorer: Optional[ConfidenceScorer] = None
    ):
        """
        Initialize citation engine
        
        Args:
            claim_extractor: Claim extractor instance
            citation_mapper: Citation mapper instance
            confidence_scorer: Confidence scorer instance
        """
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.citation_mapper = citation_mapper or CitationMapper(similarity_threshold=0.3)
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        
        logger.info("CitationEngine initialized")

    def process_response(
        self,
        generated_text: str,
        retrieved_chunks: List,
        pending_review_chunks: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Process a generated response through the citation pipeline
        
        Args:
            generated_text: Generated response text
            retrieved_chunks: Retrieved chunks with metadata
            pending_review_chunks: Number of chunks pending review (optional)
            
        Returns:
            Dictionary with citations, confidence, and recommendation
        """
        logger.info("Processing response through citation pipeline")
        
        # Step 1: Extract claims
        claims = self.claim_extractor.extract_claims(generated_text)
        logger.info(f"Extracted {len(claims)} claims")
        
        # Step 2: Map claims to chunks
        citation_mappings = self.citation_mapper.map_claims_to_chunks(
            claims=claims,
            retrieved_chunks=retrieved_chunks
        )
        logger.info(f"Mapped claims to chunks")
        
        # Step 3: Score confidence
        confidence_score = self.confidence_scorer.score_response(
            retrieved_chunks=retrieved_chunks,
            citation_mappings=citation_mappings,
            num_claims=len(claims)
        )
        
        # Step 4: Adjust for corpus review status if provided
        if pending_review_chunks is not None:
            confidence_score = self.confidence_scorer.adjust_for_corpus_status(
                confidence_score=confidence_score,
                pending_review_chunks=pending_review_chunks,
                total_chunks=len(retrieved_chunks)
            )
        
        # Step 5: Validate mapping completeness
        mapping_validation = self.citation_mapper.validate_mapping_completeness(
            citation_mappings
        )
        
        # Step 6: Determine final recommendation
        should_reject = mapping_validation['should_reject'] or confidence_score.should_abstain
        
        result = {
            'claims': claims,
            'citation_mappings': citation_mappings,
            'confidence_score': confidence_score,
            'mapping_validation': mapping_validation,
            'should_reject': should_reject,
            'reject_reason': (
                mapping_validation.get('unsupported_claim_ids') if mapping_validation['should_reject']
                else confidence_score.reason
            )
        }
        
        logger.info(
            f"Citation pipeline complete: reject={should_reject}, "
            f"confidence={confidence_score.overall_confidence:.2f}"
        )
        
        return result

    def annotate_response(
        self,
        generated_text: str,
        processed_result: Dict[str, any]
    ) -> str:
        """
        Annotate response with inline citations
        
        Args:
            generated_text: Original generated text
            processed_result: Result from process_response
            
        Returns:
            Annotated response with citations
        """
        if processed_result['should_reject']:
            # Return abstention message instead
            return self.confidence_scorer.get_abstention_message(
                processed_result['confidence_score']
            )
        
        citation_mappings = processed_result['citation_mappings']
        claims = processed_result['claims']
        annotated_text = generated_text
        
        # Add citations after each claim
        offset = 0
        for mapping in citation_mappings:
            if mapping.is_supported and mapping.citations:
                # Find the corresponding claim
                claim = next((c for c in claims if c.claim_id == mapping.claim_id), None)
                if claim:
                    # Format citation
                    citation_text = self.citation_mapper.format_citations(mapping)
                    
                    # Insert citation after claim
                    insert_pos = claim.end_pos + offset
                    annotated_text = (
                        annotated_text[:insert_pos] + 
                        f" {citation_text}" + 
                        annotated_text[insert_pos:]
                    )
                    offset += len(f" {citation_text}")
        
        return annotated_text

    def get_citation_report(self, processed_result: Dict[str, any]) -> Dict[str, any]:
        """
        Generate a detailed citation report
        
        Args:
            processed_result: Result from process_response
            
        Returns:
            Detailed citation report
        """
        confidence_score = processed_result['confidence_score']
        mapping_validation = processed_result['mapping_validation']
        
        report = {
            'overall_confidence': confidence_score.overall_confidence,
            'retrieval_confidence': confidence_score.retrieval_confidence,
            'citation_confidence': confidence_score.citation_confidence,
            'should_abstain': confidence_score.should_abstain,
            'abstain_reason': confidence_score.reason,
            'total_claims': mapping_validation['total_claims'],
            'supported_claims': mapping_validation['supported_claims'],
            'unsupported_claims': mapping_validation['unsupported_claims'],
            'unsupported_claim_ids': mapping_validation['unsupported_claim_ids'],
            'is_complete': mapping_validation['is_complete'],
            'citations': []
        }
        
        # Add individual citation details
        for mapping in processed_result['citation_mappings']:
            citation_info = {
                'claim_id': mapping.claim_id,
                'claim_text': mapping.claim_text,
                'is_supported': mapping.is_supported,
                'num_citations': len(mapping.citations),
                'citations': [
                    {
                        'source_id': c.source_id,
                        'section': c.section,
                        'article': c.article,
                        'confidence': c.confidence,
                        'span_match': c.span_match
                    }
                    for c in mapping.citations
                ]
            }
            report['citations'].append(citation_info)
        
        return report

    def enforce_citation_requirement(self, processed_result: Dict[str, any]) -> bool:
        """
        Enforce AGENTS.md constraint #1: No answer without citable source
        
        Args:
            processed_result: Result from process_response
            
        Returns:
            True if response passes citation requirement
        """
        # If mapping validation says reject, reject
        if processed_result['mapping_validation']['should_reject']:
            logger.warning(
                f"Citation requirement violated: "
                f"unsupported claims {processed_result['mapping_validation']['unsupported_claim_ids']}"
            )
            return False
        
        # If confidence scorer says abstain, reject
        if processed_result['confidence_score'].should_abstain:
            logger.warning(
                f"Confidence threshold not met: "
                f"{processed_result['confidence_score'].reason}"
            )
            return False
        
        return True
