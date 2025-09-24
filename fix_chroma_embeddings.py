#!/usr/bin/env python3
"""
Fix the ChromaClient to use the BGE-M3 embeddings with 1024 dimensions.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_chroma_embeddings():
    """
    Fix the ChromaClient to use the BGE-M3 embeddings with 1024 dimensions.
    """
    chroma_adapter_file = project_root / "adapters" / "chroma_adapter.py"
    
    # Read the current content
    with open(chroma_adapter_file, "r") as f:
        content = f.read()
    
    # Replace the SentenceTransformerEmbeddingFunction with a custom embedding function
    # that uses the default embeddings from the config
    updated_content = content.replace(
        """
        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        # Use SentenceTransformer for consistent embedding dimensions
        self.connect()""",
        """
        # Use the default embeddings from the config for consistent dimensions
        from configs.load import get_default_embeddings
        from chromadb.utils import embedding_functions
        
        # Create a custom embedding function that uses the default embeddings
        class ConfigEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self):
                self.embedding_model = get_default_embeddings()
            
            def __call__(self, texts):
                # Convert single text to list if needed
                if isinstance(texts, str):
                    texts = [texts]
                
                # Use the default embeddings model to embed the texts
                embeddings = self.embedding_model.embed_documents(texts)
                return embeddings
        
        # Use the custom embedding function
        self.embedding_function = ConfigEmbeddingFunction()
        self.connect()"""
    )
    
    # Write the updated content
    with open(chroma_adapter_file, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {chroma_adapter_file} to use BGE-M3 embeddings with 1024 dimensions")

if __name__ == "__main__":
    fix_chroma_embeddings()
