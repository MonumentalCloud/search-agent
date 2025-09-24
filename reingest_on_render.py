#!/usr/bin/env python3
"""
Script to re-ingest data on Render deployment
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append('.')

def reingest_data():
    """Re-ingest data on Render"""
    
    print("Starting data re-ingestion on Render...")
    
    try:
        # Import your ingestion modules
        from ingestion.ingest_meetings import ingest_meetings
        from ingestion.ingest_documents import ingest_documents
        
        # Set up paths
        data_path = Path("data")
        if not data_path.exists():
            print("Error: data directory not found!")
            return False
        
        # Ingest meetings
        print("Ingesting meetings...")
        ingest_meetings()
        
        # Ingest other documents
        print("Ingesting documents...")
        ingest_documents()
        
        print("Data re-ingestion completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during re-ingestion: {e}")
        return False

def main():
    """Main function"""
    print("Render Data Re-ingestion")
    print("=" * 30)
    
    # Check if we're on Render
    if not os.getenv('RENDER'):
        print("This script is designed to run on Render")
        print("Make sure your data files are available in the data/ directory")
        return
    
    # Re-ingest data
    success = reingest_data()
    
    if success:
        print("✅ Data re-ingestion completed!")
    else:
        print("❌ Data re-ingestion failed!")

if __name__ == "__main__":
    main()
