/**
 * NexusAI — API Client & WebSocket Manager
 */

const API_BASE = '/api';

class NexusAPI {
  constructor() {
    this.ws = null;
    this.wsCallbacks = {};
  }

  // ── REST helpers ─────────────────────────────────────────
  async _fetch(path, options = {}) {
    const resp = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  }

  // ── Health ───────────────────────────────────────────────
  health() { return this._fetch('/health'); }

  // ── Providers ────────────────────────────────────────────
  getProviders() { return this._fetch('/providers'); }
  refreshProviders() { return this._fetch('/providers/refresh', { method: 'POST' }); }
  checkProviderHealth(name) { return this._fetch(`/providers/${name}/health`, { method: 'POST' }); }
  getModels() { return this._fetch('/models'); }
  getProviderModels(name) { return this._fetch(`/models/${name}`); }

  // ── Chat ─────────────────────────────────────────────────
  chat(data) {
    return this._fetch('/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  getConversations() { return this._fetch('/conversations'); }
  getMessages(convId) { return this._fetch(`/conversations/${convId}/messages`); }
  deleteConversation(convId) { return this._fetch(`/conversations/${convId}`, { method: 'DELETE' }); }

  // ── Agents ───────────────────────────────────────────────
  runAgent(data) {
    return this._fetch('/agent/run', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  getAgentSessions() { return this._fetch('/agent/sessions'); }
  getAgentSession(id) { return this._fetch(`/agent/sessions/${id}`); }
  getTools() { return this._fetch('/agent/tools'); }

  // ── Workflows ────────────────────────────────────────────
  getWorkflowTemplates() { return this._fetch('/workflows/templates'); }
  runWorkflow(data) {
    return this._fetch('/workflows/run', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  getWorkflows() { return this._fetch('/workflows'); }

  // ── WebSocket ────────────────────────────────────────────
  connectChatWS(onChunk, onDone, onError) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.ws = new WebSocket(`${proto}//${location.host}/ws/chat`);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chunk' && onChunk) onChunk(data);
      else if (data.type === 'done' && onDone) onDone(data);
      else if (data.type === 'error' && onError) onError(data);
    };

    this.ws.onerror = () => onError?.({ content: 'WebSocket connection error' });
    this.ws.onclose = () => {};

    return new Promise((resolve) => {
      this.ws.onopen = () => resolve(this.ws);
    });
  }

  sendChatWS(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  closeChatWS() {
    this.ws?.close();
    this.ws = null;
  }
}

export const api = new NexusAPI();
