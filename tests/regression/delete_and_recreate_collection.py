"""
Delete and recreate a Qdrant collection with fixed configuration
"""

from qdrant_client import QdrantClient

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

# Delete test collection
try:
    client.delete_collection("intl_test_domain")
    print("Deleted collection: intl_test_domain")
except Exception as e:
    print(f"Error deleting collection: {e}")

# Recreate with on_disk=False
try:
    from qdrant_client.models import Distance, VectorParams
    client.create_collection(
        collection_name="intl_test_domain",
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE, on_disk=False)
    )
    print("Recreated collection: intl_test_domain with on_disk=False")
except Exception as e:
    print(f"Error creating collection: {e}")
