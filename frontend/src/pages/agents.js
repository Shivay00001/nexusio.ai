/**
 * NexusAI — Agents Page
 * Create & run AI agents with tool access, view step-by-step execution.
 */

import { api } from '../api.js';
import { showToast } from '../components/toast.js';

let isRunning = false;

export async function renderAgents() {
  const container = document.getElementById('page-container');

  container.innerHTML = `
    <div class="chat-layout">
      <div class="page-header">
        <div>
          <h1 class="page-title">AI Agents</h1>
          <div class="page-subtitle">Run multi-step tasks with tool-calling agents</div>
        </div>
      </div>

      <div class="agent-layout">
        <!-- Config Card -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Agent Configuration</h3>
          </div>

          <div class="agent-config">
            <div class="form-group">
              <label class="form-label">Provider</label>
              <select class="input" id="agent-provider">
                <option value="">Auto (Smart Routing)</option>
                <option value="ollama">🏠 Ollama</option>
                <option value="g4f">🔄 g4f</option>
                <option value="pollinations">🎨 Pollinations</option>
                <option value="groq">⚡ Groq</option>
                <option value="openrouter">🌐 OpenRouter</option>
                <option value="huggingface">🤗 HuggingFace</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Model (optional)</label>
              <input class="input" id="agent-model" placeholder="Leave empty for default" />
            </div>
          </div>

          <div class="form-group" style="margin-top:8px">
            <label class="form-label">Available Tools</label>
            <div class="tools-grid" id="tools-grid">
              <label class="tool-check"><input type="checkbox" value="web_search" checked> 🔍 Web Search</label>
              <label class="tool-check"><input type="checkbox" value="extract_url" checked> 📄 URL Extractor</label>
              <label class="tool-check"><input type="checkbox" value="execute_python" checked> 🐍 Python Exec</label>
              <label class="tool-check"><input type="checkbox" value="http_get" checked> 🌐 HTTP GET</label>
              <label class="tool-check"><input type="checkbox" value="http_post" checked> 📡 HTTP POST</label>
              <label class="tool-check"><input type="checkbox" value="file_read" checked> 📖 File Read</label>
              <label class="tool-check"><input type="checkbox" value="file_write" checked> ✏️ File Write</label>
              <label class="tool-check"><input type="checkbox" value="file_list" checked> 📁 File List</label>
            </div>
          </div>

          <div class="form-group" style="margin-top:12px">
            <label class="form-label">Task</label>
            <textarea class="textarea" id="agent-task" placeholder="Describe what the agent should do, e.g. 'Research the top 5 programming languages in 2026 and create a comparison report'" rows="3"></textarea>
          </div>

          <button class="btn btn-primary" id="run-agent-btn" style="margin-top:8px">
            ▶ Run Agent
          </button>
        </div>

        <!-- Output -->
        <div class="agent-output" id="agent-output">
          <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="8" r="4"/>
              <path d="M6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2"/>
            </svg>
            <p>Configure your agent and click <strong>Run Agent</strong> to start.</p>
            <p style="font-size:0.82rem;margin-top:4px;color:var(--text-muted)">The agent will reason, use tools, and provide step-by-step results.</p>
          </div>
        </div>
      </div>
    </div>
  `;

  // Bind run button
  document.getElementById('run-agent-btn').addEventListener('click', runAgent);
}

async function runAgent() {
  if (isRunning) return;

  const task = document.getElementById('agent-task').value.trim();
  if (!task) {
    showToast('Please enter a task for the agent', 'error');
    return;
  }

  const provider = document.getElementById('agent-provider').value || undefined;
  const model = document.getElementById('agent-model').value.trim() || undefined;

  // Get selected tools
  const toolCheckboxes = document.querySelectorAll('#tools-grid input[type="checkbox"]:checked');
  const tools = Array.from(toolCheckboxes).map(cb => cb.value);

  isRunning = true;
  const btn = document.getElementById('run-agent-btn');
  btn.innerHTML = '<span class="spinner" style="display:inline-block"></span> Running<span class="loading-dots"></span>';
  btn.disabled = true;

  const output = document.getElementById('agent-output');
  output.innerHTML = `
    <div class="card" style="margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:8px">
        <span class="spinner" style="display:inline-block"></span>
        <span>Agent is working on your task<span class="loading-dots"></span></span>
      </div>
      <div class="progress-bar" style="margin-top:12px">
        <div class="progress-fill" style="width:10%"></div>
      </div>
    </div>
  `;

  try {
    const result = await api.runAgent({ task, provider, model, tools });

    output.innerHTML = '';

    // Render steps
    if (result.steps && result.steps.length > 0) {
      result.steps.forEach((step, i) => {
        let stepHtml = `
          <div class="agent-step">
            <div class="step-header">
              <span class="step-num">${step.step}</span>
              <span>${step.tool_call ? `Tool: ${step.tool_call.tool}` : 'Reasoning'}</span>
            </div>
        `;

        if (step.thought) {
          stepHtml += `<div class="step-content">${step.thought}</div>`;
        }

        if (step.tool_call) {
          stepHtml += `<div class="step-tool">🔧 ${step.tool_call.tool}(${JSON.stringify(step.tool_call.args || {}).slice(0, 100)})</div>`;
        }

        if (step.tool_result) {
          const truncated = step.tool_result.length > 500
            ? step.tool_result.slice(0, 500) + '...'
            : step.tool_result;
          stepHtml += `<div class="step-result">${truncated.replace(/</g,'&lt;').replace(/\n/g,'<br>')}</div>`;
        }

        if (step.response) {
          stepHtml += `<div class="step-content" style="margin-top:8px;color:var(--text-primary)">${step.response.replace(/\n/g,'<br>')}</div>`;
        }

        stepHtml += '</div>';
        output.insertAdjacentHTML('beforeend', stepHtml);
      });
    }

    // Final result
    if (result.result) {
      output.insertAdjacentHTML('beforeend', `
        <div class="card" style="border-color:rgba(16,185,129,0.3);background:rgba(16,185,129,0.05)">
          <div class="card-header">
            <h3 class="card-title" style="color:var(--accent-emerald)">✅ Final Result</h3>
            <span class="badge badge-success">Completed</span>
          </div>
          <div style="line-height:1.7;white-space:pre-wrap">${result.result.replace(/</g,'&lt;')}</div>
        </div>
      `);
    }

    showToast('Agent completed successfully!', 'success');

  } catch (err) {
    output.innerHTML = `
      <div class="card" style="border-color:rgba(244,63,94,0.3)">
        <h3 style="color:var(--accent-rose);margin-bottom:8px">Agent Error</h3>
        <p>${err.message}</p>
      </div>
    `;
    showToast(err.message, 'error');
  } finally {
    isRunning = false;
    btn.innerHTML = '▶ Run Agent';
    btn.disabled = false;
  }
}
