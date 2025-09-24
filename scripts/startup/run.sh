#!/bin/bash
# Unified Search Agent Control Script (Shell wrapper)

set -e

echo "🚀 Search Agent Control Script"
echo "============================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "run.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Make the Python script executable
chmod +x run.py

# Run the Python script with all arguments
python3 run.py "$@"
