"""
Integration tests for Retrieval and Citation pipeline
Tests hybrid retrieval, citation mapping, and confidence scoring
"""

import pytest
from orchestrator.src.retrieval.hybrid_retriever import HybridRetriever
from orchestrator.src.citation.citation_engine import CitationEngine
from orchestrator.src.citation.claim_extractor import ClaimExtractor


class TestRetrievalCitationIntegration:
    """Integration tests for retrieval and citation pipeline"""

    @pytest.fixture
    def mock_retriever(self):
        """Mock hybrid retriever (requires actual Qdrant/ES for real test)"""
        # In real integration test, would initialize with actual endpoints
        return HybridRetriever()

    @pytest.fixture
    def citation_engine(self):
        """Citation engine instance"""
        return CitationEngine()

    def test_claim_extraction(self, citation_engine):
        """Test claim extraction from generated text"""
        text = (
            "Patents protect inventions for a limited period. "
            "This is not legal advice. "
            "The patent application must be filed within 12 months of disclosure."
        )
        
        result = citation_engine.process_response(
            generated_text=text,
            retrieved_chunks=[],  # Empty for this test
        )
        
        assert result is not None
        assert len(result['claims']) > 0
        # Disclaimer claim should not require citation
        disclaimer_claim = next(
            (c for c in result['claims'] if "not legal advice" in c.text.lower()),
            None
        )
        assert disclaimer_claim is not None
        assert not disclaimer_claim.requires_citation

    def test_citation_mapping_without_chunks(self, citation_engine):
        """Test citation mapping behavior when no chunks retrieved"""
        text = "Patents protect inventions."
        
        result = citation_engine.process_response(
            generated_text=text,
            retrieved_chunks=[],
        )
        
        # Should have claims but no citations
        assert len(result['claims']) > 0
        assert result['mapping_validation']['is_complete'] is False
        assert result['should_reject'] is True

    def test_confidence_scoring_low_retrieval(self, citation_engine):
        """Test confidence scoring with low retrieval confidence"""
        text = "Test claim."
        
        # Mock low-confidence retrieval
        from dataclasses import dataclass
        @dataclass
        class MockChunk:
            chunk_id: str
            text: str
            score: float
        
        low_confidence_chunks = [
            MockChunk(chunk_id="1", text="Test", score=0.3)
        ]
        
        result = citation_engine.process_response(
            generated_text=text,
            retrieved_chunks=low_confidence_chunks,
        )
        
        # Should trigger abstention due to low confidence
        assert result['confidence_score'].should_abstain is True

    def test_jurisdiction_enforcement(self, mock_retriever):
        """Test that jurisdiction is enforced at retrieval level"""
        # This test requires actual Qdrant/ES instances
        # For now, it tests the interface
        with pytest.raises(ValueError):
            # Should reject invalid jurisdiction
            mock_retriever.retrieve(
                query="test",
                query_embedding=[0.1] * 768,
                jurisdiction="invalid",  # Invalid jurisdiction
                domain="patents"
            )

    def test_comparative_mode_structure(self, mock_retriever):
        """Test that comparative mode returns separate results"""
        # This test requires actual retrieval infrastructure
        # For now, it tests the interface
        result = mock_retriever.retrieve_comparative(
            query="test",
            query_embedding=[0.1] * 768,
            domain="patents"
        )
        
        # Should return dictionary with both jurisdictions
        assert isinstance(result, dict)
        assert 'india' in result
        assert 'international' in result
