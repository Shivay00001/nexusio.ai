/**
 * NexusAI — Chat Page
 * Multi-model chat with provider switching and streaming responses.
 */

import { api } from '../api.js';
import { showToast } from '../components/toast.js';

let currentConvId = null;
let isLoading = false;
let providers = [];

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(text) {
  // Simple markdown: code blocks, inline code, bold, links
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function createMessage(role, content, provider = '', model = '') {
  const avatar = role === 'user' ? 'U' : 'N';
  const meta = provider ? `<div class="message-meta"><span class="badge badge-info">${provider}</span>${model ? `<span>${model}</span>` : ''}</div>` : '';

  return `
    <div class="message ${role}">
      <div class="message-avatar">${avatar}</div>
      <div>
        <div class="message-content">${renderMarkdown(content)}</div>
        ${meta}
      </div>
    </div>
  `;
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message || isLoading) return;

  const providerSelect = document.getElementById('provider-select');
  const selectedProvider = providerSelect?.value || '';

  isLoading = true;
  input.value = '';
  input.style.height = 'auto';

  // Show user message
  const messagesEl = document.getElementById('chat-messages');
  const welcome = messagesEl.querySelector('.welcome-screen');
  if (welcome) welcome.remove();

  messagesEl.insertAdjacentHTML('beforeend', createMessage('user', escapeHtml(message)));

  // Show loading
  const loadingId = 'loading-' + Date.now();
  messagesEl.insertAdjacentHTML('beforeend', `
    <div class="message assistant" id="${loadingId}">
      <div class="message-avatar">N</div>
      <div>
        <div class="message-content"><span class="spinner" style="display:inline-block"></span> Thinking<span class="loading-dots"></span></div>
      </div>
    </div>
  `);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Update send button
  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  try {
    const result = await api.chat({
      message,
      conversation_id: currentConvId,
      provider: selectedProvider || undefined,
    });

    currentConvId = result.conversation_id;

    // Replace loading with response
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) {
      loadingEl.outerHTML = createMessage('assistant', result.response, result.provider, result.model);
    }

  } catch (err) {
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) {
      loadingEl.outerHTML = createMessage('assistant', `⚠️ Error: ${err.message}`);
    }
    showToast(err.message, 'error');
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

function handleQuickAction(prompt) {
  const input = document.getElementById('chat-input');
  input.value = prompt;
  sendMessage();
}

export function renderChat() {
  const container = document.getElementById('page-container');

  container.innerHTML = `
    <div class="chat-layout">
      <div class="page-header">
        <div>
          <h1 class="page-title">Chat</h1>
          <div class="page-subtitle">Multi-provider AI chat with smart routing</div>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <button class="btn btn-secondary btn-sm" id="new-chat-btn">+ New Chat</button>
        </div>
      </div>

      <div class="chat-messages" id="chat-messages">
        <div class="welcome-screen">
          <svg class="welcome-icon" viewBox="0 0 80 80" fill="none">
            <defs>
              <linearGradient id="wg" x1="0" y1="0" x2="80" y2="80">
                <stop offset="0%" stop-color="#06b6d4"/>
                <stop offset="100%" stop-color="#8b5cf6"/>
              </linearGradient>
            </defs>
            <circle cx="40" cy="40" r="36" stroke="url(#wg)" stroke-width="3" fill="none" opacity="0.5"/>
            <path d="M25 50L40 25L55 50" stroke="url(#wg)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="40" cy="40" r="6" fill="url(#wg)" opacity="0.7"/>
          </svg>
          <h2 class="welcome-title">Welcome to NexusAI</h2>
          <p class="welcome-subtitle">Chat with any AI model through 6 unified providers — local, free, and fast.</p>
          <div class="quick-actions">
            <div class="quick-action" onclick="window.__quickAction('Explain how machine learning works in simple terms')">
              <div class="quick-action-title">🧠 Explain ML</div>
              <div class="quick-action-desc">Get a simple explanation of machine learning</div>
            </div>
            <div class="quick-action" onclick="window.__quickAction('Write a Python function to find prime numbers up to N')">
              <div class="quick-action-title">💻 Code Helper</div>
              <div class="quick-action-desc">Generate Python code for common tasks</div>
            </div>
            <div class="quick-action" onclick="window.__quickAction('Summarize the latest trends in AI and technology for 2026')">
              <div class="quick-action-title">📊 AI Trends</div>
              <div class="quick-action-desc">Get insights on latest AI developments</div>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <div class="chat-input-container">
          <div class="chat-input-wrapper">
            <textarea class="chat-input" id="chat-input" placeholder="Type your message... (Enter to send, Shift+Enter for new line)" rows="1"></textarea>
            <div class="chat-controls">
              <select class="provider-select-mini" id="provider-select">
                <option value="">Auto</option>
                <option value="ollama">Ollama</option>
                <option value="g4f">g4f</option>
                <option value="pollinations">Pollinations</option>
                <option value="groq">Groq</option>
                <option value="openrouter">OpenRouter</option>
                <option value="huggingface">HuggingFace</option>
              </select>
              <button class="send-btn" id="send-btn" title="Send message">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Bind events
  window.__quickAction = handleQuickAction;

  document.getElementById('send-btn').addEventListener('click', sendMessage);

  const chatInput = document.getElementById('chat-input');
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
  });

  document.getElementById('new-chat-btn').addEventListener('click', () => {
    currentConvId = null;
    renderChat();
  });

  // Focus input
  chatInput.focus();
}
