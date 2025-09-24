#!/usr/bin/env python3
"""
Script to upload ChromaDB data to Render deployment
"""

import os
import zipfile
import requests
import argparse
from pathlib import Path

def create_chroma_archive():
    """Create a zip archive of the ChromaDB data"""
    print("Creating ChromaDB archive...")
    
    # Create zip file
    zip_path = "chroma_db_backup.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        chroma_path = Path("chroma_db")
        if chroma_path.exists():
            for file_path in chroma_path.rglob("*"):
                if file_path.is_file():
                    # Add file to zip with relative path
                    arcname = file_path.relative_to(chroma_path.parent)
                    zipf.write(file_path, arcname)
                    print(f"Added: {arcname}")
        else:
            print("Error: chroma_db directory not found!")
            return None
    
    print(f"Created archive: {zip_path}")
    return zip_path

def upload_to_render(archive_path, render_url, api_key=None):
    """Upload archive to Render service"""
    print(f"Uploading {archive_path} to Render...")
    
    # This is a placeholder - you'll need to implement the actual upload
    # based on your Render service's upload endpoint
    print("Note: You'll need to manually upload the archive to your Render disk")
    print(f"Archive location: {os.path.abspath(archive_path)}")
    print(f"Upload to: {render_url}/admin/disk-upload")

def main():
    parser = argparse.ArgumentParser(description="Upload ChromaDB to Render")
    parser.add_argument("--render-url", help="Your Render service URL")
    parser.add_argument("--api-key", help="Render API key (optional)")
    
    args = parser.parse_args()
    
    # Create archive
    archive_path = create_chroma_archive()
    if not archive_path:
        return
    
    # Upload to Render
    if args.render_url:
        upload_to_render(archive_path, args.render_url, args.api_key)
    else:
        print(f"\nArchive created: {os.path.abspath(archive_path)}")
        print("Upload this file to your Render disk manually:")
        print("1. Go to your Render service dashboard")
        print("2. Click on 'Disks' tab")
        print("3. Click on your chroma-data disk")
        print("4. Upload the zip file")
        print("5. Extract it in the disk")

if __name__ == "__main__":
    main()
