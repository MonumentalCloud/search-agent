#!/usr/bin/env python3
"""
Check entity structure in Chroma chunks
"""

import json
import chromadb
from pathlib import Path

# Connect to Chroma
client = chromadb.PersistentClient('./chroma_db')
coll = client.get_collection('Chunk')

# Get chunks
results = coll.get(limit=10, include=['metadatas', 'documents'])

print(f"Found {len(results['ids'])} chunks\n")

for i, (metadata, document) in enumerate(zip(results['metadatas'], results['documents'])):
    print(f"Chunk {i+1} (ID: {results['ids'][i]}):")
    print(f"Doc ID: {metadata.get('doc_id', 'None')}")
    print(f"Section: {metadata.get('section', 'None')}")
    print(f"Valid From: {metadata.get('valid_from', 'None')}")
    
    # Parse entities
    entities_str = metadata.get('entities', '[]')
    try:
        entities = json.loads(entities_str)
        print(f"Entities ({len(entities)}):")
        for entity in entities:
            print(f"  - {entity}")
    except json.JSONDecodeError:
        print(f"Failed to parse entities: {entities_str}")
    
    # Check for relationships in document text
    print(f"Document excerpt: {document[:100]}...")
    
    # Look for relationship patterns
    relationship_patterns = ["관계", "관련", "연결", "연관", "belongs to", "part of", "related to"]
    for pattern in relationship_patterns:
        if pattern in document:
            print(f"  Found potential relationship: '{pattern}'")
    
    # Look for date patterns
    date_patterns = ["년", "월", "일", "2025", "2024", "date"]
    for pattern in date_patterns:
        if pattern in document:
            print(f"  Found potential date reference: '{pattern}'")
    
    # Look for number patterns
    number_patterns = ["금액", "비용", "예산", "수량", "개수", "percentage", "amount"]
    for pattern in number_patterns:
        if pattern in document:
            print(f"  Found potential number reference: '{pattern}'")
    
    print("\n" + "-"*50 + "\n")

# Check for any entity-relationship-entity patterns
print("\nSearching for entity-relationship-entity patterns:")

for i, document in enumerate(results['documents']):
    # This is a simplified check - in reality, you'd need more sophisticated NLP
    # to properly extract relationship triples
    for rel in ["담당", "책임", "관리", "보고", "승인"]:
        if rel in document:
            context = document[max(0, document.find(rel)-30):min(len(document), document.find(rel)+30)]
            print(f"Document {i+1}: Found '{rel}' relationship:")
            print(f"  Context: ...{context}...")
            print()
