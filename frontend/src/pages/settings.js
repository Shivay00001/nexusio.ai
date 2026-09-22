/**
 * NexusAI — Settings Page
 */

import { showToast } from '../components/toast.js';

export function renderSettings() {
  const container = document.getElementById('page-container');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Settings</h1>
        <div class="page-subtitle">Configure NexusAI system preferences</div>
      </div>
    </div>

    <div class="settings-layout">
      <div class="settings-section">
        <h3 class="settings-section-title">🔑 API Keys</h3>
        <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:16px">
          API keys are stored in the <code>.env</code> file in the project root. 
          Ollama, g4f, and Pollinations work without any keys.
        </p>

        <div class="card" style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <strong>OpenRouter</strong>
              <div style="font-size:0.82rem;color:var(--text-muted)">Free key from openrouter.ai</div>
            </div>
            <span class="badge badge-info">Optional</span>
          </div>
        </div>

        <div class="card" style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <strong>Groq</strong>
              <div style="font-size:0.82rem;color:var(--text-muted)">Free key from console.groq.com</div>
            </div>
            <span class="badge badge-info">Optional</span>
          </div>
        </div>

        <div class="card" style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <strong>HuggingFace</strong>
              <div style="font-size:0.82rem;color:var(--text-muted)">Free key from huggingface.co/settings/tokens</div>
            </div>
            <span class="badge badge-info">Optional</span>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <h3 class="settings-section-title">⚙️ Provider Priority</h3>
        <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:16px">
          Set in <code>.env</code> file via <code>PROVIDER_PRIORITY</code>. The first available healthy provider is used.
        </p>
        <div class="card">
          <code style="font-family:var(--font-mono);font-size:0.88rem;color:var(--accent-cyan)">
            PROVIDER_PRIORITY=ollama,groq,g4f,pollinations,openrouter,huggingface
          </code>
        </div>
      </div>

      <div class="settings-section">
        <h3 class="settings-section-title">📂 Configuration Files</h3>
        <div class="card">
          <div style="display:flex;flex-direction:column;gap:10px">
            <div style="display:flex;justify-content:space-between">
              <span><code>.env</code></span>
              <span style="color:var(--text-muted);font-size:0.88rem">API keys & server config</span>
            </div>
            <div style="display:flex;justify-content:space-between">
              <span><code>.env.example</code></span>
              <span style="color:var(--text-muted);font-size:0.88rem">Template with all options</span>
            </div>
            <div style="display:flex;justify-content:space-between">
              <span><code>backend/config.py</code></span>
              <span style="color:var(--text-muted);font-size:0.88rem">Python configuration module</span>
            </div>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <h3 class="settings-section-title">ℹ️ About</h3>
        <div class="card">
          <div style="display:flex;flex-direction:column;gap:8px">
            <div style="display:flex;justify-content:space-between">
              <span style="color:var(--text-muted)">Version</span>
              <span>1.0.0</span>
            </div>
            <div style="display:flex;justify-content:space-between">
              <span style="color:var(--text-muted)">Backend</span>
              <span>FastAPI + Python</span>
            </div>
            <div style="display:flex;justify-content:space-between">
              <span style="color:var(--text-muted)">Frontend</span>
              <span>Vite + Vanilla JS</span>
            </div>
            <div style="display:flex;justify-content:space-between">
              <span style="color:var(--text-muted)">Providers</span>
              <span>6 (Ollama, g4f, Pollinations, OpenRouter, Groq, HuggingFace)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}
