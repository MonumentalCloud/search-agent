# Server-Sent Events (SSE) Implementation

This document describes the Server-Sent Events (SSE) implementation that replaces the WebSocket-based communication in the search agent.

## Overview

Server-Sent Events (SSE) is a standard that enables servers to push real-time updates to clients over a single HTTP connection. Unlike WebSockets, SSE is unidirectional (server to client only) and uses standard HTTP, making it simpler to implement and more compatible with existing infrastructure.

## Key Components

### Backend Implementation

1. **SSE Server (`apps/api/sse_server.py`)**
   - Provides SSE endpoints for real-time updates
   - Handles client connections and message delivery
   - Processes search queries and streams results

2. **SSE Manager**
   - Manages client connections
   - Tracks active connections and handles disconnections

3. **SSE Observer**
   - Observes the search agent's processing nodes
   - Queues updates for delivery to clients
   - Creates summaries of node updates for the frontend

### Frontend Implementation

1. **SSE Client (`frontend/ssense.js`)**
   - Connects to the SSE endpoint using the EventSource API
   - Processes incoming SSE events
   - Updates the UI with real-time information

2. **Minimalist UI (`frontend/ssense.html`, `frontend/ssense.css`)**
   - Clean, SSense-style design with black text on white background
   - Shows real-time processing updates within the chat interface
   - Displays citations and source documents

## Event Types

1. **connected**
   - Sent when a client successfully connects to the SSE endpoint
   - Contains the client ID for tracking

2. **node_update**
   - Sent when a search agent node updates its status
   - Contains a summary of the update for display in the UI
   - Includes the node ID, status, and detailed content

3. **answer**
   - Sent when the search agent completes processing a query
   - Contains the final answer text and citations
   - Includes enhanced citation information with document content

4. **error**
   - Sent when an error occurs during processing
   - Contains an error message for display in the UI

## How It Works

1. **Client Connection**
   - The client connects to the `/sse/agent` endpoint using the EventSource API
   - The server accepts the connection and assigns a unique client ID
   - The server sends a "connected" event to confirm the connection

2. **Query Processing**
   - The client sends a query to the `/api/query` endpoint using a standard HTTP POST request
   - The server starts processing the query and creates an SSE stream for the response
   - As the search agent processes the query, node updates are sent as SSE events
   - The frontend displays these updates in real-time within the chat interface

3. **Result Delivery**
   - When the search agent completes processing, the final answer is sent as an "answer" event
   - The frontend updates the UI to display the answer and citations
   - The SSE connection remains open for future queries

## Benefits Over WebSockets

1. **Simplicity**
   - SSE uses standard HTTP, making it simpler to implement and deploy
   - No need for special protocols or libraries

2. **Compatibility**
   - Works with standard HTTP infrastructure (proxies, load balancers, etc.)
   - Better support in older browsers and environments

3. **Automatic Reconnection**
   - The EventSource API automatically handles reconnection if the connection is lost
   - Reduces the need for complex reconnection logic in the client

4. **Lower Overhead**
   - SSE has lower overhead than WebSockets for unidirectional communication
   - Efficient for the search agent's use case, where updates flow primarily from server to client

## Usage

### Running the SSE Server

```bash
python run_sse_server.py
```

### Testing the SSE Implementation

```bash
python test_sse_client.py "Your query here"
```

### Accessing the Frontend

Open `http://localhost:8000/ssense.html` in your web browser to access the minimalist SSense-style frontend.

## Future Improvements

1. **Authentication and Authorization**
   - Add user authentication for secure access to the search agent
   - Implement authorization for different user roles

2. **Connection Pooling**
   - Optimize server resources by implementing connection pooling
   - Handle large numbers of concurrent connections efficiently

3. **Compression**
   - Implement compression for SSE events to reduce bandwidth usage
   - Particularly useful for large result sets

4. **Offline Support**
   - Add service workers for offline support
   - Cache previous search results for offline access
