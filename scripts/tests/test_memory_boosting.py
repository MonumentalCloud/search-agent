#!/usr/bin/env python
"""
Test script to verify memory-based boosting in the reranker.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from adapters.weaviate_adapter import WeaviateClient
from memory.stores import get_chunk_stats, CHUNK_STATS
from memory.schemas import QueryCluster
from agent.nodes.memory_updater import update_memory
from agent.nodes.rerank_diversify import rerank_and_diversify
from configs.load import get_default_embeddings

def test_memory_boosting():
    """Test memory-based boosting in the reranker."""
    print("Testing memory-based boosting in the reranker...")
    
    # Connect to Weaviate
    client = WeaviateClient()
    try:
        client._connect()
        client._connected = True  # Manually set the connected flag
        print("Connected to Weaviate")
    except Exception as e:
        print(f"Failed to connect to Weaviate: {e}")
        return
    
    # Get a few random chunks to use for testing
    chunks = client.hybrid_search("test", alpha=0.5, limit=10)
    if not chunks:
        print("No chunks found in Weaviate")
        return
    
    print(f"Found {len(chunks)} chunks for testing")
    
    # Step 1: Create memory for specific chunks with specific query centroids
    
    # First query: "python programming language"
    query1 = "python programming language"
    try:
        embeddings_model = get_default_embeddings()
        query1_embedding = embeddings_model.embed_query(query1)
        print(f"Generated embedding for query: '{query1}'")
    except Exception as e:
        print(f"Failed to generate query embedding: {e}")
        return
    
    # Second query: "data science and machine learning"
    query2 = "data science and machine learning"
    try:
        query2_embedding = embeddings_model.embed_query(query2)
        print(f"Generated embedding for query: '{query2}'")
    except Exception as e:
        print(f"Failed to generate query embedding: {e}")
        return
    
    # Create memory for first chunk with query1
    chunk1 = chunks[0]
    chunk1_id = chunk1.get("chunk_id")
    
    # Create mock answer and verdict
    mock_answer1 = {
        "text": "This is about Python programming.",
        "citations": [{"chunk_id": chunk1_id, "text": chunk1.get("body", "")[:50]}]
    }
    
    mock_verdict1 = {
        "valid": True,
        "confidence": 0.95,
        "intent": "programming",
        "reason": "Test memory updates",
        "query": query1
    }
    
    # Update memory for chunk1 with query1
    print(f"\nCreating memory for chunk {chunk1_id} with query '{query1}'...")
    update_memory(mock_answer1, [chunk1], mock_verdict1)
    
    # Create memory for second chunk with query2
    chunk2 = chunks[1]
    chunk2_id = chunk2.get("chunk_id")
    
    # Create mock answer and verdict
    mock_answer2 = {
        "text": "This is about data science and machine learning.",
        "citations": [{"chunk_id": chunk2_id, "text": chunk2.get("body", "")[:50]}]
    }
    
    mock_verdict2 = {
        "valid": True,
        "confidence": 0.95,
        "intent": "data_science",
        "reason": "Test memory updates",
        "query": query2
    }
    
    # Update memory for chunk2 with query2
    print(f"\nCreating memory for chunk {chunk2_id} with query '{query2}'...")
    update_memory(mock_answer2, [chunk2], mock_verdict2)
    
    # Print memory stats
    print("\nMemory stats after updates:")
    for chunk_id in [chunk1_id, chunk2_id]:
        if chunk_id in CHUNK_STATS:
            stats = CHUNK_STATS[chunk_id]
            print(f"Chunk {chunk_id}:")
            print(f"  useful_count: {stats.useful_count}")
            print(f"  query_centroids: {len(stats.query_centroids)} clusters")
            for i, cluster in enumerate(stats.query_centroids):
                print(f"    Cluster #{i+1}: count={cluster.count}, sample_queries={cluster.sample_queries}")
    
    # Step 2: Test reranking with a query similar to query1
    test_query1 = "how to program in python"
    print(f"\nTesting reranking with query similar to first memory: '{test_query1}'")
    
    # Create mock plan
    mock_plan = {"alpha": 0.5}
    
    # Rerank the chunks
    reranked1 = rerank_and_diversify(test_query1, chunks, mock_plan)
    
    # Print top 5 results
    print("\nTop 5 results after reranking:")
    for i, chunk in enumerate(reranked1[:5]):
        print(f"{i+1}. Chunk {chunk.get('chunk_id')}: score={chunk.get('rerank_score'):.3f}, memory_score={chunk.get('memory_score', 0.0):.3f}")
        print(f"   First 50 chars: {chunk.get('body', '')[:50]}")
    
    # Step 3: Test reranking with a query similar to query2
    test_query2 = "machine learning algorithms for data analysis"
    print(f"\nTesting reranking with query similar to second memory: '{test_query2}'")
    
    # Rerank the chunks
    reranked2 = rerank_and_diversify(test_query2, chunks, mock_plan)
    
    # Print top 5 results
    print("\nTop 5 results after reranking:")
    for i, chunk in enumerate(reranked2[:5]):
        print(f"{i+1}. Chunk {chunk.get('chunk_id')}: score={chunk.get('rerank_score'):.3f}, memory_score={chunk.get('memory_score', 0.0):.3f}")
        print(f"   First 50 chars: {chunk.get('body', '')[:50]}")

if __name__ == "__main__":
    test_memory_boosting()
