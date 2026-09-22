/**
 * NexusAI — SPA Client-Side Router
 */

class Router {
  constructor() {
    this.routes = {};
    this.currentPage = null;
    window.addEventListener('hashchange', () => this.navigate());
  }

  register(path, handler) {
    this.routes[path] = handler;
  }

  navigate(path) {
    if (path) window.location.hash = path;
    const hash = window.location.hash.slice(1) || '/chat';
    const handler = this.routes[hash] || this.routes['/chat'];

    // Update active nav
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.page === hash.slice(1));
    });

    this.currentPage = hash;
    if (handler) handler();
  }

  init() {
    this.navigate();
  }
}

export const router = new Router();
