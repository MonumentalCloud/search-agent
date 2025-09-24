#!/bin/bash
# Retrieval Agent Startup Script (Shell wrapper)

set -e

echo "🚀 Retrieval Agent Startup Script"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "start.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Parse command line arguments
ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            ARGS="$ARGS --skip-docker"
            shift
            ;;
        --skip-ingest)
            ARGS="$ARGS --skip-ingest"
            shift
            ;;
        --skip-vectors)
            ARGS="$ARGS --skip-vectors"
            shift
            ;;
        --skip-test)
            ARGS="$ARGS --skip-test"
            shift
            ;;
        --api-only)
            ARGS="$ARGS --api-only"
            shift
            ;;
        --host)
            ARGS="$ARGS --host $2"
            shift 2
            ;;
        --port)
            ARGS="$ARGS --port $2"
            shift 2
            ;;
        --verbose|-v)
            ARGS="$ARGS --verbose"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-docker     Skip Docker/Weaviate setup"
            echo "  --skip-ingest     Skip PDF ingestion"
            echo "  --skip-vectors    Skip metadata vector rebuild"
            echo "  --skip-test       Skip system test"
            echo "  --api-only        Only start the API server"
            echo "  --host HOST       API server host (default: 0.0.0.0)"
            echo "  --port PORT       API server port (default: 8001)"
            echo "  --verbose, -v     Verbose logging"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Full startup with all features"
            echo "  $0 --api-only         # Only start API server"
            echo "  $0 --skip-docker      # Skip Weaviate setup"
            echo "  $0 --port 8080        # Use different port"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run the Python startup script
echo "🐍 Running Python startup script..."
python3 start.py $ARGS
