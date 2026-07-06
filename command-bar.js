/* ============================================================
   Life OS — Command Bar (shared component)
   Ctrl+K opens overlay, parses actions
   Include in shared.js or page <script>
   ============================================================ */

const CommandBar = {
  open: false,
  selectedIndex: 0,
  query: '',
  actions: [],

  init() {
    // Register keyboard shortcut
    document.addEventListener('keydown', (e) => {
      // Ctrl+K or Cmd+K to open
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.toggle();
      }
      // Escape to close
      if (e.key === 'Escape' && this.open) {
        this.close();
      }
      // Arrow navigation
      if (this.open) {
        if (e.key === 'ArrowDown') { e.preventDefault(); this.moveSelection(1); }
        if (e.key === 'ArrowUp') { e.preventDefault(); this.moveSelection(-1); }
        if (e.key === 'Enter') { e.preventDefault(); this.executeSelected(); }
      }
    });

    // Create DOM if not exists
    if (!document.getElementById('commandBarOverlay')) {
      this.createDOM();
    }
  },

  createDOM() {
    const overlay = document.createElement('div');
    overlay.className = 'command-bar-overlay';
    overlay.id = 'commandBarOverlay';
    overlay.onclick = (e) => { if (e.target === overlay) this.close(); };
    overlay.innerHTML = `
      <div class="command-bar" role="dialog" aria-label="Command bar">
        <div class="command-bar-input-row">
          <span class="icon">⌘</span>
          <input type="text" class="command-bar-input" id="commandBarInput" placeholder="Type an action..." autocomplete="off" spellcheck="false">
        </div>
        <div class="command-bar-results" id="commandBarResults"></div>
        <div class="command-bar-hint">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>Enter</kbd> execute</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    // Input listener
    const input = document.getElementById('commandBarInput');
    input.addEventListener('input', () => {
      this.query = input.value.toLowerCase().trim();
      this.selectedIndex = 0;
      this.render();
    });
  },

  registerActions(actions) {
    this.actions = actions;
  },

  toggle() {
    this.open = !this.open;
    const overlay = document.getElementById('commandBarOverlay');
    overlay.classList.toggle('open', this.open);
    if (this.open) {
      this.query = '';
      const input = document.getElementById('commandBarInput');
      input.value = '';
      setTimeout(() => input.focus(), 50);
      this.render();
    }
  },

  close() {
    this.open = false;
    document.getElementById('commandBarOverlay').classList.remove('open');
  },

  moveSelection(dir) {
    const items = document.querySelectorAll('.command-bar-item');
    this.selectedIndex = Math.max(0, Math.min(this.selectedIndex + dir, items.length - 1));
    items.forEach((el, i) => el.classList.toggle('selected', i === this.selectedIndex));
    if (items[this.selectedIndex]) items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
  },

  executeSelected() {
    const items = document.querySelectorAll('.command-bar-item');
    if (items[this.selectedIndex]) {
      const actionId = items[this.selectedIndex].dataset.action;
      const action = this.actions.find(a => a.id === actionId);
      if (action) {
        this.close();
        action.execute();
      }
    }
  },

  render() {
    const container = document.getElementById('commandBarResults');
    let filtered = this.actions;

    if (this.query) {
      filtered = this.actions.filter(a =>
        a.title.toLowerCase().includes(this.query) ||
        (a.desc && a.desc.toLowerCase().includes(this.query)) ||
        (a.keywords && a.keywords.some(k => k.includes(this.query)))
      );
    }

    if (filtered.length === 0) {
      container.innerHTML = '<div class="command-bar-empty">No matching actions. Try "send", "create", "search", or "go to".</div>';
      return;
    }

    container.innerHTML = filtered.map((a, i) => `
      <div class="command-bar-item ${i === this.selectedIndex ? 'selected' : ''}" data-action="${a.id}" onclick="CommandBar.executeAction('${a.id}')">
        <span class="item-icon">${a.icon}</span>
        <div class="item-text">
          <div class="item-title">${a.title}</div>
          ${a.desc ? `<div class="item-desc">${a.desc}</div>` : ''}
        </div>
        ${a.shortcut ? `<span class="item-shortcut">${a.shortcut}</span>` : ''}
      </div>
    `).join('');
  },

  executeAction(id) {
    const action = this.actions.find(a => a.id === id);
    if (action) {
      this.close();
      action.execute();
    }
  }
};

// Default actions (can be extended per-page)
function getDefaultActions() {
  return [
    { id: 'nav-dashboard', icon: '⚡', title: 'Go to Dashboard', desc: 'Main overview and KPIs', shortcut: 'G D', keywords: ['dashboard', 'home', 'overview'], execute: () => { window.location.href = 'index.html'; } },
    { id: 'nav-chat', icon: '💬', title: 'New Chat', desc: 'Start a conversation with Hermes', shortcut: '', keywords: ['chat', 'message', 'talk', 'hermes'], execute: () => { window.location.href = 'chat.html'; } },
    { id: 'nav-kanban', icon: '📝', title: 'Kanban Board', desc: 'View and manage your tasks', shortcut: 'G T', keywords: ['tasks', 'todo', 'kanban', 'board'], execute: () => { window.location.href = 'kanban.html'; } },
    { id: 'nav-files', icon: '📁', title: 'File Browser', desc: 'Browse vault files and folders', shortcut: 'G F', keywords: ['files', 'browse', 'vault', 'folder'], execute: () => { window.location.href = 'files.html'; } },
    { id: 'nav-graph3d', icon: '🧠', title: '3D Knowledge Brain', desc: '3D force graph of vault', shortcut: '', keywords: ['3d', 'brain', 'graph', 'force'], execute: () => { window.location.href = 'graph3d.html'; } },
    { id: 'nav-skills', icon: '🔧', title: 'Skills Library', desc: 'Browse installed skills', shortcut: '', keywords: ['skills', 'plugins', 'tools'], execute: () => { window.location.href = 'skills.html'; } },
    { id: 'nav-keys', icon: '🔑', title: 'API Keys', desc: 'Manage provider API keys', shortcut: '', keywords: ['keys', 'api', 'providers', 'connect'], execute: () => { window.location.href = 'keys.html'; } },
    { id: 'nav-playbook', icon: '⚡', title: 'Playbook (Use Cases & Prompts)', desc: 'Curated use case & prompt library', shortcut: '', keywords: ['use cases', 'prompts', 'library', 'playbook'], execute: () => { window.location.href = 'use-cases.html'; } },
    { id: 'nav-models', icon: '🤖', title: 'Models & Usage', desc: 'AI model catalog and token usage', shortcut: '', keywords: ['models', 'ai', 'llm', 'tokens', 'usage'], execute: () => { window.location.href = 'models.html'; } },
    { id: 'nav-loops', icon: '🔁', title: 'Loops (Automations)', desc: 'Automation registry — every scheduled job', shortcut: '', keywords: ['loops', 'cron', 'scheduled', 'jobs', 'automation'], execute: () => { window.location.href = 'loops.html'; } },
    { id: 'action-search', icon: '🔍', title: 'Search Vault', desc: 'Search all notes and files', shortcut: '/', keywords: ['search', 'find', 'lookup'], execute: () => { const q = prompt('Search vault for:'); if (q) window.location.href = 'files.html?search=' + encodeURIComponent(q); } },
    { id: 'action-ship', icon: '🚀', title: 'What did I ship today?', desc: 'Show today\'s accomplishments', shortcut: '', keywords: ['ship', 'today', 'progress', 'recap'], execute: () => { Notify.info('📦 Today\'s ships will appear here. Coming in Batch 5.'); } },
  ];
}

// Auto-init
document.addEventListener('DOMContentLoaded', () => {
  CommandBar.init();
  CommandBar.registerActions(getDefaultActions());
});
