#!/usr/bin/env python3
"""
Script to upload ChromaDB data and other files to Render deployment
"""

import os
import zipfile
import requests
import argparse
from pathlib import Path
import json

def create_data_package():
    """Create a zip package of ChromaDB data and other files"""
    print("Creating data package...")
    
    # Create zip file
    zip_path = "render_data_package.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # Add ChromaDB data
        chroma_path = Path("chroma_db")
        if chroma_path.exists():
            print("Adding ChromaDB data...")
            for file_path in chroma_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(chroma_path.parent)
                    zipf.write(file_path, arcname)
                    print(f"  Added: {arcname}")
        else:
            print("Warning: chroma_db directory not found!")
        
        # Add .env file if it exists
        env_path = Path(".env")
        if env_path.exists():
            print("Adding .env file...")
            zipf.write(env_path, ".env")
        else:
            print("No .env file found (using environment variables from Render dashboard)")
        
        # Add any other important files
        important_files = ["data/", "logs/"]
        for file_pattern in important_files:
            path = Path(file_pattern)
            if path.exists():
                if path.is_dir():
                    for file_path in path.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(Path("."))
                            zipf.write(file_path, arcname)
                            print(f"  Added: {arcname}")
                else:
                    zipf.write(path, path.name)
                    print(f"  Added: {path.name}")
    
    print(f"Created package: {os.path.abspath(zip_path)}")
    return zip_path

def upload_via_render_dashboard(zip_path):
    """Instructions for uploading via Render dashboard"""
    print("\n" + "="*60)
    print("UPLOAD INSTRUCTIONS FOR RENDER DASHBOARD")
    print("="*60)
    print(f"1. Go to your Render service dashboard")
    print(f"2. Click on the 'Disks' tab")
    print(f"3. Click on your 'chroma-data' disk")
    print(f"4. Upload the file: {os.path.abspath(zip_path)}")
    print(f"5. Extract the zip file in the disk")
    print(f"6. Make sure the chroma_db folder is in the root of the disk")
    print("="*60)

def create_manual_instructions():
    """Create manual instructions for data transfer"""
    instructions = """
# Manual Data Transfer Instructions for Render

## Method 1: Render Dashboard (Recommended)

1. **Create a zip file** of your local data:
   ```bash
   zip -r render_data.zip chroma_db/ data/ .env
   ```

2. **Go to Render Dashboard**:
   - Navigate to your service
   - Click on "Disks" tab
   - Click on your "chroma-data" disk

3. **Upload and extract**:
   - Upload the zip file
   - Extract it in the disk
   - Make sure `chroma_db/` is in the root

## Method 2: Re-ingest Data on Render

1. **Upload source data**:
   - Put your source documents in the `data/` folder
   - Upload via Render dashboard

2. **Run re-ingestion**:
   - SSH into your Render service (if available)
   - Run: `python reingest_on_render.py`

## Method 3: Use the Upload Script

Run this script to create a package:
```bash
python upload_to_render.py
```

Then follow the instructions it provides.

## Environment Variables

Make sure these are set in Render dashboard:
- `OPENROUTER_API_KEY`
- `BGE_API_KEY`
- `CONFIG_PATH=configs/default.yaml`
- `PYTHONPATH=.`
"""
    
    with open("RENDER_DATA_TRANSFER.md", "w") as f:
        f.write(instructions)
    
    print("Created RENDER_DATA_TRANSFER.md with detailed instructions")

def main():
    parser = argparse.ArgumentParser(description="Upload data to Render deployment")
    parser.add_argument("--create-package", action="store_true", help="Create data package")
    parser.add_argument("--instructions", action="store_true", help="Create instruction file")
    
    args = parser.parse_args()
    
    if args.create_package:
        zip_path = create_data_package()
        upload_via_render_dashboard(zip_path)
    
    if args.instructions:
        create_manual_instructions()
    
    if not args.create_package and not args.instructions:
        # Default: create package and instructions
        zip_path = create_data_package()
        upload_via_render_dashboard(zip_path)
        create_manual_instructions()

if __name__ == "__main__":
    main()
