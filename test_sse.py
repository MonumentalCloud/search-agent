#!/usr/bin/env python3
"""
Simple test script for the SSE implementation.
"""

import requests
import json
import time
import uuid
import sys

def test_sse_query(query):
    """Send a query to the SSE server and print the response."""
    query_id = str(uuid.uuid4())
    url = "http://localhost:8001/api/query"
    
    print(f"Sending query: '{query}'")
    print(f"Query ID: {query_id}")
    print("Waiting for response...")
    
    try:
        # Send the query
        response = requests.post(
            url,
            json={
                "query": query,
                "query_id": query_id
            },
            stream=True  # Important for SSE
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return
        
        # Process the SSE events
        for line in response.iter_lines():
            if line:
                # SSE format: "data: {...}"
                if line.startswith(b'data: '):
                    data = json.loads(line[6:].decode('utf-8'))
                    
                    # Check the event type from the previous line
                    event_type = None
                    if hasattr(test_sse_query, 'previous_line') and test_sse_query.previous_line.startswith(b'event: '):
                        event_type = test_sse_query.previous_line[7:].decode('utf-8')
                    
                    # Process different event types
                    if event_type == "node_update":
                        print(f"Update: {data.get('summary', 'No summary available')}")
                    elif event_type == "answer":
                        print("\nAnswer received:")
                        print(f"{data.get('text', 'No answer text')}")
                        
                        if data.get('citations'):
                            print(f"\nCitations: {len(data.get('citations'))} found")
                            for i, citation in enumerate(data.get('citations')):
                                print(f"  [{i+1}] {citation.get('doc_id', 'Unknown')} - {citation.get('section', 'Unknown')}")
                        
                        # End the stream
                        return
                    elif event_type == "error":
                        print(f"\nError: {data.get('message', 'Unknown error')}")
                        return
                
                # Store the current line for context
                test_sse_query.previous_line = line
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Get the query from command line arguments or use a default query
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the main topic of the marketing meeting?"
    
    # Test the query
    test_sse_query(query)
