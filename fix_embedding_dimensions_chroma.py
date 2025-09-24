#!/usr/bin/env python3
"""
Fix the embedding dimensions mismatch in Chroma collections.
"""

import sys
import os
import logging
from pathlib import Path
import chromadb
import shutil
from dotenv import load_dotenv
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def backup_chroma_db():
    """Create a backup of the Chroma database."""
    chroma_dir = project_root / "chroma_db"
    backup_dir = project_root / "chroma_db_backup"
    
    if not chroma_dir.exists():
        logger.error(f"Chroma directory {chroma_dir} does not exist")
        return False
    
    # Remove existing backup if it exists
    if backup_dir.exists():
        logger.info(f"Removing existing backup at {backup_dir}")
        shutil.rmtree(backup_dir)
    
    # Create backup
    logger.info(f"Creating backup of Chroma database at {backup_dir}")
    shutil.copytree(chroma_dir, backup_dir)
    logger.info("Backup created successfully")
    return True

def reset_chroma_collections():
    """Reset Chroma collections with dimension mismatch."""
    try:
        # Connect to Chroma
        client = chromadb.PersistentClient('./chroma_db')
        
        # Get all collections
        collections = client.list_collections()
        logger.info(f"Found {len(collections)} collections")
        
        # Delete the Chunk collection to recreate it with the correct embedding function
        try:
            client.delete_collection("Chunk")
            logger.info("Deleted Chunk collection")
        except Exception as e:
            logger.warning(f"Error deleting Chunk collection: {e}")
        
        # Create a new Chunk collection with SentenceTransformer embedding function
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            
            client.create_collection(
                name="Chunk",
                embedding_function=embedding_function,
                metadata={"description": "Chunk collection", "dimension": 384}
            )
            logger.info("Created new Chunk collection with embedding dimension 384")
        except Exception as e:
            logger.error(f"Error creating new Chunk collection: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting Chroma collections: {e}")
        return False

def update_embedding_functions():
    """Update the embedding functions in the code to use consistent dimensions."""
    try:
        # Update chroma_adapter.py
        adapter_path = project_root / "adapters" / "chroma_adapter.py"
        
        with open(adapter_path, "r") as f:
            content = f.readlines()
        
        # Find the import section
        import_end_line = 0
        for i, line in enumerate(content):
            if line.strip() == "logger = logging.getLogger(__name__)":
                import_end_line = i
                break
        
        # Add SentenceTransformer import if needed
        if not any("SentenceTransformerEmbeddingFunction" in line for line in content[:import_end_line]):
            content.insert(import_end_line, "from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction\n")
            logger.info("Added import for SentenceTransformerEmbeddingFunction")
        
        # Find the ChromaClient.__init__ method
        init_start_line = 0
        init_end_line = 0
        for i, line in enumerate(content):
            if line.strip() == "def __init__(self) -> None:":
                init_start_line = i
            elif init_start_line > 0 and line.strip() == "def __enter__(self):":
                init_end_line = i
                break
        
        # Add embedding_function attribute to __init__
        if init_start_line > 0 and init_end_line > init_start_line:
            for i in range(init_start_line, init_end_line):
                if "self.connect()" in content[i]:
                    content.insert(i, "        # Use SentenceTransformer for consistent embedding dimensions\n")
                    content.insert(i, "        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name=\"all-MiniLM-L6-v2\")\n")
                    content.insert(i, "\n")
                    logger.info("Added embedding_function attribute to __init__")
                    break
        
        # Find the ensure_schema method
        schema_start_line = 0
        schema_end_line = 0
        for i, line in enumerate(content):
            if line.strip() == "def ensure_schema(self) -> bool:":
                schema_start_line = i
            elif schema_start_line > 0 and line.strip().startswith("def ") and "ensure_schema" not in line:
                schema_end_line = i
                break
        
        # Update the ensure_schema method to use embedding_function
        if schema_start_line > 0 and schema_end_line > schema_start_line:
            for i in range(schema_start_line, schema_end_line):
                if "self._client.create_collection(" in content[i]:
                    # Check if the next line has embedding_function
                    if "embedding_function" not in content[i+1]:
                        indentation = content[i].split("self")[0]
                        content.insert(i+1, f"{indentation}    embedding_function=self.embedding_function,\n")
                        logger.info("Updated create_collection to use embedding_function")
        
        # Find the batch_upsert_chunks method
        upsert_start_line = 0
        upsert_end_line = 0
        for i, line in enumerate(content):
            if line.strip() == "def batch_upsert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:":
                upsert_start_line = i
            elif upsert_start_line > 0 and line.strip().startswith("def ") and "batch_upsert_chunks" not in line:
                upsert_end_line = i
                break
        
        # Update the batch_upsert_chunks method to use embedding_function
        if upsert_start_line > 0 and upsert_end_line > upsert_start_line:
            for i in range(upsert_start_line, upsert_end_line):
                if "collection = self._client.get_collection(self.chunk_collection)" in content[i]:
                    indentation = content[i].split("collection")[0]
                    content.insert(i+1, f"{indentation}# Ensure we use the consistent embedding function\n")
                    content.insert(i+2, f"{indentation}collection._embedding_function = self.embedding_function\n")
                    logger.info("Updated batch_upsert_chunks to use embedding_function")
                    break
        
        # Find the hybrid_search method
        search_start_line = 0
        search_end_line = 0
        for i, line in enumerate(content):
            if line.strip() == "def hybrid_search(self, query: str, alpha: float = None, limit: int = None, where: Dict[str, Any] = None) -> List[Dict[str, Any]]:":
                search_start_line = i
            elif search_start_line > 0 and line.strip().startswith("def ") and "hybrid_search" not in line:
                search_end_line = i
                break
        
        # Update the hybrid_search method to use embedding_function
        if search_start_line > 0 and search_end_line > search_start_line:
            for i in range(search_start_line, search_end_line):
                if "collection = self._client.get_collection(self.chunk_collection)" in content[i]:
                    indentation = content[i].split("collection")[0]
                    content.insert(i+1, f"{indentation}# Ensure we use the consistent embedding function\n")
                    content.insert(i+2, f"{indentation}collection._embedding_function = self.embedding_function\n")
                    logger.info("Updated hybrid_search to use embedding_function")
                    break
        
        # Write the updated content back to the file
        with open(adapter_path, "w") as f:
            f.writelines(content)
        
        logger.info("Updated chroma_adapter.py to use consistent embedding functions")
        return True
    except Exception as e:
        logger.error(f"Error updating embedding functions: {e}")
        return False

def main():
    """Main function to fix embedding dimensions."""
    # Load environment variables
    load_dotenv()
    
    logger.info("Starting embedding dimensions fix")
    
    # Backup Chroma database
    if not backup_chroma_db():
        logger.error("Failed to backup Chroma database")
        return False
    
    # Reset Chroma collections with dimension mismatch
    if not reset_chroma_collections():
        logger.error("Failed to reset Chroma collections")
        return False
    
    # Update embedding functions in the code
    if not update_embedding_functions():
        logger.error("Failed to update embedding functions")
        return False
    
    logger.info("Embedding dimensions fix completed successfully")
    return True

if __name__ == "__main__":
    main()