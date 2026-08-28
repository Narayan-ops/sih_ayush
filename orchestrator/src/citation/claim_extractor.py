"""
Claim Extractor for extracting individual claims from generated text
Supports citation mapping per AGENTS.md constraint #1
"""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    """Represents a single claim in generated text"""
    text: str
    start_pos: int
    end_pos: int
    claim_id: str
    requires_citation: bool = True


class ClaimExtractor:
    """
    Extracts individual claims from generated text for citation mapping
    
    Per AGENTS.md #1: Every generated sentence must map to a retrieved chunk
    This extractor breaks down responses into claim units for citation
    """

    def __init__(self):
        """Initialize claim extractor"""
        logger.info("ClaimExtractor initialized")

    def extract_claims(self, text: str) -> List[Claim]:
        """
        Extract claims from generated text
        
        Args:
            text: Generated response text
            
        Returns:
            List of claims with positions
        """
        claims = []
        
        # Split by sentence boundaries
        sentences = self._split_sentences(text)
        
        current_pos = 0
        for idx, sentence in enumerate(sentences):
            if not sentence.strip():
                current_pos += len(sentence)
                continue
            
            start_pos = current_pos
            end_pos = current_pos + len(sentence)
            
            # Check if claim requires citation
            requires_citation = self._requires_citation(sentence)
            
            claim = Claim(
                text=sentence.strip(),
                start_pos=start_pos,
                end_pos=end_pos,
                claim_id=f"claim_{idx}",
                requires_citation=requires_citation
            )
            
            claims.append(claim)
            current_pos = end_pos
        
        logger.info(f"Extracted {len(claims)} claims from text")
        return claims

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using improved boundary detection
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Basic sentence splitting - can be enhanced with NLP libraries
        # This handles common cases: . ? ! followed by space and capital letter
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(pattern, text)
        
        # Handle edge cases where split might fail
        if len(sentences) == 1 and len(text) > 100:
            # Fallback: split by period-space
            sentences = text.split('. ')
        
        return sentences

    def _requires_citation(self, sentence: str) -> bool:
        """
        Determine if a sentence requires citation
        
        Per AGENTS.md #1: Most sentences require citations except:
        - Disclaimers
        - Greetings/pleasantries
        - Transition phrases
        
        Args:
            sentence: Sentence text
            
        Returns:
            True if citation required
        """
        sentence_lower = sentence.lower().strip()
        
        # Phrases that don't require citation
        non_citable_phrases = [
            'this is not legal advice',
            'please consult',
            'i cannot provide',
            'i am an ai assistant',
            'here is information',
            'based on the documents',
            'according to',
            'note that',
            'important to note',
            'you should',
            'it is recommended'
        ]
        
        # Check if it's a non-citable phrase
        for phrase in non_citable_phrases:
            if phrase in sentence_lower:
                return False
        
        # Check if it's purely transitional
        if len(sentence_lower) < 10:
            return False
        
        # Check if it's a question
        if sentence.strip().endswith('?'):
            return False
        
        # Default: requires citation
        return True

    def extract_key_claims(self, text: str, max_claims: int = 5) -> List[Claim]:
        """
        Extract only the most important claims for citation
        
        Args:
            text: Generated text
            max_claims: Maximum number of claims to extract
            
        Returns:
            Top claims requiring citation
        """
        all_claims = self.extract_claims(text)
        
        # Filter to only those requiring citation
        citable_claims = [c for c in all_claims if c.requires_citation]
        
        # If too many, prioritize by length (longer claims typically more substantive)
        citable_claims.sort(key=lambda x: len(x.text), reverse=True)
        
        return citable_claims[:max_claims]

    def validate_claim_coverage(self, text: str, mapped_claim_ids: List[str]) -> Dict[str, any]:
        """
        Validate that all citable claims have been mapped
        
        Args:
            text: Generated text
            mapped_claim_ids: List of claim IDs that have citations
            
        Returns:
            Validation result with coverage statistics
        """
        all_claims = self.extract_claims(text)
        citable_claims = [c for c in all_claims if c.requires_citation]
        
        mapped_set = set(mapped_claim_ids)
        total_citable = len(citable_claims)
        mapped_count = sum(1 for c in citable_claims if c.claim_id in mapped_set)
        
        unmapped_claims = [
            c.claim_id for c in citable_claims if c.claim_id not in mapped_set
        ]
        
        coverage_rate = mapped_count / total_citable if total_citable > 0 else 1.0
        
        return {
            'total_claims': len(all_claims),
            'citable_claims': total_citable,
            'mapped_claims': mapped_count,
            'unmapped_claims': unmapped_claims,
            'coverage_rate': coverage_rate,
            'is_complete': coverage_rate >= 1.0
        }
