/* ============================================================
   LIFE OS — Core JavaScript v2.0
   Shared utilities: state, notifications, storage, router,
   theme, command palette, data management.
   ============================================================ */

const LIFE_OS = {
  VERSION: '2.0.0',
  STORAGE_PREFIX: 'fb-os-',
};

// ============================================================
// STATE MANAGEMENT
// ============================================================
const Store = {
  data: {},
  
  init() {
    try {
      const saved = localStorage.getItem(LIFE_OS.STORAGE_PREFIX + 'state');
      if (saved) this.data = JSON.parse(saved);
    } catch(e) { this.data = {}; }
    return this.data;
  },
  
  get(key, defaultValue) {
    return this.data[key] !== undefined ? this.data[key] : defaultValue;
  },
  
  set(key, value) {
    this.data[key] = value;
    this.persist();
  },
  
  remove(key) {
    delete this.data[key];
    this.persist();
  },
  
  persist() {
    try {
      localStorage.setItem(LIFE_OS.STORAGE_PREFIX + 'state', JSON.stringify(this.data));
    } catch(e) { console.warn('Storage full'); }
  },
  
  exportAll() {
    const all = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(LIFE_OS.STORAGE_PREFIX) || key.startsWith('fb-')) {
        try { all[key] = JSON.parse(localStorage.getItem(key)); } catch(e) { all[key] = localStorage.getItem(key); }
      }
    }
    return all;
  },
  
  importAll(data) {
    if (!data || typeof data !== 'object') throw new Error('Invalid data');
    Object.entries(data).forEach(([key, value]) => {
      localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
    });
  },
  
  clearAll() {
    const toRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.startsWith(LIFE_OS.STORAGE_PREFIX) || key.startsWith('fb-')) toRemove.push(key);
    }
    toRemove.forEach(k => localStorage.removeItem(k));
    this.data = {};
  }
};

Store.init();

// ============================================================
// NOTIFICATIONS (Toast System)
// ============================================================
const Notify = {
  container: null,
  
  init() {
    if (this.container) return;
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    this.container.setAttribute('role', 'alert');
    this.container.setAttribute('aria-live', 'polite');
    document.body.appendChild(this.container);
  },
  
  show(message, type = 'info', duration = 4000) {
    this.init();
    const icons = {
      success: '<svg class="icon" width="15" height="15" style="color:var(--status-live)"><use href="assets/lucide-sprite.svg#icon-circle-check"/></svg>',
      error: '<svg class="icon" width="15" height="15" style="color:var(--status-failed)"><use href="assets/lucide-sprite.svg#icon-circle-x"/></svg>',
      info: '<svg class="icon" width="15" height="15" style="color:var(--accent-2)"><use href="assets/lucide-sprite.svg#icon-circle-check"/></svg>',
      warning: '<svg class="icon" width="15" height="15" style="color:var(--status-stale)"><use href="assets/lucide-sprite.svg#icon-triangle-alert"/></svg>',
    };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message.replace(/^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}✅❌ℹ️⚠]+\s*/u, '')}</span>`;
    this.container.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 300);
    }, duration);
    
    return toast;
  },
  
  success(msg, dur) { return this.show(msg, 'success', dur); },
  error(msg, dur) { return this.show(msg, 'error', dur); },
  info(msg, dur) { return this.show(msg, 'info', dur); },
  warning(msg, dur) { return this.show(msg, 'warning', dur); },
};

// ============================================================
// THEME MANAGEMENT (R13 — three switchable themes)
// ============================================================
const Theme = {
  LIST: [
    { id: 'blueprint', label: 'Blueprint Dark', swatchVar: '--swatch-blueprint' },
    { id: 'graphite',  label: 'Graphite & Gold', swatchVar: '--swatch-graphite' },
    { id: 'light',     label: 'Site-Office Light', swatchVar: '--swatch-light' },
  ],

  current: Store.get('theme', 'blueprint'),

  init() {
    // The anti-flash inline script in <head> already set data-theme before
    // first paint; this just syncs state + wires the dropdown UI.
    this.apply(this.current, /*skipStore*/ true);
    document.addEventListener('click', (e) => {
      const switcher = document.querySelector('.theme-switcher');
      if (switcher && !switcher.contains(e.target)) this.closeDropdown();
    });
  },

  apply(theme, skipStore) {
    if (!this.LIST.some(t => t.id === theme)) theme = 'blueprint';
    this.current = theme;
    document.documentElement.setAttribute('data-theme', theme);
    if (!skipStore) Store.set('theme', theme);
    this.renderDropdown();
  },

  toggle() {
    // Kept for the "g then l" shortcut / any legacy callers: cycles the 3 themes.
    const idx = this.LIST.findIndex(t => t.id === this.current);
    this.apply(this.LIST[(idx + 1) % this.LIST.length].id);
  },

  toggleDropdown() {
    const dd = document.getElementById('theme-switcher-dropdown');
    if (!dd) { this.toggle(); return; } // page has no dropdown markup — fall back to cycling
    dd.classList.toggle('open');
    if (dd.classList.contains('open')) this.renderDropdown();
  },

  closeDropdown() {
    const dd = document.getElementById('theme-switcher-dropdown');
    if (dd) dd.classList.remove('open');
  },

  renderDropdown() {
    const dd = document.getElementById('theme-switcher-dropdown');
    if (!dd) return;
    dd.innerHTML = this.LIST.map(t => `
      <div class="theme-option ${t.id === this.current ? 'active' : ''}" onclick="Theme.apply('${t.id}'); Theme.closeDropdown();">
        <span class="theme-swatch" style="background:var(${t.swatchVar})"></span>
        <span>${t.label}</span>
        ${t.id === this.current ? '<span class="theme-check">&#10003;</span>' : ''}
      </div>
    `).join('');
  },
};

Theme.init();

// ============================================================
// ACTIVITY LOG
// ============================================================
function logActivity(page) {
  const icons = {
    dashboard:'⚡', models:'🤖', mcp:'🔌', keys:'🔑', files:'📁', cases:'💡', graph:'🕸️', brain:'🧠', sessions:'💬'
  };
  const names = {
    dashboard:'Dashboard', models:'Models', mcp:'MCP', keys:'API Keys', files:'Files', cases:'Use Cases', graph:'Graph', brain:'3D Brain', sessions:'Chat'
  };
  try {
    const activities = JSON.parse(localStorage.getItem('fb-activity') || '[]');
    activities.unshift({ icon: icons[page] || '📄', title: `Opened ${names[page] || page}`, time: new Date().toLocaleString() });
    localStorage.setItem('fb-activity', JSON.stringify(activities.slice(0, 50)));
  } catch(e) {}
}

// ============================================================
// COMMAND PALETTE (Ctrl+K)
// ============================================================
const CommandPalette = {
  open: false,
  selectedIndex: 0,
  commands: [],
  query: '',
  overlay: null,
  
  init() {
    // Build command list from nav items
    this.buildCommands();
    this.render();
    this.bindKeyboard();
  },
  
  buildCommands() {
    this.commands = [
      { id: 'theme', name: 'Toggle Theme', icon: '🌓', shortcut: '', action: () => Theme.toggle() },
      { id: 'backup', name: 'Backup All Data', icon: '💾', shortcut: '', action: () => DataManager.backup() },
      { id: 'restore', name: 'Restore Data', icon: '📥', shortcut: '', action: () => DataManager.restore() },
      { id: 'export', name: 'Export Usage Log', icon: '📊', shortcut: '', action: () => Notify.info('Open Models page → Token Tracker → Export') },
      { id: 'clear', name: 'Clear All Data', icon: '🗑️', shortcut: '', action: () => DataManager.clearAll() },
    ];
    
    // Add nav items as commands
    document.querySelectorAll('.nav-item[data-page]').forEach(item => {
      const page = item.getAttribute('data-page');
      const icon = item.querySelector('.nav-icon')?.textContent || '📄';
      const name = item.textContent.trim();
      this.commands.push({ id: 'page-' + page, name, icon, shortcut: '', action: () => navigateTo(page) });
    });
  },
  
  render() {
    if (this.overlay) return;
    
    this.overlay = document.createElement('div');
    this.overlay.className = 'cmd-palette-overlay';
    this.overlay.innerHTML = `
      <div class="cmd-palette" role="dialog" aria-label="Command Palette">
        <div class="cmd-input-wrap">
          <span>🔍</span>
          <input type="text" class="cmd-input" placeholder="Type a command..." aria-label="Search commands">
        </div>
        <div class="cmd-results"></div>
      </div>
    `;
    document.body.appendChild(this.overlay);
    
    this.input = this.overlay.querySelector('.cmd-input');
    this.results = this.overlay.querySelector('.cmd-results');
    
    this.input.addEventListener('input', () => this.filter());
    this.input.addEventListener('keydown', (e) => this.handleKey(e));
    this.overlay.addEventListener('click', (e) => { if (e.target === this.overlay) this.close(); });
  },
  
  openPalette() {
    if (!this.overlay) this.render();
    this.open = true;
    this.query = '';
    this.selectedIndex = 0;
    this.input.value = '';
    this.overlay.classList.add('open');
    this.input.focus();
    this.filter(document.querySelectorAll('.nav-item[data-page]').length ? document.querySelectorAll('.nav-item[data-page]').length : 0);
    this.filter();
  },
  
  close() {
    this.open = false;
    this.overlay?.classList.remove('open');
  },
  
  filter() {
    this.query = this.input.value.toLowerCase();
    const filtered = this.commands.filter(c => c.name.toLowerCase().includes(this.query) || c.id.includes(this.query));
    this.selectedIndex = 0;
    this.results.innerHTML = '';
    
    filtered.forEach((cmd, i) => {
      const div = document.createElement('div');
      div.className = 'cmd-result-item' + (i === 0 ? ' selected' : '');
      div.setAttribute('role', 'option');
      div.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      div.innerHTML = `
        <span class="cmd-result-icon">${cmd.icon}</span>
        <span class="cmd-result-name">${cmd.name}</span>
        ${cmd.shortcut ? `<span class="cmd-result-shortcut">${cmd.shortcut}</span>` : ''}
      `;
      div.addEventListener('click', () => { cmd.action(); this.close(); });
      div.addEventListener('mouseenter', () => {
        this.selectedIndex = i;
        this.updateSelection();
      });
      this.results.appendChild(div);
    });
    
    if (!filtered.length) {
      this.results.innerHTML = '<div class="cmd-result-item"><span class="cmd-result-name" style="color:var(--text-muted);">No commands found</span></div>';
    }
  },
  
  handleKey(e) {
    const items = this.results.querySelectorAll('.cmd-result-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
      this.updateSelection();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
      this.updateSelection();
    } else if (e.key === 'Enter' && items[this.selectedIndex]) {
      items[this.selectedIndex].click();
    } else if (e.key === 'Escape') {
      this.close();
    }
  },
  
  updateSelection() {
    const items = this.results.querySelectorAll('.cmd-result-item');
    items.forEach((item, i) => {
      item.classList.toggle('selected', i === this.selectedIndex);
      item.setAttribute('aria-selected', i === this.selectedIndex ? 'true' : 'false');
    });
    if (items[this.selectedIndex]) items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
  },
  
  bindKeyboard() {
    // Disabled — CommandBar handles Ctrl+K now (see bottom of file)
  }
};

// ============================================================
// NAVIGATION
// ============================================================
function navigateTo(page) {
  // Update sidebar nav active state
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-page') === page);
  });
  
  // Update mobile bottom nav active state
  document.querySelectorAll('.mobile-nav-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-page') === page);
  });
  
  // Update page title
  const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
  const title = navItem?.textContent.trim() || page;
  const titleEl = document.getElementById('page-title');
  if (titleEl) titleEl.textContent = title;
  
  // Map page to file and navigate directly
  const moduleFiles = {
    'dashboard': 'dashboard.html',
    'crm': 'crm.html',
    'projects': 'projects.html',
    'models': 'models.html',
    'mcp': 'mcp.html',
    'keys': 'keys.html',
    'files': 'files.html',
    'live': 'use-cases.html',
    'brain': 'graph3d.html',
    'sessions': 'chat.html',
    'skills': 'skills.html',
    'kanban': 'kanban.html',
    'triage': 'admin.html',
    'artifacts': 'artifacts.html',
    'imagegen': 'imagegen.html',
    'browser': 'browser.html',
    'loops': 'loops.html',
    'meetings': 'meetings.html',
    'area-career': 'life-areas.html#career',
    'area-fieldbridge': 'fieldbridge.html',
    'area-construction': 'life-areas.html#construction',
    'area-trading': 'trading.html',
    'area-health': 'fitness.html',
    'area-family': 'life-areas.html#family',
    'area-knowledge': 'life-areas.html#knowledge',
    'area-admin': 'life-areas.html#admin',
  };

  // Dashboard loads inline into the shell (don't redirect)
  if (page === 'dashboard') {
    loadModule('dashboard');
    logActivity(page);
    return;
  }
  
  const file = moduleFiles[page];
  if (file) {
    window.location.href = file;
    return;
  }
  
  // Fallback for pages without module files
  loadModule(page);
  
  // Log activity
  logActivity(page);
}

function loadModule(page) {
  const content = document.getElementById('module-content');
  if (!content) return;
  
  // Show loading state
  content.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted);"><div style="font-size:32px;margin-bottom:12px;">⏳</div>Loading...</div>';
  
  // Map page to file
  const moduleFiles = {
    'dashboard': 'dashboard.html',
    'crm': 'crm.html',
    'projects': 'projects.html',
    'models': 'models.html',
    'mcp': 'mcp.html',
    'keys': 'keys.html',
    'files': 'files.html',
    'live': 'use-cases.html',
    'brain': 'graph3d.html',
    'sessions': 'chat.html',
    'skills': 'skills.html',
    'kanban': 'kanban.html',
    'triage': 'admin.html',
    'artifacts': 'artifacts.html',
    'imagegen': 'imagegen.html',
    'browser': 'browser.html',
    'loops': 'loops.html',
    'meetings': 'meetings.html',
    'area-career': 'life-areas.html#career',
    'area-fieldbridge': 'fieldbridge.html',
    'area-construction': 'life-areas.html#construction',
    'area-trading': 'trading.html',
    'area-health': 'fitness.html',
    'area-family': 'life-areas.html#family',
    'area-knowledge': 'life-areas.html#knowledge',
    'area-admin': 'life-areas.html#admin',
  };
  
  const file = moduleFiles[page];
  if (!file) {
    content.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-muted);"><div style="font-size:32px;margin-bottom:12px;">🚧</div>Module "${page}" is loaded inline or coming soon.</div>`;
    return;
  }
  
  fetch(file)
    .then(r => r.text())
    .then(html => {
      // Extract body content
      const match = html.match(/<body[^>]*>([\s\S]*)<\/body>/i);
      content.innerHTML = match ? match[1] : html;
      // Execute any inline scripts
      content.querySelectorAll('script').forEach(old => {
        const script = document.createElement('script');
        script.textContent = old.textContent;
        old.replaceWith(script);
      });
      // Dashboard keeps sidebar visible (fixed sidebar)
      if (page === 'dashboard') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.style.display = 'flex';
        const main = document.querySelector('.main-content');
        if (main) main.style.marginLeft = 'var(--sidebar-width)';
        const content = document.querySelector('.content');
        if (content) content.classList.remove('dashboard-mode');
        document.body.classList.remove('dashboard-mode');
        const container = document.getElementById('dashboardContainer');
        if (container) container.style.maxWidth = '';
      }
    })
    .catch(() => {
      content.innerHTML = `<div style="padding:40px;text-align:center;color:var(--red);">Failed to load module: ${page}</div>`;
    });
}

// ============================================================
// DATA MANAGEMENT (Backup/Restore)
// ============================================================
const DataManager = {
  backup() {
    const data = Store.exportAll();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `life-os-backup-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    Notify.success('✅ Backup downloaded!');
  },
  
  restore() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = JSON.parse(ev.target.result);
          Store.importAll(data);
          Notify.success('✅ Data restored! Refreshing...');
          setTimeout(() => location.reload(), 1000);
        } catch(err) {
          Notify.error('❌ Invalid backup file');
        }
      };
      reader.readAsText(e.target.files[0]);
    };
    input.click();
  },
  
  clearAll() {
    if (!confirm('⚠️ Delete ALL Life OS data? This cannot be undone.')) return;
    Store.clearAll();
    Notify.success('✅ All data cleared! Refreshing...');
    setTimeout(() => location.reload(), 1000);
  },
};

// ============================================================
// MOBILE SIDEBAR TOGGLE
// ============================================================
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  sidebar?.classList.toggle('open');
  overlay?.classList.toggle('open');
}

// ============================================================
// GLOBAL NAV — one consistent nav on EVERY standalone page.
// index.html already has the full .sidebar, so this is skipped there.
// Overlay drawer + floating button: never shifts a page's layout, and the
// whole thing is guarded so a nav error can't break the host page.
// ============================================================
function toggleGlobalNav(open) {
  const d = document.getElementById('global-nav-drawer');
  const o = document.getElementById('global-nav-overlay');
  if (!d || !o) return;
  d.classList.toggle('open', open);
  o.classList.toggle('open', open);
}
function renderGlobalNav() {
  try {
    if (document.querySelector('.sidebar')) return;       // index.html: full sidebar already
    if (document.getElementById('global-nav-drawer')) return;
    const groups = [
      { title: 'Today',  items: [['index.html','zap','Today'], ['kanban.html','clipboard-list','Kanban'], ['admin.html','inbox','Triage']] },
      { title: 'Work',   items: [['crm.html','users','CRM'], ['projects.html','clipboard-list','Projects']] },
      { title: 'Life',   items: [['trading.html','candlestick-chart','Trading'], ['fitness.html','heart-pulse','Fitness']] },
      { title: 'Brain',  items: [['graph3d.html','brain','3D Brain'], ['files.html','folder','Files']] },
      { title: 'Agents', items: [['chat.html','message-square','Chat'], ['use-cases.html','zap','Playbook'], ['loops.html','repeat','Loops'], ['skills.html','puzzle','Skills'], ['models.html','bot','Models']] },
      { title: 'System', items: [['keys.html','key-round','Keys'], ['mcp.html','settings','MCP'], ['meetings.html','calendar','Meetings'], ['imagegen.html','image','Image'], ['browser.html','globe','Browser'], ['artifacts.html','maximize','Artifacts']] },
    ];
    const here = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
    const ic = n => `<svg class="icon icon-sm" width="15" height="15"><use href="assets/lucide-sprite.svg#icon-${n}"/></svg>`;
    const overlay = document.createElement('div');
    overlay.id = 'global-nav-overlay';
    overlay.className = 'gnav-overlay';
    overlay.addEventListener('click', () => toggleGlobalNav(false));
    const drawer = document.createElement('nav');
    drawer.id = 'global-nav-drawer';
    drawer.className = 'gnav-drawer';
    drawer.setAttribute('aria-label', 'Main navigation');
    drawer.innerHTML =
      `<div class="gnav-head"><span class="gnav-logo">${ic('brain')} Life OS</span>` +
      `<button class="gnav-x" aria-label="Close menu" onclick="toggleGlobalNav(false)">${ic('x')}</button></div>` +
      groups.map(g => `<div class="gnav-group"><div class="gnav-group-title">${g.title}</div>` +
        g.items.map(([href, icon, label]) =>
          `<a class="gnav-item${href.toLowerCase() === here ? ' active' : ''}" href="${href}">${ic(icon)}<span>${label}</span></a>`
        ).join('') + `</div>`).join('');
    const fab = document.createElement('button');
    fab.id = 'global-nav-fab';
    fab.className = 'gnav-fab';
    fab.setAttribute('aria-label', 'Open menu');
    fab.innerHTML = ic('compass');
    fab.addEventListener('click', () => toggleGlobalNav(true));
    document.body.appendChild(overlay);
    document.body.appendChild(drawer);
    document.body.appendChild(fab);
  } catch (e) { /* nav injection must never break the host page */ }
}
document.addEventListener('DOMContentLoaded', renderGlobalNav);

// Close sidebar on mobile when clicking outside or on nav item
document.addEventListener('DOMContentLoaded', () => {
  // Create overlay if it doesn't exist
  if (!document.querySelector('.sidebar-overlay')) {
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.addEventListener('click', toggleSidebar);
    document.body.appendChild(overlay);
  }
  
  // Init command palette — DISABLED: using CommandBar instead
  // CommandPalette.init();
  
  // Auto-close sidebar on mobile after clicking a nav item
  document.querySelectorAll('.nav-item[data-page]').forEach(item => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        sidebar?.classList.remove('open');
        overlay?.classList.remove('open');
      }
    });
  });
  
  // Handle resize
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
      document.querySelector('.sidebar')?.classList.remove('open');
      document.querySelector('.sidebar-overlay')?.classList.remove('open');
    }
  });
});

// ============================================================
// UTILITY FUNCTIONS
// ============================================================
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => Notify.success('Copied to clipboard!')).catch(() => Notify.error('Failed to copy'));
}

function formatNumber(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
}

function formatPrice(pricePer1M) {
  if (pricePer1M === 0) return 'FREE';
  if (pricePer1M < 0.000001) return '$' + (pricePer1M * 1000000).toFixed(3) + '/1M';
  if (pricePer1M < 0.00001) return '$' + (pricePer1M * 1000000).toFixed(2) + '/1M';
  return '$' + (pricePer1M * 1000000).toFixed(0) + '/1M';
}

function debounce(fn, ms) {
  let timeout;
  return (...args) => { clearTimeout(timeout); timeout = setTimeout(() => fn(...args), ms); };
}

// ============================================================
// COMMAND BAR
// ============================================================
const CommandBar = {
  open: false,
  selectedIndex: 0,
  query: '',
  actions: [],

  init() {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.toggle();
      }
      if (e.key === 'Escape' && this.open) this.close();
      if (this.open) {
        if (e.key === 'ArrowDown') { e.preventDefault(); this.moveSelection(1); }
        if (e.key === 'ArrowUp') { e.preventDefault(); this.moveSelection(-1); }
        if (e.key === 'Enter') { e.preventDefault(); this.executeSelected(); }
      }
    });

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
          <svg class="icon" width="18" height="18"><use href="assets/lucide-sprite.svg#icon-search"/></svg>
          <input type="text" class="command-bar-input" id="commandBarInput" placeholder="Type an action..." autocomplete="off" spellcheck="false">
        </div>
        <div class="command-bar-results" id="commandBarResults"></div>
        <div class="command-bar-hint">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> execute</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    const input = document.getElementById('commandBarInput');
    input.addEventListener('input', () => {
      this.query = input.value.toLowerCase().trim();
      this.selectedIndex = 0;
      this.render();
    });
  },

  registerActions(actions) { this.actions = actions; },

  toggle() {
    this.open = !this.open;
    document.getElementById('commandBarOverlay').classList.toggle('open', this.open);
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
      if (action) { this.close(); action.execute(); }
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
        <span class="item-icon"><svg class="icon" width="16" height="16"><use href="assets/lucide-sprite.svg#icon-${a.icon}"/></svg></span>
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
    if (action) { this.close(); action.execute(); }
  }
};

function getDefaultActions() {
  return [
    { id: 'nav-dashboard', icon: 'zap', title: 'Go to Dashboard', desc: 'Main overview and KPIs', keywords: ['dashboard', 'home', 'overview'], execute: () => { window.location.href = 'index.html'; } },
    { id: 'nav-chat', icon: 'message-square', title: 'New Chat', desc: 'Start a conversation with Hermes', keywords: ['chat', 'message', 'talk', 'hermes'], execute: () => { window.location.href = 'chat.html'; } },
    { id: 'nav-files', icon: 'folder', title: 'File Browser', desc: 'Browse vault files and folders', keywords: ['files', 'browse', 'vault', 'folder'], execute: () => { window.location.href = 'files.html'; } },
    { id: 'nav-graph3d', icon: 'brain', title: '3D Knowledge Brain', desc: '3D force graph of vault', keywords: ['3d', 'brain', 'graph', 'force'], execute: () => { window.location.href = 'graph3d.html'; } },
    { id: 'nav-skills', icon: 'puzzle', title: 'Skills Library', desc: 'Browse installed skills', keywords: ['skills', 'plugins', 'tools'], execute: () => { window.location.href = 'skills.html'; } },
    { id: 'nav-keys', icon: 'key-round', title: 'API Keys', desc: 'Manage provider API keys', keywords: ['keys', 'api', 'providers', 'connect'], execute: () => { window.location.href = 'keys.html'; } },
    { id: 'nav-playbook', icon: 'zap', title: 'Playbook (Use Cases & Prompts)', desc: 'Curated use case & prompt library', keywords: ['use cases', 'prompts', 'library', 'playbook'], execute: () => { window.location.href = 'use-cases.html'; } },
    { id: 'nav-models', icon: 'bot', title: 'Models & Usage', desc: 'AI model catalog and token usage', keywords: ['models', 'ai', 'llm', 'tokens', 'usage'], execute: () => { window.location.href = 'models.html'; } },
    { id: 'nav-loops', icon: 'repeat', title: 'Loops (Automations)', desc: 'Automation registry — every scheduled job', keywords: ['loops', 'cron', 'scheduled', 'jobs', 'automation'], execute: () => { window.location.href = 'loops.html'; } },
    { id: 'action-search', icon: 'search', title: 'Search Vault', desc: 'Search all notes and files', keywords: ['search', 'find', 'lookup'], execute: () => { const q = prompt('Search vault for:'); if (q) window.location.href = 'files.html?search=' + encodeURIComponent(q); } },
    { id: 'action-ship', icon: 'rocket', title: 'What did I ship today?', desc: "Show today's accomplishments", keywords: ['ship', 'today', 'progress', 'recap'], execute: () => { ShipToday.render(); const card = document.getElementById('shipTodayCard'); if (card) { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); card.style.transition = 'box-shadow 0.5s'; card.style.boxShadow = '0 0 0 3px var(--accent)'; setTimeout(() => card.style.boxShadow = '', 2000); } else { Notify.info('Ship Today card is on the Dashboard.'); } } },
  ];
}

// Init CommandBar — call directly since shared.js loads at end of body
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    CommandBar.init();
    if (CommandBar.actions.length === 0) {
      CommandBar.registerActions(getDefaultActions());
    }
    QuickCapture.init();
    Capture.migrateLegacy();
    Capture.flushQueue();
    ShortcutsOverlay.init();
    ContextSwitcher.init();
    ShipToday.init();
    I18n.init();
  });
} else {
  // DOM already loaded — init immediately
  CommandBar.init();
  if (CommandBar.actions.length === 0) {
    CommandBar.registerActions(getDefaultActions());
  }
  QuickCapture.init();
  Capture.migrateLegacy();
  Capture.flushQueue();
  ShortcutsOverlay.init();
  ContextSwitcher.init();
  ShipToday.init();
  I18n.init();
}

// ============================================================
// PROJECT CONTEXT SWITCHER
// ============================================================
const ContextSwitcher = {
  current: 'all',
  key: 'fb-context',

  init() {
    const saved = localStorage.getItem(this.key);
    if (saved) this.current = saved;
    this.updateUI();

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      const btn = document.getElementById('ctxSwitcher');
      if (btn && !btn.contains(e.target)) {
        document.getElementById('ctxDropdown')?.classList.remove('open');
      }
    });
  },

  toggle() {
    document.getElementById('ctxDropdown')?.classList.toggle('open');
  },

  set(ctx) {
    this.current = ctx;
    localStorage.setItem(this.key, ctx);
    this.updateUI();
    this.toggle();
    // Filter dashboard content based on context
    this.applyFilter();
  },

  updateUI() {
    const icons = {
      all: '<svg class="icon" width="14" height="14" style="color:var(--area-fieldbridge)"><use href="assets/lucide-sprite.svg#icon-hard-hat"/></svg>',
      fieldbridge: '<svg class="icon" width="14" height="14" style="color:var(--area-fieldbridge)"><use href="assets/lucide-sprite.svg#icon-building-2"/></svg>',
      personal: '<svg class="icon" width="14" height="14"><use href="assets/lucide-sprite.svg#icon-home"/></svg>',
    };
    const labels = { all: 'All Projects', fieldbridge: 'FieldBridge HQ', personal: 'Personal' };
    const iconEl = document.getElementById('ctxCurrentIcon');
    const labelEl = document.getElementById('ctxCurrentLabel');
    if (iconEl) iconEl.innerHTML = icons[this.current] || icons.all;
    if (labelEl) labelEl.textContent = labels[this.current] || 'All Projects';

    document.querySelectorAll('.ctx-option').forEach(opt => {
      opt.classList.toggle('active', opt.dataset.ctx === this.current);
    });
  },

  applyFilter() {
    // Filter today strip tasks by context
    const tasks = document.querySelectorAll('.strip-task');
    const contextMap = {
      'Update LinkedIn headline + About': ['personal'],
      'Send first recruiter message': ['personal'],
      'Submit first job application': ['personal'],
      'Review FieldBridge SSL status': ['fieldbridge'],
    };
    tasks.forEach(task => {
      const text = task.textContent.trim();
      const belongsTo = contextMap[text] || ['all'];
      const show = this.current === 'all' || belongsTo.includes(this.current) || belongsTo.includes('all');
      task.style.display = show ? 'flex' : 'none';
    });
    Notify.success(`🔍 Filtered: ${this.current === 'all' ? 'All Projects' : this.current}`);
  }
};

// ============================================================
// VOICE MEMO → AIRTABLE
// ============================================================
const VoiceMemo = {
  recording: false,
  mediaRecorder: null,
  chunks: [],

  async start() {
    if (this.recording) {
      this.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.chunks = [];
      this.mediaRecorder.ondataavailable = (e) => this.chunks.push(e.data);
      this.mediaRecorder.onstop = () => this.processRecording(stream);
      this.mediaRecorder.start();
      this.recording = true;
      this.updateButton(true);
      Notify.info('🎙️ Recording... Press again to stop.');
    } catch(e) {
      // Fallback for environments without mic access (VPS, HTTPS required)
      Notify.warning('🎤 Mic not available. Saving text memo instead.');
      this.fallbackText();
    }
  },

  stop() {
    if (this.recording && this.mediaRecorder) {
      this.mediaRecorder.stop();
      this.recording = false;
      this.updateButton(false);
    }
  },

  processRecording(stream) {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(this.chunks, { type: 'audio/webm' });
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `voice-memo-${timestamp}.webm`;

    // Save to localStorage as base64 for demo (in production would upload to Airtable)
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const memos = JSON.parse(localStorage.getItem('fb-voice-memos') || '[]');
        memos.unshift({
          filename,
          audioData: reader.result,
          timestamp: new Date().toISOString(),
          context: ContextSwitcher.current,
          synced: false
        });
        localStorage.setItem('fb-voice-memos', JSON.stringify(memos.slice(0, 50)));
        Notify.success('✅ Voice memo saved! Will sync to Airtable when connected.');
      } catch(e) {
        Notify.error('❌ Could not save memo (storage full?)');
      }
    };
    reader.readAsDataURL(blob);
  },

  fallbackText() {
    const text = prompt('🎤 Type your voice memo (mic not available):');
    if (text && text.trim()) {
      try {
        const memos = JSON.parse(localStorage.getItem('fb-voice-memos') || '[]');
        memos.unshift({
          filename: `text-memo-${Date.now()}`,
          text: text.trim(),
          timestamp: new Date().toISOString(),
          context: ContextSwitcher.current,
          synced: false
        });
        localStorage.setItem('fb-voice-memos', JSON.stringify(memos.slice(0, 50)));
        Notify.success('✅ Text memo saved!');
      } catch(e) {
        Notify.error('❌ Could not save memo');
      }
    }
  },

  updateButton(recording) {
    const btn = document.getElementById('voiceBtn');
    if (!btn) return;
    if (recording) {
      btn.classList.add('recording');
      btn.textContent = '⏹️ Stop Recording';
    } else {
      btn.classList.remove('recording');
      btn.textContent = '🎙️ Voice Memo → Airtable';
    }
  }
};

// ============================================================
// LOADING SKELETONS
// ============================================================
const Skeleton = {
  show(container, count = 3) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const row = document.createElement('div');
      row.className = 'skeleton-row';
      row.style.cssText = `
        background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-elevated) 50%, var(--bg-tertiary) 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: var(--radius-md);
        height: ${40 + Math.random() * 30}px;
        margin-bottom: var(--space-2);
        width: ${60 + Math.random() * 40}%;
      `;
      el.appendChild(row);
    }
  }
};

// ============================================================
// SHIP TODAY
// ============================================================
const ShipToday = {
  key: 'fb-ship-today',

  init() {
    this.render();
  },

  getItems() {
    try {
      return JSON.parse(localStorage.getItem(this.key) || '[]');
    } catch(e) { return []; }
  },

  getTodayItems() {
    const items = this.getItems();
    const today = new Date().toISOString().split('T')[0];
    return items.filter(i => i.time && i.time.startsWith(today));
  },

  add(text, icon = '📦') {
    const items = this.getItems();
    items.unshift({ text, icon, time: new Date().toISOString() });
    localStorage.setItem(this.key, JSON.stringify(items.slice(0, 100)));
    this.render();
  },

  render() {
    const container = document.getElementById('shipTodayList');
    const countEl = document.getElementById('shipTodayCount');
    if (!container) return;

    const todayItems = this.getTodayItems();

    if (countEl) countEl.textContent = `${todayItems.length} item${todayItems.length !== 1 ? 's' : ''}`;

    if (todayItems.length === 0) {
      container.innerHTML = '<div class="ship-today-empty">Nothing shipped yet. Get something done! 💪</div>';
      return;
    }

    container.innerHTML = todayItems.map(item => {
      const time = new Date(item.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return `
        <div class="ship-today-item">
          <span class="ship-item-icon">${item.icon}</span>
          <span class="ship-item-text">${item.text}</span>
          <span class="ship-item-time">${time}</span>
        </div>
      `;
    }).join('');
  }
};

// ============================================================
// I18N TOGGLE (Phase 1: Labels Only)
// ============================================================
const I18n = {
  current: localStorage.getItem('fb-lang') || 'en',

  dict: {
    ar: {
      // Nav
      home: 'الرئيسية',
      dashboard: 'لوحة التحكم',
      models: 'النماذج والرموز',
      mcp: 'خوادم MCP',
      keys: 'مفاتيح API',
      artifacts: 'العناصر الحية',
      imagegen: 'توليد الصور',
      browser: 'أتمتة المتصفح',
      cron: 'المهام المجدولة',
      files: 'متصفح الملفات',
      live: 'حالات الاستخدام',
      clip: 'قاطع الويب',
      graph: 'رسم المعرفة',
      tasks: 'لوحة المهام',
      brain: 'الدماغ ثلاثي الأبعاد',
      tokens: 'تحليل الرموز',
      skills: 'مكتبة المهارات',
      chat: 'الدردشة',
      // Dashboard
      welcome: '👋 مرحباً بعودتك، فادي',
      subtitle: 'لوحة تحكم Life OS — كل شيء في مكان واحد. اضغط Ctrl+K للأوامر السريعة.',
      voiceBtn: '🎙️ مذكرة صوتية → Airtable',
      modelsBtn: '🤖 النماذج',
      mcpBtn: '🔌 MCP',
      keysBtn: '🔑 المفاتيح',
      voice: '🎙️ الصوت',
      cases: '💡 حالات الاستخدام',
      // Context
      allProjects: 'جميع المشاريع',
      fieldbridge: 'فيلد بريدج',
      personal: 'شخصي',
      // Ship Today
      shipToday: '🚀 شحن اليوم',
      shipEmpty: 'لا شيء تم شحنه بعد. أنجز شيئاً! 💪',
      shipCount: 'عنصر',
      // Today Strip
      todayTitle: '📌 اليوم',
      // Misc
      refresh: '↻ تحديث',
      search: '🔍 بحث',
      // Placeholder for dynamic content
      daysLeft: 'يوم متبقي',
      p1Goal: 'هدف P1',
      p2Goal: 'هدف P2',
      p3Goal: 'هدف P3',
    }
  },

  init() {
    if (this.current === 'ar') this.apply();
  },

  toggle() {
    this.current = this.current === 'en' ? 'ar' : 'en';
    localStorage.setItem('fb-lang', this.current);
    this.apply();
  },

  apply() {
    const isAr = this.current === 'ar';
    document.documentElement.setAttribute('lang', isAr ? 'ar' : 'en');
    document.documentElement.setAttribute('dir', isAr ? 'rtl' : 'ltr');

    // Update i18n label button
    const label = document.getElementById('i18nLabel');
    if (label) label.textContent = isAr ? 'EN' : 'عربي';

    // Translate all elements with data-i18n
    if (isAr) {
      const dict = this.dict.ar;
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
          // If element has a span child (icon), preserve it
          const icon = el.querySelector(':first-child');
          if (icon && icon.classList.contains('nav-icon')) {
            // Keep icon, replace text after it
            const textNode = Array.from(el.childNodes).find(n => n.nodeType === 3);
            if (textNode) textNode.textContent = ' ' + dict[key];
            else el.appendChild(document.createTextNode(' ' + dict[key]));
          } else {
            el.textContent = dict[key];
          }
        }
      });
    } else {
      // Reload page to restore original English text (simplest approach for Phase 1)
      // In Phase 2, we'd store original text and restore it
      // For now, just reload
      if (this._needsReload) {
        location.reload();
        return;
      }
    }
    this._needsReload = isAr;
  }
};
// ============================================================
// CAPTURE BACKEND (Productivity Hub v1, Builder Session 5, 2026-07-14)
// One real inbox behind POST/GET /api/capture (DATA_DIR/.capture_inbox.
// json — dashboard-owned operational triage buffer, see server.py for
// the full architecture note). Replaces the two localStorage-only
// silos this file and dashboard.html used to write independently
// (QuickCapture's 'fb-captures', dashboard.html's 'cmd-inbox'). Backend
// unreachable -> queue locally under CAPTURE_QUEUE_KEY, auto-flushed on
// the next successful submit or page load. Drain UI lives in
// admin.html (Triage).
// ============================================================
const Capture = {
  QUEUE_KEY: 'capture-queue-fallback',

  // Submit one capture. Always "succeeds" from the caller's perspective
  // (queued locally if the backend is down) — callers don't need to
  // branch on the return value, but it's returned in case a caller
  // wants to distinguish "reached the server" from "queued offline".
  async submit(text, source) {
    if (!text || !text.trim()) return false;
    const ok = await this._post(text.trim(), source);
    if (ok) {
      this.flushQueue(); // good moment to drain anything stranded earlier
      return true;
    }
    this._queueLocally(text.trim(), source);
    return false;
  },

  async _post(text, source) {
    try {
      const resp = await fetch('/api/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source: source || 'unknown' })
      });
      return resp.ok;
    } catch (e) {
      return false;
    }
  },

  _queueLocally(text, source) {
    try {
      const q = JSON.parse(localStorage.getItem(this.QUEUE_KEY) || '[]');
      q.push({ text, source: source || 'unknown', time: new Date().toISOString() });
      localStorage.setItem(this.QUEUE_KEY, JSON.stringify(q.slice(-200)));
    } catch (e) {}
  },

  async flushQueue() {
    let q = [];
    try { q = JSON.parse(localStorage.getItem(this.QUEUE_KEY) || '[]'); } catch (e) {}
    if (!q.length) return;
    const remaining = [];
    for (const item of q) {
      const ok = await this._post(item.text, item.source);
      if (!ok) remaining.push(item);
    }
    try {
      if (remaining.length) localStorage.setItem(this.QUEUE_KEY, JSON.stringify(remaining));
      else localStorage.removeItem(this.QUEUE_KEY);
    } catch (e) {}
  },

  // One-time transfer of anything sitting in the two old localStorage-only
  // silos into the real backend queue, then clear the legacy keys so this
  // never re-runs on old data. Nothing else in the repo ever reads
  // 'fb-captures' or 'cmd-inbox' (write-only silos), so this is safe.
  migrateLegacy() {
    try {
      ['fb-captures', 'cmd-inbox'].forEach(key => {
        const raw = localStorage.getItem(key);
        if (!raw) return;
        let items = [];
        try { items = JSON.parse(raw); } catch (e) { items = []; }
        if (Array.isArray(items)) {
          items.forEach(it => {
            const text = (it && it.text) ? String(it.text).trim() : '';
            if (text) this._queueLocally(text, 'legacy:' + key);
          });
        }
        localStorage.removeItem(key);
      });
    } catch (e) {}
  }
};

const QuickCapture = {
  init() {
    if (document.getElementById('fabCapture')) return;
    const fab = document.createElement('button');
    fab.className = 'fab-capture';
    fab.id = 'fabCapture';
    fab.title = 'Quick Capture (Ctrl+N)';
    fab.innerHTML = '<svg class="icon" width="22" height="22"><use href="assets/lucide-sprite.svg#icon-plus"/></svg>';
    fab.onclick = () => this.openModal();
    document.body.appendChild(fab);
  },

  openModal() {
    let overlay = document.getElementById('captureModal');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'capture-modal-overlay';
      overlay.id = 'captureModal';
      overlay.innerHTML = `
        <div class="capture-modal">
          <h3><svg class="icon" width="18" height="18"><use href="assets/lucide-sprite.svg#icon-zap"/></svg> Quick Capture</h3>
          <textarea id="captureInput" placeholder="Idea, task, note, brain dump... type, or hit Speak and just talk." autofocus></textarea>
          <div class="capture-modal-actions">
            <button class="btn-ghost cap-mic" id="captureMic" onclick="QuickCapture.toggleMic()" title="Voice brain dump — click to start/stop"><svg class="icon icon-sm" width="15" height="15"><use href="assets/lucide-sprite.svg#icon-mic"/></svg> Speak</button>
            <span style="flex:1"></span>
            <button class="btn-ghost" onclick="QuickCapture.closeModal()">Cancel</button>
            <button class="btn-ghost" onclick="QuickCapture.summarizeToTasks()">Summarize into tasks</button>
            <button class="btn-primary" onclick="QuickCapture.save()">Save to Inbox</button>
          </div>
          <div id="captureReview" class="capture-review" style="display:none"></div>
        </div>
      `;
      document.body.appendChild(overlay);
    }
    const box = document.getElementById('captureReview');
    if (box) { box.style.display = 'none'; box.innerHTML = ''; }
    overlay.classList.add('open');
    setTimeout(() => document.getElementById('captureInput')?.focus(), 100);
  },

  closeModal() {
    if (this._recording) this._stopRec();
    const overlay = document.getElementById('captureModal');
    if (overlay) overlay.classList.remove('open');
  },

  save() {
    const input = document.getElementById('captureInput');
    if (!input || !input.value.trim()) return;
    const text = input.value.trim();
    Capture.submit(text, 'fab'); // backend /api/capture; queues locally if offline
    input.value = '';
    this.closeModal();
    // Ask if they want to mark as shipped
    if (confirm('✅ Saved! Mark this as shipped?')) {
      ShipToday.add(text);
    }
    Notify.success('✅ Saved to your inbox!');
  },

  // ---- Voice brain dump (records -> /api/transcribe -> appends to the textarea) ----
  _MIC_IDLE: '<svg class="icon icon-sm" width="15" height="15"><use href="assets/lucide-sprite.svg#icon-mic"/></svg> Speak',
  _MIC_REC: '<svg class="icon icon-sm" width="15" height="15"><use href="assets/lucide-sprite.svg#icon-circle-x"/></svg> Stop',
  _MIC_BUSY: '<svg class="icon icon-sm icon-spin" width="15" height="15"><use href="assets/lucide-sprite.svg#icon-loader"/></svg> …',

  async toggleMic() {
    if (this._recording) { this._stopRec(); return; }
    const btn = document.getElementById('captureMic');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this._stream = stream;
      this._chunks = [];
      this._rec = new MediaRecorder(stream);
      this._rec.ondataavailable = (e) => { if (e.data.size > 0) this._chunks.push(e.data); };
      this._rec.onstop = async () => {
        const blob = new Blob(this._chunks, { type: 'audio/webm' });
        try { this._stream.getTracks().forEach(t => t.stop()); } catch(e) {}
        await this._transcribe(blob);
      };
      this._rec.start();
      this._recording = true;
      if (btn) { btn.classList.add('recording'); btn.innerHTML = this._MIC_REC; }
    } catch(e) {
      if (typeof Notify !== 'undefined') Notify.error('Microphone access denied.');
    }
  },

  _stopRec() {
    try { if (this._rec && this._rec.state !== 'inactive') this._rec.stop(); } catch(e) {}
    this._recording = false;
    const btn = document.getElementById('captureMic');
    if (btn) { btn.classList.remove('recording'); btn.innerHTML = this._MIC_IDLE; }
  },

  async _transcribe(blob) {
    const input = document.getElementById('captureInput');
    const btn = document.getElementById('captureMic');
    if (btn) btn.innerHTML = this._MIC_BUSY;
    try {
      const fd = new FormData();
      fd.append('audio', blob, 'voice-capture.webm');
      const resp = await fetch('/api/transcribe', { method: 'POST', body: fd });
      const data = await resp.json();
      if (data.success && data.text) {
        input.value = (input.value ? input.value.trim() + ' ' : '') + data.text;
      } else if (typeof Notify !== 'undefined') {
        Notify.error('Transcription failed — type it instead.');
      }
    } catch(e) {
      if (typeof Notify !== 'undefined') Notify.error('Transcription error.');
    }
    if (btn) btn.innerHTML = this._MIC_IDLE;
  },

  // ---- Brain dump -> tasks (Hermes extracts, you review, then create as kanban cards) ----
  async summarizeToTasks() {
    const input = document.getElementById('captureInput');
    const text = (input && input.value.trim()) || '';
    const box = document.getElementById('captureReview');
    if (!text) { if (typeof Notify !== 'undefined') Notify.error('Type or record a brain dump first.'); return; }
    if (box) { box.style.display = 'block'; box.innerHTML = '<div class="capture-review-loading"><svg class="icon icon-sm icon-spin" width="14" height="14"><use href="assets/lucide-sprite.svg#icon-loader"/></svg> Summarizing into tasks…</div>'; }
    try {
      const resp = await fetch('/api/braindump', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text }) });
      const data = await resp.json();
      if (data.available === false) {
        if (box) { const d = document.createElement('div'); d.className = 'capture-review-empty'; d.textContent = data.error || 'Could not extract tasks.'; box.innerHTML = ''; box.appendChild(d); }
        return;
      }
      this.renderReview(data.tasks || []);
    } catch(e) {
      if (box) box.innerHTML = '<div class="capture-review-empty">Could not reach the summarizer. Save to Inbox instead.</div>';
    }
  },

  renderReview(tasks) {
    const box = document.getElementById('captureReview');
    if (!box) return;
    box.style.display = 'block';
    box.innerHTML = '';
    if (!tasks.length) {
      const d = document.createElement('div');
      d.className = 'capture-review-empty';
      d.textContent = 'No clear tasks in that dump. Edit the text and try again, or Save to Inbox.';
      box.appendChild(d);
      return;
    }
    const head = document.createElement('div');
    head.className = 'capture-review-head';
    head.textContent = 'Review — uncheck any you don’t want, edit titles or tags, then add to the board:';
    box.appendChild(head);

    const list = document.createElement('div');
    list.className = 'capture-review-list';
    const TAGS = ['project','fieldbridge','career','trading','personal','urgent'];
    tasks.forEach(t => {
      const row = document.createElement('div');
      row.className = 'capture-review-row';
      row.dataset.pri = (t.priority || 'medium');
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = true; cb.className = 'cap-rev-check';
      const title = document.createElement('input');
      title.type = 'text'; title.className = 'cap-rev-title'; title.value = t.title || '';
      const sel = document.createElement('select');
      sel.className = 'cap-rev-tag';
      TAGS.forEach(tg => { const o = document.createElement('option'); o.value = tg; o.textContent = tg; if (tg === (t.tag || 'project')) o.selected = true; sel.appendChild(o); });
      const rm = document.createElement('button');
      rm.type = 'button'; rm.className = 'cap-rev-remove'; rm.title = 'Remove'; rm.textContent = '✕';
      rm.onclick = () => row.remove();
      row.appendChild(cb); row.appendChild(title); row.appendChild(sel); row.appendChild(rm);
      list.appendChild(row);
    });
    box.appendChild(list);

    const add = document.createElement('button');
    add.type = 'button'; add.className = 'btn-primary cap-rev-add';
    add.textContent = 'Add to board';
    add.onclick = () => this.addApprovedToBoard();
    box.appendChild(add);
  },

  async addApprovedToBoard() {
    const rows = document.querySelectorAll('#captureReview .capture-review-row');
    const picked = [];
    rows.forEach(row => {
      const cb = row.querySelector('.cap-rev-check');
      if (!cb || !cb.checked) return;
      const title = row.querySelector('.cap-rev-title').value.trim();
      if (!title) return;
      picked.push({ title, tag: row.querySelector('.cap-rev-tag').value, priority: row.dataset.pri || 'medium' });
    });
    if (!picked.length) { if (typeof Notify !== 'undefined') Notify.error('Nothing selected to add.'); return; }
    let ok = 0;
    for (const p of picked) {
      const task = {
        id: 'task_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6),
        title: p.title,
        description: '',
        priority: p.priority,
        tag: p.tag,
        column: 'backlog',
        source: 'Brain dump',
        created: new Date().toISOString()
      };
      try {
        await fetch('/api/task', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(task) });
        ok++;
      } catch(e) {}
    }
    const input = document.getElementById('captureInput');
    if (input) input.value = '';
    this.closeModal();
    if (typeof Notify !== 'undefined') Notify.success(`Added ${ok} task${ok === 1 ? '' : 's'} to your board (Backlog).`);
    if (typeof loadTasks === 'function') { try { loadTasks(); } catch(e) {} }
  }
};

// ============================================================
// KEYBOARD SHORTCUTS OVERLAY
// ============================================================
const ShortcutsOverlay = {
  init() {
    document.addEventListener('keydown', (e) => {
      if ((e.key === '?' || e.key === '/') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        // Don't trigger if user is typing in an input
        const tag = document.activeElement?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;
        e.preventDefault();
        this.toggle();
      }
      if (e.key === 'Escape' && this.isOpen()) this.close();
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        QuickCapture.openModal();
      }
    });
  },

  isOpen() {
    const overlay = document.getElementById('shortcutsOverlay');
    return overlay?.classList.contains('open') || false;
  },

  toggle() {
    let overlay = document.getElementById('shortcutsOverlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'shortcuts-overlay';
      overlay.id = 'shortcutsOverlay';
      overlay.onclick = (e) => { if (e.target === overlay) this.close(); };
      overlay.innerHTML = `
        <div class="shortcuts-panel">
          <h3><svg class="icon" width="18" height="18"><use href="assets/lucide-sprite.svg#icon-command"/></svg> Keyboard Shortcuts</h3>
          <div class="shortcuts-row"><span class="shortcut-label">Command bar</span><kbd>Ctrl</kbd>+<kbd>K</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Quick capture</span><kbd>Ctrl</kbd>+<kbd>N</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Show shortcuts</span><kbd>?</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Close any overlay</span><kbd>Esc</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Navigate to Dashboard</span><kbd>g</kbd> then <kbd>d</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Navigate to Tasks</span><kbd>g</kbd> then <kbd>t</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Navigate to Chat</span><kbd>g</kbd> then <kbd>c</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Navigate to Files</span><kbd>g</kbd> then <kbd>f</kbd></div>
          <div class="shortcuts-row"><span class="shortcut-label">Toggle theme</span><kbd>g</kbd> then <kbd>l</kbd></div>
        </div>
      `;
      document.body.appendChild(overlay);
    }
    overlay.classList.toggle('open');
  },

  close() {
    const overlay = document.getElementById('shortcutsOverlay');
    if (overlay) overlay.classList.remove('open');
  }
};
