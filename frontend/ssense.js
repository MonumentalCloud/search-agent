// DOM Elements
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const chatMessages = document.getElementById('chat-messages');
const errorContainer = document.getElementById('error-container');

// Global variables
let currentQueryId = null;
let isProcessingQuery = false;
let eventSource = null;
let sessionId = generateSessionId();
let processingUpdates = {};

// Debug data storage
let currentWorkflowData = null;
let currentNodeUpdates = [];

// Initialize the app
function init() {
    // Set up event listeners
    queryForm.addEventListener('submit', handleQuerySubmit);
    
    // Debug export event listeners (only if elements exist)
    const downloadWorkflowBtn = document.getElementById('download-workflow');
    const downloadNodeUpdatesBtn = document.getElementById('download-node-updates');
    const downloadCompleteDebugBtn = document.getElementById('download-complete-debug');
    
    if (downloadWorkflowBtn) downloadWorkflowBtn.addEventListener('click', downloadWorkflow);
    if (downloadNodeUpdatesBtn) downloadNodeUpdatesBtn.addEventListener('click', downloadNodeUpdates);
    if (downloadCompleteDebugBtn) downloadCompleteDebugBtn.addEventListener('click', downloadCompleteDebug);
}

// Generate a unique session ID
function generateSessionId() {
    return 's_' + Math.random().toString(36).substring(2, 15);
}

// Connect to SSE
function connectSSE(queryId) {
    // Use relative URL for internal communication on Render
    const sseUrl = queryId 
        ? `/sse/agent?query_id=${queryId}` 
        : `/sse/agent`;
    
    console.log(`Connecting to SSE at ${sseUrl}`);
    
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(sseUrl);
    
    eventSource.onopen = () => {
        console.log('SSE connection established');
        console.log('EventSource readyState:', eventSource.readyState);
        errorContainer.style.display = 'none';
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        console.log('EventSource readyState:', eventSource.readyState);
        console.log('EventSource url:', eventSource.url);
        errorContainer.innerHTML = '<p>Connection error. Reconnecting...</p>';
        errorContainer.style.display = 'block';
        
        // Try to reconnect after a delay
        setTimeout(() => connectSSE(queryId), 3000);
    };
    
    // Listen for connected event
    eventSource.addEventListener('connected', (event) => {
        console.log('Received connected event:', event);
        const data = JSON.parse(event.data);
        console.log('SSE connected:', data);
    });
    
    // Listen for node_update events
    eventSource.addEventListener('node_update', (event) => {
        console.log('Received node_update event:', event);
        const data = JSON.parse(event.data);
        console.log('Node update:', data);
        
        // Store the processing update
        if (!processingUpdates[data.query_id]) {
            processingUpdates[data.query_id] = [];
        }
        
        // Add the update to the list
        processingUpdates[data.query_id].push({
            node_id: data.node_id,
            status: data.status,
            summary: data.summary
        });
        
        // Update the UI
        updateProcessingUI(data.query_id);
    });
    
    // Listen for processing started events
    eventSource.addEventListener('processing_started', (event) => {
        const data = JSON.parse(event.data);
        console.log('Processing started:', data);
        
        // Update the processing UI
        updateProcessingUI(data.query_id);
    });
    
    // Listen for answer events
    eventSource.addEventListener('answer', (event) => {
        const data = JSON.parse(event.data);
        console.log('Answer received:', data);
        
        // Display the answer
        displayAnswer(data);
        
        // Reset processing state
        isProcessingQuery = false;
        
        // Clear processing updates
        processingUpdates[data.query_id] = [];
    });
    
    // Listen for error events
    eventSource.addEventListener('error', (event) => {
        const data = JSON.parse(event.data);
        console.error('Error from server:', data);
        
        // Display the error
        displayError(data.message || 'An error occurred while processing your query.');
        
        // Reset processing state
        isProcessingQuery = false;
    });
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
    
    // Clear previous results
    clearResults();
    
    // Add user message to chat
    addUserMessage(query);
    
    // Add agent message with loading indicator
    addAgentProcessingMessage(currentQueryId);
    
    // Send the query to the server (this will return an SSE stream)
    sendQuery(query, currentQueryId);
    
    // Clear the input
    queryInput.value = '';
}

// Generate a unique query ID
function generateQueryId() {
    return 'q_' + Math.random().toString(36).substring(2, 15);
}

// Generate workflow visualization
function generateBoostVisualization(boostInfo) {
    if (!boostInfo) return '';
    
    const winners = boostInfo.winners || [];
    const losers = boostInfo.losers || [];
    const queryIntent = boostInfo.query_intent || {};
    
    let html = `
        <div class="boost-visualization" style="
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 12px;
            margin-top: 8px;
        ">
            <div style="font-size: 0.75em; color: #666; margin-bottom: 8px;">
                Query Intent: ${queryIntent.intent || 'Unknown'} | 
                Detected: ${queryIntent.day_of_week ? queryIntent.day_of_week.join(', ') : 'None'} | 
                Entities: ${queryIntent.entities ? queryIntent.entities.join(', ') : 'None'}
            </div>
    `;
    
    if (winners.length > 0) {
        html += `
            <div style="margin-bottom: 12px;">
                <div style="font-size: 0.8em; color: #28a745; font-weight: 600; margin-bottom: 6px;">🏆 Top 3 Boosted Chunks</div>
                <div style="display: flex; flex-direction: column; gap: 4px;">
        `;
        
        winners.forEach(winner => {
            const topic = winner.topic || 'Unknown Topic';
            const date = winner.meeting_date || 'N/A';
            const boostChange = winner.boost_change || 0;
            const positionChange = winner.position_change || 0;
            const reasons = winner.reasons || [];
            
            html += `
                <div style="
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    padding: 6px 8px;
                    font-size: 0.8em;
                ">
                    <div style="font-weight: 500; color: #155724;">${topic}</div>
                    <div style="color: #666; font-size: 0.75em;">
                        📅 ${date} | 
                        📈 +${boostChange.toFixed(2)} boost | 
                        ⬆️ ${positionChange > 0 ? `+${positionChange}` : positionChange} positions
                    </div>
                    <div style="color: #666; font-size: 0.7em; margin-top: 2px;">
                        ${reasons.join(' • ')}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    if (losers.length > 0) {
        html += `
            <div>
                <div style="font-size: 0.8em; color: #dc3545; font-weight: 600; margin-bottom: 6px;">📉 Bottom 3 Debuffed Chunks</div>
                <div style="display: flex; flex-direction: column; gap: 4px;">
        `;
        
        losers.forEach(loser => {
            const topic = loser.topic || 'Unknown Topic';
            const date = loser.meeting_date || 'N/A';
            const boostChange = loser.boost_change || 0;
            const positionChange = loser.position_change || 0;
            const reasons = loser.reasons || [];
            
            html += `
                <div style="
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 6px 8px;
                    font-size: 0.8em;
                ">
                    <div style="font-weight: 500; color: #721c24;">${topic}</div>
                    <div style="color: #666; font-size: 0.75em;">
                        📅 ${date} | 
                        📉 ${boostChange.toFixed(2)} boost | 
                        ⬇️ ${positionChange < 0 ? positionChange : `+${positionChange}`} positions
                    </div>
                    <div style="color: #666; font-size: 0.7em; margin-top: 2px;">
                        ${reasons.join(' • ')}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    html += `
        </div>
    `;
    
    return html;
}

function generateWorkflowVisualization(schema) {
    if (!schema) return '';
    
    // Parse the schema to extract nodes and connections
    let nodes = [];
    
    // Handle arrow-separated workflow schemas (e.g., "semantic_search -> extract_dates -> filter_tuesdays -> format_results")
    if (schema.includes(' -> ')) {
        nodes = schema.split(' -> ').map(node => node.trim()).filter(node => node);
    } else {
        // Fallback: try to extract nodes from the text
        const lines = schema.split('\n').filter(line => line.trim());
        lines.forEach(line => {
            // Look for workflow steps in the schema
            const workflowSteps = line.match(/\b\w+(?:_\w+)*\b/g);
            if (workflowSteps) {
                workflowSteps.forEach(step => {
                    // Filter out common words and keep meaningful workflow steps
                    const meaningfulSteps = ['comprehensive_search', 'semantic_search', 'data_extraction', 
                                           'computation', 'complex_filtering', 'answerer', 'listener', 
                                           'context_enhancer', 'planner', 'candidate_search', 'facet_discovery', 
                                           'facet_planner', 'narrowed_search', 'rerank_diversify', 'validator', 
                                           'memory_updater', 'python_runtime', 'extract_dates', 'filter_tuesdays', 
                                           'format_results'];
                    
                    if (meaningfulSteps.includes(step) && !nodes.includes(step)) {
                        nodes.push(step);
                    }
                });
            }
        });
    }
    
    // If no meaningful nodes found, create a simple flow
    if (nodes.length === 0) {
        nodes.push('search', 'process', 'respond');
    }
    
    // Calculate layout
    const containerWidth = Math.max(400, nodes.length * 100 + 40);
    const nodeWidth = 80;
    const nodeHeight = 32;
    const spacing = 100;
    
    // Create node elements with better positioning
    const nodeElements = nodes.map((node, index) => {
        const x = 20 + (index * spacing);
        const y = 20;
        
        // Style nodes differently based on type
        let nodeStyle = 'workflow-node';
        if (node.includes('search') || node === 'semantic_search') {
            nodeStyle += ' search-node';
        } else if (node.includes('computation') || node.includes('python') || node.includes('extract') || node.includes('filter')) {
            nodeStyle += ' compute-node';
        } else if (node.includes('answerer') || node.includes('format')) {
            nodeStyle += ' output-node';
        }
        
        return `
            <div class="${nodeStyle}" style="
                left: ${x}px;
                top: ${y}px;
                width: ${nodeWidth}px;
                height: ${nodeHeight}px;
            ">
                ${node.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </div>
        `;
    }).join('');
    
    // Create connection lines
    const connectionElements = nodes.slice(0, -1).map((_, index) => {
        const startX = 20 + (index * spacing) + nodeWidth;
        const endX = 20 + ((index + 1) * spacing);
        const y = 36;
        const lineWidth = endX - startX;
        
        return `
            <div class="workflow-connection" style="
                left: ${startX}px;
                top: ${y}px;
                width: ${lineWidth}px;
            "></div>
            <div class="workflow-arrow" style="
                left: ${endX - 10}px;
                top: ${y - 4}px;
            "></div>
        `;
    }).join('');
    
    return `
        <div class="workflow-container" style="width: ${containerWidth}px; height: 80px;">
            ${nodeElements}
            ${connectionElements}
        </div>
    `;
}

// Handle SSE events from the streaming response
function handleSSEEvent(eventType, eventData) {
    console.log(`Received SSE event: ${eventType}`, eventData);
    
    switch (eventType) {
        case 'processing_started':
            console.log('Processing started:', eventData);
            updateProcessingUI(eventData.query_id);
            break;
            
        case 'node_update':
            console.log('Node update:', eventData);
            
            // Store the processing update
            if (!processingUpdates[eventData.query_id]) {
                processingUpdates[eventData.query_id] = [];
            }
            
            const nodeUpdate = {
                node_id: eventData.node_id,
                status: eventData.status,
                summary: eventData.summary,
                content: eventData.content,
                timestamp: new Date().toISOString()
            };
            
            // Add the update to the list
            processingUpdates[eventData.query_id].push(nodeUpdate);
            
            // Store for debug export
            currentNodeUpdates.push(nodeUpdate);
            
            // Capture workflow data from meta_agent completed
            if (eventData.node_id === 'meta_agent' && eventData.status === 'completed' && eventData.content) {
                currentWorkflowData = {
                    query: eventData.content.query || '',
                    workflow_type: eventData.content.workflow_type,
                    complexity_score: eventData.content.complexity_score,
                    reasoning: eventData.content.reasoning,
                    workflow_schema: eventData.content.workflow_schema,
                    agent_summary: eventData.content.agent_summary,
                    workflow_steps: eventData.content.workflow_steps,
                    required_components: eventData.content.required_components,
                    python_code: eventData.content.python_code,
                    timestamp: new Date().toISOString()
                };
            }
            
            // Update the UI
            updateProcessingUI(eventData.query_id);
            break;
            
        case 'answer':
            console.log('Answer received:', eventData);
            
            // Display the answer
            displayAnswer(eventData);
            
            // Reset processing state
            isProcessingQuery = false;
            
            // Clear processing updates
            processingUpdates[eventData.query_id] = [];
            break;
            
        case 'error':
            console.error('Error from server:', eventData);
            
            // Display the error
            displayError(eventData.message || 'An error occurred while processing your query.');
            
            // Reset processing state
            isProcessingQuery = false;
            break;
            
        default:
            console.log('Unknown SSE event type:', eventType, eventData);
    }
}

// Send a query to the server and handle SSE response
function sendQuery(query, queryId) {
    // Use relative URL for internal communication on Render
    const queryUrl = '/api/query';
    
    console.log(`Sending query to ${queryUrl}`);
    
    // Set processing state
    isProcessingQuery = true;
    
    // Initialize processing updates for this query
    processingUpdates[queryId] = [];
    
    // Reset debug data for new query
    currentWorkflowData = null;
    currentNodeUpdates = [];
    currentQueryId = queryId;
    
    // Hide debug export section (only if it exists)
    const debugExport = document.getElementById('debug-export');
    if (debugExport) {
        debugExport.style.display = 'none';
    }
    
    // Send the query as a POST request and handle SSE response
    fetch(queryUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: query,
            query_id: queryId,
            session_id: sessionId
        })
    }).then(response => {
        // Check if the response is ok (status in the range 200-299)
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        console.log('Query sent successfully, processing SSE stream...');
        
        // Handle the SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        function readStream() {
            return reader.read().then(({ done, value }) => {
                if (done) {
                    console.log('SSE stream completed');
                    return;
                }
                
                // Decode the chunk
                buffer += decoder.decode(value, { stream: true });
                
                // Process complete SSE messages
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer
                
                let eventType = 'message';
                let data = '';
                
                for (let line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.substring(7);
                    } else if (line.startsWith('data: ')) {
                        data = line.substring(6);
                    } else if (line === '') {
                        // Empty line indicates end of message
                        if (data) {
                            try {
                                const eventData = JSON.parse(data);
                                handleSSEEvent(eventType, eventData);
                            } catch (e) {
                                console.error('Error parsing SSE data:', e, data);
                            }
                        }
                        eventType = 'message';
                        data = '';
                    }
                }
                
                // Continue reading
                return readStream();
            });
        }
        
        readStream().catch(error => {
            console.error('Error reading SSE stream:', error);
            displayError('Error processing response stream.');
            isProcessingQuery = false;
        });
        
    }).catch(error => {
        console.error('Error sending query:', error);
        displayError('Failed to send query. Please try again.');
        isProcessingQuery = false;
    });
}

// Clear results
function clearResults() {
    // Clear error container
    errorContainer.innerHTML = '';
    errorContainer.style.display = 'none';
}

// Add a user message to the chat
function addUserMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message user-message';
    messageElement.innerHTML = `
        <div class="message-header">
            <div class="message-avatar user-avatar">U</div>
            <div class="message-role">You</div>
        </div>
        <div class="message-content">${formatText(text)}</div>
    `;
    chatMessages.appendChild(messageElement);
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add an agent message with loading indicator
function addAgentProcessingMessage(queryId) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message agent-message';
    messageElement.id = `agent-message-${queryId}`;
    messageElement.innerHTML = `
        <div class="message-header">
            <div class="message-avatar agent-avatar">A</div>
            <div class="message-role">Agent</div>
        </div>
        <div class="message-content">
            <div class="loading-indicator"></div>
        </div>
        <div class="processing-updates" id="processing-updates-${queryId}"></div>
    `;
    chatMessages.appendChild(messageElement);
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update the processing UI with the latest updates
function updateProcessingUI(queryId) {
    const processingElement = document.getElementById(`processing-updates-${queryId}`);
    if (!processingElement) return;
    
    // Get the updates for this query
    const updates = processingUpdates[queryId] || [];
    
    // Show all updates in reverse order (latest first)
    const sortedUpdates = [...updates].reverse();
    
    // Create HTML for the updates - clean and minimal
    const updatesHTML = sortedUpdates.map((update, index) => {
        let updateHTML = `
            <div class="processing-update">
                <div style="font-size: 0.8em; color: #999; text-transform: uppercase; letter-spacing: 0.5px;">${update.node_id.replace('_', ' ')}</div>
                <div style="font-size: 0.9em; color: #666; margin-top: 2px;">${update.summary}</div>
        `;
        
                    // Add workflow schema for meta_agent completed
                    if (update.node_id === 'meta_agent' && update.status === 'completed' && update.content && update.content.workflow_schema) {
                        updateHTML += `
                            <div style="margin-top: 12px;">
                                <div style="font-size: 0.8em; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Generated Workflow</div>
                                <div class="workflow-visualization">
                                    ${generateWorkflowVisualization(update.content.workflow_schema)}
                                </div>
                            </div>
                        `;
                    }
                    
                    // Add boost winners and losers for complex_filtering completed
                    if (update.node_id === 'complex_filtering' && update.status === 'completed' && update.content && update.content.boost_info) {
                        updateHTML += `
                            <div style="margin-top: 12px;">
                                <div style="font-size: 0.8em; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Soft Filtering Results</div>
                                ${generateBoostVisualization(update.content.boost_info)}
                            </div>
                        `;
                    }
        
        updateHTML += `</div>`;
        return updateHTML;
    }).join('');
    
    // Update the element
    processingElement.innerHTML = updatesHTML;
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Display the answer in the UI
function displayAnswer(data) {
    // Get the agent message element
    const messageElement = document.getElementById(`agent-message-${data.query_id}`);
    if (!messageElement) return;
    
    // Update the message content
    const messageContent = messageElement.querySelector('.message-content');
    if (messageContent) {
        messageContent.innerHTML = formatText(data.text);
    }
    
    // Collapse the processing updates instead of clearing them
    const processingElement = document.getElementById(`processing-updates-${data.query_id}`);
    if (processingElement) {
        processingElement.classList.add('collapsed');
        
        // Add a toggle button to expand/collapse
        const toggleButton = document.createElement('div');
        toggleButton.className = 'processing-toggle';
        toggleButton.innerHTML = '▼ Processing Details';
        toggleButton.style.cssText = `
            cursor: pointer;
            font-size: 0.8em;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
            padding: 0.25rem 0;
            border-bottom: 1px solid var(--border-color);
        `;
        
        toggleButton.onclick = () => {
            processingElement.classList.toggle('collapsed');
            toggleButton.innerHTML = processingElement.classList.contains('collapsed') 
                ? '▼ Processing Details' 
                : '▲ Processing Details';
        };
        
        // Insert the toggle button before the processing updates
        processingElement.parentNode.insertBefore(toggleButton, processingElement);
    }
    
    // Show debug export section if we have workflow data
    if (currentWorkflowData || currentNodeUpdates.length > 0) {
        const debugExport = document.getElementById('debug-export');
        debugExport.style.display = 'block';
    }
    
    // Add citations if available
    if (data.citations && data.citations.length > 0) {
        const citationsElement = document.createElement('div');
        citationsElement.className = 'citations';
        
        // Add citation buttons
        data.citations.forEach((citation, index) => {
            const citationButton = document.createElement('span');
            citationButton.className = 'citation';
            citationButton.textContent = `[${index + 1}]`;
            citationButton.dataset.index = index;
            citationButton.dataset.queryId = data.query_id;
            
            // Add click event to show citation content
            citationButton.addEventListener('click', () => {
                showCitationContent(data.query_id, index, citation);
            });
            
            citationsElement.appendChild(citationButton);
        });
        
        // Add citations container to message
        messageElement.appendChild(citationsElement);
        
        // Create a container for citation content
        const citationContentElement = document.createElement('div');
        citationContentElement.className = 'citation-content';
        citationContentElement.id = `citation-content-${data.query_id}`;
        citationContentElement.style.display = 'none';
        messageElement.appendChild(citationContentElement);
    }
    
    // Scroll to the bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Show citation content
async function showCitationContent(queryId, index, citation) {
    const citationContentElement = document.getElementById(`citation-content-${queryId}`);
    if (!citationContentElement) return;
    
    // Show loading state
    citationContentElement.innerHTML = `
        <div class="citation-detail" style="
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            font-size: 0.9em;
            text-align: center;
            color: #6c757d;
        ">
            <div>Loading document details...</div>
        </div>
    `;
    citationContentElement.style.display = 'block';
    
    try {
        // Fetch rich document information from the API
        const chunkId = citation.doc_id || citation.chunk_id;
        const protocol = 'http:';
        const host = window.location.hostname || 'localhost';
        const port = window.location.port || '8001';
        const apiUrl = `${protocol}//${host}:${port}/api/document/${encodeURIComponent(chunkId)}`;
        
        const response = await fetch(apiUrl);
        const docInfo = await response.json();
        
        if (docInfo.error) {
            throw new Error(docInfo.error);
        }
        
        // Display rich document information
        citationContentElement.innerHTML = createRichCitationHTML(index, docInfo);
        
    } catch (error) {
        console.error('Error fetching document details:', error);
        
        // Fallback to enhanced basic citation display
        const docId = citation.doc_id || 'Unknown';
        const chunkBody = citation.chunk_body || citation.body || 'No content available';
        const meetingDate = citation.valid_from || 'Unknown Date';
        const docTitle = parseDocumentTitle(docId);
        const dayOfWeek = getDayOfWeek(meetingDate);
        
        // Extract additional information from the document ID
        const documentType = extractDocumentType(docId);
        const documentNumber = extractDocumentNumber(docId);
        
        citationContentElement.innerHTML = createGenericCitationHTML(
            index, 
            docTitle, 
            meetingDate, 
            dayOfWeek, 
            documentType, 
            documentNumber, 
            chunkBody, 
            docId, 
            citation.chunk_id
        );
    }
    
    // Scroll to the citation content
    citationContentElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function parseDocumentTitle(docId) {
    // Parse document ID to create a more readable title
    if (!docId || docId === 'Unknown') return 'Unknown Document';
    
    // Remove file extensions and clean up the document ID
    let title = docId;
    
    // Handle various document naming patterns
    if (title.includes('_')) {
        // Split by underscore and create readable title
        const parts = title.split('_');
        if (parts.length >= 2) {
            // Take the meaningful parts and join them
            const meaningfulParts = parts.slice(1); // Skip first part (usually doc type)
            return meaningfulParts.join(' ').replace(/[_:]/g, ' ').replace(/\s+/g, ' ').trim();
        }
    }
    
    // Fallback: clean up the document ID
    return title.replace(/[_:]/g, ' ').replace(/\s+/g, ' ').trim();
}

function getDayOfWeek(dateString) {
    if (!dateString || dateString === 'Unknown Date') return null;
    
    try {
        const date = new Date(dateString);
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[date.getDay()];
    } catch (e) {
        return null;
    }
}

function extractDocumentType(docId) {
    // Extract document type from various naming patterns
    if (!docId) return null;
    
    const parts = docId.split('_');
    if (parts.length >= 1) {
        return parts[0]; // First part is usually the document type
    }
    return null;
}

function extractDocumentNumber(docId) {
    // Extract document number/sequence from various naming patterns
    if (!docId) return null;
    
    const parts = docId.split('_');
    if (parts.length >= 2) {
        // Look for numeric patterns in the second part
        const secondPart = parts[1];
        if (/^\d+$/.test(secondPart)) {
            return secondPart;
        }
    }
    return null;
}

function createRichCitationHTML(index, docInfo) {
    // Generic document metadata extraction
    const title = docInfo.topic || docInfo.title || parseDocumentTitle(docInfo.doc_id);
    const date = docInfo.meeting_date || docInfo.date || docInfo.valid_from || '';
    const dayOfWeek = getDayOfWeek(date);
    const location = docInfo.location || docInfo.venue || '';
    
    // Generic metadata arrays (flexible for different document types)
    const people = Array.isArray(docInfo.attendees) ? docInfo.attendees : 
                  Array.isArray(docInfo.authors) ? docInfo.authors :
                  Array.isArray(docInfo.participants) ? docInfo.participants : [];
    
    const decisions = Array.isArray(docInfo.key_decisions) ? docInfo.key_decisions :
                     Array.isArray(docInfo.conclusions) ? docInfo.conclusions :
                     Array.isArray(docInfo.findings) ? docInfo.findings : [];
    
    const actions = Array.isArray(docInfo.action_items) ? docInfo.action_items :
                   Array.isArray(docInfo.next_steps) ? docInfo.next_steps :
                   Array.isArray(docInfo.recommendations) ? docInfo.recommendations : [];
    
    return `
        <div class="citation-detail" style="
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            font-size: 0.9em;
        ">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                <div>
                    <h4 style="margin: 0 0 4px 0; color: #495057; font-size: 1.1em;">${title}</h4>
                    <div style="color: #6c757d; font-size: 0.85em;">
                        ${date ? `📅 ${date} ${dayOfWeek ? `(${dayOfWeek})` : ''}` : ''}
                        ${location ? ` • 📍 ${location}` : ''}
                    </div>
                </div>
                <div style="
                    background: #007bff;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75em;
                    font-weight: 500;
                ">
                    Citation [${index + 1}]
                </div>
            </div>
            
            ${people.length > 0 ? `
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: #495057; margin-bottom: 4px; font-size: 0.85em;">👥 ${getPeopleLabel(docInfo)}</div>
                <div style="
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 0.8em;
                    color: #495057;
                ">
                    ${people.join(', ')}
                </div>
            </div>
            ` : ''}
            
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: #495057; margin-bottom: 4px; font-size: 0.85em;">📄 Document Content</div>
                <div style="
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 12px;
                    font-size: 0.85em;
                    line-height: 1.4;
                    color: #495057;
                    max-height: 200px;
                    overflow-y: auto;
                ">
                    ${formatText(docInfo.content_preview || docInfo.full_content || 'No content available')}
                </div>
            </div>
            
            ${decisions.length > 0 ? `
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: #495057; margin-bottom: 4px; font-size: 0.85em;">🎯 ${getDecisionsLabel(docInfo)}</div>
                <div style="
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 0.8em;
                    color: #495057;
                ">
                    <ul style="margin: 0; padding-left: 16px;">
                        ${decisions.map(decision => `<li>${decision}</li>`).join('')}
                    </ul>
                </div>
            </div>
            ` : ''}
            
            ${actions.length > 0 ? `
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: #495057; margin-bottom: 4px; font-size: 0.85em;">✅ ${getActionsLabel(docInfo)}</div>
                <div style="
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 0.8em;
                    color: #495057;
                ">
                    <ul style="margin: 0; padding-left: 16px;">
                        ${actions.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
            </div>
            ` : ''}
            
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.8em;
                color: #6c757d;
                border-top: 1px solid #e9ecef;
                padding-top: 8px;
            ">
                <span>📄 ${docInfo.file_name || docInfo.doc_id}</span>
                <span>🔗 Chunk ${docInfo.chunk_id}</span>
            </div>
        </div>
    `;
}

function createGenericCitationHTML(index, docTitle, date, dayOfWeek, documentType, documentNumber, content, docId, chunkId) {
    return `
        <div class="citation-detail" style="
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            font-size: 0.9em;
        ">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                <div>
                    <h4 style="margin: 0 0 4px 0; color: #495057; font-size: 1.1em;">${docTitle}</h4>
                    <div style="color: #6c757d; font-size: 0.85em;">
                        ${date && date !== 'Unknown Date' ? `📅 ${date} ${dayOfWeek ? `(${dayOfWeek})` : ''}` : ''}
                        ${documentType ? ` • 📋 ${documentType}` : ''}
                    </div>
                </div>
                <div style="
                    background: #007bff;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75em;
                    font-weight: 500;
                ">
                    Citation [${index + 1}]
                </div>
            </div>
            
            ${documentNumber ? `
            <div style="margin-bottom: 8px;">
                <div style="
                    background: #e3f2fd;
                    border: 1px solid #bbdefb;
                    border-radius: 4px;
                    padding: 6px 8px;
                    font-size: 0.8em;
                    color: #1976d2;
                ">
                    📊 ${documentType || 'Document'} #${documentNumber}
                </div>
            </div>
            ` : ''}
            
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: #495057; margin-bottom: 4px; font-size: 0.85em;">📄 Document Content</div>
                <div style="
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 12px;
                    font-size: 0.85em;
                    line-height: 1.4;
                    color: #495057;
                    max-height: 200px;
                    overflow-y: auto;
                ">
                    ${formatText(content)}
                </div>
            </div>
            
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.8em;
                color: #6c757d;
                border-top: 1px solid #e9ecef;
                padding-top: 8px;
            ">
                <span>📄 ${docId}</span>
                <span>🔗 Chunk ${chunkId || 'N/A'}</span>
            </div>
        </div>
    `;
}

// Helper functions to determine appropriate labels based on document type
function getPeopleLabel(docInfo) {
    if (docInfo.attendees) return 'Attendees';
    if (docInfo.authors) return 'Authors';
    if (docInfo.participants) return 'Participants';
    return 'People';
}

function getDecisionsLabel(docInfo) {
    if (docInfo.key_decisions) return 'Key Decisions';
    if (docInfo.conclusions) return 'Conclusions';
    if (docInfo.findings) return 'Findings';
    return 'Key Points';
}

function getActionsLabel(docInfo) {
    if (docInfo.action_items) return 'Action Items';
    if (docInfo.next_steps) return 'Next Steps';
    if (docInfo.recommendations) return 'Recommendations';
    return 'Follow-up Items';
}

// Display an error message
function displayError(message) {
    // Show error message
    errorContainer.innerHTML = `<p>${message}</p>`;
    errorContainer.style.display = 'block';
    
    // Scroll to the error
    errorContainer.scrollIntoView({ behavior: 'smooth' });
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

// Initialize the app when the DOM is loaded
// Debug export functions
function downloadWorkflow() {
    if (!currentWorkflowData) {
        alert('No workflow data available for download');
        return;
    }
    
    const filename = `workflow_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    downloadJSON(currentWorkflowData, filename);
}

function downloadNodeUpdates() {
    if (currentNodeUpdates.length === 0) {
        alert('No node updates available for download');
        return;
    }
    
    const data = {
        session_id: sessionId,
        query_id: currentQueryId,
        timestamp: new Date().toISOString(),
        node_updates: currentNodeUpdates
    };
    
    const filename = `node_updates_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    downloadJSON(data, filename);
}

function downloadCompleteDebug() {
    const debugData = {
        session_id: sessionId,
        query_id: currentQueryId,
        timestamp: new Date().toISOString(),
        workflow: currentWorkflowData,
        node_updates: currentNodeUpdates,
        processing_updates: processingUpdates[currentQueryId] || [],
        environment: {
            user_agent: navigator.userAgent,
            timestamp: new Date().toISOString(),
            url: window.location.href
        }
    };
    
    const filename = `complete_debug_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    downloadJSON(debugData, filename);
}

function downloadJSON(data, filename) {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

document.addEventListener('DOMContentLoaded', init);
