import logging
import json
from typing import Dict, Any, Optional

from adapters.chroma_adapter import ChromaClient

logger = logging.getLogger(__name__)

class ChunkRetriever:
    """A utility class to retrieve chunk data from Chroma."""
    
    def __init__(self):
        self._client = ChromaClient()
    
    def close(self):
        """Close the connection to Chroma."""
        self._client.close()
        logger.info("Closed Chroma connection")
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a chunk by its ID."""
        try:
            if not self._client._connected:
                return None
                
            collection = self._client._client.get_collection(self._client.chunk_collection)
            
            # Query for the specific chunk by ID
            result = collection.get(
                ids=[chunk_id],
                include=["metadatas", "documents"]
            )
            
            if result and 'ids' in result and result['ids'] and len(result['ids']) > 0:
                # Get the first result
                if 'metadatas' in result and result['metadatas'] and len(result['metadatas']) > 0:
                    metadata = result['metadatas'][0]
                    document = result['documents'][0] if 'documents' in result and result['documents'] and len(result['documents']) > 0 else ""
                    
                    # Convert entities from JSON string back to list
                    if 'entities' in metadata and metadata['entities']:
                        try:
                            metadata['entities'] = json.loads(metadata['entities'])
                        except:
                            metadata['entities'] = []
                    
                    # Create a chunk dictionary with all metadata and body
                    chunk = {
                        **metadata,
                        "body": document
                    }
                    
                    return chunk
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving chunk by ID: {e}")
            return None
