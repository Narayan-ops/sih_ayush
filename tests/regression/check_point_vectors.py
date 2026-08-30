"""
Check if individual points have vectors by retrieving them directly
"""

from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Get a point from in_gi collection
try:
    response = client.scroll(
        collection_name="in_gi",
        limit=1,
        with_vectors=True
    )
    
    if response[0]:
        point = response[0][0]
        print(f"Point ID: {point.id}")
        print(f"Has vector: {point.vector is not None}")
        if point.vector:
            print(f"Vector length: {len(point.vector) if isinstance(point.vector, list) else 'non-list type'}")
            print(f"Vector type: {type(point.vector)}")
        print(f"Payload keys: {point.payload.keys()}")
    else:
        print("No points found")
        
except Exception as e:
    print(f"Error: {e}")
