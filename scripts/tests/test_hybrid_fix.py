#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from adapters.weaviate_adapter import WeaviateClient

def test_hybrid_fix():
    print("Testing hybrid search fix...")

    with WeaviateClient() as client:
        print(f"Connected: {client._connected}")

        # Test hybrid search with vector parameter
        print("\nTesting hybrid search...")
        results = client.hybrid_search(
            query="전자금융거래",
            alpha=0.5,
            limit=5
        )

        print(f"Results count: {len(results)}")
        if results:
            print("✅ Hybrid search is working!")
            for i, result in enumerate(results):
                print(f"Result {i}: {result.get('body', 'No body')[:100]}...")
                print(f"  Score: {result.get('score', 'No score')}")
        else:
            print("❌ No results found")

if __name__ == "__main__":
    test_hybrid_fix()
