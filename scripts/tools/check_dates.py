#!/usr/bin/env python3
"""
Check dates in the ingested documents
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from adapters.weaviate_adapter import WeaviateClient
from adapters.soft_filters import SoftFilter

def main():
    # Connect to Weaviate
    client = WeaviateClient()
    print(f"Connected to Weaviate: {client._connected}")
    
    if not client._connected:
        print("Failed to connect to Weaviate")
        return
    
    # Query all chunks to check their dates
    try:
        collection = client._client.collections.get(client.chunk_class)
        
        # Get all chunks with valid_from field
        result = collection.query.fetch_objects(
            limit=100,
            return_properties=["chunk_id", "doc_id", "section", "valid_from", "valid_to"]
        )
        
        print(f"\nFound {len(result.objects)} chunks")
        
        # Group by document
        docs = {}
        for obj in result.objects:
            doc_id = obj.properties.get("doc_id", "unknown")
            if doc_id not in docs:
                docs[doc_id] = []
            
            docs[doc_id].append({
                "chunk_id": obj.properties.get("chunk_id", "unknown"),
                "section": obj.properties.get("section", "unknown"),
                "valid_from": obj.properties.get("valid_from", None),
                "valid_to": obj.properties.get("valid_to", None)
            })
        
        # Print document dates
        print("\nDocument dates:")
        for doc_id, chunks in docs.items():
            print(f"\nDocument: {doc_id}")
            dates = set()
            for chunk in chunks:
                if chunk["valid_from"]:
                    dates.add(chunk["valid_from"])
            
            print(f"  Valid from dates: {sorted(list(dates))}")
            
            # Print a sample chunk
            if chunks:
                print(f"  Sample chunk: {json.dumps(chunks[0], indent=2)}")
        
        # Test date filtering for 8월 11일
        print("\nTesting date filter for 8월 11일:")
        date_filter = SoftFilter.create_date_filter("valid_from", "8월 11일")
        print(f"Generated filter alternatives: {json.dumps(date_filter, indent=2)}")
        
        # Try to search with this date
        query = "사이버 보안"
        print(f"\nSearching for '{query}' with date filter for 8월 11일:")
        
        # Use current year in the filter
        import datetime
        current_year = datetime.datetime.now().year
        date_str = f"{current_year}-08-11T00:00:00"
        
        where = {"valid_from": date_str}
        results = client.hybrid_search(query, 0.5, 5, where=where)
        
        print(f"Results with exact filter: {len(results)}")
        for i, r in enumerate(results[:2]):
            print(f"\nResult {i+1}:")
            print(f"ID: {r.get('chunk_id', 'N/A')}")
            print(f"Valid from: {r.get('valid_from', 'N/A')}")
            print(f"Section: {r.get('section', 'N/A')}")
            print(f"Body snippet: {r.get('body', 'N/A')[:100]}...")
        
        # Try with soft filters
        from adapters.soft_filters import apply_soft_filters
        print("\nTrying with soft filters:")
        
        try:
            results = apply_soft_filters(
                collection=client._client.collections.get(client.chunk_class),
                query=query,
                facets={"valid_from": "8월 11일"},
                alpha=0.5,
                limit=5
            )
            
            print(f"Results with soft filter: {len(results)}")
            for i, r in enumerate(results[:2]):
                print(f"\nResult {i+1}:")
                print(f"ID: {r.get('chunk_id', 'N/A')}")
                print(f"Valid from: {r.get('valid_from', 'N/A')}")
                print(f"Section: {r.get('section', 'N/A')}")
                print(f"Body snippet: {r.get('body', 'N/A')[:100]}...")
        except Exception as e:
            print(f"Soft filter search failed: {e}")
            
    except Exception as e:
        print(f"Error querying chunks: {e}")

if __name__ == "__main__":
    main()
