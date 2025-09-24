#!/usr/bin/env python
"""
Test script for Korean meeting queries using soft meta filtering.
"""

import os
import sys
import json
import datetime
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from adapters.weaviate_adapter import WeaviateClient
from ingestion.docx_ingestion import ingest_docx_directory, ingest_docx
from agent.graph import run_graph

def ingest_meeting_files(file_name=None):
    """Ingest Korean meeting DOCX files into Weaviate.
    
    Args:
        file_name: Optional name of a specific file to ingest (e.g., "회의록_01_마케팅.docx")
                  If None, ingest all DOCX files.
    """
    logger.info("Connecting to Weaviate...")
    client = WeaviateClient()
    client._connect()
    client._connected = True
    
    # Ensure schema exists
    client.ensure_schema()
    
    # Ingest DOCX files
    data_dir = os.path.join(project_root, "data")
    
    if file_name:
        # Ingest only the specified file
        file_path = os.path.join(data_dir, file_name)
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return 0
        
        logger.info(f"Ingesting single file: {file_name}...")
        success = ingest_docx(file_path, client)
        results = {file_path: success}
    else:
        # Ingest all DOCX files
        logger.info(f"Ingesting all DOCX files from {data_dir}...")
        results = ingest_docx_directory(data_dir, client)
    
    # Print results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Ingested {success_count} out of {len(results)} files successfully")
    
    for file_path, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"{status} {os.path.basename(file_path)}")
    
    return success_count

def test_meeting_queries():
    """Test the system with Korean meeting queries."""
    # List of test queries
    queries = [
        "8월 16일 회의 내용 요약해줘.",          # Summarize the meeting on August 16 (marketing meeting).
        "8월 11일 이후 어떤 회의들을 진행했어?",  # What meetings were held after August 11?
        "8월에 진행한 회의내용들 알려줘.",        # Tell me about the meetings held in August.
    ]
    
    # Run each query
    for i, query in enumerate(queries):
        logger.info(f"\n\nQuery {i+1}: {query}")
        logger.info("=" * 80)
        
        # Generate a trace ID for logging
        trace_id = f"test-{i+1}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Run the query through the agent graph
        result = run_graph(query=query, time_hint=None, lang="ko", trace_id=trace_id)
        
        # Print the result
        logger.info(f"Answer: {result.get('text', 'No answer generated')}")
        
        # Print citations if available
        citations = result.get('citations', [])
        if citations:
            logger.info(f"Citations ({len(citations)}):")
            for j, citation in enumerate(citations):
                logger.info(f"  {j+1}. {citation.get('chunk_id', 'Unknown chunk')}")
                logger.info(f"     {citation.get('text', '')[:100]}...")
        else:
            logger.info("No citations provided")

def main():
    """Main function."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test Korean meeting queries")
    parser.add_argument("--ingest", action="store_true", help="Ingest DOCX files")
    parser.add_argument("--file", type=str, help="Specific DOCX file to ingest (e.g., '회의록_01_마케팅.docx')")
    parser.add_argument("--query", action="store_true", help="Run test queries")
    args = parser.parse_args()
    
    # Default behavior: if no flags are provided, just run queries
    if not (args.ingest or args.query):
        args.query = True
    
    # Check if we need to ingest files
    if args.ingest:
        ingest_meeting_files(args.file)
    
    # Run test queries
    if args.query:
        test_meeting_queries()

if __name__ == "__main__":
    main()
