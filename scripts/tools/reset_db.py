#!/usr/bin/env python3
"""
Database Reset Script

This script deletes the current Weaviate database and re-ingests all PDFs from the data directory.
It's useful for starting fresh or when you need to update the database with new documents.

Usage:
  python reset_db.py                    # Reset database and re-ingest PDFs
  python reset_db.py --skip-ingest      # Only reset database (don't re-ingest)
  python reset_db.py --verbose          # Verbose logging
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from configs.load import setup_root_logger
from adapters.weaviate_adapter import WeaviateClient
from ingestion.background_ingestion import start_background_ingestion, get_ingestion_status
from ingestion.metadata_vectors import rebuild_all_facet_value_vectors

logger = logging.getLogger(__name__)


def reset_database() -> bool:
    """Reset the Weaviate database by deleting all collections and recreating schema."""
    logger.info("🗑️  Resetting Weaviate database...")
    
    try:
        with WeaviateClient() as client:
            if not client._connected:
                logger.error("❌ Cannot connect to Weaviate. Make sure it's running.")
                return False
            
            # Reset the database
            if client.reset_database():
                logger.info("✅ Database reset successfully!")
                return True
            else:
                logger.error("❌ Failed to reset database")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        return False


def ingest_pdfs() -> bool:
    """Start background PDF ingestion and monitor progress."""
    logger.info("📄 Starting background PDF ingestion...")
    
    try:
        # Start background ingestion
        job_id = start_background_ingestion(
            directory_path="data",
            doc_type="regulation",
            jurisdiction="KR",
            lang="ko"
        )
        
        logger.info(f"🚀 Started background ingestion job: {job_id}")
        logger.info("📊 Monitoring progress...")
        
        # Monitor progress
        while True:
            status = get_ingestion_status(job_id)
            if not status:
                logger.error("❌ Could not get ingestion status")
                return False
            
            # Show progress
            progress = status["progress"]
            logger.info(f"📈 Progress: {progress:.1%} - {status['current_step']}")
            
            if status["status"] == "completed":
                logger.info("✅ Background ingestion completed successfully!")
                logger.info(f"   Files processed: {status['files_processed']}")
                logger.info(f"   Documents created: {status['documents_created']}")
                logger.info(f"   Chunks created: {status['chunks_created']}")
                return True
            elif status["status"] == "failed":
                logger.error(f"❌ Background ingestion failed: {status.get('error_message', 'Unknown error')}")
                return False
            
            # Wait before next check
            time.sleep(2)
        
    except Exception as e:
        logger.error(f"❌ Background ingestion failed: {e}")
        return False


def rebuild_metadata_vectors() -> bool:
    """Rebuild metadata vectors."""
    logger.info("🔧 Rebuilding metadata vectors...")
    
    try:
        count = rebuild_all_facet_value_vectors()
        logger.info(f"✅ Rebuilt {count} metadata vectors")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to rebuild metadata vectors: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Reset Weaviate Database and Re-ingest PDFs")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip PDF ingestion (only reset database)")
    parser.add_argument("--skip-vectors", action="store_true", help="Skip metadata vector rebuild")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_root_logger(log_level)
    
    logger.info("🚀 Starting database reset process...")
    
    # Step 1: Reset database
    if not reset_database():
        logger.error("❌ Database reset failed. Exiting.")
        sys.exit(1)
    
    # Step 2: Ingest PDFs (unless skipped)
    if not args.skip_ingest:
        if not ingest_pdfs():
            logger.error("❌ PDF ingestion failed. Exiting.")
            sys.exit(1)
        
        # Step 3: Rebuild metadata vectors (unless skipped)
        if not args.skip_vectors:
            if not rebuild_metadata_vectors():
                logger.warning("⚠️  Metadata vector rebuild failed, but continuing...")
    
    logger.info("🎉 Database reset and re-ingestion completed successfully!")
    logger.info("💡 You can now start the system with: python start.py --full-stack")


if __name__ == "__main__":
    main()
