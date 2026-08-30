"""
Test single document ingestion with debug output
"""

import requests
import json

# Simple test data
test_data = {
    "data_source": "json",
    "data": [{
        "text": "Traditional herbal medicinal product means a herbal medicinal product that fulfils the conditions laid down in Article 16a(1)",
        "section": "Key Definitions",
        "clause": "definition"
    }],
    "metadata": {
        "source": "Test",
        "jurisdiction": "intl",
        "domain": "test_domain"
    },
    "jurisdiction": "intl",
    "domain": "test_domain"
}

try:
    response = requests.post(
        "http://localhost:8002/ingest",
        json=test_data,
        timeout=120
    )
    response.raise_for_status()
    result = response.json()
    print("Ingestion Response:")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")
