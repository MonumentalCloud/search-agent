#!/bin/bash
# Simple script to create a package for Render deployment

echo "Creating Render deployment package..."

# Create zip file with ChromaDB data and other important files
zip -r render_data_package.zip \
    chroma_db/ \
    data/ \
    .env \
    logs/ \
    -x "*.pyc" "__pycache__/*" "*.log"

echo "Package created: render_data_package.zip"
echo ""
echo "Next steps:"
echo "1. Go to your Render service dashboard"
echo "2. Click on 'Disks' tab"
echo "3. Click on your 'chroma-data' disk"
echo "4. Upload render_data_package.zip"
echo "5. Extract it in the disk"
echo "6. Make sure chroma_db/ folder is in the root of the disk"
