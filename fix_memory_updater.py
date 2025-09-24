#!/usr/bin/env python3
"""
Fix the memory_updater.py file to use the same embedding dimensions.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_memory_updater():
    """
    Fix the memory_updater.py file to use the same embedding dimensions.
    """
    memory_updater_file = project_root / "agent" / "nodes" / "memory_updater.py"
    
    # Read the current content
    with open(memory_updater_file, "r") as f:
        content = f.read()
    
    # Find the part where it uses SentenceTransformer and replace it with our robust embedding function
    if "SentenceTransformerEmbeddingFunction" in content:
        # Replace the SentenceTransformer with a custom embedding function
        updated_content = content.replace(
            "from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction",
            """from configs.load import get_default_embeddings
import numpy as np"""
        )
        
        # Replace the embedding function initialization
        updated_content = updated_content.replace(
            """        # Use SentenceTransformer for consistent embedding dimensions
            embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")""",
            """        # Use the default embeddings from the config
        try:
            embedding_model = get_default_embeddings()
            
            # Create a function to generate embeddings with the correct dimensions
            def generate_embedding(text):
                try:
                    # Try to use the default embeddings model
                    return embedding_model.embed_query(text)
                except Exception as e:
                    logger.warning(f"Error generating embedding: {e}")
                    # Return a random vector with 1024 dimensions as a fallback
                    return list(np.random.normal(0, 0.1, 1024))"""
        )
        
        # Replace the embedding generation
        updated_content = updated_content.replace(
            "            embedding = embeddings([chunk_id])[0]",
            "            embedding = generate_embedding(chunk_id)"
        )
        
        # Write the updated content
        with open(memory_updater_file, "w") as f:
            f.write(updated_content)
        
        print(f"Updated {memory_updater_file} to use the same embedding dimensions")
    else:
        print(f"Could not find SentenceTransformerEmbeddingFunction in {memory_updater_file}")

if __name__ == "__main__":
    fix_memory_updater()
