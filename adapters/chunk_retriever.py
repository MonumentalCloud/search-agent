import logging
from typing import Dict, Any, Optional

from adapters.weaviate_adapter import WeaviateClient

logger = logging.getLogger(__name__)

class ChunkRetriever:
    """A utility class to retrieve chunk data from Weaviate."""
    
    def __init__(self):
        self._client = WeaviateClient()
    
    def close(self):
        """Close the connection to Weaviate."""
        if hasattr(self._client, "_client") and hasattr(self._client._client, "close"):
            self._client._client.close()
            logger.info("Closed Weaviate connection")
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a chunk by its ID."""
        try:
            if not self._client._connected:
                return None
                
            # Use the appropriate API based on the client version
            if hasattr(self._client._client, "collections"):
                # Weaviate v4 API
                from weaviate.classes.query import Filter
                
                result = self._client._client.collections.get(
                    self._client.chunk_class
                ).query.fetch_objects(
                    filters=Filter.by_property("chunk_id").equal(chunk_id),
                    limit=1
                )
                
                if result.objects:
                    # Convert to a dictionary
                    chunk = {}
                    for key, value in result.objects[0].properties.items():
                        chunk[key] = value
                    return chunk
            else:
                # Weaviate v3 API
                result = self._client._client.data_object.get(
                    class_name=self._client.chunk_class,
                    where={
                        "path": ["chunk_id"],
                        "operator": "Equal",
                        "valueString": chunk_id
                    },
                    limit=1
                )
                
                if result and "objects" in result and result["objects"]:
                    return result["objects"][0]["properties"]
                    
            return None
        except Exception as e:
            logger.error(f"Error retrieving chunk by ID: {e}")
            return None

