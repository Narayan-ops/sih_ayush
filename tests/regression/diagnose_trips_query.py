"""
Diagnose TRIPS patentability query retrieval
"""

import requests
import json

query = "What are the patentability criteria under TRIPS?"

try:
    response = requests.post(
        "http://localhost:8001/query",
        json={
            "query": query,
            "jurisdiction": "international"
        },
        timeout=120
    )
    response.raise_for_status()
    result = response.json()
    
    print("TRIPS Patentability Query Diagnostic")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"Jurisdiction: international")
    print(f"\nAPI Response:")
    print(f"Answer: {result.get('answer', 'N/A')[:300]}...")
    print(f"Confidence: {result.get('confidence_score', 0.0):.2f}")
    print(f"Citations: {len(result.get('citations', []))}")
    
    print(f"\nCitation Details:")
    for i, citation in enumerate(result.get('citations', [])[:5]):
        print(f"  Citation {i+1}:")
        print(f"    Section: {citation.get('section', 'N/A')}")
        print(f"    Article: {citation.get('article', 'N/A')}")
        print(f"    Confidence: {citation.get('confidence', 0.0):.3f}")
    
    # Check if answer mentions TRIPS or patentability
    answer_text = result.get('answer', '')
    if 'trips' in answer_text.lower() or 'patentability' in answer_text.lower():
        print(f"\n[X] Answer contains TRIPS/patentability information")
    else:
        print(f"\n[!] Answer does NOT contain TRIPS/patentability information")
        print("This suggests TRIPS content is not being retrieved effectively")
        
except Exception as e:
    print(f"Error: {e}")
