"""
Unit tests for Citation Mapper
"""

import pytest
from orchestrator.src.citation.citation_mapper import CitationMapper, Citation, CitationMapping
from orchestrator.src.citation.claim_extractor import Claim
from dataclasses import dataclass


@dataclass
class MockChunk:
    """Mock chunk for testing"""
    chunk_id: str
    source_id: str
    section: str
    article: str
    text: str
    score: float
    version_hash: str
    jurisdiction: str
    domain: str
    metadata: dict


class TestCitationMapper:
    """Test citation mapping functionality"""

    def test_initialization(self):
        """Test citation mapper initialization"""
        mapper = CitationMapper()
        assert mapper is not None
        assert mapper.similarity_threshold == 0.55

    def test_map_claims_to_chunks(self):
        """Test mapping claims to chunks"""
        mapper = CitationMapper()
        
        # Create mock claim
        claim = Claim(
            text="Patents protect inventions.",
            start_pos=0,
            end_pos=25,
            claim_id="claim_0",
            requires_citation=True
        )
        
        # Create mock chunk
        chunk = MockChunk(
            chunk_id="chunk_1",
            source_id="Patents Act 1970",
            section="3",
            article="3(p)",
            text="Patents protect inventions for a limited period.",
            score=0.8,
            version_hash="abc123",
            jurisdiction="india",
            domain="patents",
            metadata={}
        )
        
        mappings = mapper.map_claims_to_chunks([claim], [chunk])
        
        assert len(mappings) == 1
        assert mappings[0].claim_id == "claim_0"

    def test_validate_mapping_completeness(self):
        """Test mapping completeness validation"""
        mapper = CitationMapper()
        
        claim = Claim(
            text="Test claim.",
            start_pos=0,
            end_pos=11,
            claim_id="claim_0",
            requires_citation=True
        )
        
        chunk = MockChunk(
            chunk_id="chunk_1",
            source_id="Test",
            section="1",
            article="1",
            text="Test claim text.",
            score=0.8,
            version_hash="abc123",
            jurisdiction="india",
            domain="test",
            metadata={}
        )
        
        mappings = mapper.map_claims_to_chunks([claim], [chunk])
        validation = mapper.validate_mapping_completeness(mappings)
        
        assert validation['is_complete'] is True
        assert validation['should_reject'] is False

    def test_format_citations(self):
        """Test citation formatting"""
        mapper = CitationMapper()
        
        mapping = CitationMapping(
            claim_id="claim_0",
            claim_text="Test claim.",
            citations=[
                Citation(
                    claim_id="claim_0",
                    chunk_id="chunk_1",
                    source_id="Patents Act 1970",
                    section="3",
                    article="3(p)",
                    version_hash="abc123",
                    confidence=0.85
                )
            ],
            is_supported=True
        )
        
        formatted = mapper.format_citations(mapping)
        
        assert "Patents Act 1970" in formatted
        assert "Section 3" in formatted
        assert "Article 3(p)" in formatted

    def test_paraphrase_is_supported_by_directional_coverage(self):
        mapper = CitationMapper()
        claim = Claim("A registered proprietor may use a registered geographical indication.", 0, 68, "claim_0")
        chunk = MockChunk(
            chunk_id="chunk_2", source_id="GI Act 1999", section="21", article="21(1)(b)",
            text="The registered proprietor of a geographical indication has the right to use the geographical indication.",
            score=0.8, version_hash="def456", jurisdiction="india", domain="gi", metadata={}
        )
        assert mapper.map_claims_to_chunks([claim], [chunk])[0].is_supported is True

    def test_incomplete_provenance_cannot_support_claim(self):
        mapper = CitationMapper()
        claim = Claim("Patents protect inventions.", 0, 27, "claim_0")
        chunk = MockChunk(
            chunk_id="chunk_3", source_id="", section="3", article="3(p)",
            text="Patents protect inventions for a limited period.", score=0.8,
            version_hash="abc123", jurisdiction="india", domain="patents", metadata={}
        )
        assert mapper.map_claims_to_chunks([claim], [chunk])[0].is_supported is False
