#!/usr/bin/env python3
"""
Script to create a combined ChromaDB from meeting logs and FiQA databases.
This will merge chunks from both databases into a new combined database.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
import chromadb
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from adapters.chroma_adapter import ChromaClient
from configs.load import get_default_embeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/combined_db_creation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_database_info(db_path: Path) -> Dict[str, Any]:
    """Get information about a ChromaDB database."""
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        collections = client.list_collections()
        
        info = {
            'path': str(db_path),
            'collections': [],
            'total_docs': 0,
            'accessible': True
        }
        
        for col in collections:
            count = col.count()
            info['collections'].append({
                'name': col.name,
                'count': count
            })
            info['total_docs'] += count
        
        return info
    except Exception as e:
        logger.error(f"Error accessing database at {db_path}: {e}")
        return {
            'path': str(db_path),
            'collections': [],
            'total_docs': 0,
            'accessible': False,
            'error': str(e)
        }

def extract_chunks_from_db(db_path: Path, collection_name: str = None) -> List[Dict[str, Any]]:
    """Extract all chunks from a ChromaDB database."""
    try:
        client = chromadb.PersistentClient(path=str(db_path))
        collections = client.list_collections()
        
        all_chunks = []
        
        for col in collections:
            # If collection_name is specified, only process that collection
            if collection_name and col.name != collection_name:
                continue
                
            logger.info(f"Extracting chunks from collection: {col.name}")
            
            # Get all documents from this collection (without embeddings to avoid array issues)
            results = col.get(include=['metadatas', 'documents'])
            
            if not results or not results.get('ids') or len(results['ids']) == 0:
                logger.info(f"No documents found in collection {col.name}")
                continue
            
            logger.info(f"Found {len(results['ids'])} documents in {col.name}")
            
            # Process each document
            for i, doc_id in enumerate(results['ids']):
                try:
                    metadata = results['metadatas'][i] if results.get('metadatas') and i < len(results['metadatas']) else {}
                    document = results['documents'][i] if results.get('documents') and i < len(results['documents']) else ''
                    
                    # Handle None metadata
                    if metadata is None:
                        metadata = {}
                    
                    # Add source database info to metadata
                    enhanced_metadata = {
                        **metadata,
                        'source_database': db_path.name,
                        'source_collection': col.name,
                        'original_id': doc_id
                    }
                    
                    # Create a unique ID for the combined database
                    combined_id = f"{db_path.name}_{col.name}_{doc_id}"
                    
                    chunk = {
                        'id': combined_id,
                        'document': document,
                        'metadata': enhanced_metadata
                    }
                    
                    all_chunks.append(chunk)
                    
                except Exception as e:
                    logger.error(f"Error processing document {i} in {col.name}: {e}")
                    continue
        
        logger.info(f"Extracted {len(all_chunks)} total chunks from {db_path.name}")
        return all_chunks
        
    except Exception as e:
        logger.error(f"Error extracting chunks from {db_path}: {e}")
        return []

def create_combined_database(meeting_db_path: Path, fiqa_db_path: Path, output_path: Path):
    """Create a combined database from meeting logs and FiQA databases."""
    
    logger.info("🚀 Starting combined database creation")
    logger.info(f"📁 Meeting DB: {meeting_db_path}")
    logger.info(f"📁 FiQA DB: {fiqa_db_path}")
    logger.info(f"📁 Output: {output_path}")
    
    # Check if source databases exist and are accessible
    meeting_info = get_database_info(meeting_db_path)
    fiqa_info = get_database_info(fiqa_db_path)
    
    if not meeting_info['accessible']:
        logger.error(f"❌ Cannot access meeting database at {meeting_db_path}")
        return False
        
    if not fiqa_info['accessible']:
        logger.error(f"❌ Cannot access FiQA database at {fiqa_db_path}")
        return False
    
    logger.info(f"📊 Meeting DB: {meeting_info['total_docs']} docs, {len(meeting_info['collections'])} collections")
    logger.info(f"📊 FiQA DB: {fiqa_info['total_docs']} docs, {len(fiqa_info['collections'])} collections")
    
    # Remove existing combined database if it exists
    if output_path.exists():
        logger.info(f"🗑️ Removing existing combined database at {output_path}")
        shutil.rmtree(output_path)
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize the combined database
        combined_client = chromadb.PersistentClient(path=str(output_path))
        
        # Extract chunks from both databases
        logger.info("📥 Extracting chunks from meeting database...")
        meeting_chunks = extract_chunks_from_db(meeting_db_path)
        
        logger.info("📥 Extracting chunks from FiQA database...")
        fiqa_chunks = extract_chunks_from_db(fiqa_db_path)
        
        total_chunks = len(meeting_chunks) + len(fiqa_chunks)
        logger.info(f"📊 Total chunks to combine: {total_chunks}")
        logger.info(f"   - Meeting chunks: {len(meeting_chunks)}")
        logger.info(f"   - FiQA chunks: {len(fiqa_chunks)}")
        
        if total_chunks == 0:
            logger.error("❌ No chunks found to combine")
            return False
        
        # Create combined collection
        collection_name = "combined_chunks"
        logger.info(f"📝 Creating combined collection: {collection_name}")
        
        # Prepare data for insertion
        ids = []
        documents = []
        metadatas = []
        
        # Add meeting chunks
        for chunk in meeting_chunks:
            ids.append(chunk['id'])
            documents.append(chunk['document'])
            metadatas.append(chunk['metadata'])
        
        # Add FiQA chunks
        for chunk in fiqa_chunks:
            ids.append(chunk['id'])
            documents.append(chunk['document'])
            metadatas.append(chunk['metadata'])
        
        # Create the collection with default embedding function
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        embedding_function = DefaultEmbeddingFunction()
        
        collection = combined_client.create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"description": "Combined chunks from meeting logs and FiQA databases"}
        )
        
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"✅ Added {len(ids)} chunks with default embeddings")
        
        # Verify the combined database
        final_count = collection.count()
        logger.info(f"🎉 Combined database created successfully!")
        logger.info(f"📊 Final count: {final_count} chunks")
        logger.info(f"📁 Database location: {output_path}")
        
        # Show some sample metadata
        sample_results = collection.get(limit=3, include=['metadatas'])
        if sample_results and sample_results['metadatas']:
            logger.info("📋 Sample metadata:")
            for i, metadata in enumerate(sample_results['metadatas'][:2]):
                logger.info(f"   {i+1}. Source: {metadata.get('source_database', 'Unknown')}")
                logger.info(f"      Collection: {metadata.get('source_collection', 'Unknown')}")
                logger.info(f"      Original ID: {metadata.get('original_id', 'Unknown')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating combined database: {e}")
        return False

def main():
    """Main function to create the combined database."""
    
    # Define paths
    project_root = Path(__file__).parent
    meeting_db_path = project_root / "chroma_db"        # Meeting logs (currently active)
    fiqa_db_path = project_root / "fiqa_chroma"         # FiQA database
    combined_db_path = project_root / "chroma_db_combined"  # New combined database
    
    logger.info("🎯 Creating Combined ChromaDB")
    logger.info("=" * 50)
    
    # Create the combined database
    success = create_combined_database(meeting_db_path, fiqa_db_path, combined_db_path)
    
    if success:
        logger.info("=" * 50)
        logger.info("🎉 Combined database creation completed successfully!")
        logger.info(f"📁 Combined database: {combined_db_path}")
        logger.info("💡 You can now test the agent with the combined database by:")
        logger.info("   1. python switch_database.py combined")
        logger.info("   2. python run.py --port 8001")
        logger.info("   3. Test with queries like 'meetings' or 'financial questions'")
    else:
        logger.error("❌ Combined database creation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
