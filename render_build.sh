#!/bin/bash
# Render.com build script for the search agent

set -e

echo "Starting build process for search agent..."

# Install Python dependencies
echo "Installing Python dependencies..."

# Upgrade pip, setuptools, and wheel first
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install numpy first with pre-built wheels to avoid build issues
echo "Installing numpy with pre-built wheels..."
pip install --only-binary=all numpy

# Install remaining dependencies
echo "Installing remaining dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p chroma_db

# Set permissions
echo "Setting permissions..."
chmod +x render_start.py

# Create a simple .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating default .env file..."
    cat > .env << EOF
# API Keys - Replace with your actual keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
BGE_API_KEY=your_bge_api_key_here

# Configuration
CONFIG_PATH=configs/default.yaml
PYTHONPATH=.

# Service URLs
API_HOST=0.0.0.0
API_PORT=\$PORT
EOF
fi

echo "Build completed successfully!"
