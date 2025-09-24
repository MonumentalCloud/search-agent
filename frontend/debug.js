// Debug script to test WebSocket connection
console.log('Debug script loaded');

// Test WebSocket connection
function testWebSocketConnection() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || 'localhost';
    const wsUrl = `${protocol}//${host}:8000/ws/agent`;
    
    console.log(`Connecting to WebSocket at ${wsUrl}`);
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
        console.log('WebSocket connection established');
        document.getElementById('ws-status').textContent = 'Connected';
        document.getElementById('ws-status').style.color = 'green';
        
        // Send a test message
        const testMessage = {
            type: 'query',
            query_id: 'debug_test_' + Math.random().toString(36).substring(2, 15),
            content: 'What are the meeting dates?',
            session_id: 'debug_session'
        };
        
        console.log('Sending test message:', testMessage);
        socket.send(JSON.stringify(testMessage));
    };
    
    socket.onmessage = (event) => {
        console.log('WebSocket message received:', event.data);
        try {
            const data = JSON.parse(event.data);
            document.getElementById('ws-response').textContent = JSON.stringify(data, null, 2);
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
            document.getElementById('ws-response').textContent = event.data;
        }
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        document.getElementById('ws-status').textContent = 'Error';
        document.getElementById('ws-status').style.color = 'red';
    };
    
    socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        document.getElementById('ws-status').textContent = 'Disconnected';
        document.getElementById('ws-status').style.color = 'red';
    };
}

// Create debug UI
function createDebugUI() {
    const debugContainer = document.createElement('div');
    debugContainer.style.position = 'fixed';
    debugContainer.style.bottom = '10px';
    debugContainer.style.right = '10px';
    debugContainer.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    debugContainer.style.color = 'white';
    debugContainer.style.padding = '10px';
    debugContainer.style.borderRadius = '5px';
    debugContainer.style.zIndex = '9999';
    debugContainer.style.maxWidth = '400px';
    debugContainer.style.maxHeight = '300px';
    debugContainer.style.overflow = 'auto';
    
    debugContainer.innerHTML = `
        <h3>WebSocket Debug</h3>
        <div>Status: <span id="ws-status">Disconnected</span></div>
        <button id="ws-connect">Connect</button>
        <button id="ws-disconnect">Disconnect</button>
        <h4>Response:</h4>
        <pre id="ws-response" style="max-height: 150px; overflow: auto; background-color: #333; padding: 5px;"></pre>
    `;
    
    document.body.appendChild(debugContainer);
    
    document.getElementById('ws-connect').addEventListener('click', testWebSocketConnection);
    document.getElementById('ws-disconnect').addEventListener('click', () => {
        if (socket) {
            socket.close();
        }
    });
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, creating debug UI');
    createDebugUI();
});
