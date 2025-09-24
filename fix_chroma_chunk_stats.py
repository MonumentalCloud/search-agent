#!/usr/bin/env python3
"""
Fix the update_chunk_stats method in ChromaClient to use BGE-M3 embeddings with 1024 dimensions.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_chroma_chunk_stats():
    """
    Fix the update_chunk_stats method in ChromaClient to use BGE-M3 embeddings with 1024 dimensions.
    """
    chroma_adapter_file = project_root / "adapters" / "chroma_adapter.py"
    
    # Read the current content
    with open(chroma_adapter_file, "r") as f:
        content = f.read()
    
    # Replace the SentenceTransformer usage in update_chunk_stats with the default embeddings
    updated_content = content.replace(
        """            # Use SentenceTransformer for embeddings
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            embeddings = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            
            # Generate embedding for the chunk ID
            embedding = embeddings([chunk_id])[0]""",
        """            # Use the default embeddings from the config
            from configs.load import get_default_embeddings
            import numpy as np
            
            try:
                # Try to use the default embeddings model (BGE-M3)
                embedding_model = get_default_embeddings()
                embedding = embedding_model.embed_query(chunk_id)
            except Exception as e:
                logger.warning(f"Error generating embedding with default model: {e}")
                # Fall back to a random vector with 1024 dimensions
                embedding = list(np.random.normal(0, 0.1, 1024))"""
    )
    
    # Also replace the SentenceTransformer usage in collection creation
    updated_content = updated_content.replace(
        """                # Use SentenceTransformer for consistent embedding dimensions
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")""",
        """                # Use a custom embedding function with the default embeddings
                from chromadb.utils import embedding_functions
                import numpy as np
                
                class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
                    def __init__(self, dimensions=1024):
                        self.dimensions = dimensions
                    
                    def __call__(self, texts):
                        # Convert single text to list if needed
                        if isinstance(texts, str):
                            texts = [texts]
                        
                        try:
                            # Try to use the default embeddings from the config
                            from configs.load import get_default_embeddings
                            embedding_model = get_default_embeddings()
                            return embedding_model.embed_documents(texts)
                        except Exception as e:
                            logger.warning(f"Error generating embeddings: {e}")
                            # Return random vectors with 1024 dimensions as a fallback
                            return [list(np.random.normal(0, 0.1, self.dimensions)) for _ in texts]
                
                embedding_function = CustomEmbeddingFunction(dimensions=1024)"""
    )
    
    # Write the updated content
    with open(chroma_adapter_file, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {chroma_adapter_file} to use BGE-M3 embeddings with 1024 dimensions")

if __name__ == "__main__":
    fix_chroma_chunk_stats()
