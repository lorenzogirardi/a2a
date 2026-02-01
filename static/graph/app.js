/**
 * LangGraph Execution Visualizer
 *
 * Real-time visualization of DAG execution using vis.js.
 * Connects to SSE endpoint for live updates.
 */

// ============================================
// vis.js Graph Setup
// ============================================

const nodes = new vis.DataSet([]);
const edges = new vis.DataSet([]);

let graphContainer = null;
let network = null;

function initNetwork() {
    graphContainer = document.getElementById('graph-container');
    if (!graphContainer) {
        console.error('Graph container not found!');
        return;
    }

    const options = {
        physics: {
            enabled: true,
            solver: 'hierarchicalRepulsion',
            hierarchicalRepulsion: {
                centralGravity: 0.0,
                springLength: 150,
                springConstant: 0.01,
                nodeDistance: 120,
                damping: 0.09
            },
            stabilization: {
                enabled: true,
                iterations: 50
            }
        },
        nodes: {
            shape: 'box',
            size: 20,
            font: {
                size: 12,
                color: '#f1f5f9',
                face: 'Inter, sans-serif'
            },
            borderWidth: 2,
            margin: 10,
            shadow: true
        },
        edges: {
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 0.8
                }
            },
            smooth: {
                type: 'cubicBezier',
                forceDirection: 'horizontal',
                roundness: 0.4
            },
            color: {
                color: '#64748b',
                highlight: '#94a3b8',
                hover: '#94a3b8'
            },
            width: 2,
            font: {
                size: 10,
                color: '#94a3b8'
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true,
            dragView: true
        },
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'LR',
                sortMethod: 'directed',
                levelSeparation: 180,
                nodeSpacing: 80,
                treeSpacing: 100
            }
        }
    };

    network = new vis.Network(graphContainer, { nodes, edges }, options);

    // Fit to container after stabilization
    network.once('stabilized', function() {
        network.fit({ animation: { duration: 500 } });
    });
}

// ============================================
// Color Schemes
// ============================================

const colors = {
    pending: {
        background: '#475569',
        border: '#64748b',
        highlight: { background: '#64748b', border: '#94a3b8' }
    },
    running: {
        background: '#f59e0b',
        border: '#fbbf24',
        highlight: { background: '#fbbf24', border: '#fcd34d' }
    },
    completed: {
        background: '#22c55e',
        border: '#4ade80',
        highlight: { background: '#4ade80', border: '#86efac' }
    },
    failed: {
        background: '#ef4444',
        border: '#f87171',
        highlight: { background: '#f87171', border: '#fca5a5' }
    },
    matched: {
        background: '#3b82f6',
        border: '#60a5fa',
        highlight: { background: '#60a5fa', border: '#93c5fd' }
    },
    unmatched: {
        background: '#6b7280',
        border: '#9ca3af',
        highlight: { background: '#9ca3af', border: '#d1d5db' }
    }
};

const nodeShapes = {
    processor: 'diamond',
    capability: 'box',
    agent: 'dot'
};

// ============================================
// State
// ============================================

let eventSource = null;
let currentTaskId = null;

// ============================================
// Graph Update Functions
// ============================================

function addNode(nodeData) {
    const { id, label, state = 'pending', type = 'processor' } = nodeData;

    const colorScheme = colors[state] || colors.pending;
    const shape = nodeShapes[type] || 'dot';

    try {
        nodes.add({
            id,
            label,
            color: colorScheme,
            shape,
            title: `${label} (${state})`
        });
    } catch (e) {
        // Node might already exist
        updateNode(nodeData);
    }
}

function updateNode(nodeData) {
    const { id, state } = nodeData;

    const colorScheme = colors[state] || colors.pending;

    try {
        nodes.update({
            id,
            color: colorScheme,
            title: `${nodes.get(id)?.label || id} (${state})`
        });
    } catch (e) {
        console.warn('Could not update node:', id, e);
    }
}

function addEdge(edgeData) {
    const { from, to, label = '' } = edgeData;

    const edgeId = `${from}->${to}`;

    try {
        edges.add({
            id: edgeId,
            from,
            to,
            label
        });
    } catch (e) {
        // Edge might already exist
    }
}

function resetGraph() {
    nodes.clear();
    edges.clear();
}

// ============================================
// Event Handling
// ============================================

function handleGraphUpdate(event) {
    const data = typeof event === 'string' ? JSON.parse(event) : event;

    if (data.action === 'add_node') {
        addNode(data.node);
    } else if (data.action === 'update_node') {
        updateNode(data.node);
    } else if (data.action === 'add_edge') {
        addEdge(data.edge);
    }
}

function addTimelineEvent(event) {
    const timeline = document.getElementById('timeline');

    // Remove placeholder if present
    const placeholder = timeline.querySelector('.placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const eventItem = document.createElement('div');
    eventItem.className = 'event-item';

    const timestamp = event.timestamp
        ? new Date(event.timestamp).toLocaleTimeString()
        : new Date().toLocaleTimeString();

    const eventType = event.type || 'unknown';
    const typeClass = ['graph_update', 'execution_started', 'execution_completed', 'execution_failed']
        .includes(eventType) ? eventType : 'default';

    let message = '';
    if (event.type === 'graph_update') {
        message = `${event.action}: ${event.node?.id || event.edge?.from + ' → ' + event.edge?.to}`;
    } else if (event.type === 'execution_started') {
        message = `Task started: ${event.task || 'unknown'}`;
    } else if (event.type === 'execution_completed') {
        message = `Completed in ${event.duration_ms}ms`;
    } else if (event.type === 'execution_failed') {
        message = `Error: ${event.error}`;
    } else {
        message = JSON.stringify(event).substring(0, 100);
    }

    eventItem.innerHTML = `
        <span class="event-time">${timestamp}</span>
        <span class="event-type ${typeClass}">${eventType}</span>
        <span class="event-message">${message}</span>
    `;

    timeline.appendChild(eventItem);
    timeline.scrollTop = timeline.scrollHeight;
}

// ============================================
// SSE Connection
// ============================================

function connectSSE(taskId) {
    if (eventSource) {
        eventSource.close();
    }

    currentTaskId = taskId;

    eventSource = new EventSource(`/api/graph/events/${taskId}`);

    eventSource.addEventListener('graph_update', (e) => {
        const data = JSON.parse(e.data);
        handleGraphUpdate(data);
        addTimelineEvent(data);
    });

    eventSource.addEventListener('execution_started', (e) => {
        const data = JSON.parse(e.data);
        addTimelineEvent(data);
        setStatus('running', 'Running...');
    });

    eventSource.addEventListener('execution_completed', (e) => {
        const data = JSON.parse(e.data);
        addTimelineEvent(data);
        setStatus('completed', 'Completed');
        setDuration(data.duration_ms);
        setOutput(data.final_output);
        eventSource.close();
    });

    eventSource.addEventListener('execution_failed', (e) => {
        const data = JSON.parse(e.data);
        addTimelineEvent(data);
        setStatus('error', 'Failed');
        setOutput(`Error: ${data.error}`);
        eventSource.close();
    });

    eventSource.addEventListener('done', () => {
        eventSource.close();
    });

    eventSource.onerror = (e) => {
        console.error('SSE error:', e);
        eventSource.close();
    };
}

// ============================================
// UI Functions
// ============================================

function setTask(task) {
    document.getElementById('task').value = task;
}

function setStatus(state, text) {
    const statusEl = document.getElementById('status');
    statusEl.className = state;
    statusEl.textContent = text;
}

function setDuration(ms) {
    document.getElementById('duration').textContent = `Duration: ${ms}ms`;
}

function setOutput(text) {
    const outputEl = document.getElementById('output');
    if (text) {
        outputEl.innerHTML = `<pre>${escapeHtml(text)}</pre>`;
    } else {
        outputEl.innerHTML = '<p class="placeholder">No output</p>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function clearUI() {
    resetGraph();
    document.getElementById('timeline').innerHTML = '<p class="placeholder">Events will appear here...</p>';
    document.getElementById('output').innerHTML = '<p class="placeholder">Run a task to see the output...</p>';
    document.getElementById('duration').textContent = '';
    setStatus('', 'Ready');
}

// ============================================
// Main Functions
// ============================================

async function runGraph() {
    const task = document.getElementById('task').value.trim();

    if (!task) {
        alert('Please enter a task');
        return;
    }

    // Disable button
    const btn = document.getElementById('runBtn');
    btn.disabled = true;

    // Clear previous state
    clearUI();
    setStatus('running', 'Starting...');

    try {
        // Start the graph execution with streaming
        const response = await fetch('/api/graph/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events from buffer
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            let eventType = 'message';
            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    eventType = line.substring(7).trim();
                } else if (line.startsWith('data: ')) {
                    const data = line.substring(6).trim();
                    if (data) {
                        try {
                            const parsed = JSON.parse(data);
                            parsed.type = parsed.type || eventType;

                            if (eventType === 'graph_update' || parsed.type === 'graph_update') {
                                handleGraphUpdate(parsed);
                            }

                            addTimelineEvent(parsed);

                            if (parsed.type === 'execution_completed') {
                                console.log('execution_completed event:', parsed);
                                console.log('final_output:', parsed.final_output);
                                setStatus('completed', 'Completed');
                                setDuration(parsed.duration_ms);
                                setOutput(parsed.final_output);
                            } else if (parsed.type === 'execution_failed') {
                                setStatus('error', 'Failed');
                                setOutput(`Error: ${parsed.error}`);
                            }
                        } catch (e) {
                            console.warn('Could not parse SSE data:', data);
                        }
                    }
                }
            }
        }

    } catch (error) {
        console.error('Error running graph:', error);
        setStatus('error', 'Error');
        setOutput(`Error: ${error.message}`);
    } finally {
        btn.disabled = false;
    }
}

// ============================================
// Keyboard Shortcuts
// ============================================

document.getElementById('task').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        runGraph();
    }
});

// ============================================
// Load Graph Structure on Init
// ============================================

async function loadGraphStructure() {
    try {
        const response = await fetch('/api/graph/structure');
        const data = await response.json();

        console.log('Graph structure loaded:', data.mermaid);

        // Add base nodes for the static graph structure
        addNode({ id: '__start__', label: 'START', type: 'processor', state: 'completed' });
        addNode({ id: 'analyze', label: 'Analyze', type: 'processor', state: 'pending' });
        addNode({ id: 'discover', label: 'Discover', type: 'processor', state: 'pending' });
        addNode({ id: 'execute', label: 'Execute', type: 'processor', state: 'pending' });
        addNode({ id: 'synthesize', label: 'Synthesize', type: 'processor', state: 'pending' });
        addNode({ id: '__end__', label: 'END', type: 'processor', state: 'pending' });

        addEdge({ from: '__start__', to: 'analyze' });
        addEdge({ from: 'analyze', to: 'discover' });
        addEdge({ from: 'discover', to: 'execute' });
        addEdge({ from: 'execute', to: 'synthesize', label: 'if 2+ outputs' });
        addEdge({ from: 'execute', to: '__end__', label: 'if 1 output' });
        addEdge({ from: 'synthesize', to: '__end__' });

    } catch (error) {
        console.warn('Could not load graph structure:', error);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initNetwork();
    loadGraphStructure();
});
