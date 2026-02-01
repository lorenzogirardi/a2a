/**
 * Chain Pipeline Demo - Frontend Application
 *
 * Connects to the backend via SSE to receive real-time pipeline events
 * and displays the document processing flow with KPIs.
 */

// DOM Elements
const promptInput = document.getElementById('prompt');
const runBtn = document.getElementById('runBtn');
const timeline = document.getElementById('timeline');
const output = document.getElementById('output');
const stepDetails = document.getElementById('step-details');
const communication = document.getElementById('communication');

// KPI Elements
const kpiDuration = document.getElementById('kpi-duration');
const kpiInputTokens = document.getElementById('kpi-input-tokens');
const kpiOutputTokens = document.getElementById('kpi-output-tokens');
const kpiTotalTokens = document.getElementById('kpi-total-tokens');
const kpiModel = document.getElementById('kpi-model');
const kpiCost = document.getElementById('kpi-cost');

// Agent boxes
const agentBoxes = {
    writer: document.getElementById('writer-box'),
    editor: document.getElementById('editor-box'),
    publisher: document.getElementById('publisher-box')
};

// Agent token displays
const agentTokens = {
    writer: document.getElementById('writer-tokens'),
    editor: document.getElementById('editor-tokens'),
    publisher: document.getElementById('publisher-tokens')
};

// Arrows
const arrows = {
    1: document.getElementById('arrow-1'),
    2: document.getElementById('arrow-2')
};

// State
let currentPipelineId = null;
let eventSource = null;
let stepData = {};
let totalStats = {
    inputTokens: 0,
    outputTokens: 0,
    duration: 0,
    model: ''
};

// Cost per 1M tokens (Claude Sonnet pricing estimate)
const COST_PER_1M_INPUT = 3.0;
const COST_PER_1M_OUTPUT = 15.0;

/**
 * Initialize the application
 */
function init() {
    runBtn.addEventListener('click', runPipeline);

    // Allow Enter + Ctrl to submit
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            runPipeline();
        }
    });
}

/**
 * Run the pipeline with the entered prompt
 */
async function runPipeline() {
    const prompt = promptInput.value.trim();
    if (!prompt) {
        alert('Please enter a topic to write about.');
        return;
    }

    // Reset UI
    resetUI();
    setLoading(true);

    try {
        // Start the pipeline
        const response = await fetch('/api/chain/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();
        currentPipelineId = data.pipeline_id;

        // Connect to SSE for real-time updates
        connectToSSE(currentPipelineId);

    } catch (error) {
        console.error('Failed to start pipeline:', error);
        addTimelineEvent('error', 'Failed to start pipeline', error.message);
        setLoading(false);
    }
}

/**
 * Connect to SSE endpoint for real-time events
 */
function connectToSSE(pipelineId) {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/api/chain/events/${pipelineId}`);

    eventSource.addEventListener('connected', (e) => {
        const data = JSON.parse(e.data);
        addTimelineEvent('connected', 'Connected to pipeline', `Pipeline ID: ${data.pipeline_id}`);
    });

    eventSource.addEventListener('pipeline_started', (e) => {
        const data = JSON.parse(e.data);
        addTimelineEvent('pipeline_started', 'Pipeline Started', `Prompt: "${truncate(data.prompt, 50)}"`);
    });

    eventSource.addEventListener('step_started', (e) => {
        const data = JSON.parse(e.data);
        setAgentStatus(data.step_name, 'active', 'Processing...');

        // Activate arrow if transitioning
        if (data.step_index > 0) {
            arrows[data.step_index].classList.add('active');
        }

        // Update model in KPI
        if (data.model) {
            totalStats.model = data.model;
            updateKPI('model', formatModel(data.model));
        }

        addTimelineEvent('step_started', `${capitalize(data.step_name)} Started`,
            `Input: ${data.input_length} chars`);
    });

    eventSource.addEventListener('step_completed', (e) => {
        const data = JSON.parse(e.data);

        // Update agent status
        setAgentStatus(data.step_name, 'completed', `Done (${data.duration_ms}ms)`);

        // Deactivate arrow
        if (data.step_index > 0) {
            arrows[data.step_index].classList.remove('active');
        }

        // Update agent tokens display
        if (agentTokens[data.step_name]) {
            agentTokens[data.step_name].innerHTML = `
                📥 ${data.input_tokens || 0} | 📤 ${data.output_tokens || 0}
            `;
        }

        // Accumulate stats
        totalStats.inputTokens += data.input_tokens || 0;
        totalStats.outputTokens += data.output_tokens || 0;
        totalStats.duration += data.duration_ms || 0;

        // Update KPIs
        updateAllKPIs();

        // Store step data
        stepData[data.step_name] = data;

        // Add to timeline with token info
        let tokenInfo = '';
        if (data.input_tokens || data.output_tokens) {
            tokenInfo = ` | Tokens: ${data.input_tokens}→${data.output_tokens}`;
        }
        addTimelineEvent('step_completed', `${capitalize(data.step_name)} Completed`,
            `Duration: ${data.duration_ms}ms${tokenInfo}`, data);
    });

    eventSource.addEventListener('message_passed', (e) => {
        const data = JSON.parse(e.data);

        // Add to communication flow
        addCommunicationMessage(data);

        addTimelineEvent('message_passed', 'Message Passed',
            `${capitalize(data.from_step)} → ${capitalize(data.to_step)} (${data.content_length} chars)`);
    });

    eventSource.addEventListener('pipeline_completed', (e) => {
        const data = JSON.parse(e.data);
        if (data.status === 'completed') {
            addTimelineEvent('pipeline_completed', 'Pipeline Completed',
                `Total time: ${data.total_duration_ms}ms`);
        } else {
            addTimelineEvent('error', 'Pipeline Failed', data.error || 'Unknown error');
        }
    });

    eventSource.addEventListener('result', (e) => {
        const data = JSON.parse(e.data);
        displayFinalOutput(data);
        setLoading(false);
        eventSource.close();
    });

    eventSource.addEventListener('ping', (e) => {
        // Keepalive, no action needed
    });

    eventSource.addEventListener('error', (e) => {
        const data = e.data ? JSON.parse(e.data) : { message: 'Connection error' };
        addTimelineEvent('error', 'Error', data.message);
        setLoading(false);
    });

    eventSource.onerror = () => {
        console.error('SSE connection error');
        setLoading(false);
    };
}

/**
 * Reset the UI to initial state
 */
function resetUI() {
    // Clear timeline
    timeline.innerHTML = '';

    // Clear output
    output.innerHTML = '<div class="output-placeholder">The final document will appear here...</div>';

    // Clear step details
    stepDetails.innerHTML = '<div class="details-placeholder">Click on a step in the timeline to see details...</div>';

    // Clear communication
    communication.innerHTML = '<div class="communication-placeholder">Messages between agents will appear here...</div>';

    // Reset agent boxes
    Object.values(agentBoxes).forEach(box => {
        box.classList.remove('active', 'completed', 'error');
        box.querySelector('.agent-status').textContent = 'Waiting';
    });

    // Reset agent tokens
    Object.values(agentTokens).forEach(el => {
        if (el) el.innerHTML = '';
    });

    // Reset arrows
    Object.values(arrows).forEach(arrow => {
        if (arrow) arrow.classList.remove('active');
    });

    // Reset stats
    totalStats = { inputTokens: 0, outputTokens: 0, duration: 0, model: '' };
    stepData = {};

    // Reset KPIs
    kpiDuration.textContent = '-';
    kpiInputTokens.textContent = '-';
    kpiOutputTokens.textContent = '-';
    kpiTotalTokens.textContent = '-';
    kpiModel.textContent = '-';
    kpiCost.textContent = '-';
}

/**
 * Set loading state
 */
function setLoading(isLoading) {
    runBtn.disabled = isLoading;
    runBtn.querySelector('.btn-text').style.display = isLoading ? 'none' : 'inline';
    runBtn.querySelector('.btn-loader').style.display = isLoading ? 'inline' : 'none';
}

/**
 * Set the status of an agent box
 */
function setAgentStatus(agentName, status, text) {
    const box = agentBoxes[agentName];
    if (!box) return;

    // Remove all status classes
    box.classList.remove('active', 'completed', 'error');

    // Add new status class
    if (status) {
        box.classList.add(status);
    }

    // Update status text
    box.querySelector('.agent-status').textContent = text;
}

/**
 * Update a single KPI
 */
function updateKPI(name, value) {
    const el = document.getElementById(`kpi-${name}`);
    if (el) el.textContent = value;
}

/**
 * Update all KPIs from accumulated stats
 */
function updateAllKPIs() {
    updateKPI('duration', `${(totalStats.duration / 1000).toFixed(2)}s`);
    updateKPI('input-tokens', totalStats.inputTokens.toLocaleString());
    updateKPI('output-tokens', totalStats.outputTokens.toLocaleString());
    updateKPI('total-tokens', (totalStats.inputTokens + totalStats.outputTokens).toLocaleString());

    // Calculate estimated cost
    const inputCost = (totalStats.inputTokens / 1000000) * COST_PER_1M_INPUT;
    const outputCost = (totalStats.outputTokens / 1000000) * COST_PER_1M_OUTPUT;
    const totalCost = inputCost + outputCost;
    updateKPI('cost', `$${totalCost.toFixed(4)}`);
}

/**
 * Add an event to the timeline
 */
function addTimelineEvent(type, title, detail, data = null) {
    // Remove placeholder if present
    const placeholder = timeline.querySelector('.timeline-placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const event = document.createElement('div');
    event.className = `timeline-event ${type}`;

    const time = new Date().toLocaleTimeString();

    let tokensHtml = '';
    if (data && (data.input_tokens || data.output_tokens)) {
        tokensHtml = `<div class="event-tokens">📥 ${data.input_tokens} | 📤 ${data.output_tokens} tokens</div>`;
    }

    event.innerHTML = `
        <div class="event-time">${time}</div>
        <div class="event-content">
            <div class="event-type">${title}</div>
            <div class="event-detail">${detail}</div>
            ${tokensHtml}
        </div>
    `;

    // Add click handler for step_completed events
    if (type === 'step_completed' && data) {
        event.addEventListener('click', () => showStepDetails(data));
    }

    timeline.appendChild(event);
    timeline.scrollTop = timeline.scrollHeight;
}

/**
 * Add a message to the communication flow
 */
function addCommunicationMessage(data) {
    // Remove placeholder if present
    const placeholder = communication.querySelector('.communication-placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const message = document.createElement('div');
    message.className = `message-bubble from-${data.from_step}`;

    message.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${capitalize(data.from_step)}</span>
            <span class="message-arrow">→</span>
            <span class="message-receiver">${capitalize(data.to_step)}</span>
        </div>
        <div class="message-content">${escapeHtml(truncate(data.content, 500))}</div>
        <div class="message-meta">
            <span>📝 ${data.content_length} chars</span>
        </div>
    `;

    communication.appendChild(message);
    communication.scrollTop = communication.scrollHeight;
}

/**
 * Display the final output
 */
function displayFinalOutput(result) {
    if (result.status === 'failed') {
        output.innerHTML = `<div class="error">Error: ${result.error}</div>`;
        return;
    }

    // Convert markdown-style headers to HTML
    let content = result.final_output;
    content = content.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    content = content.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    content = content.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    output.innerHTML = content;

    // Update final KPIs from result
    if (result.total_duration_ms) {
        updateKPI('duration', `${(result.total_duration_ms / 1000).toFixed(2)}s`);
    }
    if (result.total_input_tokens !== undefined) {
        updateKPI('input-tokens', result.total_input_tokens.toLocaleString());
    }
    if (result.total_output_tokens !== undefined) {
        updateKPI('output-tokens', result.total_output_tokens.toLocaleString());
    }
    if (result.total_tokens !== undefined) {
        updateKPI('total-tokens', result.total_tokens.toLocaleString());
    }
}

/**
 * Show details for a specific step
 */
function showStepDetails(data) {
    stepDetails.innerHTML = `
        <div class="detail-grid">
            <div class="detail-stat">
                <div class="detail-stat-value">${data.duration_ms}ms</div>
                <div class="detail-stat-label">Duration</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${data.input_tokens || 0}</div>
                <div class="detail-stat-label">Input Tokens</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${data.output_tokens || 0}</div>
                <div class="detail-stat-label">Output Tokens</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${formatModel(data.model || '-')}</div>
                <div class="detail-stat-label">Model</div>
            </div>
        </div>
        <div class="detail-section">
            <div class="detail-label">Step</div>
            <div class="detail-content">${capitalize(data.step_name)} (Index: ${data.step_index})</div>
        </div>
        <div class="detail-section">
            <div class="detail-label">Output</div>
            <div class="detail-content">${escapeHtml(data.output || 'N/A')}</div>
        </div>
    `;
}

/**
 * Format model name for display
 */
function formatModel(model) {
    if (!model || model === '-') return '-';
    // Shorten long model names
    return model.replace('claude-', '').replace('gpt-', 'GPT-');
}

/**
 * Truncate text
 */
function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}

/**
 * Capitalize first letter
 */
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on load
init();
