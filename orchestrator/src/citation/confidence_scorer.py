"""
Confidence Scorer for assessing retrieval and citation confidence
Implements safe abstention per ARCHITECTURE.md
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from .citation_mapper import CitationMapping, Citation

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Represents confidence score for a response"""
    overall_confidence: float
    retrieval_confidence: float
    citation_confidence: float
    should_abstain: bool
    reason: Optional[str] = None
    breakdown: Dict[str, float] = None


class ConfidenceScorer:
    """
    Scores confidence for responses and determines when to abstain
    
    Per ARCHITECTURE.md: System must abstain when retrieval confidence is insufficient
    This prevents hallucination when relevant content is not found
    """

    def __init__(
        self,
        min_retrieval_confidence: float = 0.6,
        min_citation_confidence: float = 0.7,
        min_overall_confidence: float = 0.65
    ):
        """
        Initialize confidence scorer
        
        Args:
            min_retrieval_confidence: Minimum average retrieval score
            min_citation_confidence: Minimum citation mapping confidence
            min_overall_confidence: Minimum overall confidence to respond
        """
        self.min_retrieval_confidence = min_retrieval_confidence
        self.min_citation_confidence = min_citation_confidence
        self.min_overall_confidence = min_overall_confidence
        
        logger.info(
            f"ConfidenceScorer initialized: "
            f"retrieval_threshold={min_retrieval_confidence}, "
            f"citation_threshold={min_citation_confidence}, "
            f"overall_threshold={min_overall_confidence}"
        )

    def score_response(
        self,
        retrieved_chunks: List,
        citation_mappings: List[CitationMapping],
        num_claims: int
    ) -> ConfidenceScore:
        """
        Score overall confidence for a response
        
        Args:
            retrieved_chunks: Retrieved chunks with scores
            citation_mappings: Citation mappings from mapper
            num_claims: Total number of claims
            
        Returns:
            Confidence score with abstention decision
        """
        # Score retrieval quality
        retrieval_score = self._score_retrieval(retrieved_chunks)
        
        # Score citation quality
        citation_score = self._score_citations(citation_mappings, num_claims)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall(
            retrieval_score,
            citation_score
        )
        
        # Determine if should abstain
        should_abstain, reason = self._should_abstain(
            overall_confidence,
            retrieval_score,
            citation_score
        )
        
        # Breakdown
        breakdown = {
            'retrieval': retrieval_score,
            'citation': citation_score,
            'overall': overall_confidence
        }
        
        score = ConfidenceScore(
            overall_confidence=overall_confidence,
            retrieval_confidence=retrieval_score,
            citation_confidence=citation_score,
            should_abstain=should_abstain,
            reason=reason,
            breakdown=breakdown
        )
        
        logger.info(
            f"Confidence score: overall={overall_confidence:.2f}, "
            f"retrieval={retrieval_score:.2f}, citation={citation_score:.2f}, "
            f"abstain={should_abstain}"
        )
        
        return score

    def _score_retrieval(self, retrieved_chunks: List) -> float:
        """
        Score retrieval quality based on chunk scores
        
        Args:
            retrieved_chunks: Retrieved chunks with scores
            
        Returns:
            Retrieval confidence score (0-1)
        """
        if not retrieved_chunks:
            return 0.0
        
        # Average of top chunk scores
        scores = [c.score for c in retrieved_chunks[:5]]  # Top 5
        avg_score = sum(scores) / len(scores)
        
        # Boost if we have enough high-quality chunks
        high_quality_count = sum(1 for s in scores if s >= 0.8)
        if high_quality_count >= 2:
            avg_score = min(avg_score * 1.1, 1.0)
        
        return avg_score

    def _score_citations(self, citation_mappings: List[CitationMapping], num_claims: int) -> float:
        """
        Score citation mapping quality
        
        Args:
            citation_mappings: Citation mappings
            num_claims: Total number of claims
            
        Returns:
            Citation confidence score (0-1)
        """
        if not citation_mappings:
            return 0.0
        
        # Coverage: percentage of claims with citations
        supported_count = sum(1 for m in citation_mappings if m.is_supported)
        coverage = supported_count / len(citation_mappings)
        
        # Average citation confidence
        citable_mappings = [m for m in citation_mappings if m.is_supported]
        if not citable_mappings:
            return 0.0
        
        avg_citation_confidence = 0.0
        total_citations = 0
        
        for mapping in citable_mappings:
            if mapping.citations:
                avg_conf = sum(c.confidence for c in mapping.citations) / len(mapping.citations)
                avg_citation_confidence += avg_conf
                total_citations += 1
        
        if total_citations > 0:
            avg_citation_confidence /= total_citations
        
        # Combine coverage and confidence
        citation_score = (coverage * 0.6) + (avg_citation_confidence * 0.4)
        
        return citation_score

    def _calculate_overall(self, retrieval_score: float, citation_score: float) -> float:
        """
        Calculate overall confidence from components
        
        Args:
            retrieval_score: Retrieval confidence
            citation_score: Citation confidence
            
        Returns:
            Overall confidence score (0-1)
        """
        # Weight retrieval slightly higher as it's the foundation
        overall = (retrieval_score * 0.6) + (citation_score * 0.4)
        
        return overall

    def _should_abstain(
        self,
        overall_confidence: float,
        retrieval_score: float,
        citation_score: float
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if system should abstain from responding
        
        Per ARCHITECTURE.md: Abstain when retrieval confidence is insufficient
        
        Args:
            overall_confidence: Overall confidence score
            retrieval_score: Retrieval confidence
            citation_score: Citation confidence
            
        Returns:
            Tuple of (should_abstain, reason)
        """
        reasons = []
        
        # Check overall threshold
        if overall_confidence < self.min_overall_confidence:
            reasons.append(f"Overall confidence {overall_confidence:.2f} below threshold {self.min_overall_confidence}")
        
        # Check retrieval threshold (per ARCHITECTURE.md)
        if retrieval_score < self.min_retrieval_confidence:
            reasons.append(f"Retrieval confidence {retrieval_score:.2f} below threshold {self.min_retrieval_confidence}")
        
        # Check citation threshold
        if citation_score < self.min_citation_confidence:
            reasons.append(f"Citation confidence {citation_score:.2f} below threshold {self.min_citation_confidence}")
        
        should_abstain = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else None
        
        return should_abstain, reason

    def get_abstention_message(self, confidence_score: ConfidenceScore) -> str:
        """
        Generate abstention message for user
        
        Args:
            confidence_score: Confidence score object
            
        Returns:
            Abstention message
        """
        if not confidence_score.should_abstain:
            return ""
        
        base_message = (
            "I cannot provide a confident answer to this question based on the available documents. "
            "This is not legal advice - please consult with a qualified legal professional or "
            "the All India Institute of Ayurveda for specific guidance."
        )
        
        if confidence_score.reason:
            base_message += f"\n\nReason: {confidence_score.reason}"
        
        return base_message

    def adjust_for_corpus_status(
        self,
        confidence_score: ConfidenceScore,
        pending_review_chunks: int,
        total_chunks: int
    ) -> ConfidenceScore:
        """
        Adjust confidence based on corpus review status
        
        Per ARCHITECTURE.md: Unreviewed content is treated as lower-confidence
        
        Args:
            confidence_score: Original confidence score
            pending_review_chunks: Number of chunks pending review
            total_chunks: Total chunks used
            
        Returns:
            Adjusted confidence score
        """
        if total_chunks == 0:
            return confidence_score
        
        pending_ratio = pending_review_chunks / total_chunks
        
        # Reduce confidence if significant content is pending review
        if pending_ratio > 0.5:
            # More than 50% pending - significant reduction
            confidence_score.overall_confidence *= 0.7
            confidence_score.reason = (
                f"{pending_ratio:.0%} of sources are pending review; "
                f"confidence reduced accordingly"
            )
        elif pending_ratio > 0.2:
            # 20-50% pending - moderate reduction
            confidence_score.overall_confidence *= 0.85
        
        # Re-evaluate abstention
        should_abstain, reason = self._should_abstain(
            confidence_score.overall_confidence,
            confidence_score.retrieval_confidence,
            confidence_score.citation_confidence
        )
        
        confidence_score.should_abstain = should_abstain
        if reason:
            confidence_score.reason = reason
        
        return confidence_score
