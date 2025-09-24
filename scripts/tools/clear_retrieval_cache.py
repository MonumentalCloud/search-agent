#!/usr/bin/env python3
"""
Clear Retrieval Cache Script

This script clears the retrieval cache without affecting document data or chunk statistics.
It's useful when you want to force fresh retrievals for all queries.

Usage:
  python clear_retrieval_cache.py           # Clear retrieval cache
  python clear_retrieval_cache.py --verbose # Verbose logging
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from configs.load import setup_root_logger
from memory.retrieval_cache import retrieval_cache

logger = logging.getLogger(__name__)


def clear_cache() -> bool:
    """Clear the retrieval cache."""
    logger.info("🔄 Clearing retrieval cache...")
    
    try:
        # Get cache stats before clearing
        stats = retrieval_cache.get_cache_stats()
        
        # Clear the cache
        retrieval_cache.clear_cache()
        
        logger.info(f"✅ Successfully cleared retrieval cache")
        logger.info(f"   Cleared {stats['size']} cached queries for {stats['unique_chunks']} unique chunks")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear retrieval cache: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Clear Retrieval Cache")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_root_logger(log_level)
    
    logger.info("🚀 Starting retrieval cache clearing...")
    
    # Clear cache
    if clear_cache():
        logger.info("🎉 Retrieval cache clearing completed successfully!")
    else:
        logger.error("❌ Retrieval cache clearing failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
