#!/usr/bin/env python3
"""
Remove all SentenceTransformer fallbacks from the codebase.
We will only use the Genos API embedder and fail fast if there are any issues.
"""

import os
import logging
import re
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent

def backup_file(file_path):
    """Create a backup of a file."""
    backup_path = str(file_path) + ".bak"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup of {file_path} at {backup_path}")

def clean_chroma_adapter():
    """Remove SentenceTransformer references from chroma_adapter.py."""
    file_path = project_root / "adapters" / "chroma_adapter.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create a backup
    backup_file(file_path)
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Remove SentenceTransformer import
    content = re.sub(
        r"from chromadb\.utils\.embedding_functions import SentenceTransformerEmbeddingFunction\n",
        "",
        content
    )
    
    # Remove embedding_function attribute from __init__
    content = re.sub(
        r"\s+# Use SentenceTransformer for consistent embedding dimensions\n\s+self\.embedding_function = SentenceTransformerEmbeddingFunction\(model_name=\"all-MiniLM-L6-v2\"\)\n\n",
        "",
        content
    )
    
    # Remove embedding_function parameter from create_collection
    content = re.sub(
        r"embedding_function=self\.embedding_function,\n",
        "",
        content
    )
    
    # Remove embedding_function assignment in batch_upsert_chunks
    content = re.sub(
        r"\s+# Ensure we use the consistent embedding function\n\s+collection\._embedding_function = self\.embedding_function\n",
        "",
        content
    )
    
    # Remove embedding_function assignment in hybrid_search
    content = re.sub(
        r"\s+# Ensure we use the consistent embedding function\n\s+collection\._embedding_function = self\.embedding_function\n",
        "",
        content
    )
    
    # Write the cleaned content back to the file
    with open(file_path, "w") as f:
        f.write(content)
    
    logger.info(f"Removed SentenceTransformer references from {file_path}")
    return True

def clean_memory_updater():
    """Remove SentenceTransformer references from memory_updater.py."""
    file_path = project_root / "agent" / "nodes" / "memory_updater.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create a backup
    backup_file(file_path)
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Replace update_chunk_stats_without_embedding with update_chunk_stats
    content = re.sub(
        r"client\.update_chunk_stats_without_embedding",
        "client.update_chunk_stats",
        content
    )
    
    # Write the cleaned content back to the file
    with open(file_path, "w") as f:
        f.write(content)
    
    logger.info(f"Updated memory_updater.py to use update_chunk_stats")
    return True

def clean_run_py():
    """Clean run.py to remove SentenceTransformer fallbacks."""
    file_path = project_root / "run.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create a backup
    backup_file(file_path)
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Remove any SentenceTransformer references
    content = re.sub(
        r"from chromadb\.utils\.embedding_functions import SentenceTransformerEmbeddingFunction",
        "",
        content
    )
    
    # Write the cleaned content back to the file
    with open(file_path, "w") as f:
        f.write(content)
    
    logger.info(f"Removed SentenceTransformer references from {file_path}")
    return True

def reset_chroma_collections():
    """Reset Chroma collections to use default embeddings."""
    try:
        import chromadb
        
        # Connect to Chroma
        client = chromadb.PersistentClient('./chroma_db')
        
        # Delete collections that might have SentenceTransformer embeddings
        collections_to_reset = ["Chunk", "ChunkStats", "FacetValueVector"]
        
        for collection_name in collections_to_reset:
            try:
                client.delete_collection(collection_name)
                logger.info(f"Deleted collection {collection_name}")
                
                # Recreate with default settings (no embedding function)
                client.create_collection(
                    name=collection_name,
                    metadata={"description": f"{collection_name} collection"}
                )
                logger.info(f"Recreated collection {collection_name} with default settings")
            except Exception as e:
                logger.warning(f"Error resetting collection {collection_name}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting Chroma collections: {e}")
        return False

def main():
    """Main function to remove SentenceTransformer fallbacks."""
    logger.info("Starting removal of SentenceTransformer fallbacks")
    
    # Clean chroma_adapter.py
    if not clean_chroma_adapter():
        logger.error("Failed to clean chroma_adapter.py")
        return False
    
    # Clean memory_updater.py
    if not clean_memory_updater():
        logger.error("Failed to clean memory_updater.py")
        return False
    
    # Clean run.py
    if not clean_run_py():
        logger.error("Failed to clean run.py")
        return False
    
    # Reset Chroma collections
    if not reset_chroma_collections():
        logger.error("Failed to reset Chroma collections")
        return False
    
    logger.info("Successfully removed all SentenceTransformer fallbacks")
    return True

if __name__ == "__main__":
    main()
