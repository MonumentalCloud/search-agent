#!/usr/bin/env python3
"""
Check Chroma collections and their embedding dimensions.
"""

import chromadb

def main():
    # Connect to Chroma
    client = chromadb.PersistentClient('./chroma_db')
    
    # List collections
    collections = client.list_collections()
    print(f"Found {len(collections)} collections:")
    
    # Check each collection
    for collection in collections:
        name = collection.name
        print(f"\nCollection: {name}")
        
        # Get collection metadata
        metadata = collection.metadata
        print(f"Metadata: {metadata}")
        
        # Try to get embedding dimension
        dimension = metadata.get("dimension") if metadata else "unknown"
        print(f"Dimension: {dimension}")
        
        # Get a sample document if available
        try:
            sample = collection.get(limit=1)
            if sample and "embeddings" in sample and sample["embeddings"] and len(sample["embeddings"]) > 0:
                embedding_dim = len(sample["embeddings"][0])
                print(f"Sample embedding dimension: {embedding_dim}")
            else:
                print("No embeddings found in sample")
        except Exception as e:
            print(f"Error getting sample: {e}")

if __name__ == "__main__":
    main()
