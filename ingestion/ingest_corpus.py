"""
Generalized Corpus Ingestion Script
Ingests all JSON files from a given phase folder into the ingestion service

Usage:
    python ingest_corpus.py --folder data/corpus/phase1
"""

import json
import argparse
import uuid
import sys
import os
from pathlib import Path
import requests
from typing import Dict, List, Any

# Domain lookup table: filename stem -> domain
DOMAIN_LOOKUP = {
    # Patents
    "patents_act_sections_1_11": "patents",
    "patents_act_chapter_vi": "patents",
    "patents_act_chapter_vii": "patents",
    "patents_act_section_25": "patents",
    "section_3_patents_act": "patents",
    "tkdl_methodology_overview": "patents",
    "patents_amendment_rules_2024": "patents",
    
    # Biological Diversity ABS
    "biological_diversity_act_chapter_ii": "bda_abs",
    "biological_diversity_act_definitions": "bda_abs",
    "biological_diversity_act_finance": "bda_abs",
    "biological_diversity_act_government_duties": "bda_abs",
    "biological_diversity_act_nba_establishment": "bda_abs",
    "biological_diversity_act_section_18": "bda_abs",
    "biological_diversity_act_section_21": "bda_abs",
    "biological_diversity_act_state_board": "bda_abs",
    "biological_diversity_rules_2024": "bda_abs",
    
    # Drugs & Cosmetics
    "drugs_cosmetics_chapter_iva": "drugs_cosmetics",
    "drugs_cosmetics_schedule_t": "drugs_cosmetics",
    "drugs_magic_remedies_act_1954": "drugs_cosmetics",
    
    # Geographical Indications
    "gi_act_1999": "gi",
    
    # Trademarks
    "trade_marks_act_1999": "trademarks",
    
    # Designs
    "designs_act_2000": "designs",
    
    # Copyright
    "copyright_act_1957_formulation_text": "copyright",
    
    # Plant Variety
    "plant_variety_protection_act_2001": "plant_variety",
    
    # FSSAI
    "fssai_ayurveda_aahara_regulations_2022": "fssai",
    
    # International Treaties
    "trips_agreement_patentability_articles": "trips",
    "cbd_nagoya_protocol_abs_articles": "cbd_nagoya",
    "wipo_gratk_treaty_2024": "wipo_gratk",
    "pct_procedural_overview": "pct",
    "madrid_system_procedural_overview": "madrid",
    "hague_system_procedural_overview": "hague",
    "budapest_treaty_procedural_overview": "budapest",
    "eu_traditional_herbal_medicinal_products_directive": "herbal_market_access",
}

# Jurisdiction normalization mapping
JURISDICTION_NORMALIZATION = {
    "in": "in",  # Use collection prefix directly
    "un": "intl",  # Use collection prefix directly
    "wto": "intl",  # Use collection prefix directly
}

INGESTION_URL = "http://localhost:8002/ingest"


def normalize_jurisdiction(jurisdiction: str, filename: str) -> str:
    """
    Normalize jurisdiction from corpus values to collection prefixes
    """
    jurisdiction_lower = jurisdiction.lower()
    
    if jurisdiction_lower not in JURISDICTION_NORMALIZATION:
        print(f"ERROR: Unknown jurisdiction '{jurisdiction}' in file {filename}")
        print(f"       Expected one of: {list(JURISDICTION_NORMALIZATION.keys())}")
        sys.exit(1)
    
    normalized = JURISDICTION_NORMALIZATION[jurisdiction_lower]
    print(f"  Jurisdiction: {jurisdiction} -> {normalized}")
    return normalized


def get_domain(filename_stem: str, filename: str) -> str:
    """
    Look up domain from filename stem
    """
    if filename_stem not in DOMAIN_LOOKUP:
        print(f"ERROR: Filename '{filename}' not in domain lookup table")
        print(f"       Please add mapping for '{filename_stem}' to DOMAIN_LOOKUP")
        sys.exit(1)
    
    domain = DOMAIN_LOOKUP[filename_stem]
    print(f"  Domain: {domain}")
    return domain


def detect_shape(corpus_data: Dict[str, Any], filename: str) -> str:
    """
    Detect whether JSON uses clauses[] or sections[] structure
    """
    has_clauses = "clauses" in corpus_data and isinstance(corpus_data["clauses"], list)
    has_sections = "sections" in corpus_data and isinstance(corpus_data["sections"], list)
    
    if has_clauses and has_sections:
        print(f"ERROR: File {filename} has both 'clauses' and 'sections' - ambiguous structure")
        sys.exit(1)
    
    if not has_clauses and not has_sections:
        print(f"ERROR: File {filename} has neither 'clauses' nor 'sections' - unknown structure")
        sys.exit(1)
    
    shape = "clauses" if has_clauses else "sections"
    print(f"  Shape: {shape}")
    return shape


def extract_clauses_shape(corpus_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract chunks from clauses[] structure
    """
    chunks = []
    
    # Get section info from top-level fields
    section = corpus_data.get("section", corpus_data.get("section_title", "unknown"))
    
    for item in corpus_data["clauses"]:
        chunk = {
            "text": item["text"],
            "section": section,
            "clause": item["clause_id"],
        }
        chunks.append(chunk)
    
    return chunks


def extract_sections_shape(corpus_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract chunks from sections[] structure
    """
    chunks = []
    
    for item in corpus_data["sections"]:
        chunk = {
            "text": item["content"],
            "section": item["section_id"],
            "clause": None,  # Sections don't have clauses
            "section_title": item.get("title", ""),  # Store title in metadata
        }
        chunks.append(chunk)
    
    return chunks


def build_citation_label(chunk: Dict[str, Any], shape: str, doc_index: int) -> str:
    """
    Build citation label for a chunk
    """
    if shape == "clauses":
        # Document N (Section X, Clause Y)
        return f"Document {doc_index} (Section {chunk['section']}, Clause {chunk['clause']})"
    else:
        # Document N (Section <section_id>: <title>)
        title = chunk.get("section_title", "")
        if title:
            return f"Document {doc_index} (Section {chunk['section']}: {title})"
        else:
            return f"Document {doc_index} (Section {chunk['section']})"


def process_file(filepath: Path, doc_index: int) -> int:
    """
    Process a single JSON file and ingest it
    Returns the number of chunks processed
    """
    print(f"\n{'='*60}")
    print(f"Processing: {filepath.name}")
    print(f"{'='*60}")
    
    # Load JSON
    with open(filepath, "r", encoding="utf-8") as f:
        corpus_data = json.load(f)
    
    # Get filename stem for domain lookup
    filename_stem = filepath.stem
    
    # Look up domain
    domain = get_domain(filename_stem, filepath.name)
    
    # Normalize jurisdiction
    jurisdiction = corpus_data.get("jurisdiction")
    if not jurisdiction:
        print(f"ERROR: Missing 'jurisdiction' field in {filepath.name}")
        sys.exit(1)
    
    normalized_jurisdiction = normalize_jurisdiction(jurisdiction, filepath.name)
    
    # Detect shape
    shape = detect_shape(corpus_data, filepath.name)
    
    # Extract chunks based on shape
    if shape == "clauses":
        raw_chunks = extract_clauses_shape(corpus_data)
    else:
        raw_chunks = extract_sections_shape(corpus_data)
    
    chunk_count = len(raw_chunks)
    print(f"  Chunks extracted: {chunk_count}")
    
    # Build ingestion data with UUIDs and citation labels
    data = []
    for i, chunk in enumerate(raw_chunks):
        chunk_id = str(uuid.uuid4())
        citation_label = build_citation_label(chunk, shape, doc_index + i)
        
        data_item = {
            "text": chunk["text"],
            "section": chunk["section"],
            "clause": chunk["clause"],
            "chunk_id": chunk_id,
            "citation_label": citation_label,
        }
        data.append(data_item)
    
    # Build metadata
    metadata = {
        "title": corpus_data.get("source", ""),
        "chapter": corpus_data.get("chapter", ""),
        "chapter_title": corpus_data.get("chapter_title", ""),
        "section": corpus_data.get("section", ""),
        "section_title": corpus_data.get("section_title", ""),
        "source_url": corpus_data.get("source_url", ""),
        "retrieved_date": corpus_data.get("retrieved_date", ""),
        "content_type": corpus_data.get("content_type", ""),
        "amendment_notes": corpus_data.get("amendment_notes", ""),
        "version": "1.0",
        "shape": shape,
    }
    
    # If sections shape, add section-specific metadata
    if shape == "sections":
        metadata["has_sections_structure"] = True
    
    # Build ingestion payload
    payload = {
        "data_source": "json",
        "data": data,
        "metadata": metadata,
        "jurisdiction": normalized_jurisdiction,  # Pass normalized jurisdiction
        "domain": domain,
    }
    
    # Send to ingestion service
    print(f"  Sending to ingestion service...")
    try:
        resp = requests.post(INGESTION_URL, json=payload, timeout=300)
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"  [OK] Ingestion successful")
            print(f"    Chunks processed: {result.get('chunks_processed', 0)}")
            print(f"    Qdrant points: {result.get('qdrant_points', 0)}")
            print(f"    Elasticsearch docs: {result.get('elasticsearch_docs', 0)}")
            if result.get('errors'):
                print(f"    Errors: {result['errors']}")
        else:
            print(f"  [FAIL] Ingestion failed with status {resp.status_code}")
            print(f"    Response: {resp.text}")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"  X Failed to connect to ingestion service: {e}")
        print(f"    Ensure ingestion service is running at {INGESTION_URL}")
        sys.exit(1)
    
    return chunk_count


def main():
    parser = argparse.ArgumentParser(description="Ingest corpus JSON files")
    parser.add_argument("--folder", required=True, help="Path to corpus folder (e.g., data/corpus/phase1)")
    args = parser.parse_args()
    
    folder_path = Path(args.folder)
    
    if not folder_path.exists():
        print(f"ERROR: Folder does not exist: {folder_path}")
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"ERROR: Path is not a directory: {folder_path}")
        sys.exit(1)
    
    # Glob all JSON files in the folder (non-recursive)
    json_files = list(folder_path.glob("*.json"))
    
    if not json_files:
        print(f"ERROR: No JSON files found in {folder_path}")
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files in {folder_path}")
    print(f"Starting ingestion...\n")
    
    # Process each file
    doc_index = 0
    for filepath in sorted(json_files):
        chunk_count = process_file(filepath, doc_index)
        doc_index += chunk_count  # Increment by chunks processed, not file count
    
    print(f"\n{'='*60}")
    print(f"Ingestion complete for {len(json_files)} files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
