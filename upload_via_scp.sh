#!/bin/bash
# Upload ChromaDB data and .env file to Render via SCP

SERVICE_NAME="search-agent"
REGION="oregon"
REMOTE_HOST="ssh.${REGION}.render.com"

echo "Uploading files to Render via SCP..."
echo "Service: ${SERVICE_NAME}"
echo "Host: ${REMOTE_HOST}"
echo ""

# Check if files exist
if [ ! -d "chroma_db" ]; then
    echo "Error: chroma_db directory not found!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    exit 1
fi

echo "Transferring ChromaDB data..."
scp -r ./chroma_db/ ${SERVICE_NAME}@${REMOTE_HOST}:/app/chroma_db/

echo "Transferring .env file..."
scp ./.env ${SERVICE_NAME}@${REMOTE_HOST}:/app/.env

echo ""
echo "✅ Upload complete!"
echo ""
echo "Next steps:"
echo "1. SSH into your service: ssh ${SERVICE_NAME}@${REMOTE_HOST}"
echo "2. Verify files: ls -la /app/chroma_db/ && ls -la /app/.env"
echo "3. Restart your service in Render dashboard"
