#!/usr/bin/env python3
"""
Get embedding dimensions from different embedding providers.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("Checking embedding dimensions from different providers...")
    
    # Check BGE-M3 embeddings from configs
    print("\n1. BGE-M3 embeddings from configs:")
    try:
        from configs.load import get_default_embeddings
        embedder = get_default_embeddings()
        print(f"Embedder type: {type(embedder).__name__}")
        test_embedding = embedder.embed_query("test")
        print(f"Embedding dimension: {len(test_embedding)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Check Chroma's default SentenceTransformer embeddings
    print("\n2. Chroma's SentenceTransformer embeddings:")
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        embedder = SentenceTransformerEmbeddingFunction()
        test_embedding = embedder(["test"])[0]
        print(f"Embedder model: {embedder.model_name}")
        print(f"Embedding dimension: {len(test_embedding)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Check embeddings for a sample chunk in the Chunk collection
    print("\n3. Sample chunk from Chunk collection:")
    try:
        import chromadb
        client = chromadb.PersistentClient('./chroma_db')
        chunk_collection = client.get_collection("Chunk")
        sample = chunk_collection.get(limit=1, include=["embeddings"])
        if sample and "embeddings" in sample and sample["embeddings"] and len(sample["embeddings"]) > 0:
            embedding_dim = len(sample["embeddings"][0])
            print(f"Sample embedding dimension: {embedding_dim}")
        else:
            print("No embeddings found in sample")
    except Exception as e:
        print(f"Error: {e}")
    
    # Check embeddings for a sample in the ChunkStats collection
    print("\n4. Sample from ChunkStats collection:")
    try:
        chunk_stats = client.get_collection("ChunkStats")
        sample = chunk_stats.get(limit=1, include=["embeddings"])
        if sample and "embeddings" in sample and sample["embeddings"] and len(sample["embeddings"]) > 0:
            embedding_dim = len(sample["embeddings"][0])
            print(f"Sample embedding dimension: {embedding_dim}")
        else:
            print("No embeddings found in sample")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
