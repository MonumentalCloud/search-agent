#!/usr/bin/env python3
"""
Script to set up ChromaDB on Render deployment
"""

import os
import shutil
from pathlib import Path

def setup_chroma_on_render():
    """Set up ChromaDB on Render deployment"""
    
    # Check if we're running on Render
    if os.getenv('RENDER'):
        print("Running on Render - setting up ChromaDB...")
        
        # Create ChromaDB directory
        chroma_path = Path("/opt/render/project/src/chroma_db")
        chroma_path.mkdir(parents=True, exist_ok=True)
        
        # Check if data already exists
        if any(chroma_path.iterdir()):
            print("ChromaDB data already exists")
        else:
            print("ChromaDB directory is empty - you need to upload your data")
            print("Use the upload script or Render dashboard to upload your chroma_db folder")
        
        return True
    else:
        print("Not running on Render - this script is for Render deployment only")
        return False

def check_chroma_data():
    """Check if ChromaDB data exists"""
    chroma_path = Path("chroma_db")
    
    if chroma_path.exists():
        files = list(chroma_path.rglob("*"))
        print(f"Found {len(files)} files in chroma_db")
        
        # Show some key files
        key_files = [f for f in files if f.suffix in ['.sqlite3', '.parquet', '.json']]
        if key_files:
            print("Key files found:")
            for f in key_files[:5]:  # Show first 5
                print(f"  - {f}")
        else:
            print("No key ChromaDB files found")
    else:
        print("chroma_db directory not found")

if __name__ == "__main__":
    print("ChromaDB Setup for Render")
    print("=" * 30)
    
    # Check local data
    check_chroma_data()
    
    # Set up on Render
    setup_chroma_on_render()
