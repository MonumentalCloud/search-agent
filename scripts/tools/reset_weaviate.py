#!/usr/bin/env python
"""
Script to reset the Weaviate database.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from adapters.weaviate_adapter import WeaviateClient

def reset_weaviate():
    """Reset the Weaviate database by deleting and recreating all collections."""
    logger.info("Connecting to Weaviate...")
    client = WeaviateClient()
    client._connect()
    client._connected = True
    
    # Delete existing collections
    logger.info("Deleting existing collections...")
    try:
        if client._client.collections.exists("Document"):
            client._client.collections.delete("Document")
            logger.info("Deleted Document collection")
        
        if client._client.collections.exists("Chunk"):
            client._client.collections.delete("Chunk")
            logger.info("Deleted Chunk collection")
        
        if client._client.collections.exists("FacetValueVector"):
            client._client.collections.delete("FacetValueVector")
            logger.info("Deleted FacetValueVector collection")
        
        if client._client.collections.exists("ChunkStats"):
            client._client.collections.delete("ChunkStats")
            logger.info("Deleted ChunkStats collection")
    except Exception as e:
        logger.error(f"Error deleting collections: {e}")
    
    # Recreate schema
    logger.info("Recreating schema...")
    client.ensure_schema()
    
    logger.info("Weaviate database reset complete")

if __name__ == "__main__":
    reset_weaviate()
