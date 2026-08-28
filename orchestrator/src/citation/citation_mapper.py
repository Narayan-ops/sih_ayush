"""
Citation Mapper for mapping claims to retrieved chunks
Per AGENTS.md constraint #1: Every sentence must map to a retrieved chunk
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .claim_extractor import Claim

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a citation mapping"""
    claim_id: str
    chunk_id: str
    source_id: str
    section: str
    article: str
    version_hash: str
    confidence: float
    span_match: Optional[str] = None  # Exact text span that supports the claim


@dataclass
class CitationMapping:
    """Represents complete citation mapping for a response"""
    claim_id: str
    claim_text: str
    citations: List[Citation]
    is_supported: bool
    reason: Optional[str] = None


class CitationMapper:
    """
    Maps claims to retrieved chunks with source attribution
    
    Per AGENTS.md #1: Every generated sentence must map to a retrieved chunk
    with source_id, section/article, version_hash
    
    This mapper ensures unmapped sentences are rejected
    """

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize citation mapper
        
        Args:
            similarity_threshold: Minimum similarity for citation acceptance
        """
        self.similarity_threshold = similarity_threshold
        logger.info(f"CitationMapper initialized with threshold={similarity_threshold}")

    def map_claims_to_chunks(
        self,
        claims: List[Claim],
        retrieved_chunks: List
    ) -> List[CitationMapping]:
        """
        Map each claim to relevant retrieved chunks
        
        Args:
            claims: List of claims from claim extractor
            retrieved_chunks: List of retrieved chunks from retrieval engine
            
        Returns:
            List of citation mappings with support status
        """
        mappings = []
        
        for claim in claims:
            if not claim.requires_citation:
                # Non-citable claims are auto-supported
                mappings.append(CitationMapping(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    citations=[],
                    is_supported=True,
                    reason="Non-citable claim"
                ))
                continue
            
            # Find supporting chunks
            citations = self._find_supporting_chunks(claim, retrieved_chunks)
            
            # Determine if claim is supported
            is_supported = len(citations) > 0
            reason = None if is_supported else "No supporting chunk found above threshold"
            
            mapping = CitationMapping(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                citations=citations,
                is_supported=is_supported,
                reason=reason
            )
            
            mappings.append(mapping)
        
        logger.info(f"Mapped {len(mappings)} claims, {sum(1 for m in mappings if m.is_supported)} supported")
        return mappings

    def _find_supporting_chunks(
        self,
        claim: Claim,
        retrieved_chunks: List
    ) -> List[Citation]:
        """
        Find chunks that support a given claim
        
        Args:
            claim: Claim to find support for
            retrieved_chunks: Retrieved chunks to search
            
        Returns:
            List of citations supporting the claim
        """
        citations = []
        
        for chunk in retrieved_chunks:
            # Calculate similarity between claim and chunk
            similarity = self._calculate_similarity(claim.text, chunk.text)
            
            if similarity >= self.similarity_threshold:
                # Find exact span match if possible
                span_match = self._find_span_match(claim.text, chunk.text)
                
                citation = Citation(
                    claim_id=claim.claim_id,
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    section=chunk.section,
                    article=chunk.article,
                    version_hash=chunk.version_hash,
                    confidence=similarity,
                    span_match=span_match
                )
                
                citations.append(citation)
        
        # Sort by confidence
        citations.sort(key=lambda x: x.confidence, reverse=True)
        
        return citations

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts
        
        Simple word overlap-based similarity
        Can be enhanced with semantic similarity models
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        # Simple word overlap
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard = len(intersection) / len(union)
        
        # Boost for exact phrase matches
        if text1.lower() in text2.lower() or text2.lower() in text1.lower():
            jaccard = min(jaccard * 1.5, 1.0)
        
        return jaccard

    def _find_span_match(self, claim: str, chunk: str) -> Optional[str]:
        """
        Find exact text span in chunk that supports claim
        
        Args:
            claim: Claim text
            chunk: Chunk text
            
        Returns:
            Matching span or None
        """
        # Extract key terms from claim
        key_terms = self._extract_key_terms(claim)
        
        # Find sentences in chunk containing key terms
        chunk_sentences = chunk.split('. ')
        
        for sentence in chunk_sentences:
            term_count = sum(1 for term in key_terms if term.lower() in sentence.lower())
            if term_count >= len(key_terms) * 0.5:  # At least 50% of key terms
                return sentence.strip()
        
        return None

    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from text for span matching
        
        Args:
            text: Input text
            
        Returns:
            List of key terms
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'whom', 'when', 'where',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there'
        }
        
        words = text.lower().split()
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return key_terms

    def validate_mapping_completeness(self, mappings: List[CitationMapping]) -> Dict[str, any]:
        """
        Validate that all citable claims have citations
        
        Per AGENTS.md #1: Reject unmapped sentences
        
        Args:
            mappings: List of citation mappings
            
        Returns:
            Validation result
        """
        total_claims = len(mappings)
        supported_claims = sum(1 for m in mappings if m.is_supported)
        unsupported_claims = [m for m in mappings if not m.is_supported]
        
        is_complete = len(unsupported_claims) == 0
        
        return {
            'total_claims': total_claims,
            'supported_claims': supported_claims,
            'unsupported_claims': len(unsupported_claims),
            'unsupported_claim_ids': [m.claim_id for m in unsupported_claims],
            'is_complete': is_complete,
            'should_reject': not is_complete
        }

    def format_citations(self, mapping: CitationMapping) -> str:
        """
        Format citations for display
        
        Args:
            mapping: Citation mapping
            
        Returns:
            Formatted citation string
        """
        if not mapping.citations:
            return "No citation available"
        
        # Format the best citation
        best = mapping.citations[0]
        
        citation_text = f"[{best.source_id}, {best.section}, {best.article}]"
        
        if best.span_match:
            citation_text += f" - \"{best.span_match[:100]}...\""
        
        return citation_text
