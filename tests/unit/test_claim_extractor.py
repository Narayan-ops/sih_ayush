"""
Unit tests for Claim Extractor
"""

import pytest
from orchestrator.src.citation.claim_extractor import ClaimExtractor


class TestClaimExtractor:
    """Test claim extraction functionality"""

    def test_initialization(self):
        """Test claim extractor initialization"""
        extractor = ClaimExtractor()
        assert extractor is not None

    def test_extract_claims_simple(self):
        """Test extracting claims from simple text"""
        extractor = ClaimExtractor()
        text = "This is a sentence. This is another sentence."
        claims = extractor.extract_claims(text)
        
        assert len(claims) == 2
        assert claims[0].text == "This is a sentence."
        assert claims[1].text == "This is another sentence."

    def test_extract_claims_empty(self):
        """Test extracting claims from empty text"""
        extractor = ClaimExtractor()
        claims = extractor.extract_claims("")
        
        assert len(claims) == 0

    def test_requires_citation(self):
        """Test citation requirement detection"""
        extractor = ClaimExtractor()
        
        # Should require citation
        assert extractor._requires_citation("Patents protect inventions.")
        
        # Should not require citation (disclaimer)
        assert not extractor._requires_citation("This is not legal advice.")
        
        # Should not require citation (greeting)
        assert not extractor._requires_citation("Hello there.")

    def test_extract_key_claims(self):
        """Test extracting only key claims"""
        extractor = ClaimExtractor()
        text = (
            "This is a greeting. "
            "Patents protect inventions. "
            "Trademarks protect brands. "
            "Copyright protects creative works."
        )
        claims = extractor.extract_key_claims(text, max_claims=2)
        
        assert len(claims) <= 2

    def test_validate_claim_coverage(self):
        """Test claim coverage validation"""
        extractor = ClaimExtractor()
        text = "Claim 1. Claim 2. Claim 3."
        claims = extractor.extract_claims(text)
        
        # All claims mapped
        mapped_ids = [c.claim_id for c in claims]
        validation = extractor.validate_claim_coverage(text, mapped_ids)
        
        assert validation['is_complete'] is True
        
        # Partial mapping
        partial_mapped = [claims[0].claim_id]
        validation = extractor.validate_claim_coverage(text, partial_mapped)
        
        assert validation['is_complete'] is False
        assert validation['coverage_rate'] < 1.0
