"""
Check Elasticsearch for GI clause 21(1)(b)
"""

import requests
import json

def check_es_for_clause():
    """Check if clause 21(1)(b) exists in Elasticsearch"""
    
    query = {
        "query": {
            "match": {
                "clause": "21(1)(b)"
            }
        },
        "size": 5
    }
    
    try:
        response = requests.post(
            "http://localhost:9200/in_gi/_search",
            json=query,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        print("Elasticsearch Results for clause 21(1)(b):")
        print(f"Total hits: {result['hits']['total']['value']}")
        
        for hit in result['hits']['hits']:
            print(f"\nChunk ID: {hit['_id']}")
            print(f"Clause: {hit['_source'].get('clause', 'N/A')}")
            print(f"Content: {hit['_source'].get('content', 'N/A')[:200]}...")
            print(f"Score: {hit['_score']}")
        
    except Exception as e:
        print(f"Error querying Elasticsearch: {e}")

if __name__ == "__main__":
    check_es_for_clause()
