"""
Check TRIPS collection content directly
"""

from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Get points from intl_trips collection
try:
    response = client.scroll(
        collection_name="intl_trips",
        limit=5,
        with_vectors=False
    )
    
    print("TRIPS Collection Sample Content:")
    print("=" * 60)
    
    if response[0]:
        for i, point in enumerate(response[0]):
            print(f"\nPoint {i+1}:")
            print(f"  Section: {point.payload.get('section', 'N/A')}")
            print(f"  Clause: {point.payload.get('clause', 'N/A')}")
            print(f"  Content: {point.payload.get('content', 'N/A')[:200]}...")
    else:
        print("No points found in intl_trips collection")
        
except Exception as e:
    print(f"Error: {e}")
