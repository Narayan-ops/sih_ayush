from orchestrator.src.citation.citation_engine import CitationEngine


def test_model_negative_assertion_is_rejected_without_evidence():
    """The model cannot turn an unsupported refusal into a confident answer."""
    result = CitationEngine().process_response(
        "There is no information in the available documents about this topic.", []
    )
    assert result["should_reject"] is True
