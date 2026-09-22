/**
 * NexusAI — Providers Page
 * Real-time provider health dashboard with status cards.
 */

import { api } from '../api.js';
import { showToast } from '../components/toast.js';

const PROVIDER_META = {
  ollama: { icon: '🏠', label: 'Ollama', color: '#06b6d4', desc: 'Local LLM • No limits • Private' },
  g4f: { icon: '🔄', label: 'GPT4Free', color: '#8b5cf6', desc: 'Multi-model aggregator • Free' },
  pollinations: { icon: '🎨', label: 'Pollinations', color: '#10b981', desc: 'Text & Image gen • No key needed' },
  openrouter: { icon: '🌐', label: 'OpenRouter', color: '#3b82f6', desc: 'Free :free models • Reliable' },
  groq: { icon: '⚡', label: 'Groq', color: '#f59e0b', desc: 'Ultra-fast inference • Free tier' },
  huggingface: { icon: '🤗', label: 'HuggingFace', color: '#f43f5e', desc: 'Serverless models • Free tier' },
};

export async function renderProviders() {
  const container = document.getElementById('page-container');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Providers</h1>
        <div class="page-subtitle">Monitor and manage AI provider connections</div>
      </div>
      <button class="btn btn-primary btn-sm" id="refresh-all-btn">
        ↻ Refresh All
      </button>
    </div>
    <div class="providers-grid" id="providers-grid">
      <div style="text-align:center;padding:40px;grid-column:1/-1">
        <span class="spinner" style="display:inline-block;width:32px;height:32px"></span>
        <p style="margin-top:12px;color:var(--text-muted)">Checking provider health<span class="loading-dots"></span></p>
      </div>
    </div>
  `;

  document.getElementById('refresh-all-btn').addEventListener('click', async () => {
    const btn = document.getElementById('refresh-all-btn');
    btn.innerHTML = '<span class="spinner" style="display:inline-block;width:14px;height:14px"></span> Refreshing';
    btn.disabled = true;
    try {
      await api.refreshProviders();
      showToast('All providers refreshed', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      btn.innerHTML = '↻ Refresh All';
      btn.disabled = false;
      loadProviders();
    }
  });

  loadProviders();
}

async function loadProviders() {
  const grid = document.getElementById('providers-grid');

  try {
    const data = await api.getProviders();
    const providers = data.providers || [];

    grid.innerHTML = providers.map(p => {
      const meta = PROVIDER_META[p.name] || { icon: '🔌', label: p.name, color: '#94a3b8', desc: '' };
      const health = p.health || {};
      const isHealthy = health.healthy;
      const latency = health.latency_ms || 0;
      const detail = health.detail || 'Not checked';

      // Latency color
      let latencyColor = 'var(--accent-emerald)';
      if (latency > 2000) latencyColor = 'var(--accent-rose)';
      else if (latency > 500) latencyColor = 'var(--accent-amber)';

      const statusBadge = isHealthy === true
        ? '<span class="badge badge-success">Online</span>'
        : isHealthy === false
          ? '<span class="badge badge-danger">Offline</span>'
          : '<span class="badge badge-warning">Unknown</span>';

      return `
        <div class="provider-card">
          <div class="provider-header">
            <div class="provider-name">
              <div class="provider-icon" style="background:${meta.color}22;font-size:1.3rem">${meta.icon}</div>
              ${meta.label}
            </div>
            ${statusBadge}
          </div>
          <div class="provider-details">
            <div class="provider-detail">
              <span class="provider-detail-label">Type</span>
              <span class="provider-detail-value">${p.type}</span>
            </div>
            <div class="provider-detail">
              <span class="provider-detail-label">API Key</span>
              <span class="provider-detail-value">${p.requires_api_key ? '🔑 Required' : '✅ Not needed'}</span>
            </div>
            <div class="provider-detail">
              <span class="provider-detail-label">Latency</span>
              <span class="provider-detail-value" style="color:${latencyColor}">${latency ? latency.toFixed(0) + 'ms' : '—'}</span>
            </div>
            ${latency ? `
              <div class="latency-bar">
                <div class="latency-fill" style="width:${Math.min(latency / 30, 100)}%;background:${latencyColor}"></div>
              </div>
            ` : ''}
            <div style="font-size:0.82rem;color:var(--text-muted);margin-top:4px">${detail}</div>
          </div>
          <button class="btn btn-secondary btn-sm" style="margin-top:14px;width:100%" onclick="window.__checkProvider('${p.name}')">
            Test Connection
          </button>
        </div>
      `;
    }).join('');

    // Bind test buttons
    window.__checkProvider = async (name) => {
      try {
        showToast(`Testing ${name}...`, 'info', 2000);
        await api.checkProviderHealth(name);
        showToast(`${name} is reachable!`, 'success');
        loadProviders();
      } catch (e) {
        showToast(`${name} failed: ${e.message}`, 'error');
      }
    };

  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;color:var(--accent-rose)">Failed to load providers: ${err.message}</div>`;
  }
}
