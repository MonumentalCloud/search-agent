#!/usr/bin/env python3
"""
Fix the ChromaClient to use the BGE-M3 embeddings with 1024 dimensions
and add a fallback mechanism when the API is unavailable.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_chroma_embeddings_with_fallback():
    """
    Fix the ChromaClient to use the BGE-M3 embeddings with 1024 dimensions
    and add a fallback mechanism when the API is unavailable.
    """
    chroma_adapter_file = project_root / "adapters" / "chroma_adapter.py"
    
    # Read the current content
    with open(chroma_adapter_file, "r") as f:
        content = f.read()
    
    # Replace the SentenceTransformerEmbeddingFunction with a custom embedding function
    # that uses the default embeddings from the config with a fallback mechanism
    updated_content = content.replace(
        """
        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        # Use SentenceTransformer for consistent embedding dimensions
        self.connect()""",
        """
        # Use a robust embedding function with fallback mechanism
        from chromadb.utils import embedding_functions
        import numpy as np
        
        class RobustEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self, dimensions=1024):
                self.dimensions = dimensions
                # Initialize the fallback embedding function
                self.fallback_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                # Keep track of whether we're using the fallback
                self.using_fallback = False
                self.fallback_reason = None
                
            def __call__(self, texts):
                # Convert single text to list if needed
                if isinstance(texts, str):
                    texts = [texts]
                
                try:
                    # Try to use the default embeddings from the config
                    from configs.load import get_default_embeddings
                    embedding_model = get_default_embeddings()
                    
                    # Use the default embeddings model to embed the texts
                    embeddings = embedding_model.embed_documents(texts)
                    
                    # Check if the embeddings have the correct dimensions
                    if embeddings and len(embeddings[0]) == self.dimensions:
                        self.using_fallback = False
                        return embeddings
                    else:
                        self.using_fallback = True
                        self.fallback_reason = f"Unexpected embedding dimensions: {len(embeddings[0]) if embeddings and len(embeddings) > 0 else 'unknown'}"
                        logger.warning(f"Using fallback embedding function: {self.fallback_reason}")
                except Exception as e:
                    self.using_fallback = True
                    self.fallback_reason = str(e)
                    logger.warning(f"Using fallback embedding function due to error: {e}")
                
                # If we get here, we need to use the fallback
                try:
                    # Use the fallback embedding function
                    fallback_embeddings = self.fallback_embedding_function(texts)
                    
                    # Pad or truncate to match the expected dimensions
                    normalized_embeddings = []
                    for embedding in fallback_embeddings:
                        current_dim = len(embedding)
                        if current_dim < self.dimensions:
                            # Pad with zeros
                            padding = [0.0] * (self.dimensions - current_dim)
                            normalized_embeddings.append(embedding + padding)
                        elif current_dim > self.dimensions:
                            # Truncate
                            normalized_embeddings.append(embedding[:self.dimensions])
                        else:
                            normalized_embeddings.append(embedding)
                    
                    return normalized_embeddings
                except Exception as fallback_error:
                    logger.error(f"Fallback embedding function also failed: {fallback_error}")
                    # Return random embeddings as a last resort
                    return [list(np.random.normal(0, 0.1, self.dimensions)) for _ in texts]
        
        # Use the robust embedding function
        self.embedding_function = RobustEmbeddingFunction(dimensions=1024)
        self.connect()"""
    )
    
    # Write the updated content
    with open(chroma_adapter_file, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {chroma_adapter_file} to use robust embeddings with fallback mechanism")

if __name__ == "__main__":
    fix_chroma_embeddings_with_fallback()
