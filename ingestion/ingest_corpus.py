"""Repeatable, local-only corpus ingestion client.

It accepts an extracted corpus directory or the supplied zip, emits a manifest
without printing legal text, and defaults every record to ``pending_review``.
Run it only against an operator-controlled ingestion service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import requests

DOMAIN_LOOKUP = {
    "patents_act_sections_1_11": "patents", "patents_act_chapter_vi": "patents", "patents_act_chapter_vii": "patents", "patents_act_section_25": "patents", "section_3_patents_act": "patents", "tkdl_methodology_overview": "patents", "patents_amendment_rules_2024": "patents",
    "biological_diversity_act_chapter_ii": "bda_abs", "biological_diversity_act_definitions": "bda_abs", "biological_diversity_act_finance": "bda_abs", "biological_diversity_act_government_duties": "bda_abs", "biological_diversity_act_nba_establishment": "bda_abs", "biological_diversity_act_section_18": "bda_abs", "biological_diversity_act_section_21": "bda_abs", "biological_diversity_act_state_board": "bda_abs", "biological_diversity_rules_2024": "bda_abs",
    "drugs_cosmetics_chapter_iva": "drugs_cosmetics", "drugs_cosmetics_schedule_t": "drugs_cosmetics", "drugs_magic_remedies_act_1954": "drugs_cosmetics", "gi_act_1999": "gi", "trade_marks_act_1999": "trademarks", "designs_act_2000": "designs", "copyright_act_1957_formulation_text": "copyright", "plant_variety_protection_act_2001": "plant_variety", "fssai_ayurveda_aahara_regulations_2022": "fssai",
    "eu_traditional_herbal_medicinal_products_directive": "herbal_market_access", "budapest_treaty_procedural_overview": "budapest", "cbd_nagoya_protocol_abs_articles": "cbd_nagoya", "hague_system_procedural_overview": "hague", "madrid_system_procedural_overview": "madrid", "pct_procedural_overview": "pct", "trips_agreement_patentability_articles": "trips", "wipo_gratk_treaty_2024": "wipo_gratk",
}
JURISDICTIONS = {"in": "in", "india": "in", "un": "intl", "wto": "intl", "eu": "intl", "international": "intl", "intl": "intl"}


def chunks(document: dict[str, Any], filename: str) -> list[dict[str, str | None]]:
    if isinstance(document.get("clauses"), list) and isinstance(document.get("sections"), list):
        raise ValueError(f"{filename}: both clauses and sections are present")
    if isinstance(document.get("clauses"), list):
        section = str(document.get("section") or document.get("section_title") or "not_specified")
        return [{"text": str(item["text"]), "section": section, "clause": str(item.get("clause_id") or "not_applicable")} for item in document["clauses"]]
    if isinstance(document.get("sections"), list):
        return [{"text": str(item["content"]), "section": str(item["section_id"]), "clause": "not_applicable"} for item in document["sections"]]
    raise ValueError(f"{filename}: expected clauses[] or sections[]")


def payload(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    jurisdiction = JURISDICTIONS.get(str(document.get("jurisdiction", "")).lower())
    if not jurisdiction or path.stem not in DOMAIN_LOOKUP:
        raise ValueError(f"{path.name}: missing a recognized jurisdiction or domain mapping")
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    source = str(document.get("source") or path.stem)
    metadata = {
        "source": source, "source_id": f"corpus:{path.stem}", "source_url": str(document.get("source_url") or "local-curated-corpus"),
        "retrieved_date": str(document.get("retrieved_date") or date.today().isoformat()), "review_status": "pending_review",
        "corpus_file": path.name, "file_hash": file_hash, "content_type": str(document.get("content_type") or "legal_text"),
    }
    extracted = chunks(document, path.name)
    data = [{**item, "source_id": metadata["source_id"]} for item in extracted]
    return {"data": data, "metadata": metadata, "jurisdiction": jurisdiction, "domain": DOMAIN_LOOKUP[path.stem]}, {"file": path.name, "sha256": file_hash, "chunks": len(extracted), "jurisdiction": jurisdiction, "domain": DOMAIN_LOOKUP[path.stem]}


def process(folder: Path, endpoint: str, dry_run: bool) -> int:
    files = sorted(folder.rglob("*.json"))
    if not files:
        raise ValueError("no JSON files found")
    manifest, failures = [], []
    for file in files:
        try:
            body, entry = payload(file)
            manifest.append(entry)
            if not dry_run:
                response = requests.post(endpoint, json=body, timeout=600)
                response.raise_for_status()
        except Exception as error:
            failures.append({"file": file.name, "error": str(error)})
    report = {"files": len(files), "processed": len(manifest), "chunks": sum(item["chunks"] for item in manifest), "review_status": "pending_review", "manifest": manifest, "failures": failures}
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest curated IP-SAKTI corpus without external network access")
    parser.add_argument("--source", required=True, type=Path, help="Corpus directory or zip file")
    parser.add_argument("--endpoint", default="http://localhost:8002/ingest")
    parser.add_argument("--dry-run", action="store_true", help="Validate metadata and print a non-content manifest only")
    args = parser.parse_args()
    if not args.source.exists():
        parser.error(f"source does not exist: {args.source}")
    if args.source.suffix.lower() != ".zip":
        return process(args.source, args.endpoint, args.dry_run)
    with tempfile.TemporaryDirectory(prefix="ipsakti-corpus-") as temporary:
        with zipfile.ZipFile(args.source) as archive:
            archive.extractall(temporary)
        return process(Path(temporary), args.endpoint, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
