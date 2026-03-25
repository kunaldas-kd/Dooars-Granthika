/**
 * members/members.js
 * ──────────────────
 * Shared utilities for all members-app pages.
 *
 * Provides:
 *   postForm(url, formData)  – fetch POST with CSRF, returns Response promise
 *   postAction(url, body)    – fetch POST with CSRF + JSON body, returns Response promise
 *   showToast(msg, type)     – display a toast notification (success / error / info)
 *   applyStatusBadgeColors() – colour .status-badge spans by their CSS class
 *   initSearch()             – wire #memberSearch to live-filter #membersTable rows
 *   initSort()               – wire [data-sortable] <th> clicks to sort table
 *   initFilterReset()        – wire #resetFilters button
 *
 * All page-specific JS files depend on this file being loaded first.
 */

'use strict';

// ── CSRF helper ───────────────────────────────────────────────────────────────

function getCsrfToken() {
  // 1. Try the cookie (works when SESSION_COOKIE_SAMESITE allows it)
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  if (match) return decodeURIComponent(match[1]);

  // 2. Fallback: read from a hidden input in the page
  const el = document.querySelector('[name=csrfmiddlewaretoken]');
  return el ? el.value : '';
}


// ── Network helpers ───────────────────────────────────────────────────────────

/**
 * POST a FormData object (e.g. from a <form>) with the CSRF token header.
 * @param {string}   url
 * @param {FormData} formData
 * @returns {Promise<Response>}
 */
function postForm(url, formData) {
  return fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrfToken() },
    body: formData,
  });
}

/**
 * POST a plain JSON body (or no body) with the CSRF token header.
 * Used by action buttons (send reminder, mark cleared, etc.).
 * @param {string} url
 * @param {object} [body={}]
 * @returns {Promise<Response>}
 */
function postAction(url, body = {}) {
  return fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify(body),
  });
}

// Expose globally so page-specific scripts can call them without imports
window.postForm   = postForm;
window.postAction = postAction;


// ── Toast notifications ───────────────────────────────────────────────────────

/**
 * Show a toast notification at the bottom-right of the screen.
 * @param {string} message
 * @param {'success'|'error'|'info'|'warning'} [type='info']
 * @param {number} [duration=3500]  ms before auto-dismiss
 */
function showToast(message, type = 'info', duration = 3500) {
  // Ensure toast container exists
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    Object.assign(container.style, {
      position:  'fixed',
      bottom:    '1.5rem',
      right:     '1.5rem',
      zIndex:    '9999',
      display:   'flex',
      flexDirection: 'column',
      gap:       '0.5rem',
    });
    document.body.appendChild(container);
  }

  const colors = {
    success: { bg: '#10b981', icon: 'fa-check-circle' },
    error:   { bg: '#ef4444', icon: 'fa-exclamation-circle' },
    warning: { bg: '#f59e0b', icon: 'fa-exclamation-triangle' },
    info:    { bg: '#3b82f6', icon: 'fa-info-circle' },
  };
  const { bg, icon } = colors[type] || colors.info;

  const toast = document.createElement('div');
  Object.assign(toast.style, {
    background:   bg,
    color:        'white',
    padding:      '0.75rem 1.25rem',
    borderRadius: '10px',
    boxShadow:    '0 4px 12px rgba(0,0,0,0.15)',
    display:      'flex',
    alignItems:   'center',
    gap:          '0.6rem',
    fontSize:     '0.9rem',
    fontWeight:   '500',
    minWidth:     '260px',
    maxWidth:     '400px',
    opacity:      '0',
    transform:    'translateY(8px)',
    transition:   'opacity 0.25s, transform 0.25s',
  });
  toast.innerHTML = `<i class="fas ${icon}"></i><span>${message}</span>`;
  container.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => {
    toast.style.opacity   = '1';
    toast.style.transform = 'translateY(0)';
  });

  // Auto dismiss
  setTimeout(() => {
    toast.style.opacity   = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

window.showToast = showToast;


// ── Status badge colours ──────────────────────────────────────────────────────

/**
 * Apply background colours to .status-badge elements based on their CSS class.
 * Call this after dynamically injecting HTML that contains status badges.
 */
function applyStatusBadgeColors() {
  const palette = {
    active:   '#10b981',
    inactive: '#ef4444',
    passout:  '#f59e0b',
    cleared:  '#10b981',
    pending:  '#f59e0b',
    issued:   '#3b82f6',
    returned: '#10b981',
    overdue:  '#ef4444',
    lost:     '#8b5cf6',
    student:  '#3b82f6',
    teacher:  '#8b5cf6',
    general:  '#6b7280',
  };

  document.querySelectorAll('.status-badge').forEach((el) => {
    for (const [cls, color] of Object.entries(palette)) {
      if (el.classList.contains(cls)) {
        el.style.background  = color;
        el.style.color       = 'white';
        el.style.padding     = '3px 10px';
        el.style.borderRadius = '12px';
        el.style.fontSize    = '11px';
        el.style.fontWeight  = '600';
        el.style.display     = 'inline-flex';
        el.style.alignItems  = 'center';
        el.style.gap         = '4px';
        break;
      }
    }
  });
}

window.applyStatusBadgeColors = applyStatusBadgeColors;


// ── Live search / filter ──────────────────────────────────────────────────────

/**
 * Wire the #memberSearch input to filter visible rows in #membersTable.
 * Searches across all <td> text content (case-insensitive).
 */
function initSearch() {
  const input = document.getElementById('memberSearch');
  const table = document.getElementById('membersTable');
  if (!input || !table) return;

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    table.querySelectorAll('tbody tr').forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.style.display = (!q || text.includes(q)) ? '' : 'none';
    });
  });
}


// ── Column sort ───────────────────────────────────────────────────────────────

/**
 * Add click-to-sort behaviour to all <th data-sortable> elements in #membersTable.
 * Sorts alphabetically; clicking the same column toggles asc / desc.
 */
function initSort() {
  const table = document.getElementById('membersTable');
  if (!table) return;

  let lastTh   = null;
  let ascending = true;

  table.querySelectorAll('thead th[data-sortable]').forEach((th) => {
    th.style.cursor = 'pointer';
    th.title        = 'Click to sort';

    th.addEventListener('click', () => {
      const colIdx = Array.from(th.parentElement.children).indexOf(th);

      if (lastTh === th) {
        ascending = !ascending;
      } else {
        ascending = true;
        if (lastTh) lastTh.dataset.sortDir = '';
      }
      th.dataset.sortDir = ascending ? 'asc' : 'desc';
      lastTh = th;

      const tbody = table.querySelector('tbody');
      const rows  = Array.from(tbody.querySelectorAll('tr'));

      rows.sort((a, b) => {
        const aText = (a.cells[colIdx]?.textContent || '').trim().toLowerCase();
        const bText = (b.cells[colIdx]?.textContent || '').trim().toLowerCase();
        return ascending
          ? aText.localeCompare(bText)
          : bText.localeCompare(aText);
      });

      rows.forEach((r) => tbody.appendChild(r));
    });
  });
}


// ── Filter reset ──────────────────────────────────────────────────────────────

/**
 * Wire #resetFilters button to clear all selects inside #filterForm
 * and submit the form (which reloads with no filters).
 */
function initFilterReset() {
  const btn  = document.getElementById('resetFilters');
  const form = document.getElementById('filterForm');
  if (!btn || !form) return;

  btn.addEventListener('click', () => {
    form.querySelectorAll('select').forEach((s) => { s.value = ''; });
    form.querySelectorAll('input[type="text"]').forEach((i) => { i.value = ''; });
    form.submit();
  });
}


// ── Row click → member detail ─────────────────────────────────────────────────

/**
 * Make table rows clickable if they contain an <a> with class "action-icon view".
 * Clicking anywhere on the row (except an existing <a> or <button>) navigates
 * to the member detail URL.
 */
function initRowClick() {
  const table = document.getElementById('membersTable');
  if (!table) return;

  table.querySelectorAll('tbody tr').forEach((row) => {
    const viewLink = row.querySelector('a.action-icon.view');
    if (!viewLink) return;

    row.style.cursor = 'pointer';
    row.addEventListener('click', (e) => {
      if (e.target.closest('a') || e.target.closest('button')) return;
      window.location.href = viewLink.href;
    });
  });
}


// ── Bootstrap on DOMContentLoaded ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  applyStatusBadgeColors();
  initSearch();
  initSort();
  initFilterReset();
  initRowClick();
  initDeleteButtons();
});

// ── Delete member ─────────────────────────────────────────────────────────────

/**
 * Wire all .delete-member-btn elements (buttons with data-delete-url and
 * data-member-name attributes) to a confirm → AJAX POST → redirect flow.
 *
 * Markup pattern (members_list, member_detail, etc.):
 *   <button class="delete-member-btn"
 *           data-member-name="John Doe"
 *           data-delete-url="/members/<pk>/delete/">
 *     <i class="fas fa-trash"></i> Delete Member
 *   </button>
 */
function initDeleteButtons() {
  document.querySelectorAll('.delete-member-btn').forEach((btn) => {
    btn.addEventListener('click', function () {
      const name      = this.dataset.memberName || 'this member';
      const deleteUrl = this.dataset.deleteUrl;
      if (!deleteUrl) return;

      if (!confirm(`Are you sure you want to delete ${name}?\nThis action cannot be undone.`)) return;

      this.disabled  = true;
      const origHtml = this.innerHTML;
      this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

      fetch(deleteUrl, {
        method:  'POST',
        headers: {
          'Accept':      'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      })
        .then((resp) => resp.json().then((data) => ({ ok: resp.ok, data })))
        .then(({ ok, data }) => {
          if (ok && data.success) {
            showToast(data.message || 'Member deleted.', 'success');
            setTimeout(() => {
              window.location.href = data.redirect_url || '/members/';
            }, 800);
          } else {
            showToast(data.message || 'Could not delete member.', 'error');
            this.disabled  = false;
            this.innerHTML = origHtml;
          }
        })
        .catch(() => {
          showToast('Network error. Please try again.', 'error');
          this.disabled  = false;
          this.innerHTML = origHtml;
        });
    });
  });
}

window.initDeleteButtons = initDeleteButtons;


// ── Select-or-create mutual exclusivity ──────────────────────────────────────

/**
 * Wire all .select-or-create widgets so that typing in the "create new" input
 * clears the corresponding select (and vice-versa), preventing both values
 * from being submitted at once.
 *
 * Each widget must have id="soc-<key>" on the outer div, and contain:
 *   • a <select>  inside .select-or-create__left
 *   • an <input>  inside .select-or-create__right
 */
function initSelectOrCreate() {
  document.querySelectorAll('.select-or-create').forEach((widget) => {
    const selectEl = widget.querySelector('.select-or-create__left select');
    const inputEl  = widget.querySelector('.select-or-create__right input[type="text"]');
    const leftPane = widget.querySelector('.select-or-create__left');
    const rightPane= widget.querySelector('.select-or-create__right');

    if (!selectEl || !inputEl) return;

    function setActive(side) {
      leftPane?.classList.toggle('soc-active',  side === 'left');
      rightPane?.classList.toggle('soc-active', side === 'right');
    }

    // Selecting a value in the dropdown → clear the text input
    selectEl.addEventListener('change', () => {
      if (selectEl.value) {
        inputEl.value = '';
        setActive('left');
      } else {
        setActive(null);
      }
    });

    // Typing in the text input → reset the select to empty
    inputEl.addEventListener('input', () => {
      if (inputEl.value.trim()) {
        selectEl.value = '';
        setActive('right');
      } else {
        setActive(null);
      }
    });

    // Set initial active side on page load
    if (selectEl.value)          setActive('left');
    else if (inputEl.value.trim()) setActive('right');
  });
}

window.initSelectOrCreate = initSelectOrCreate;


// ── Phone validation ──────────────────────────────────────────────────────────

/**
 * Attach live UX validation to phone number inputs.
 * @param {Array<{id: string, required: boolean}>} fields
 */
function initPhoneValidation(fields) {
  fields.forEach(({ id, required }) => {
    const el = document.getElementById(id);
    if (!el) return;

    // Allow only digits
    el.addEventListener('input', () => {
      el.value = el.value.replace(/\D/g, '').slice(0, 10);
    });

    el.addEventListener('blur', () => {
      const val = el.value.trim();
      let errEl = el.nextElementSibling;
      // Find or create error message element
      if (!errEl || !errEl.classList.contains('error-message')) {
        errEl = document.createElement('span');
        errEl.className = 'error-message';
        el.parentNode.insertBefore(errEl, el.nextSibling);
      }

      if (required && !val) {
        errEl.textContent = 'Phone number is required.';
      } else if (val && val.length !== 10) {
        errEl.textContent = 'Enter a valid 10-digit phone number.';
      } else {
        errEl.textContent = '';
      }
    });
  });
}

window.initPhoneValidation = initPhoneValidation;


// ── Email validation ──────────────────────────────────────────────────────────

/**
 * Attach live UX validation to an email input.
 * @param {string} id — element id
 */
function initEmailValidation(id) {
  const el = document.getElementById(id);
  if (!el) return;

  el.addEventListener('blur', () => {
    const val = el.value.trim();
    let errEl = el.nextElementSibling;
    if (!errEl || !errEl.classList.contains('error-message')) {
      errEl = document.createElement('span');
      errEl.className = 'error-message';
      el.parentNode.insertBefore(errEl, el.nextSibling);
    }

    const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    if (!val) {
      errEl.textContent = 'Email address is required.';
    } else if (!valid) {
      errEl.textContent = 'Enter a valid email address.';
    } else {
      errEl.textContent = '';
    }
  });
}

window.initEmailValidation = initEmailValidation;