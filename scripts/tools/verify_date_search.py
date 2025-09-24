#!/usr/bin/env python3
"""
Verify date-based search in Weaviate
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from adapters.weaviate_adapter import WeaviateClient
from adapters.soft_filters import apply_soft_filters

def main():
    # Connect to Weaviate
    client = WeaviateClient()
    print(f"Connected to Weaviate: {client._connected}")
    
    if not client._connected:
        print("Failed to connect to Weaviate")
        return
    
    # Search for documents on August 11th
    print("\n=== Searching for documents on August 11th ===")
    
    # Format the date as RFC3339
    date_str = "2025-08-11T00:00:00"
    
    # Create where filter
    where = {"valid_from": date_str}
    
    # Run the search
    results = client.hybrid_search("사이버 보안", 0.5, 10, where=where)
    
    print(f"Found {len(results)} results for date {date_str}")
    
    # Display results
    for i, r in enumerate(results[:3]):
        print(f"\nResult {i+1}:")
        print(f"ID: {r.get('chunk_id', 'N/A')}")
        print(f"Valid from: {r.get('valid_from', 'N/A')}")
        print(f"Section: {r.get('section', 'N/A')}")
        print(f"Body snippet: {r.get('body', 'N/A')[:100]}...")
    
    # Try with soft filters
    print("\n=== Using soft filters for August 11th ===")
    collection = client._client.collections.get(client.chunk_class)
    
    try:
        results = apply_soft_filters(
            collection=collection,
            query="사이버 보안",
            facets={"valid_from": "8월 11일"},
            alpha=0.5,
            limit=10
        )
        
        print(f"Found {len(results)} results with soft filter")
        
        # Display results
        for i, r in enumerate(results[:3]):
            print(f"\nResult {i+1}:")
            print(f"ID: {r.get('chunk_id', 'N/A')}")
            print(f"Valid from: {r.get('valid_from', 'N/A')}")
            print(f"Section: {r.get('section', 'N/A')}")
            print(f"Body snippet: {r.get('body', 'N/A')[:100]}...")
    except Exception as e:
        print(f"Soft filter search failed: {e}")
    
    # Try searching for documents on August 2nd
    print("\n=== Searching for documents on August 2nd ===")
    
    # Format the date as RFC3339
    date_str = "2025-08-02T00:00:00"
    
    # Create where filter
    where = {"valid_from": date_str}
    
    # Run the search
    results = client.hybrid_search("마케팅", 0.5, 10, where=where)
    
    print(f"Found {len(results)} results for date {date_str}")
    
    # Display results
    for i, r in enumerate(results[:3]):
        print(f"\nResult {i+1}:")
        print(f"ID: {r.get('chunk_id', 'N/A')}")
        print(f"Valid from: {r.get('valid_from', 'N/A')}")
        print(f"Section: {r.get('section', 'N/A')}")
        print(f"Body snippet: {r.get('body', 'N/A')[:100]}...")
    
    # Try with soft filters
    print("\n=== Using soft filters for August 2nd ===")
    
    try:
        results = apply_soft_filters(
            collection=collection,
            query="마케팅",
            facets={"valid_from": "8월 2일"},
            alpha=0.5,
            limit=10
        )
        
        print(f"Found {len(results)} results with soft filter")
        
        # Display results
        for i, r in enumerate(results[:3]):
            print(f"\nResult {i+1}:")
            print(f"ID: {r.get('chunk_id', 'N/A')}")
            print(f"Valid from: {r.get('valid_from', 'N/A')}")
            print(f"Section: {r.get('section', 'N/A')}")
            print(f"Body snippet: {r.get('body', 'N/A')[:100]}...")
    except Exception as e:
        print(f"Soft filter search failed: {e}")

if __name__ == "__main__":
    main()
