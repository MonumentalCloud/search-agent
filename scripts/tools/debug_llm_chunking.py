#!/usr/bin/env python3
"""
Debug script to examine LLM chunking output
"""

import logging
import sys
import os
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from configs.load import get_default_llm

def main():
    # Read the test document
    with open('data/test_document_v2.txt', 'r') as f:
        text = f.read()
    
    print(f"Input text length: {len(text)} characters")
    
    # Create the prompt for document structure analysis
    prompt = f"""
You are an expert at analyzing and segmenting text. Split the following text into coherent, self-contained units of information. Each chunk should represent a complete logical unit (like a section, paragraph, or distinct concept) that is understandable on its own.

IMPORTANT RULES:
1. NEVER split in the middle of sentences or paragraphs.
2. Each section header (like "# Title", "## Section 2:", etc.) should start a new chunk.
3. Make sure each chunk is a complete, coherent unit with proper context.
4. Do not create chunks that start with conjunctions, partial sentences, or other fragments.
5. Ensure that the start_pos and end_pos values are accurate and do not overlap.

For each chunk, provide its start and end character positions and a short summary. Return a JSON object:
{{
  "structure": [
    {{
      "start_pos": <start_index>,
      "end_pos": <end_index>,
      "type": "<section|paragraph|list|other>",
      "title": "<section title if applicable>",
      "summary": "<short summary of the chunk>"
    }},
    ...
  ]
}}

Text:
{text}
"""

    # Get the LLM response
    llm = get_default_llm()
    response = llm.invoke(prompt)
    
    print("\n=== RAW LLM RESPONSE ===")
    print(response.content)
    
    # Try to parse the JSON
    try:
        # Find JSON in the response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            structure = json.loads(json_match.group())
            
            print("\n=== PARSED STRUCTURE ===")
            print(json.dumps(structure, indent=2))
            
            # Analyze the structure
            if "structure" in structure:
                items = structure["structure"]
                print(f"\nFound {len(items)} chunks in the structure")
                
                # Verify start and end positions
                for i, item in enumerate(items):
                    start_pos = item.get("start_pos", 0)
                    end_pos = item.get("end_pos", 0)
                    
                    if end_pos <= start_pos:
                        print(f"WARNING: Chunk {i} has end_pos <= start_pos: {start_pos}:{end_pos}")
                    
                    # Extract the chunk text
                    chunk_text = text[start_pos:end_pos].strip()
                    print(f"\n--- Chunk {i} ---")
                    print(f"Position: {start_pos}:{end_pos}")
                    print(f"Type: {item.get('type', 'unknown')}")
                    print(f"Title: {item.get('title', 'N/A')}")
                    print(f"Summary: {item.get('summary', 'N/A')}")
                    print(f"Text: {chunk_text[:100]}...")
                    
                    # Check if chunk starts with lowercase
                    if chunk_text and chunk_text[0].islower():
                        print(f"WARNING: Chunk {i} starts with lowercase: '{chunk_text[:50]}...'")
                    
                    # Check if chunk ends without proper punctuation
                    if chunk_text and chunk_text[-1] not in '.!?":\')}]':
                        print(f"WARNING: Chunk {i} ends without proper punctuation: '{chunk_text[-50:]}...'")
            else:
                print("No 'structure' key found in the response")
        else:
            print("No JSON found in the response")
    except Exception as e:
        print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    main()
