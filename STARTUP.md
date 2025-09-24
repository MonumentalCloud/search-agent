# Retrieval Agent Startup Guide

## Quick Start

### Option 1: Python Script
```bash
python start.py
```

### Option 2: Shell Script
```bash
./start.sh
```

## What the Startup Script Does

1. **Installs Dependencies** - Installs all required Python packages
2. **Starts Weaviate** - Launches Weaviate vector database (if Docker is available)
3. **Ingests PDFs** - Processes all PDFs in the `data/` directory
4. **Rebuilds Metadata Vectors** - Creates facet-value vectors for better search
5. **Starts API Server** - Launches the FastAPI server
6. **Tests System** - Runs a sample query to verify everything works

## Command Line Options

### Full Startup (Default)
```bash
python start.py
```
- Installs dependencies
- Starts Weaviate (if Docker available)
- Ingests PDFs from `data/` directory
- Rebuilds metadata vectors
- Starts API server on port 8001
- Tests system with sample query

### API Only Mode
```bash
python start.py --api-only
```
- Only starts the API server
- Skips all setup steps

### Chat GUI Mode
```bash
python start.py --chat-only
# or
python chat.py
# or
make chat
```
- Only starts the Streamlit chat interface
- Requires API server to be running separately

### Skip Specific Steps
```bash
python start.py --skip-docker    # Skip Weaviate setup
python start.py --skip-ingest    # Skip PDF ingestion
python start.py --skip-vectors   # Skip metadata vector rebuild
python start.py --skip-test      # Skip system test
```

### Custom Configuration
```bash
python start.py --host 0.0.0.0 --port 8080  # Custom host/port
python start.py --verbose                    # Verbose logging
```

## API Endpoints

Once started, the system provides these endpoints:

- **Health Check**: `GET http://localhost:8001/health`
- **Query Agent**: `POST http://localhost:8001/agent/query`
- **Ingest PDFs**: `POST http://localhost:8001/ingest/data-directory`
- **API Docs**: `GET http://localhost:8001/docs`

## Chat GUI

The system includes a beautiful Streamlit-based chat interface:

- **Chat Interface**: `http://localhost:8501`
- **Features**: Real-time streaming, thought process visualization, citations, performance metrics
- **Sample Queries**: Pre-loaded Korean financial regulation questions

## Example Usage

### Start Everything
```bash
python start.py
```

### Start Without Docker (Offline Mode)
```bash
python start.py --skip-docker
```

### Start API Only (for development)
```bash
python start.py --api-only
```

### Custom Port
```bash
python start.py --port 8080
```

## Troubleshooting

### Docker Not Available
If Docker is not installed, use:
```bash
python start.py --skip-docker
```
The system will work in offline mode with placeholder responses.

### Port Already in Use
Change the port:
```bash
python start.py --port 8080
```

### PDF Ingestion Fails
Check that PDFs exist in the `data/` directory:
```bash
ls data/*.pdf
```

### Weaviate Connection Issues
Check if Weaviate is running:
```bash
curl http://localhost:8080/v1/meta
```

## System Requirements

- Python 3.8+
- Docker (optional, for Weaviate)
- 8GB+ RAM (recommended for Weaviate)

## What Gets Ingested

The startup script automatically processes:
- All PDF files in the `data/` directory
- Korean financial regulation documents
- Extracts sections and creates searchable chunks
- Builds metadata vectors for better search relevance
