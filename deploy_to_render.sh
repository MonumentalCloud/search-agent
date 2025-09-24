#!/bin/bash
# Script to prepare and deploy the search agent to Render.com

set -e

echo "🚀 Preparing Search Agent for Render.com deployment..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Please run this script from the project root."
    exit 1
fi

# Create deployment package
echo "📦 Creating deployment package..."
DEPLOY_DIR="render_deploy"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Copy necessary files
echo "📋 Copying project files..."
cp -r adapters "$DEPLOY_DIR/"
cp -r agent "$DEPLOY_DIR/"
cp -r apps "$DEPLOY_DIR/"
cp -r configs "$DEPLOY_DIR/"
cp -r frontend "$DEPLOY_DIR/"
cp -r ingestion "$DEPLOY_DIR/"
cp -r memory "$DEPLOY_DIR/"
cp -r utils "$DEPLOY_DIR/"
cp -r scripts "$DEPLOY_DIR/"

# Copy individual files
cp requirements.txt "$DEPLOY_DIR/"
cp render_start.py "$DEPLOY_DIR/"
cp render_build.sh "$DEPLOY_DIR/"
cp render.yaml "$DEPLOY_DIR/"
cp env.production "$DEPLOY_DIR/"
cp RENDER_DEPLOYMENT.md "$DEPLOY_DIR/"

# Create necessary directories
mkdir -p "$DEPLOY_DIR/logs"
mkdir -p "$DEPLOY_DIR/chroma_db"

# Set permissions
chmod +x "$DEPLOY_DIR/render_build.sh"
chmod +x "$DEPLOY_DIR/render_start.py"

# Create deployment zip
echo "🗜️  Creating deployment archive..."
cd "$DEPLOY_DIR"
zip -r ../search-agent-render-deploy.zip . -x "*.pyc" "__pycache__/*" "*.log"
cd ..

echo "✅ Deployment package created: search-agent-render-deploy.zip"
echo ""
echo "📋 Next steps:"
echo "1. Go to https://dashboard.render.com"
echo "2. Create a new Web Service"
echo "3. Upload the search-agent-render-deploy.zip file"
echo "4. Set environment variables (OPENROUTER_API_KEY, BGE_API_KEY)"
echo "5. Add a persistent disk (1GB, mount at /opt/render/project/src/chroma_db)"
echo ""
echo "📖 For detailed instructions, see: RENDER_DEPLOYMENT.md"
echo ""
echo "🎉 Ready to deploy!"
