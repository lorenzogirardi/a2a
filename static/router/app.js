/**
 * Smart Task Router - Frontend Application
 *
 * Connects to the backend via SSE to receive real-time routing events
 * and displays the 3-step routing process.
 */

// DOM Elements
const taskInput = document.getElementById('task');
const routeBtn = document.getElementById('routeBtn');
const timeline = document.getElementById('timeline');

// Step sections
const stepAnalyze = document.getElementById('step-analyze');
const stepDiscover = document.getElementById('step-discover');
const stepExecute = document.getElementById('step-execute');
const stepSynthesize = document.getElementById('step-synthesize');

// Step content
const detectedCapabilities = document.getElementById('detected-capabilities');
const subtasksList = document.getElementById('subtasks-list');
const discoveryResults = document.getElementById('discovery-results');
const executionResults = document.getElementById('execution-results');
const registryList = document.getElementById('registry-list');
const finalOutput = document.getElementById('final-output');

// Metrics
const metricDuration = document.getElementById('metric-duration');
const metricAgents = document.getElementById('metric-agents');
const metricCapabilities = document.getElementById('metric-capabilities');

// Status elements
const analyzeStatus = document.getElementById('analyze-status');
const discoverStatus = document.getElementById('discover-status');
const executeStatus = document.getElementById('execute-status');
const synthesizeStatus = document.getElementById('synthesize-status');

// Synthesis info
const synthesisInfo = document.getElementById('synthesis-info');

// State
let currentTaskId = null;
let eventSource = null;
let registryAgents = {};

// Agent icons
const AGENT_ICONS = {
    'echo': '🔊',
    'calculator': '🔢',
    'writer': '✍️',
    'editor': '📝',
    'publisher': '📰',
    'default': '🤖'
};

// Capability colors (matching CSS)
const CAP_COLORS = {
    'calculation': 'calculation',
    'echo': 'echo',
    'creative_writing': 'creative_writing',
    'text_editing': 'text_editing',
    'formatting': 'formatting'
};

/**
 * Initialize the application
 */
async function init() {
    routeBtn.addEventListener('click', routeTask);

    taskInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            routeTask();
        }
    });

    // Load registry on start
    await loadRegistry();
}

/**
 * Load agents from registry
 */
async function loadRegistry() {
    try {
        const response = await fetch('/api/router/registry');
        const data = await response.json();

        registryList.innerHTML = '';
        registryAgents = {};

        data.agents.forEach(agent => {
            registryAgents[agent.id] = agent;
            const icon = AGENT_ICONS[agent.id] || AGENT_ICONS.default;
            const caps = agent.capabilities.join(', ');

            const div = document.createElement('div');
            div.className = 'registry-agent';
            div.id = `registry-${agent.id}`;
            div.innerHTML = `
                <span class="agent-icon">${icon}</span>
                <div class="agent-info">
                    <div class="agent-name">${agent.name || agent.id}</div>
                    <div class="agent-caps">${caps}</div>
                </div>
            `;
            registryList.appendChild(div);
        });
    } catch (error) {
        console.error('Failed to load registry:', error);
        registryList.innerHTML = '<div class="placeholder">Failed to load agents</div>';
    }
}

/**
 * Route the task
 */
async function routeTask() {
    const task = taskInput.value.trim();
    if (!task) {
        alert('Please enter a task.');
        return;
    }

    resetUI();
    setLoading(true);

    try {
        const response = await fetch('/api/router/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task })
        });

        const data = await response.json();
        currentTaskId = data.task_id;

        addTimelineEvent('started', `Routing started: ${truncate(task, 50)}`);
        connectToSSE(currentTaskId);

    } catch (error) {
        console.error('Failed to start routing:', error);
        addTimelineEvent('error', `Failed to start: ${error.message}`);
        setLoading(false);
    }
}

/**
 * Connect to SSE for real-time events
 */
function connectToSSE(taskId) {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/api/router/events/${taskId}`);

    eventSource.addEventListener('connected', (e) => {
        addTimelineEvent('connected', 'Connected to router');
    });

    eventSource.addEventListener('routing_started', (e) => {
        const data = JSON.parse(e.data);
        setStepActive('analyze');
    });

    eventSource.addEventListener('analysis_started', (e) => {
        analyzeStatus.textContent = 'Analyzing...';
        addTimelineEvent('analysis', 'Analyzing task with LLM...');
    });

    eventSource.addEventListener('analysis_completed', (e) => {
        const data = JSON.parse(e.data);
        setStepCompleted('analyze');
        displayCapabilities(data.capabilities);
        displaySubtasks(data.subtasks);
        addTimelineEvent('analysis', `Detected ${data.capabilities.length} capabilities`);

        metricCapabilities.textContent = data.capabilities.length;
        setStepActive('discover');
    });

    eventSource.addEventListener('discovery_started', (e) => {
        const data = JSON.parse(e.data);
        discoverStatus.textContent = 'Searching...';
        highlightCapabilityAgents(data.capability);
    });

    eventSource.addEventListener('discovery_completed', (e) => {
        const data = JSON.parse(e.data);
        addDiscoveryResult(data);
        addTimelineEvent('discovery', `${data.capability}: found ${data.agents.length} agent(s)`);
    });

    eventSource.addEventListener('execution_started', (e) => {
        const data = JSON.parse(e.data);
        if (stepDiscover.classList.contains('active')) {
            setStepCompleted('discover');
            setStepActive('execute');
        }
        executeStatus.textContent = 'Executing...';
        setAgentExecuting(data.agent_id);
        addTimelineEvent('execution', `Executing on ${data.agent_name}...`);
    });

    eventSource.addEventListener('execution_completed', (e) => {
        const data = JSON.parse(e.data);
        clearAgentExecuting(data.agent_id);
        addExecutionResult(data);
        addTimelineEvent('execution', `${data.agent_id}: ${data.success ? 'completed' : 'failed'}`);
    });

    eventSource.addEventListener('synthesis_started', (e) => {
        const data = JSON.parse(e.data);
        setStepCompleted('execute');
        setStepActive('synthesize');
        synthesizeStatus.textContent = 'Synthesizing...';
        addTimelineEvent('synthesis', `Synthesizing outputs from ${data.sources.length} agents...`);
    });

    eventSource.addEventListener('synthesis_completed', (e) => {
        const data = JSON.parse(e.data);
        setStepCompleted('synthesize');
        displaySynthesisInfo(data);
        addTimelineEvent('synthesis', `Synthesis completed in ${data.duration_ms}ms`);
    });

    eventSource.addEventListener('routing_completed', (e) => {
        const data = JSON.parse(e.data);
        // Mark appropriate step as completed
        if (!stepSynthesize.classList.contains('completed')) {
            setStepCompleted('execute');
        }

        metricDuration.textContent = `${(data.total_duration_ms / 1000).toFixed(2)}s`;
        metricAgents.textContent = data.executions_count || 0;

        addTimelineEvent('completed', `Routing completed in ${data.total_duration_ms}ms`);
    });

    eventSource.addEventListener('result', (e) => {
        const data = JSON.parse(e.data);
        displayFinalOutput(data);
        setLoading(false);
        eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
        addTimelineEvent('error', 'Connection error');
        setLoading(false);
    });

    eventSource.onerror = () => {
        console.error('SSE connection error');
        setLoading(false);
    };
}

/**
 * Reset the UI
 */
function resetUI() {
    // Reset steps
    [stepAnalyze, stepDiscover, stepExecute, stepSynthesize].forEach(step => {
        step.classList.remove('active', 'completed');
    });

    // Reset status
    analyzeStatus.textContent = 'Waiting';
    discoverStatus.textContent = 'Waiting';
    executeStatus.textContent = 'Waiting';
    synthesizeStatus.textContent = 'Waiting';

    // Reset content
    detectedCapabilities.innerHTML = '<div class="placeholder">Capabilities will appear here...</div>';
    subtasksList.innerHTML = '';
    discoveryResults.innerHTML = '<div class="placeholder">Agent matches will appear here...</div>';
    executionResults.innerHTML = '<div class="placeholder">Execution results will appear here...</div>';
    synthesisInfo.innerHTML = '<div class="placeholder">Synthesis will appear when multiple agents are used...</div>';
    finalOutput.innerHTML = '<div class="placeholder">Results will appear here...</div>';
    timeline.innerHTML = '';

    // Reset metrics
    metricDuration.textContent = '-';
    metricAgents.textContent = '-';
    metricCapabilities.textContent = '-';

    // Reset registry highlights
    document.querySelectorAll('.registry-agent').forEach(el => {
        el.classList.remove('highlighted', 'executing');
    });
}

/**
 * Set loading state
 */
function setLoading(isLoading) {
    routeBtn.disabled = isLoading;
    routeBtn.querySelector('.btn-text').style.display = isLoading ? 'none' : 'inline';
    routeBtn.querySelector('.btn-loader').style.display = isLoading ? 'inline' : 'none';
}

/**
 * Set step active
 */
function setStepActive(step) {
    const section = document.getElementById(`step-${step}`);
    section.classList.add('active');
    section.classList.remove('completed');
}

/**
 * Set step completed
 */
function setStepCompleted(step) {
    const section = document.getElementById(`step-${step}`);
    section.classList.remove('active');
    section.classList.add('completed');

    const status = document.getElementById(`${step}-status`);
    status.textContent = 'Done';
}

/**
 * Display detected capabilities
 */
function displayCapabilities(capabilities) {
    detectedCapabilities.innerHTML = '';

    capabilities.forEach((cap, i) => {
        setTimeout(() => {
            const tag = document.createElement('span');
            tag.className = `capability-tag ${CAP_COLORS[cap] || ''}`;
            tag.textContent = cap;
            detectedCapabilities.appendChild(tag);
        }, i * 200);
    });
}

/**
 * Display subtasks
 */
function displaySubtasks(subtasks) {
    subtasksList.innerHTML = '';

    for (const [cap, task] of Object.entries(subtasks)) {
        const div = document.createElement('div');
        div.className = 'subtask-item';
        div.innerHTML = `
            <span class="cap-name">${cap}:</span>
            <span class="subtask-text">${task}</span>
        `;
        subtasksList.appendChild(div);
    }
}

/**
 * Highlight agents with capability in registry
 */
function highlightCapabilityAgents(capability) {
    for (const [id, agent] of Object.entries(registryAgents)) {
        const el = document.getElementById(`registry-${id}`);
        if (el && agent.capabilities.includes(capability)) {
            el.classList.add('highlighted');
        }
    }
}

/**
 * Add discovery result
 */
function addDiscoveryResult(data) {
    const placeholder = discoveryResults.querySelector('.placeholder');
    if (placeholder) placeholder.remove();

    const div = document.createElement('div');
    div.className = `discovery-item ${data.agents.length === 0 ? 'no-match' : ''}`;

    const agentBadges = data.agents.length > 0
        ? data.agents.map(a => `<span class="agent-badge">${a.name || a.id}</span>`).join('')
        : '<span style="color: var(--error-color)">No agents found</span>';

    div.innerHTML = `
        <span class="capability">${data.capability}</span>
        <span class="arrow">→</span>
        <div class="agents">${agentBadges}</div>
    `;
    discoveryResults.appendChild(div);
}

/**
 * Set agent as executing in registry
 */
function setAgentExecuting(agentId) {
    const el = document.getElementById(`registry-${agentId}`);
    if (el) {
        el.classList.add('executing');
    }
}

/**
 * Clear agent executing state
 */
function clearAgentExecuting(agentId) {
    const el = document.getElementById(`registry-${agentId}`);
    if (el) {
        el.classList.remove('executing');
    }
}

/**
 * Add execution result
 */
function addExecutionResult(data) {
    const placeholder = executionResults.querySelector('.placeholder');
    if (placeholder) placeholder.remove();

    const div = document.createElement('div');
    div.className = `execution-item ${data.success ? '' : 'error'}`;

    div.innerHTML = `
        <div class="exec-header">
            <span class="agent-name">${data.agent_id}</span>
            <span class="exec-duration">${data.duration_ms}ms</span>
        </div>
        <div class="exec-output">${escapeHtml(data.output || data.error || '')}</div>
    `;
    executionResults.appendChild(div);
}

/**
 * Display synthesis info
 */
function displaySynthesisInfo(data) {
    synthesisInfo.innerHTML = `
        <div class="synthesis-details">
            <div class="synthesis-stat">
                <span class="stat-label">Sources:</span>
                <span class="stat-value">${data.sources.join(', ')}</span>
            </div>
            <div class="synthesis-stat">
                <span class="stat-label">Duration:</span>
                <span class="stat-value">${data.duration_ms}ms</span>
            </div>
        </div>
    `;
}

/**
 * Display final output
 */
function displayFinalOutput(result) {
    if (result.status === 'failed') {
        finalOutput.innerHTML = `<div style="color: var(--error-color)">Error: ${result.error}</div>`;
        return;
    }

    // Show if synthesis was used
    if (result.synthesis) {
        const badge = document.createElement('div');
        badge.className = 'synthesis-badge';
        badge.innerHTML = '🔗 Synthesized from multiple agents';
        finalOutput.innerHTML = '';
        finalOutput.appendChild(badge);
        finalOutput.innerHTML += formatOutput(result.final_output);
    } else {
        finalOutput.innerHTML = formatOutput(result.final_output);
    }
}

/**
 * Format output with markdown-like processing
 */
function formatOutput(text) {
    if (!text) return '<div class="placeholder">No output</div>';

    // Basic markdown
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/---/g, '<hr>');
    html = html.replace(/\n/g, '<br>');

    return html;
}

/**
 * Add timeline event
 */
function addTimelineEvent(type, message) {
    const placeholder = timeline.querySelector('.placeholder');
    if (placeholder) placeholder.remove();

    const div = document.createElement('div');
    div.className = `timeline-event ${type}`;

    const time = new Date().toLocaleTimeString();
    div.innerHTML = `
        <span class="event-time">${time}</span>
        <span class="event-message">${message}</span>
    `;

    timeline.appendChild(div);
    timeline.scrollTop = timeline.scrollHeight;
}

/**
 * Truncate text
 */
function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on load
init();
