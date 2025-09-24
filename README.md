# Search Agent with Server-Sent Events (SSE)

A minimalist implementation of a search agent using Server-Sent Events (SSE) for real-time communication.

## Overview

This search agent answers questions based on document content using:

- **Server-Sent Events (SSE)** for real-time updates
- **ChromaDB** for vector storage and retrieval
- **FastAPI** for the backend API
- **Minimalist UI** with clean black-on-white design

## Features

- Real-time search processing updates
- Clean, minimalist UI
- Citation support with source document display
- Conversation history and context

## Getting Started

### Prerequisites

- Python 3.8+
- ChromaDB
- Required Python packages (see `requirements.txt`)

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp env.sample .env
   # Edit .env with your configuration
   ```

### Running the Server

Start the server:
```bash
python run.py
```

The server will run on port 8001 by default. Access the UI by opening `http://localhost:8001/` in your web browser.

Additional options:
```bash
# Stop any running server instances
python run.py --stop

# Run on a different port
python run.py --port 8080

# Show help
python run.py --help
```

The script automatically kills any processes running on ports 8000 and 8001 before starting, ensuring a clean start every time.

### Testing

To test the SSE implementation directly:

```bash
python test_sse.py "Your query here"
```

## Architecture

### Backend Components

- **SSE Server (`apps/api/sse_server.py`)**: Handles SSE connections and streams search results
- **Search Agent (`agent/graph.py`)**: Processes search queries and generates answers
- **ChromaDB Adapter (`adapters/chroma_adapter.py`)**: Interfaces with the vector database

### Frontend Components

- **UI (`frontend/index.html`, `frontend/ssense.css`, `frontend/ssense.js`)**: Minimalist interface for the search agent

## Why SSE?

Server-Sent Events (SSE) offers several advantages:

1. **Simplicity**: Uses standard HTTP, making it easier to implement and deploy
2. **Compatibility**: Better support with HTTP infrastructure (proxies, load balancers)
3. **Automatic Reconnection**: Built-in reconnection handling in the EventSource API
4. **Unidirectional Flow**: Perfect for our use case where updates flow from server to client

## API Endpoints

### SSE Endpoint

- `GET /sse/agent`: Establishes an SSE connection for receiving real-time updates

### Query Endpoint

- `POST /api/query`: Submits a search query and streams the results
  - Request Body:
    ```json
    {
      "query": "Your question here",
      "query_id": "optional-unique-id",
      "session_id": "optional-session-id"
    }
    ```

## Event Types

1. **connected**: Sent when a client connects to the SSE endpoint
2. **node_update**: Sent when a search agent node updates its status
3. **answer**: Sent when the search agent completes processing a query
4. **error**: Sent when an error occurs during processing