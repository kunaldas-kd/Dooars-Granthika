/**
 * SAAS SUPERUSER DASHBOARD — admin.js
 * Handles: sidebar toggle, tabs, charts, toasts, filters, confirm dialogs
 */

/* ── Sidebar Toggle ─────────────────────────────────────── */
(function () {
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  const overlay = document.getElementById('sidebar-overlay');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('active');
    });
  }

  if (overlay) {
    overlay.addEventListener('click', () => {
      if (sidebar) sidebar.classList.remove('open');
      overlay.classList.remove('active');
    });
  }

  // Auto-close sidebar on nav item click (mobile)
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 1024 && sidebar) {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
      }
    });
  });
})();

/* ── Active Nav Highlight ───────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const current = window.location.pathname;
  const links = [...document.querySelectorAll('.nav-item[href]')];

  // Find the best (longest) matching href for current path
  let bestMatch = null, bestLen = 0;
  links.forEach(link => {
    const href = link.getAttribute('href');
    if (current === href || (current.startsWith(href) && href !== '/superuser/')) {
      if (href.length > bestLen) { bestMatch = link; bestLen = href.length; }
    } else if (href === '/superuser/' && current === '/superuser/') {
      bestMatch = link; bestLen = href.length;
    }
  });
  if (bestMatch) bestMatch.classList.add('active');
});

/* ── Tab System ─────────────────────────────────────────── */
function initTabs(containerSelector = '.tabs') {
  document.querySelectorAll(containerSelector).forEach(tabsEl => {
    const buttons = tabsEl.querySelectorAll('.tab-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.dataset.tab;
        const container = btn.closest('.tab-wrapper') || document;

        // Deactivate all
        buttons.forEach(b => b.classList.remove('active'));
        container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

        // Activate selected
        btn.classList.add('active');
        const panel = container.querySelector(`#${targetId}`);
        if (panel) panel.classList.add('active');
      });
    });

    // Activate first by default
    const firstBtn = tabsEl.querySelector('.tab-btn');
    if (firstBtn && !tabsEl.querySelector('.tab-btn.active')) {
      firstBtn.click();
    }
  });
}

document.addEventListener('DOMContentLoaded', initTabs);

/* ── Toast Notifications ────────────────────────────────── */
const Toast = {
  container: null,

  init() {
    this.container = document.querySelector('.toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
    // Show Django messages as toasts if present
    document.querySelectorAll('.django-message').forEach(msg => {
      this.show(msg.dataset.message, msg.dataset.type || 'info');
    });
  },

  show(message, type = 'info', duration = 4000) {
    const icons = {
      success: '✓',
      danger: '✕',
      warning: '⚠',
      info: 'ℹ',
    };

    const colors = {
      success: 'var(--success)',
      danger:  'var(--danger)',
      warning: 'var(--warning)',
      info:    'var(--info)',
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span style="color:${colors[type] || colors.info};font-size:16px;font-weight:700;flex-shrink:0;">${icons[type] || icons.info}</span>
      <span style="flex:1;">${message}</span>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);font-size:16px;line-height:1;padding:0;margin-left:8px;cursor:pointer;">×</button>
    `;

    this.container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
};

document.addEventListener('DOMContentLoaded', () => Toast.init());

/* ── Table Row Click ────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('tr[data-href]').forEach(row => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', (e) => {
      if (e.target.closest('a, button, .td-actions, input')) return;
      window.location.href = row.dataset.href;
    });
  });
});

/* ── Filter Persistence (sessionStorage) ────────────────── */
const FilterManager = {
  save(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    const data = {};
    new FormData(form).forEach((v, k) => data[k] = v);
    sessionStorage.setItem(`filters_${formId}`, JSON.stringify(data));
  },

  restore(formId) {
    const stored = sessionStorage.getItem(`filters_${formId}`);
    if (!stored) return;
    const data = JSON.parse(stored);
    const form = document.getElementById(formId);
    if (!form) return;
    Object.entries(data).forEach(([k, v]) => {
      const el = form.elements[k];
      if (el) el.value = v;
    });
  }
};

/* ── Inline Search Filter ───────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const searchInputs = document.querySelectorAll('[data-search-table]');
  searchInputs.forEach(input => {
    const tableId = input.dataset.searchTable;
    const table = document.getElementById(tableId);
    if (!table) return;

    input.addEventListener('input', () => {
      const query = input.value.toLowerCase().trim();
      table.querySelectorAll('tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = query && !text.includes(query) ? 'none' : '';
      });
    });
  });
});

/* ── Confirm Button Loading State ───────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', (e) => {
      const submitBtn = form.querySelector('[type="submit"]');
      if (!submitBtn) return;
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:8px;">
        <svg class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        Processing…
      </span>`;
    });
  });
});

/* ── Sort Table Columns ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.style.cursor = 'pointer';
    th.style.userSelect = 'none';
    th.addEventListener('click', () => {
      const table = th.closest('table');
      const colIndex = Array.from(th.parentElement.children).indexOf(th);
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const ascending = th.dataset.sortDir !== 'asc';
      th.dataset.sortDir = ascending ? 'asc' : 'desc';

      // Reset other headers
      table.querySelectorAll('th[data-sort]').forEach(h => {
        if (h !== th) { delete h.dataset.sortDir; h.querySelector('.sort-icon')?.remove(); }
      });

      rows.sort((a, b) => {
        const av = a.children[colIndex]?.textContent?.trim() || '';
        const bv = b.children[colIndex]?.textContent?.trim() || '';
        const an = parseFloat(av.replace(/[^0-9.-]/g, ''));
        const bn = parseFloat(bv.replace(/[^0-9.-]/g, ''));
        if (!isNaN(an) && !isNaN(bn)) return ascending ? an - bn : bn - an;
        return ascending ? av.localeCompare(bv) : bv.localeCompare(av);
      });

      rows.forEach(r => tbody.appendChild(r));
    });
  });
});

/* ── Chart.js Defaults (applies globally if Chart.js loaded) */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof Chart === 'undefined') return;

  Chart.defaults.color = '#8a94ab';
  Chart.defaults.borderColor = '#252b3b';
  Chart.defaults.font.family = "'DM Sans', sans-serif";

  // Revenue chart
  const revenueCtx = document.getElementById('revenueChart');
  if (revenueCtx) {
    const months = revenueCtx.dataset.labels ? JSON.parse(revenueCtx.dataset.labels) : ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const values = revenueCtx.dataset.values ? JSON.parse(revenueCtx.dataset.values) : [12000,14500,13200,16800,19200,17400,21000,22400,20100,24800,26500,28200];

    new Chart(revenueCtx, {
      type: 'line',
      data: {
        labels: months,
        datasets: [{
          label: 'Revenue',
          data: values,
          borderColor: '#3d6bff',
          backgroundColor: 'rgba(61,107,255,0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#3d6bff',
          pointRadius: 3,
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#252b3b' } },
          y: { grid: { color: '#252b3b' }, ticks: { callback: v => '₹' + (v/1000).toFixed(0) + 'k' } }
        }
      }
    });
  }

  // Subscriptions by status donut
  const subsCtx = document.getElementById('subsChart');
  if (subsCtx) {
    const labels = subsCtx.dataset.labels ? JSON.parse(subsCtx.dataset.labels) : ['Active','Suspended','Cancelled','Trial'];
    const values = subsCtx.dataset.values ? JSON.parse(subsCtx.dataset.values) : [342, 28, 94, 16];

    new Chart(subsCtx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: ['#22c55e','#f59e0b','#ef4444','#3d6bff'],
          borderColor: '#111318',
          borderWidth: 3,
          hoverOffset: 6,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { padding: 16, usePointStyle: true, pointStyleWidth: 8, font: { size: 12 } }
          }
        }
      }
    });
  }

  // Usage bar chart
  const usageCtx = document.getElementById('usageChart');
  if (usageCtx) {
    const labels = usageCtx.dataset.labels ? JSON.parse(usageCtx.dataset.labels) : ['Basic','Pro','Business','Enterprise'];
    const values = usageCtx.dataset.values ? JSON.parse(usageCtx.dataset.values) : [128, 245, 189, 78];

    new Chart(usageCtx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Subscriptions',
          data: values,
          backgroundColor: ['rgba(61,107,255,0.7)','rgba(34,197,94,0.7)','rgba(245,158,11,0.7)','rgba(6,182,212,0.7)'],
          borderColor: ['#3d6bff','#22c55e','#f59e0b','#06b6d4'],
          borderWidth: 1,
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#252b3b' } }
        }
      }
    });
  }

  // Monthly new subscribers line
  const newSubsCtx = document.getElementById('newSubsChart');
  if (newSubsCtx) {
    const months = newSubsCtx.dataset.labels
      ? JSON.parse(newSubsCtx.dataset.labels)
      : ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const vals = newSubsCtx.dataset.values ? JSON.parse(newSubsCtx.dataset.values) : [24,38,31,42,55,48,61,58,49,72,81,69];

    new Chart(newSubsCtx, {
      type: 'bar',
      data: {
        labels: months,
        datasets: [{
          label: 'New Subscriptions',
          data: vals,
          backgroundColor: 'rgba(61,107,255,0.6)',
          borderColor: '#3d6bff',
          borderWidth: 1,
          borderRadius: 5,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#252b3b' } }
        }
      }
    });
  }

  // Transaction volume chart
  const txCtx = document.getElementById('txChart');
  if (txCtx) {
    const labels = txCtx.dataset.labels ? JSON.parse(txCtx.dataset.labels) : ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const values = txCtx.dataset.values ? JSON.parse(txCtx.dataset.values) : [18, 24, 21, 30, 27, 12, 9];

    new Chart(txCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Transactions',
          data: values,
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.07)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointBackgroundColor: '#22c55e',
          pointRadius: 3,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#252b3b' } },
          y: { grid: { color: '#252b3b' } }
        }
      }
    });
  }
});

/* ── Spin animation ─────────────────────────────────────── */
const spinStyle = document.createElement('style');
spinStyle.textContent = `
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin { animation: spin 0.8s linear infinite; }
  #sidebar-overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.5); z-index: 99;
    backdrop-filter: blur(2px);
  }
  #sidebar-overlay.active { display: block; }
`;
document.head.appendChild(spinStyle);

/* ── Settings Tab Navigation ────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const settingsNav = document.querySelectorAll('.settings-nav-item');
  if (!settingsNav.length) return;

  settingsNav.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.section;

      // Update nav active state
      settingsNav.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      // Show the matching section
      document.querySelectorAll('.settings-section').forEach(sec => {
        sec.classList.toggle('active', sec.id === target);
      });

      // Persist selection
      sessionStorage.setItem('settings_section', target);
    });
  });

  // Restore last visited section
  const saved = sessionStorage.getItem('settings_section');
  const toActivate = saved
    ? document.querySelector(`.settings-nav-item[data-section="${saved}"]`)
    : settingsNav[0];
  if (toActivate) toActivate.click();
});

/* ── Global Search (topbar) ─────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('global-search');
  if (!searchInput) return;

  // Map of search terms to urls — extend as needed
  // Routes are tagged with requiredRole: 'superuser' | 'manager' | 'all'
  const routes = [
    { label: 'Dashboard',         url: '/superuser/',                    role: 'all' },
    { label: 'Libraries',         url: '/superuser/libraries/',          role: 'superuser' },
    { label: 'Subscriptions',     url: '/superuser/subscriptions/',      role: 'superuser' },
    { label: 'Plans',             url: '/superuser/plans/',              role: 'superuser' },
    { label: 'Transactions',      url: '/superuser/transactions/',       role: 'superuser' },
    { label: 'Invoices',          url: '/superuser/invoices/',           role: 'superuser' },
    { label: 'Revenue Report',    url: '/superuser/reports/revenue/',    role: 'superuser' },
    { label: 'Usage Overview',    url: '/superuser/reports/usage/',      role: 'superuser' },
    { label: 'Staff',             url: '/superuser/staff/',              role: 'all' },
    { label: 'Add Staff',         url: '/superuser/staff/add/',          role: 'manager' },
    { label: 'Roles',             url: '/superuser/roles/',              role: 'superuser' },
    { label: 'Tasks',             url: '/superuser/tasks/',              role: 'all' },
    { label: 'Settings',          url: '/superuser/settings/',           role: 'superuser' },
  ];

  // Detect current user role from a data attribute on <body> set by the base template
  const isSuperuser = document.body.dataset.superuser === 'true';
  const isManager   = document.body.dataset.manager   === 'true';

  const visibleRoutes = routes.filter(r => {
    if (r.role === 'all')       return true;
    if (r.role === 'superuser') return isSuperuser;
    if (r.role === 'manager')   return isSuperuser || isManager;
    return false;
  });

  // Build dropdown
  const dropdown = document.createElement('div');
  dropdown.style.cssText = `
    position:absolute; top:calc(100% + 6px); left:0; right:0;
    background:var(--bg-surface); border:1px solid var(--border);
    border-radius:var(--radius-md); box-shadow:var(--shadow-md);
    overflow:hidden; z-index:200; display:none;
  `;
  searchInput.parentElement.style.position = 'relative';
  searchInput.parentElement.appendChild(dropdown);

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.toLowerCase().trim();
    dropdown.innerHTML = '';
    if (!q) { dropdown.style.display = 'none'; return; }

    const matches = visibleRoutes.filter(r => r.label.toLowerCase().includes(q));
    if (!matches.length) { dropdown.style.display = 'none'; return; }

    matches.forEach(r => {
      const item = document.createElement('a');
      item.href = r.url;
      item.textContent = r.label;
      item.style.cssText = `
        display:block; padding:9px 14px; font-size:13px;
        color:var(--text-primary); border-bottom:1px solid var(--border);
        transition:background var(--transition);
      `;
      item.onmouseover = () => item.style.background = 'var(--bg-hover)';
      item.onmouseout  = () => item.style.background = '';
      dropdown.appendChild(item);
    });

    dropdown.style.display = 'block';
  });

  // Close on outside click
  document.addEventListener('click', e => {
    if (!searchInput.parentElement.contains(e.target)) {
      dropdown.style.display = 'none';
      searchInput.value = '';
    }
  });

  // Keyboard navigation
  searchInput.addEventListener('keydown', e => {
    const items = dropdown.querySelectorAll('a');
    if (!items.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); items[0].focus(); }
    if (e.key === 'Escape')    { dropdown.style.display = 'none'; searchInput.value = ''; }
  });

  dropdown.addEventListener('keydown', e => {
    const items = [...dropdown.querySelectorAll('a')];
    const idx   = items.indexOf(document.activeElement);
    if (e.key === 'ArrowDown')  { e.preventDefault(); items[Math.min(idx+1, items.length-1)]?.focus(); }
    if (e.key === 'ArrowUp')    { e.preventDefault(); idx > 0 ? items[idx-1].focus() : searchInput.focus(); }
    if (e.key === 'Escape')     { dropdown.style.display = 'none'; searchInput.focus(); }
  });
});

/* ── Settings: unsaved changes warning ───────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const settingsForms = document.querySelectorAll('.settings-section form');
  let dirty = false;

  settingsForms.forEach(form => {
    form.addEventListener('change', () => { dirty = true; });
    form.addEventListener('submit', () => { dirty = false; });
  });

  window.addEventListener('beforeunload', e => {
    if (dirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  });
});