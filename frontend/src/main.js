/**
 * NexusAI — Main Application Entry Point
 */

import { router } from './router.js';
import { renderChat } from './pages/chat.js';
import { renderAgents } from './pages/agents.js';
import { renderWorkflows } from './pages/workflows.js';
import { renderProviders } from './pages/providers.js';
import { renderSettings } from './pages/settings.js';
import { api } from './api.js';
import { showToast } from './components/toast.js';

// ── Register Routes ─────────────────────────────────────────
router.register('/chat', renderChat);
router.register('/agents', renderAgents);
router.register('/workflows', renderWorkflows);
router.register('/providers', renderProviders);
router.register('/settings', renderSettings);

// ── Sidebar Toggle ──────────────────────────────────────────
document.getElementById('sidebar-toggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('collapsed');
});

// ── Connection Health Check ─────────────────────────────────
async function checkConnection() {
  const statusEl = document.getElementById('connection-status');
  try {
    await api.health();
    statusEl.innerHTML = '<span class="status-dot online"></span><span>Connected</span>';
  } catch {
    statusEl.innerHTML = '<span class="status-dot offline"></span><span>Offline</span>';
    showToast('Backend not reachable. Start the server with: python -m backend.main', 'error', 6000);
  }
}

// ── Initialize ──────────────────────────────────────────────
checkConnection();
router.init();

// Re-check connection periodically
setInterval(checkConnection, 30000);

console.log(
  '%c🚀 NexusAI Dashboard Loaded',
  'color: #06b6d4; font-weight: bold; font-size: 14px;'
);
