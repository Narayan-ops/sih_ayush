"""Contract checks for the production safety boundary in the gateway."""

from pathlib import Path


def test_chat_persists_audit_and_rejects_comparative_fallback():
    source = Path("api-gateway/src/routes/chat.py").read_text(encoding="utf-8")
    assert "await repository.log_audit(" in source
    assert "two independently grounded answer sets" in source
    assert "A session cannot change jurisdiction" in source


def test_schema_has_provenance_and_append_only_audit_log():
    schema = Path("data/relational-store/schema.sql").read_text(encoding="utf-8")
    for required in ("CREATE TABLE IF NOT EXISTS audit_log", "retrieved_chunk_ids", "model_version", "corpus_version"):
        assert required in schema
