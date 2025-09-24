#!/bin/bash
# Render.com build script for the search agent

set -e

echo "Starting build process for search agent..."

# Install Python dependencies
echo "Installing Python dependencies..."

# Upgrade pip, setuptools, and wheel first
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Set environment variables to prevent building from source
export NUMPY_BUILD_TIMEOUT=300
export PIP_NO_BUILD_ISOLATION=1
export PIP_NO_DEPENDENCIES=0
export PIP_INDEX_URL=https://pypi.org/simple/
export PIP_EXTRA_INDEX_URL=""

# Try to install numpy with multiple strategies
echo "Attempting to install numpy with pre-built wheels..."

# Strategy 1: Try with specific version and pre-built wheels only
if ! pip install --only-binary=all --no-cache-dir "numpy==1.26.4"; then
    echo "Strategy 1 failed, trying strategy 2..."
    
    # Strategy 2: Try with a more recent version
    if ! pip install --only-binary=all --no-cache-dir "numpy>=1.24.0,<2.0.0"; then
        echo "Strategy 2 failed, trying strategy 3..."
        
        # Strategy 3: Install without build isolation
        pip install --no-build-isolation --no-cache-dir "numpy>=1.24.0,<2.0.0"
    fi
fi

echo "NumPy installation completed, installing remaining dependencies..."

# Install remaining dependencies with timeout
echo "Installing remaining dependencies..."
pip install --no-cache-dir --timeout 300 -r requirements.txt

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
