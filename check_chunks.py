#!/usr/bin/env python3
"""
Check chunks in Chroma database
"""

import chromadb
import sys
from datetime import datetime

# Connect to Chroma
client = chromadb.PersistentClient('./chroma_db')
coll = client.get_collection('Chunk')

# Get all chunks
result = coll.get(limit=100)

print(f"Found {len(result['ids'])} chunks")
print("\nSample metadata fields:")
if result['metadatas'] and len(result['metadatas']) > 0:
    print(list(result['metadatas'][0].keys()))
else:
    print("No metadata found")

print("\nSample valid_from values:")
for i, metadata in enumerate(result['metadatas'][:10]):  # Show first 10
    doc_id = metadata.get("doc_id", "None")
    valid_from = metadata.get("valid_from", "None")
    print(f"{i+1}: {valid_from} (doc_id: {doc_id})")

print("\nChecking for August 2nd (8월 2일) in documents:")
august_2nd_chunks = []

for i, (doc_id, metadata, document) in enumerate(zip(result['ids'], result['metadatas'], result['documents'])):
    # Check if the document contains 8월 2일
    if "8월 2일" in document or "8월2일" in document:
        august_2nd_chunks.append((doc_id, metadata.get("doc_id", "Unknown"), document[:100] + "..."))
    
    # Check if the valid_from date is August 2nd
    valid_from = metadata.get("valid_from", "")
    if valid_from and "2025-08-02" in valid_from:
        august_2nd_chunks.append((doc_id, metadata.get("doc_id", "Unknown"), f"Date match: {valid_from}"))

if august_2nd_chunks:
    print(f"Found {len(august_2nd_chunks)} chunks mentioning or dated August 2nd:")
    for i, (chunk_id, doc_id, content) in enumerate(august_2nd_chunks):
        print(f"{i+1}. Chunk ID: {chunk_id}")
        print(f"   Document ID: {doc_id}")
        print(f"   Content: {content}")
        print()
else:
    print("No chunks found mentioning or dated August 2nd")

# Check for any date information
print("\nSearching for date patterns in documents:")
date_patterns = ["년", "월", "일", "2025", "2024", "2023"]
date_chunks = []

for i, (doc_id, metadata, document) in enumerate(zip(result['ids'], result['metadatas'], result['documents'])):
    for pattern in date_patterns:
        if pattern in document:
            excerpt = document[:100] + "..." if len(document) > 100 else document
            date_chunks.append((doc_id, metadata.get("doc_id", "Unknown"), excerpt))
            break

if date_chunks:
    print(f"Found {len(date_chunks)} chunks with date information:")
    for i, (chunk_id, doc_id, content) in enumerate(date_chunks[:5]):  # Show first 5
        print(f"{i+1}. Document ID: {doc_id}")
        print(f"   Content: {content}")
        print()
    
    if len(date_chunks) > 5:
        print(f"... and {len(date_chunks) - 5} more")
else:
    print("No chunks found with date information")
