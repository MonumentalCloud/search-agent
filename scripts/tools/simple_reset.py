#!/usr/bin/env python3
"""
Simple Database Reset Script

This script provides a simpler approach to reset the database and re-ingest PDFs
without the complex connection handling that might cause timeouts.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from configs.load import setup_root_logger

logger = logging.getLogger(__name__)


def simple_reset():
    """Simple reset process with better error handling."""
    setup_root_logger(logging.INFO)
    
    logger.info("🚀 Starting simple database reset...")
    
    try:
        # Step 1: Reset database
        logger.info("🗑️  Resetting database...")
        from adapters.weaviate_adapter import WeaviateClient
        
        with WeaviateClient() as client:
            if not client._connected:
                logger.error("❌ Cannot connect to Weaviate")
                return False
            
            if client.reset_database():
                logger.info("✅ Database reset successfully!")
            else:
                logger.error("❌ Database reset failed")
                return False
        
        # Step 2: Test improved chunking
        logger.info("🧪 Testing improved chunking...")
        from ingestion.improved_chunking import improved_chunk_text, ChunkConfig
        
        sample_text = "제1조 (목적) 이 법은 전자금융거래의 안전성과 신뢰성을 확보하고 이용자를 보호하기 위하여 필요한 사항을 규정함을 목적으로 한다."
        config = ChunkConfig(max_tokens=50)
        chunks = improved_chunk_text(sample_text, config)
        
        logger.info(f"✅ Chunking test successful: {len(chunks)} chunks generated")
        for i, chunk in enumerate(chunks):
            logger.info(f"   Chunk {i+1}: {chunk.get('token_count', 'N/A')} tokens")
        
        # Step 3: Ingest one PDF as a test
        logger.info("📄 Testing PDF ingestion...")
        from ingestion.pipeline import ingest_pdf_file
        
        pdf_files = list(Path("data").glob("*.pdf"))
        if pdf_files:
            test_file = str(pdf_files[0])
            logger.info(f"Testing with: {Path(test_file).name}")
            
            result = ingest_pdf_file(test_file, doc_type="regulation", jurisdiction="KR", lang="ko")
            
            if "error" in result:
                logger.error(f"❌ PDF ingestion failed: {result['error']}")
                return False
            else:
                logger.info(f"✅ PDF ingestion successful!")
                logger.info(f"   Documents: {result.get('documents_ingested', 0)}")
                logger.info(f"   Chunks: {result.get('total_chunks', 0)}")
        else:
            logger.warning("⚠️  No PDF files found in data/ directory")
        
        logger.info("🎉 Simple reset completed successfully!")
        logger.info("💡 You can now start the full system with: python start.py --full-stack")
        return True
        
    except Exception as e:
        logger.error(f"❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = simple_reset()
    sys.exit(0 if success else 1)
