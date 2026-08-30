"""
Check detailed info about a specific Qdrant collection
"""

import requests

def check_collection_details(collection_name):
    """Get detailed info about a Qdrant collection"""
    try:
        # Get collection info
        response = requests.get(f"http://localhost:6333/collections/{collection_name}", timeout=10)
        response.raise_for_status()
        result = response.json()
        
        print(f"Collection: {collection_name}")
        print("=" * 60)
        
        result_data = result.get("result", {})
        print(f"Status: {result_data.get('status', 'unknown')}")
        print(f"Points count: {result_data.get('points_count', 0)}")
        print(f"Vectors count: {result_data.get('vectors_count', 0)}")
        print(f"Indexed vectors count: {result_data.get('indexed_vectors_count', 0)}")
        
        config = result_data.get("config", {})
        params = config.get("params", {})
        print(f"\nVector size: {params.get('vector_size', 'unknown')}")
        print(f"Distance: {params.get('distance', 'unknown')}")
        
        print(f"\nConfig: {config}")
        
    except Exception as e:
        print(f"Error checking collection {collection_name}: {e}")

if __name__ == "__main__":
    # Check the specific collections we queried in regression tests
    regression_collections = ["in_patents", "in_bda_abs", "in_gi"]
    
    print("Regression Test Collections (these were just queried successfully):")
    print("=" * 60)
    for col in regression_collections:
        check_collection_details(col)
        print()
    
    # Check test domain
    print("Test Domain Collection Details:")
    print("=" * 60)
    check_collection_details("intl_test_domain")
    print()
    
    # Check a few phase3 collections
    phase3_sample = ["intl_budapest", "intl_trips"]
    print("Phase 3 Sample Collections:")
    print("=" * 60)
    for col in phase3_sample:
        check_collection_details(col)
        print()
