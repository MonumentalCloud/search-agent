# SSE Connection Fixes

## Overview

This document describes the fixes made to ensure proper Server-Sent Events (SSE) communication between the frontend and backend.

## Issues Fixed

### 1. Query ID Association

**Problem:** The frontend was sending a POST request to `/api/query` and establishing an SSE connection to `/sse/agent`, but these two connections were not associated with each other. This meant that the SSE events generated during query processing were not being properly received by the frontend.

**Solution:** 
- Modified the frontend to include the query ID in the SSE connection URL
- Updated the SSE endpoint to accept and use this query ID parameter
- Established a new SSE connection for each query to ensure proper event routing

### 2. Connection Timing

**Problem:** The frontend was establishing a single SSE connection at initialization and not refreshing it for each query.

**Solution:**
- Maintained the initial SSE connection for global events
- Added code to establish a new SSE connection with the specific query ID when a query is submitted
- This ensures that each query has its own dedicated SSE connection for real-time updates

## Code Changes

### Frontend Changes

1. **Updated SSE Connection Function:**
   ```javascript
   // Connect to SSE
   function connectSSE(queryId) {
       const protocol = window.location.protocol;
       const host = window.location.hostname || 'localhost';
       const port = window.location.port || '8001';
       
       // If queryId is provided, include it in the URL to associate this connection with the query
       const sseUrl = queryId 
           ? `${protocol}//${host}:${port}/sse/agent?query_id=${queryId}` 
           : `${protocol}//${host}:${port}/sse/agent`;
       
       console.log(`Connecting to SSE at ${sseUrl}`);
       
       if (eventSource) {
           eventSource.close();
       }
       
       eventSource = new EventSource(sseUrl);
       // ...
   }
   ```

2. **Updated Query Submission:**
   ```javascript
   // Add agent message with loading indicator
   addAgentProcessingMessage(currentQueryId);
   
   // Establish a new SSE connection with this query ID
   connectSSE(currentQueryId);
   
   // Send the query to the server
   sendQuery(query, currentQueryId);
   ```

### Backend Changes

1. **Updated SSE Endpoint:**
   ```python
   @app.get("/sse/agent")
   async def sse_endpoint(request: Request, query_id: Optional[str] = None):
       client_id = query_id or str(uuid.uuid4())
       logger.info(f"SSE connection request received from {client_id} with query_id: {query_id}")
       # ...
   ```

## How It Works Now

1. When the frontend loads, it establishes an initial SSE connection without a specific query ID
2. When a user submits a query:
   - A unique query ID is generated
   - The frontend establishes a new SSE connection with this query ID
   - The frontend sends the query to the server using a POST request with the same query ID
3. The backend processes the query and sends real-time updates via the SSE connection
4. The frontend receives these updates and displays them in the UI
5. When the query is complete, the final answer is sent as an SSE event

This ensures that all SSE events related to a specific query are properly received by the frontend, allowing for real-time updates during query processing.

## Testing

To test the SSE connection:

1. Open the browser console
2. Submit a query in the UI
3. Observe the SSE connection being established with the query ID
4. Watch for real-time updates in the console and UI
5. Verify that the final answer is displayed correctly
