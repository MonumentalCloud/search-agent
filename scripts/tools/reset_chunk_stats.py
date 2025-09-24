#!/usr/bin/env python3
"""
Reset Chunk Statistics Script

This script resets the chunk statistics in the ChunkStats collection without re-ingesting documents.
It's useful for resetting memory/utility scores while keeping all documents and chunks intact.

Usage:
  python reset_chunk_stats.py           # Reset all chunk statistics
  python reset_chunk_stats.py --verbose # Verbose logging
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from configs.load import setup_root_logger
from adapters.chroma_adapter import ChromaClient

logger = logging.getLogger(__name__)


def reset_chunk_stats() -> bool:
    """Reset all chunk statistics in the ChunkStats collection."""
    logger.info("🔄 Resetting chunk statistics...")
    
    try:
        with ChromaClient() as client:
            if not client._connected:
                logger.error("❌ Cannot connect to Chroma. Make sure the database exists.")
                return False
            
            # Check if ChunkStats collection exists
            try:
                collection = client._client.get_collection("ChunkStats")
                
                # Delete all entries in the collection
                collection.delete(where={})
                
                logger.info("✅ Chunk statistics reset successfully!")
                return True
                
            except Exception as e:
                # If collection doesn't exist, create it
                logger.warning(f"ChunkStats collection not found: {e}")
                logger.info("Creating new ChunkStats collection...")
                
                # Ensure the schema includes ChunkStats
                if client.ensure_schema():
                    logger.info("✅ Created new ChunkStats collection")
                    return True
                else:
                    logger.error("❌ Failed to create ChunkStats collection")
                    return False
                
    except Exception as e:
        logger.error(f"❌ Failed to reset chunk statistics: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Reset Chunk Statistics")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_root_logger(log_level)
    
    logger.info("🚀 Starting chunk statistics reset...")
    
    # Reset chunk statistics
    if reset_chunk_stats():
        logger.info("🎉 Chunk statistics reset completed successfully!")
    else:
        logger.error("❌ Chunk statistics reset failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
