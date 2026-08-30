"""
Debug script to check chunk structure with embeddings
"""

import json
import sys
sys.path.append('C:/Users/DELL/Desktop/ayush/ingestion')

from src.parsers.statute_parser import statute_parser
from src.chunkers.legal_chunker import legal_chunker
from src.embedders.embedding_generator import embedding_generator

# Load actual phase3 data
with open('C:/Users/DELL/Desktop/ayush/data/corpus/phase3/eu_traditional_herbal_medicinal_products_directive.json', 'r') as f:
    corpus_data = json.load(f)

# Convert to format expected by parser
sample_data = corpus_data["clauses"][:1]  # Just first clause

metadata = {
    "source": corpus_data.get("source", ""),
    "chapter": corpus_data.get("chapter", ""),
    "section": corpus_data.get("section", ""),
    "section_title": corpus_data.get("section_title", ""),
    "jurisdiction": "intl",
    "domain": "herbal_market_access"
}

# Parse
parsed = statute_parser.parse_json(sample_data, metadata)
print(f"After parsing: {len(parsed)} chunks")
print(f"First chunk keys: {parsed[0].keys() if parsed else 'N/A'}")

# Chunk
chunked = legal_chunker.chunk(parsed)
print(f"\nAfter chunking: {len(chunked)} chunks")
print(f"First chunk keys: {chunked[0].keys() if chunked else 'N/A'}")

# Add metadata
enhanced = legal_chunker.add_citation_metadata(chunked, metadata)
print(f"\nAfter metadata: {len(enhanced)} chunks")
print(f"First chunk keys: {enhanced[0].keys() if enhanced else 'N/A'}")
print(f"Has 'embedding' key: {'embedding' in enhanced[0] if enhanced else 'N/A'}")

# Generate embeddings
embedded = embedding_generator.generate_embeddings(enhanced)
print(f"\nAfter embedding: {len(embedded)} chunks")
print(f"First chunk keys: {embedded[0].keys() if embedded else 'N/A'}")
print(f"Has 'embedding' key: {'embedding' in embedded[0] if embedded else 'N/A'}")
print(f"Embedding length: {len(embedded[0].get('embedding', [])) if embedded else 'N/A'}")
