/**
 * NexusAI — Workflows Page
 * Pre-built workflow templates and custom workflow execution.
 */

import { api } from '../api.js';
import { showToast } from '../components/toast.js';

const TEMPLATE_ICONS = {
  research_pipeline: { icon: '🔬', bg: 'rgba(6,182,212,0.15)' },
  content_generator: { icon: '✍️', bg: 'rgba(139,92,246,0.15)' },
  code_assistant: { icon: '💻', bg: 'rgba(16,185,129,0.15)' },
  data_processor: { icon: '📊', bg: 'rgba(245,158,11,0.15)' },
};

let isRunning = false;

export async function renderWorkflows() {
  const container = document.getElementById('page-container');

  container.innerHTML = `
    <div class="chat-layout">
      <div class="page-header">
        <div>
          <h1 class="page-title">Workflows</h1>
          <div class="page-subtitle">Automated multi-step AI pipelines</div>
        </div>
      </div>

      <div class="workflows-layout">
        <h3 style="margin-bottom:4px">Workflow Templates</h3>
        <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:16px">Click a template to configure and run it.</p>

        <div class="template-grid" id="template-grid">
          <div class="template-card" data-template="research_pipeline">
            <div class="template-icon" style="background:rgba(6,182,212,0.15)">🔬</div>
            <div class="template-name">Research Pipeline</div>
            <div class="template-desc">Search the web, extract content, and generate a summary report.</div>
          </div>
          <div class="template-card" data-template="content_generator">
            <div class="template-icon" style="background:rgba(139,92,246,0.15)">✍️</div>
            <div class="template-name">Content Generator</div>
            <div class="template-desc">Outline → Draft → Polished content in automated steps.</div>
          </div>
          <div class="template-card" data-template="code_assistant">
            <div class="template-icon" style="background:rgba(16,185,129,0.15)">💻</div>
            <div class="template-name">Code Assistant</div>
            <div class="template-desc">Analyze → Plan → Implement → Test code automatically.</div>
          </div>
          <div class="template-card" data-template="data_processor">
            <div class="template-icon" style="background:rgba(245,158,11,0.15)">📊</div>
            <div class="template-name">Data Processor</div>
            <div class="template-desc">Fetch data from URL, analyze it, and generate a report.</div>
          </div>
        </div>

        <!-- Workflow Runner (hidden until template selected) -->
        <div id="workflow-runner" style="display:none;margin-top:24px">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title" id="wf-title">Run Workflow</h3>
              <button class="btn btn-ghost btn-sm" id="wf-close">✕ Close</button>
            </div>
            <div id="wf-variables"></div>
            <button class="btn btn-primary" id="wf-run-btn" style="margin-top:12px">▶ Execute Workflow</button>
          </div>
        </div>

        <!-- Workflow Output -->
        <div id="workflow-output" style="margin-top:24px"></div>
      </div>
    </div>
  `;

  // Bind template clicks
  document.querySelectorAll('.template-card').forEach(card => {
    card.addEventListener('click', () => selectTemplate(card.dataset.template));
  });
}

const TEMPLATE_VARS = {
  research_pipeline: [{ key: 'topic', label: 'Research Topic', placeholder: 'e.g. Quantum Computing breakthroughs 2026' }],
  content_generator: [{ key: 'topic', label: 'Content Topic', placeholder: 'e.g. The Future of Renewable Energy' }],
  code_assistant: [{ key: 'task', label: 'Coding Task', placeholder: 'e.g. Build a REST API with FastAPI for a todo app' }],
  data_processor: [{ key: 'url', label: 'Data URL', placeholder: 'e.g. https://example.com/data-page' }],
};

function selectTemplate(templateId) {
  const runner = document.getElementById('workflow-runner');
  const vars = TEMPLATE_VARS[templateId] || [];
  const icon = TEMPLATE_ICONS[templateId] || { icon: '⚡' };

  document.getElementById('wf-title').textContent = `${icon.icon} Run ${templateId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}`;

  const varsHtml = vars.map(v => `
    <div class="form-group">
      <label class="form-label">${v.label}</label>
      <input class="input" id="wf-var-${v.key}" placeholder="${v.placeholder}" />
    </div>
  `).join('');

  document.getElementById('wf-variables').innerHTML = varsHtml;
  runner.style.display = 'block';
  runner.dataset.template = templateId;

  document.getElementById('wf-close').addEventListener('click', () => {
    runner.style.display = 'none';
  });

  document.getElementById('wf-run-btn').addEventListener('click', () => {
    runWorkflow(templateId, vars);
  });

  // Scroll to runner
  runner.scrollIntoView({ behavior: 'smooth' });
}

async function runWorkflow(templateId, varDefs) {
  if (isRunning) return;

  const variables = {};
  for (const v of varDefs) {
    const el = document.getElementById(`wf-var-${v.key}`);
    const val = el?.value.trim();
    if (!val) {
      showToast(`Please fill in: ${v.label}`, 'error');
      return;
    }
    variables[v.key] = val;
  }

  isRunning = true;
  const btn = document.getElementById('wf-run-btn');
  btn.innerHTML = '<span class="spinner" style="display:inline-block"></span> Running<span class="loading-dots"></span>';
  btn.disabled = true;

  const output = document.getElementById('workflow-output');
  output.innerHTML = `
    <div class="card">
      <div style="display:flex;align-items:center;gap:8px">
        <span class="spinner" style="display:inline-block"></span>
        <span>Workflow is executing<span class="loading-dots"></span></span>
      </div>
      <div class="progress-bar" style="margin-top:12px">
        <div class="progress-fill" style="width:20%"></div>
      </div>
    </div>
  `;

  try {
    const result = await api.runWorkflow({
      template: templateId,
      variables,
    });

    output.innerHTML = '';

    // Render step results
    if (result.result && result.result.steps) {
      const steps = result.result.steps;
      for (const [stepId, step] of Object.entries(steps)) {
        const statusIcon = step.status === 'completed' ? '✅' : step.status === 'failed' ? '❌' : '⏳';
        const statusClass = step.status;

        output.insertAdjacentHTML('beforeend', `
          <div class="workflow-step-card">
            <div class="workflow-step-icon ${statusClass}">${statusIcon}</div>
            <div style="flex:1;min-width:0">
              <div style="font-weight:600;margin-bottom:4px">${step.name}</div>
              <div style="font-size:0.82rem;color:var(--text-muted);margin-bottom:6px">
                ${step.type} • ${step.duration_ms ? Math.round(step.duration_ms) + 'ms' : ''}
              </div>
              ${step.result ? `<div style="background:var(--bg-tertiary);padding:12px;border-radius:var(--radius-sm);font-size:0.88rem;max-height:300px;overflow-y:auto;white-space:pre-wrap;word-break:break-word">${String(step.result).replace(/</g,'&lt;').slice(0, 2000)}</div>` : ''}
              ${step.error ? `<div style="color:var(--accent-rose);margin-top:6px">Error: ${step.error}</div>` : ''}
            </div>
          </div>
        `);
      }
    }

    showToast('Workflow completed!', 'success');

  } catch (err) {
    output.innerHTML = `
      <div class="card" style="border-color:rgba(244,63,94,0.3)">
        <h3 style="color:var(--accent-rose);margin-bottom:8px">Workflow Error</h3>
        <p>${err.message}</p>
      </div>
    `;
    showToast(err.message, 'error');
  } finally {
    isRunning = false;
    btn.innerHTML = '▶ Execute Workflow';
    btn.disabled = false;
  }
}
