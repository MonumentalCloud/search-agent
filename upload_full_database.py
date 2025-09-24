#!/usr/bin/env python3
"""
Script to upload the full database to Render.com after deployment.
This script should be run locally to upload the 558MB database with both FIQA and meeting data.
"""

import os
import sys
import requests
import zipfile
from pathlib import Path

def create_database_archive():
    """Create a zip archive of the full database."""
    print("📦 Creating database archive...")
    
    # Source database path (full database with meeting data)
    source_db = Path("/Users/jinjae/search_agent/chroma_db")
    
    if not source_db.exists():
        print(f"❌ Source database not found at {source_db}")
        return None
    
    # Create archive
    archive_path = Path("full_database.zip")
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_db):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_db.parent)
                zipf.write(file_path, arcname)
    
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"✅ Created archive: {archive_path} ({size_mb:.1f} MB)")
    return archive_path

def upload_to_render(archive_path, render_service_url):
    """Upload the database archive to Render service."""
    print(f"🚀 Uploading to Render service: {render_service_url}")
    
    # This would require Render's API or file upload endpoint
    # For now, we'll provide instructions
    print("📋 Manual upload instructions:")
    print(f"1. Go to your Render service dashboard")
    print(f"2. Navigate to the file system or use SSH")
    print(f"3. Upload {archive_path} to the service")
    print(f"4. Extract it to /opt/render/project/src/chroma_db/")
    print(f"5. Restart the service")

def main():
    """Main function to prepare database for Render upload."""
    print("🎯 Preparing Full Database for Render Upload")
    print("=" * 50)
    
    # Create archive
    archive_path = create_database_archive()
    if not archive_path:
        return
    
    print("\n📊 Database Contents:")
    print("- 57,638 FIQA financial documents (haystack)")
    print("- 10 Korean meeting documents (needles)")
    print("- Total: 57,648 documents")
    print("- Size: ~558MB")
    
    print("\n🎯 Needle in Haystack Demo Ready:")
    print("- Search for meeting-specific content")
    print("- Test Korean language queries")
    print("- Demonstrate precise retrieval from large dataset")
    
    print(f"\n📁 Archive ready: {archive_path}")
    print("💡 Upload this to your Render service to get the full database!")

if __name__ == "__main__":
    main()
