/**
 * members/clearance_check.js
 * ──────────────────────────
 * Clearance-check page AJAX handler.
 *
 * Depends on: members.js  (getCsrfToken, postForm, showToast, applyStatusBadgeColors)
 *
 * "Issue Clearance Certificate" button flow:
 *   1. Preflight POST { confirm: false }  →  blocking check (no DB write)
 *      If blocked: show red breakdown of what must be resolved.
 *      If clear:   show green confirmation modal.
 *   2. Confirm POST { confirm: true }
 *      View marks member clearance_status=cleared + status=passout, returns
 *      { certificate_url }.  JS opens it in a new tab (PDF download) and
 *      updates the result card badge without a full page reload.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  const form      = document.getElementById('clearanceCheckForm');
  const resultBox = document.getElementById('clearanceResult');
  const submitBtn = document.getElementById('searchBtn');
  const input     = document.getElementById('memberIdInput');

  if (!form || !resultBox) return;

  _injectModal();

  // Auto-search when member_id is pre-filled from passout page link
  const preFilled = new URLSearchParams(window.location.search).get('member_id');
  if (preFilled && input) {
    input.value = preFilled;
    setTimeout(() => doSearch(), 100);
  }

  form.addEventListener('submit', e => { e.preventDefault(); doSearch(); });


  // ── Search ─────────────────────────────────────────────────────────────────

  function doSearch() {
    if (submitBtn) {
      submitBtn.disabled  = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking…';
    }
    resultBox.innerHTML = '';

    postForm(form.action, new FormData(form))
      .then(r => { if (!r.ok) throw new Error('Server error ' + r.status); return r.json(); })
      .then(data => renderResult(data))
      .catch(err => { resultBox.innerHTML = _errorBox(err.message); })
      .finally(() => {
        if (submitBtn) {
          submitBtn.disabled  = false;
          submitBtn.innerHTML = '<i class="fas fa-search"></i> Check Status';
        }
      });
  }


  // ── Result card ────────────────────────────────────────────────────────────

  function renderResult(data) {
    if (!data.success) {
      resultBox.innerHTML = `
        <div style="display:flex;align-items:center;gap:.75rem;background:#fff;
                    border:1px solid #e5e7eb;border-radius:12px;padding:1.5rem;
                    color:#6b7280;font-size:1rem;margin-top:1rem;">
          <i class="fas fa-user-times" style="font-size:1.5rem;color:#ef4444;"></i>
          <span>${esc(data.message || 'Member not found.')}</span>
        </div>`;
      return;
    }

    const d           = data.data;
    const isCleared   = Boolean(d.is_cleared);
    const statusColor = isCleared ? '#10b981' : '#f59e0b';
    const statusIcon  = isCleared ? 'fa-check-circle' : 'fa-clock';
    const statusLabel = isCleared ? 'CLEARED' : 'PENDING';
    const profileUrl  = `/members/${d.pk}/`;

    const infoRow = isCleared
      ? `<div style="display:flex;align-items:center;gap:.5rem;color:#10b981;margin-bottom:1rem;">
           <i class="fas fa-check-circle"></i>
           <strong>Cleared on:</strong>&nbsp;${esc(d.clearance_date || 'N/A')}
         </div>`
      : `<div style="display:flex;flex-wrap:wrap;gap:.75rem;align-items:center;margin-bottom:1rem;">
           <span style="color:#ef4444;"><i class="fas fa-book"></i> <strong>Pending Books:</strong> ${d.pending_books}</span>
           <span style="color:#d1d5db;">|</span>
           <span style="color:#f59e0b;"><i class="fas fa-rupee-sign"></i> <strong>Pending Fines:</strong> ₹${Number(d.pending_fines).toFixed(2)}</span>
         </div>`;

    // The cert button: always show, JS handles the blocking explanation
    const certBtn = `
      <button id="issueCertBtn"
        onclick="window._issueClearance(${d.pk}, '${esc(d.full_name)}')"
        style="display:inline-flex;align-items:center;gap:.5rem;
               background:linear-gradient(135deg,#10b981,#059669);
               color:#fff;border:none;border-radius:8px;
               padding:10px 20px;font-size:.9rem;font-weight:600;
               cursor:pointer;box-shadow:0 2px 8px rgba(16,185,129,.35);
               transition:opacity .15s;">
        <i class="fas fa-file-certificate"></i> Issue Clearance Certificate
      </button>`;

    resultBox.innerHTML = `
      <div id="resultCard" style="background:#fff;border-radius:12px;padding:1.5rem;
              margin-top:1rem;box-shadow:0 2px 8px rgba(0,0,0,.08);
              border-left:5px solid ${statusColor};">

        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    margin-bottom:1rem;flex-wrap:wrap;gap:.75rem;">
          <div>
            <h3 style="margin:0;font-size:1.25rem;font-weight:700;color:#1f2937;">${esc(d.full_name)}</h3>
            <span style="font-size:.85rem;color:#6b7280;font-family:monospace;">${esc(d.member_id)}</span>
            &nbsp;<span style="font-size:.8rem;color:#9ca3af;">${esc(d.role || '')}</span>
          </div>
          <span id="statusBadge" style="background:${statusColor};color:#fff;padding:4px 16px;
                       border-radius:20px;font-size:.85rem;font-weight:700;
                       display:inline-flex;align-items:center;gap:.4rem;">
            <i class="fas ${statusIcon}"></i> ${statusLabel}
          </span>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
                    gap:.5rem .75rem;margin-bottom:1rem;">
          <div><strong>Email:</strong> ${esc(d.email || '—')}</div>
          <div><strong>Phone:</strong> ${esc(d.phone || '—')}</div>
          <div><strong>Department:</strong> ${esc(d.department || 'N/A')}</div>
          <div><strong>Member Status:</strong>
            <span class="status-badge ${esc(d.status)}" style="margin-left:.3rem;">
              <i class="fas fa-circle"></i> ${esc(d.status)}
            </span>
          </div>
        </div>

        ${infoRow}

        <!-- Blocking reasons panel — shown by JS if server rejects -->
        <div id="blockingPanel" style="display:none;"></div>

        <div style="display:flex;flex-wrap:wrap;gap:.75rem;align-items:center;margin-top:1rem;">
          <a href="${profileUrl}"
             style="display:inline-flex;align-items:center;gap:.5rem;
                    background:#f3f4f6;color:#374151;border-radius:8px;
                    padding:10px 18px;font-size:.9rem;font-weight:500;
                    text-decoration:none;border:1px solid #e5e7eb;">
            <i class="fas fa-eye"></i> View Profile
          </a>
          ${certBtn}
        </div>

      </div>`;

    applyStatusBadgeColors();
  }


  // ── Issue Clearance flow ───────────────────────────────────────────────────

  window._issueClearance = function(pk, name) {
    const btn = document.getElementById('issueCertBtn');
    if (btn) {
      btn.disabled  = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking obligations…';
    }

    // Step 1: preflight — full server-side blocking check
    _apiPost(`/members/${pk}/issue-clearance/`, { confirm: false })
      .then(({ ok, data }) => {
        if (btn) {
          btn.disabled  = false;
          btn.innerHTML = '<i class="fas fa-file-certificate"></i> Issue Clearance Certificate';
        }

        if (!ok || !data.success) {
          // Show blocking reasons inline in the card
          _showBlockingPanel(data);
          showToast(data.message || 'Cannot issue clearance.', 'error');
          return;
        }

        // All clear — show confirmation modal
        _hideBlockingPanel();
        _showConfirmModal(pk, name, data.message, data.current_status);
      })
      .catch(() => {
        showToast('Network error. Please try again.', 'error');
        if (btn) {
          btn.disabled  = false;
          btn.innerHTML = '<i class="fas fa-file-certificate"></i> Issue Clearance Certificate';
        }
      });
  };


  /** Render a red panel listing each blocking reason. */
  function _showBlockingPanel(data) {
    const panel = document.getElementById('blockingPanel');
    if (!panel) return;

    const b = data.blocking || {};
    const rows = [];

    if (b.active_loans > 0) {
      rows.push(`
        <div style="display:flex;align-items:center;gap:.6rem;">
          <i class="fas fa-book" style="color:#ef4444;width:16px;text-align:center;"></i>
          <span><strong>${b.active_loans}</strong> book(s) still issued / overdue — must be returned first.</span>
        </div>`);
    }
    if (b.lost_items > 0) {
      rows.push(`
        <div style="display:flex;align-items:center;gap:.6rem;">
          <i class="fas fa-times-circle" style="color:#8b5cf6;width:16px;text-align:center;"></i>
          <span><strong>${b.lost_items}</strong> lost book(s) — penalty must be resolved.</span>
        </div>`);
    }
    if (b.unpaid_fine > 0) {
      rows.push(`
        <div style="display:flex;align-items:center;gap:.6rem;">
          <i class="fas fa-rupee-sign" style="color:#f59e0b;width:16px;text-align:center;"></i>
          <span><strong>₹${Number(b.unpaid_fine).toFixed(2)}</strong> in unpaid fines — must be paid or waived.</span>
        </div>`);
    }

    panel.style.display = 'block';
    panel.innerHTML = `
      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;
                  padding:1rem 1.25rem;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:.6rem;
                    font-weight:700;color:#dc2626;margin-bottom:.75rem;">
          <i class="fas fa-ban"></i> Clearance Blocked — Resolve the following:
        </div>
        <div style="display:flex;flex-direction:column;gap:.5rem;color:#374151;font-size:.9rem;">
          ${rows.join('')}
        </div>
      </div>`;
  }

  function _hideBlockingPanel() {
    const panel = document.getElementById('blockingPanel');
    if (panel) { panel.style.display = 'none'; panel.innerHTML = ''; }
  }


  // ── Confirmation modal ────────────────────────────────────────────────────

  function _showConfirmModal(pk, name, message, currentStatus) {
    const modal   = document.getElementById('clearanceModal');
    const msgEl   = document.getElementById('clearanceModalMsg');
    const nameEl  = document.getElementById('clearanceModalName');
    const noteEl  = document.getElementById('clearanceModalNote');
    let   confBtn = document.getElementById('clearanceModalConfirm');

    if (nameEl) nameEl.textContent = name;
    if (msgEl)  msgEl.textContent  = message;
    if (noteEl) noteEl.textContent = currentStatus !== 'passout'
      ? 'The member will be moved to Passout status and a PDF certificate will be downloaded.'
      : 'The member is already Passout. The PDF certificate will be downloaded again.';

    // Replace button to clear any previous listener
    const newBtn = confBtn.cloneNode(true);
    confBtn.parentNode.replaceChild(newBtn, confBtn);
    newBtn.addEventListener('click', () => { _closeModal(); _doIssue(pk, name); });

    modal.style.display = 'flex';
  }


  function _doIssue(pk, name) {
    showToast('Processing certificate…', 'info');

    _apiPost(`/members/${pk}/issue-clearance/`, { confirm: true })
      .then(({ ok, data }) => {
        if (!ok || !data.success) {
          showToast(data.message || 'Failed to issue certificate.', 'error');
          return;
        }

        showToast(data.message || 'Certificate issued!', 'success');

        // Trigger PDF download in new tab
        if (data.certificate_url) window.open(data.certificate_url, '_blank');

        // Update result card badge to PASSOUT without full re-search
        _patchCardToPassout();
      })
      .catch(() => showToast('Network error. Please try again.', 'error'));
  }


  function _patchCardToPassout() {
    const card  = document.getElementById('resultCard');
    if (!card) return;
    const color = '#6366f1';
    card.style.borderLeftColor = color;

    const badge = document.getElementById('statusBadge');
    if (badge) {
      badge.style.background = color;
      badge.innerHTML = '<i class="fas fa-user-graduate"></i> PASSOUT';
    }

    const certBtn = document.getElementById('issueCertBtn');
    if (certBtn) {
      certBtn.disabled       = true;
      certBtn.style.opacity  = '0.55';
      certBtn.innerHTML      = '<i class="fas fa-check"></i> Certificate Issued';
    }

    card.querySelectorAll('.status-badge').forEach(el => {
      el.className = 'status-badge passout';
      el.innerHTML = '<i class="fas fa-circle"></i> passout';
    });
    applyStatusBadgeColors();
  }


  // ── Modal injection ────────────────────────────────────────────────────────

  function _injectModal() {
    if (document.getElementById('clearanceModal')) return;
    document.body.insertAdjacentHTML('beforeend', `
      <div id="clearanceModal"
           style="display:none;position:fixed;inset:0;z-index:9999;
                  background:rgba(0,0,0,.45);align-items:center;justify-content:center;">
        <div style="background:#fff;border-radius:16px;padding:2rem;max-width:460px;
                    width:90%;box-shadow:0 20px 60px rgba(0,0,0,.25);position:relative;">
          <button onclick="window._closeClearanceModal()"
                  style="position:absolute;top:1rem;right:1rem;background:none;
                         border:none;font-size:1.25rem;cursor:pointer;color:#6b7280;">
            <i class="fas fa-times"></i>
          </button>
          <div style="text-align:center;margin-bottom:1rem;">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                        width:60px;height:60px;border-radius:50%;
                        background:linear-gradient(135deg,#10b981,#059669);">
              <i class="fas fa-file-certificate" style="color:#fff;font-size:1.5rem;"></i>
            </div>
          </div>
          <h3 id="clearanceModalName"
              style="text-align:center;margin:0 0 .5rem;font-size:1.2rem;
                     font-weight:700;color:#1f2937;"></h3>
          <p id="clearanceModalMsg"
             style="text-align:center;color:#6b7280;font-size:.95rem;margin:0 0 1rem;"></p>
          <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                      padding:.85rem 1rem;margin-bottom:1.5rem;">
            <p id="clearanceModalNote" style="margin:0;font-size:.875rem;color:#166534;"></p>
          </div>
          <div style="display:flex;gap:.75rem;justify-content:flex-end;">
            <button onclick="window._closeClearanceModal()"
                    style="padding:10px 20px;border-radius:8px;border:1px solid #e5e7eb;
                           background:#fff;color:#374151;font-weight:500;cursor:pointer;">
              Cancel
            </button>
            <button id="clearanceModalConfirm"
                    style="padding:10px 22px;border-radius:8px;border:none;
                           background:linear-gradient(135deg,#10b981,#059669);
                           color:#fff;font-weight:600;cursor:pointer;
                           display:flex;align-items:center;gap:.5rem;">
              <i class="fas fa-file-download"></i> Confirm &amp; Download
            </button>
          </div>
        </div>
      </div>`);

    document.getElementById('clearanceModal').addEventListener('click', e => {
      if (e.target === e.currentTarget) _closeModal();
    });
  }

  function _closeModal() {
    const m = document.getElementById('clearanceModal');
    if (m) m.style.display = 'none';
  }
  window._closeClearanceModal = _closeModal;


  // ── Helpers ────────────────────────────────────────────────────────────────

  function _apiPost(url, body) {
    return fetch(url, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept':       'application/json',
        'X-CSRFToken':  getCsrfToken(),
      },
      body: JSON.stringify(body),
    }).then(r => r.json().then(data => ({ ok: r.ok, data })));
  }

  function _errorBox(msg) {
    return `<div style="display:flex;align-items:center;gap:.75rem;background:#fff;
                border:1px solid #fee2e2;border-radius:12px;padding:1.5rem;
                color:#ef4444;margin-top:1rem;">
              <i class="fas fa-exclamation-circle" style="font-size:1.5rem;"></i>
              <span>Error: ${esc(msg)}</span>
            </div>`;
  }

  function esc(str) {
    return String(str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  }

});