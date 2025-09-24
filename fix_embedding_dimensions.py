#!/usr/bin/env python3
"""
Fix the embedding dimension mismatch issue.

The issue is that the search is trying to use embeddings with 384 dimensions,
but the collection was created with 1024 dimensions.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def fix_candidate_search_chroma():
    """Fix the candidate_search_chroma.py file to use the correct embedding dimensions."""
    file_path = project_root / "agent" / "nodes" / "candidate_search_chroma.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, "r") as f:
            content = f.read()
        
        # Check if the file already imports get_default_embeddings
        if "from configs.load import get_default_embeddings" not in content:
            # Add the import
            content = content.replace(
                "from adapters.chroma_adapter import ChromaClient",
                "from adapters.chroma_adapter import ChromaClient\nfrom configs.load import get_default_embeddings"
            )
        
        # Replace any SentenceTransformer usage with get_default_embeddings
        if "from sentence_transformers import SentenceTransformer" in content:
            content = content.replace(
                "from sentence_transformers import SentenceTransformer",
                "# from sentence_transformers import SentenceTransformer"
            )
        
        # Replace model initialization
        if "model = SentenceTransformer(" in content:
            content = content.replace(
                "model = SentenceTransformer(",
                "# model = SentenceTransformer("
            )
            
            # Find the embed_query function and replace it
            import re
            embed_query_pattern = r"def embed_query\(query: str\)(.*?)return"
            embed_query_match = re.search(embed_query_pattern, content, re.DOTALL)
            
            if embed_query_match:
                old_function = embed_query_match.group(0)
                new_function = """def embed_query(query: str):
    # Embed a query using the default embeddings.
    embeddings = get_default_embeddings()
    return embeddings.embed_query(query)
    
    return"""
                
                content = content.replace(old_function, new_function)
        
        # Write the updated content back to the file
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Updated {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        return False

def fix_soft_filters_chroma():
    """Fix the soft_filters_chroma.py file to use the correct embedding dimensions."""
    file_path = project_root / "adapters" / "soft_filters_chroma.py"
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    try:
        # Read the file
        with open(file_path, "r") as f:
            content = f.read()
        
        # Check if the file already imports get_default_embeddings
        if "from configs.load import get_default_embeddings" not in content:
            # Add the import
            content = content.replace(
                "from adapters.chroma_adapter import ChromaClient",
                "from adapters.chroma_adapter import ChromaClient\nfrom configs.load import get_default_embeddings"
            )
        
        # Replace any SentenceTransformer usage with get_default_embeddings
        if "from sentence_transformers import SentenceTransformer" in content:
            content = content.replace(
                "from sentence_transformers import SentenceTransformer",
                "# from sentence_transformers import SentenceTransformer"
            )
        
        # Replace model initialization
        if "model = SentenceTransformer(" in content:
            content = content.replace(
                "model = SentenceTransformer(",
                "# model = SentenceTransformer("
            )
        
        # Replace embedding generation
        if "query_embedding = model.encode(" in content:
            content = content.replace(
                "query_embedding = model.encode(",
                "embeddings = get_default_embeddings()\n    query_embedding = embeddings.embed_query("
            )
        
        # Write the updated content back to the file
        with open(file_path, "w") as f:
            f.write(content)
        
        logger.info(f"Updated {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting embedding dimension fix")
    
    # Fix the candidate_search_chroma.py file
    if fix_candidate_search_chroma():
        logger.info("Successfully fixed candidate_search_chroma.py")
    else:
        logger.error("Failed to fix candidate_search_chroma.py")
    
    # Fix the soft_filters_chroma.py file
    if fix_soft_filters_chroma():
        logger.info("Successfully fixed soft_filters_chroma.py")
    else:
        logger.error("Failed to fix soft_filters_chroma.py")
    
    logger.info("Embedding dimension fix completed")

if __name__ == "__main__":
    main()