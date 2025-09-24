// DOM Elements
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const chatMessages = document.getElementById('chat-messages');
const loadingIndicator = document.getElementById('loading-indicator');
const nodesContainer = document.getElementById('nodes-container');
const errorContainer = document.getElementById('error-container');
const queryHistoryContainer = document.getElementById('query-history-container');
const citationsContainer = document.getElementById('citations-container');

// Global variables
let socket;
let currentQueryId = null;
let isProcessingQuery = false;
let nodeStatuses = {};
let queryHistory = [];
let sessionId = generateSessionId();

// Initialize the app
function init() {
    // Create node elements
    createNodeElements();
    
    // Connect to WebSocket
    connectWebSocket();

// Set up event listeners
    queryForm.addEventListener('submit', handleQuerySubmit);
    
    // Load query history from localStorage
    loadQueryHistory();
}

// Generate a unique session ID
function generateSessionId() {
    return 's_' + Math.random().toString(36).substring(2, 15);
}

// Connect to WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || 'localhost';
    // Use the same host but connect to port 8000 for the WebSocket
    const wsUrl = `${protocol}//${host}:8000/ws/agent`;
    
    console.log(`Connecting to WebSocket at ${wsUrl}`);
    socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
        console.log('WebSocket connection established successfully');
        console.log('WebSocket connection established');
        errorContainer.style.display = 'none';
    };
    
    socket.onmessage = (event) => {
        console.log('WebSocket message received:', event.data);
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event.code, event.reason);
        console.log('WebSocket connection closed');
        errorContainer.innerHTML = '<p>WebSocket connection is not open. Please try again later.</p>';
        errorContainer.style.display = 'block';
        
        // Try to reconnect after a delay
        setTimeout(connectWebSocket, 3000);
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        console.error('WebSocket error:', error);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    console.log('WebSocket message received:', data);
    
    if (data.type === 'node_update') {
        console.log(`Node update: ${data.node_id} - ${data.status}`);
        isProcessingQuery = true; // Set flag when we get node updates
        updateNodeStatus(data.node_id, data.status, data.content, data.raw_content);
    } else if (data.type === 'answer') {
        console.log('Answer received with citations:', data);
        displayAnswer(data);
        isProcessingQuery = false; // Reset flag when answer is received
        
        // Add to query history
        addToQueryHistory({
            query: queryInput.value,
            answer: data.text, // Changed from data.content to data.text
            citations: data.citations,
            timestamp: new Date().toISOString(),
            query_id: currentQueryId,
            session_id: sessionId
        });
    } else if (data.type === 'error') {
        console.error('Error from server:', data);
        displayError(data.message || 'An error occurred while processing your query.');
        isProcessingQuery = false; // Reset flag on error
    }
}

// Handle query form submission
function handleQuerySubmit(event) {
    event.preventDefault();
    
    const query = queryInput.value.trim();
    if (!query) return;
    
    // Check if already processing a query
    if (isProcessingQuery) {
        alert('Please wait for the current query to complete.');
        return;
    }
    
    // Generate a query ID
    currentQueryId = generateQueryId();
    
    // Clear previous results and show loading
    clearResults();
    loadingIndicator.style.display = 'flex';
    
    // Add user message to chat
    addUserMessage(query);
    
    // Send the query to the server
    sendQuery(query, currentQueryId);
    
    // Clear the input
    queryInput.value = '';
}

// Generate a unique query ID
function generateQueryId() {
    return 'q_' + Math.random().toString(36).substring(2, 15);
}

// Send a query to the server
function sendQuery(query, queryId) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        displayError('WebSocket connection is not open. Please try again later.');
        loadingIndicator.style.display = 'none';
        return;
    }
    
    const message = {
        type: 'query',
        query_id: queryId,
        session_id: sessionId,
        content: query
    };
    
    socket.send(JSON.stringify(message));
    isProcessingQuery = true;
}

// Clear results and reset node statuses
function clearResults() {
    // Reset node statuses
    for (const nodeId in nodeStatuses) {
        nodeStatuses[nodeId] = 'pending';
    }
    
    // Update node UI
    for (const nodeId in nodeStatuses) {
        updateNodeUI(nodeId);
    }
    
    // Clear error container
    errorContainer.innerHTML = '';
    errorContainer.style.display = 'none';
    
    // Clear citations container
    citationsContainer.innerHTML = '';
    
    // Hide results container
    document.getElementById('results-container').style.display = 'none';
}

// Create node elements for the agent process visualization
function createNodeElements() {
    // Define the nodes in the agent process
    const nodes = [
        { id: 'listener', name: 'Listener', description: 'Receives and processes user queries' },
        { id: 'context_enhancer', name: 'Context Enhancer', description: 'Adds conversation context to the query' },
        { id: 'planner', name: 'Planner', description: 'Determines search strategy and parameters' },
        { id: 'candidate_search', name: 'Candidate Search', description: 'Performs initial broad search for relevant chunks' },
        { id: 'facet_discovery', name: 'Facet Discovery', description: 'Identifies metadata patterns in search results' },
        { id: 'facet_planner', name: 'Facet Planner', description: 'Plans targeted searches using discovered facets' },
        { id: 'narrowed_search', name: 'Narrowed Search', description: 'Executes targeted searches with facet filters' },
        { id: 'rerank_diversify', name: 'Rerank & Diversify', description: 'Reranks results and ensures diverse information' },
        { id: 'validator', name: 'Validator', description: 'Validates search results against the query' },
        { id: 'answerer', name: 'Answerer', description: 'Generates the final answer from validated results' }
    ];
    
    // Clear the container
    nodesContainer.innerHTML = '';
    
    // Create elements for each node
    nodes.forEach(node => {
        const nodeElement = document.createElement('div');
        nodeElement.className = 'node';
        nodeElement.id = `node-${node.id}`;
        nodeElement.innerHTML = `
            <div class="node-header">
                <span class="node-name">${node.name}</span>
                <span class="node-status status-pending">Pending</span>
            </div>
            <div class="node-summary">
                <div class="node-description">${node.description}</div>
                <div class="node-details"></div>
            </div>
        `;
        nodesContainer.appendChild(nodeElement);
        
        // Initialize node status
        nodeStatuses[node.id] = 'pending';
    });
}

// Update node status
function updateNodeStatus(nodeId, status, content, rawContent) {
    // Update the node status
    nodeStatuses[nodeId] = status;
    
    // Update the UI
    updateNodeUI(nodeId, status, content, rawContent);
}

// Update node UI
function updateNodeUI(nodeId, status = null, content = null, rawContent = null) {
    const nodeElement = document.getElementById(`node-${nodeId}`);
    if (!nodeElement) return;
    
    // Use the provided status or the stored status
    status = status || nodeStatuses[nodeId] || 'pending';
    
    // Determine the status class
    let statusClass = '';
    switch (status) {
        case 'in_progress':
            statusClass = 'status-in-progress';
            break;
        case 'completed':
            statusClass = 'status-completed';
            break;
        case 'error':
            statusClass = 'status-error';
            break;
        default:
            statusClass = 'status-pending';
    }
    
    // Get the header and update its class
    const nodeHeader = nodeElement.querySelector('.node-header');
    nodeHeader.className = `node-header ${status.replace('_', '-')}`;
    
    // Update the status text
    const nodeStatus = nodeElement.querySelector('.node-status');
    nodeStatus.className = `node-status ${statusClass}`;
    nodeStatus.textContent = formatStatus(status);
    
    // Generate a summary based on the node and content
    let summary = '';
    let details = '';
    
    if (content) {
        if (nodeId === 'candidate_search') {
            const count = content.count || 0;
            summary = `Found ${count} candidate chunks`;
            if (count > 0 && content.top_score) {
                details = `Top relevance score: ${(content.top_score * 100).toFixed(1)}%`;
            }
        } else if (nodeId === 'narrowed_search') {
            const count = content.count || 0;
            summary = `Retrieved ${count} relevant chunks`;
            if (content.branches && content.branches.length) {
                details = `Executed ${content.branches.length} search branches`;
            }
        } else if (nodeId === 'rerank_diversify') {
            const count = content.count || 0;
            summary = `Selected top ${count} diverse chunks`;
            if (content.diversity_score) {
                details = `Diversity score: ${(content.diversity_score * 100).toFixed(1)}%`;
            }
        } else if (nodeId === 'validator') {
            if (content.valid) {
                summary = 'Found relevant information';
                details = content.reason || 'Information matches query intent';
            } else {
                summary = 'No relevant information found';
                details = content.reason || 'Information does not match query intent';
            }
        } else if (nodeId === 'context_enhancer') {
            if (content.has_context) {
                summary = 'Enhanced query with conversation context';
                details = `Session ID: ${content.session_id || sessionId}`;
            } else {
                summary = 'Processing new query';
            }
        } else if (nodeId === 'facet_discovery') {
            if (content.facets && Object.keys(content.facets).length) {
                const facetCount = Object.keys(content.facets).length;
                summary = `Discovered ${facetCount} facet types`;
                details = Object.keys(content.facets).join(', ');
            } else {
                summary = 'No significant facets found';
            }
        } else if (nodeId === 'facet_planner') {
            if (content.branches && content.branches.length) {
                summary = `Planned ${content.branches.length} search branches`;
                details = content.branches.map(b => Object.keys(b.facets || {}).join('+')).join(', ');
            } else {
                summary = 'Using default search strategy';
            }
        } else if (nodeId === 'planner') {
            if (content.search_type) {
                summary = `Search type: ${content.search_type}`;
                if (content.alpha) {
                    details = `Hybrid alpha: ${content.alpha}`;
                }
        } else {
                summary = 'Planning search strategy';
            }
        } else if (nodeId === 'answerer') {
            summary = 'Generating answer';
            if (content.citation_count) {
                details = `Using ${content.citation_count} citations`;
            }
        }
    }
    
    // Update the summary
    const nodeSummaryEl = nodeElement.querySelector('.node-details');
    if (nodeSummaryEl) {
        nodeSummaryEl.textContent = summary || '';
    }
    
    // Update the details if any
    const nodeDetailsEl = nodeElement.querySelector('.node-details');
    if (nodeDetailsEl) {
        nodeDetailsEl.textContent = details || '';
    }
}

// Add a user message to the chat
function addUserMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message user-message';
    messageElement.innerHTML = `
        <div class="message-content">${formatText(text)}</div>
    `;
    chatMessages.appendChild(messageElement);
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add an agent message to the chat
function addAgentMessage(text, citations = []) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message agent-message';
    
    let citationsHtml = '';
    if (citations && citations.length > 0) {
        citationsHtml = `
            <div class="message-citations">
                ${citations.map((citation, index) => `
                    <span class="citation-link" data-index="${index}">[${index + 1}]</span>
                `).join('')}
            </div>
        `;
        
        // Also update the citations container
        displayCitations(citations);
    }
    
    messageElement.innerHTML = `
        <div class="message-content">${formatText(text)}</div>
        ${citationsHtml}
    `;
    
    // Add event listeners to citation links
    setTimeout(() => {
        const citationLinks = messageElement.querySelectorAll('.citation-link');
        citationLinks.forEach(link => {
            link.addEventListener('click', () => {
                const index = parseInt(link.getAttribute('data-index'));
                highlightCitation(index);
                document.getElementById('results-container').style.display = 'block';
            });
        });
    }, 0);
    
    chatMessages.appendChild(messageElement);
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Display the answer in the UI
function displayAnswer(data) {
    // Hide loading indicator
    loadingIndicator.style.display = 'none';
    
    // Add agent message to chat
    addAgentMessage(data.text, data.citations); // Changed from data.content to data.text
    
    // Show the citations container if there are citations
    if (data.citations && data.citations.length > 0) {
        document.getElementById('results-container').style.display = 'block';
    }
}

// Display citations in the UI
function displayCitations(citations) {
    citationsContainer.innerHTML = '';
    
    if (!citations || citations.length === 0) {
        citationsContainer.innerHTML = '<p class="history-empty">No citations available.</p>';
        return;
    }
    
        const citationsList = document.createElement('div');
        citationsList.className = 'citations-list';
        
        citations.forEach((citation, index) => {
            const citationItem = document.createElement('div');
            citationItem.className = 'citation-item';
        citationItem.id = `citation-${index}`;
            
            const docId = citation.doc_id || 'Unknown';
        const section = citation.section || 'Unknown';
        const chunkBody = citation.chunk_body || citation.body || 'No content available';
            
            citationItem.innerHTML = `
            <div class="citation-header">
                <span class="citation-number">${index + 1}</span>
                <span class="citation-doc">${docId}</span>
                <span class="citation-section">${section}</span>
                    </div>
            <div class="citation-content">${formatText(chunkBody)}</div>
            `;
            
            citationsList.appendChild(citationItem);
        });
        
    citationsContainer.appendChild(citationsList);
}

// Highlight a citation
function highlightCitation(index) {
    // Remove highlight from all citations
    document.querySelectorAll('.citation-item').forEach(item => {
        item.classList.remove('highlighted');
    });
    
    // Add highlight to the selected citation
    const citationItem = document.getElementById(`citation-${index}`);
    if (citationItem) {
        citationItem.classList.add('highlighted');
        citationItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Display an error message
function displayError(message) {
    // Hide loading indicator
    loadingIndicator.style.display = 'none';
    
    // Show error message
    errorContainer.innerHTML = `<p>${message}</p>`;
    errorContainer.style.display = 'block';
}

// Format node name for display
function formatNodeName(nodeId) {
    // Convert snake_case to Title Case
    return nodeId.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Format status for display
function formatStatus(status) {
    switch (status) {
        case 'in_progress':
            return 'In Progress';
        case 'completed':
            return 'Completed';
        case 'error':
            return 'Error';
        default:
            return 'Pending';
    }
}

// Format text for display (basic markdown-like formatting)
function formatText(text) {
    if (!text) return '';
    
    // Escape HTML
    text = text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;');
    
    // Convert markdown-style formatting
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
               .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
               .replace(/`(.*?)`/g, '<code>$1</code>') // Inline code
               .replace(/\n\n/g, '<br><br>') // Paragraphs
               .replace(/\n/g, '<br>'); // Line breaks
    
    return text;
}

// Add a query to the history
function addToQueryHistory(item) {
    // Add to the beginning of the array
    queryHistory.unshift(item);
    
    // Limit the history size
    if (queryHistory.length > 10) {
        queryHistory = queryHistory.slice(0, 10);
    }
    
    // Save to localStorage with session ID as key
    saveQueryHistory();
    
    // Update the UI
    updateQueryHistoryUI();
}

// Save query history to localStorage
function saveQueryHistory() {
    // Save history with session ID as part of the key
    localStorage.setItem(`queryHistory_${sessionId}`, JSON.stringify(queryHistory));
}

// Load query history from localStorage
function loadQueryHistory() {
    // Load history for current session only
    const savedHistory = localStorage.getItem(`queryHistory_${sessionId}`);
    if (savedHistory) {
        try {
            queryHistory = JSON.parse(savedHistory);
            updateQueryHistoryUI();
        } catch (e) {
            console.error('Error loading query history:', e);
            queryHistory = [];
        }
    } else {
        // No history for this session yet
        queryHistory = [];
    }
}

// Update query history UI
function updateQueryHistoryUI() {
    queryHistoryContainer.innerHTML = '';
    
    if (queryHistory.length === 0) {
        queryHistoryContainer.innerHTML = '<p class="history-empty">No history yet.</p>';
        return;
    }
    
    const historyList = document.createElement('div');
    historyList.className = 'history-list';
    
    queryHistory.forEach((item, index) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        
        // Format the timestamp
        const date = new Date(item.timestamp);
        const formattedTime = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
        
        historyItem.innerHTML = `
            <div class="history-header">
                <span class="history-time">${formattedTime}</span>
            </div>
            <div class="history-query">${item.query}</div>
        `;
        
        // Add click event to re-run the query
        historyItem.addEventListener('click', () => {
            queryInput.value = item.query;
            queryForm.dispatchEvent(new Event('submit'));
        });
        
        historyList.appendChild(historyItem);
    });
    
    queryHistoryContainer.appendChild(historyList);
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);