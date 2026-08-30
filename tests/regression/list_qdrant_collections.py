"""
List Qdrant collections to verify phase3 collection names
"""

import requests

def list_collections():
    """List all Qdrant collections"""
    try:
        response = requests.get("http://localhost:6333/collections", timeout=10)
        response.raise_for_status()
        result = response.json()
        
        print("Qdrant Collections:")
        print("=" * 60)
        
        collections = result.get("result", {}).get("collections", [])
        
        # Filter for phase3 (intl) collections
        intl_collections = [c for c in collections if c.get("name", "").startswith("intl_")]
        
        # Filter for phase1/phase2 (in_) collections
        in_collections = [c for c in collections if c.get("name", "").startswith("in_")]
        
        print(f"\nTotal collections: {len(collections)}")
        print(f"International (intl_) collections: {len(intl_collections)}")
        print(f"India (in_) collections: {len(in_collections)}")
        
        print("\nInternational collections:")
        for col in sorted(intl_collections, key=lambda x: x["name"]):
            print(f"  - {col['name']} (points: {col.get('points_count', 0)})")
        
        print("\nIndia collections:")
        for col in sorted(in_collections, key=lambda x: x["name"]):
            print(f"  - {col['name']} (points: {col.get('points_count', 0)})")
        
        # Check for any unexpected eu_ collections
        eu_collections = [c for c in collections if c.get("name", "").startswith("eu_")]
        if eu_collections:
            print(f"\nWARNING: Found unexpected 'eu_' collections:")
            for col in eu_collections:
                print(f"  - {col['name']}")
        else:
            print(f"\nNo unexpected 'eu_' collections found")
        
    except Exception as e:
        print(f"Error querying Qdrant: {e}")

if __name__ == "__main__":
    list_collections()
