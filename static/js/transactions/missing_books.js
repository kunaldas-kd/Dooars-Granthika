/* ============================================================
   missing_books.js
   ============================================================ */

(function () {
  'use strict';

  /* ── Select All ── */
  const selectAll = document.getElementById('selectAll');
  const rowChecks = document.querySelectorAll('.row-check');
  setupSelectAll(selectAll, rowChecks);

  /* ── Mark Lost Modal ── */
  const markLostModal   = document.getElementById('markLostModal');
  const markLostForm    = document.getElementById('markLostForm');
  const markLostTxnId   = document.getElementById('markLostTxnId');
  const closeMarkLost   = document.getElementById('closeMarkLostModal');
  const cancelMarkLost  = document.getElementById('cancelMarkLost');
  const markLostBackdrop = document.getElementById('markLostBackdrop');

  document.querySelectorAll('.action-btn--mark-lost').forEach(btn => {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      markLostTxnId.value = id;
      if (markLostForm) {
        const action = markLostForm.action.replace('/0/', `/${id}/`);
        markLostForm.action = action;
      }
      openModal(markLostModal);
    });
  });

  [closeMarkLost, cancelMarkLost, markLostBackdrop].forEach(el => {
    el?.addEventListener('click', () => closeModal(markLostModal));
  });

  /* ── Add Penalty Modal ── */
  const addPenaltyModal    = document.getElementById('addPenaltyModal');
  const addPenaltyForm     = document.getElementById('addPenaltyForm');
  const penaltyMissingId   = document.getElementById('penaltyMissingId');
  const penaltyAmount      = document.getElementById('penaltyAmount');
  const bookValueHint      = document.getElementById('bookValueHint');
  const penaltyBookInfo    = document.getElementById('penaltyBookInfo');
  const closeAddPenalty    = document.getElementById('closeAddPenaltyModal');
  const cancelAddPenalty   = document.getElementById('cancelAddPenalty');
  const addPenaltyBackdrop = document.getElementById('addPenaltyBackdrop');

  document.querySelectorAll('.action-btn--penalty').forEach(btn => {
    btn.addEventListener('click', function () {
      const id    = this.dataset.id;
      const book  = this.dataset.book;
      const value = this.dataset.value;

      penaltyMissingId.value = id;
      if (bookValueHint) bookValueHint.textContent = value ? `₹${value}` : 'N/A';
      if (penaltyAmount && value) penaltyAmount.placeholder = value;
      if (penaltyBookInfo) penaltyBookInfo.textContent = `Book: ${book}`;

      if (addPenaltyForm) {
        addPenaltyForm.action = addPenaltyForm.action.replace(/\/\d+\/$/, `/${id}/`);
      }

      openModal(addPenaltyModal);
    });
  });

  [closeAddPenalty, cancelAddPenalty, addPenaltyBackdrop].forEach(el => {
    el?.addEventListener('click', () => closeModal(addPenaltyModal));
  });

  /* ── Recover Button ── */
  document.querySelectorAll('.action-btn--recover').forEach(btn => {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      if (!confirm('Mark this book as recovered? The inventory will be updated.')) return;

      this.disabled = true;
      this.textContent = 'Recovering…';

      fetch(`/transactions/missing/${id}/recover/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showToast('Book marked as recovered.', 'success');
          setTimeout(() => window.location.reload(), 900);
        } else {
          showToast(data.error || 'Error.', 'error');
          this.disabled = false;
          this.textContent = 'Recover';
        }
      })
      .catch(() => {
        showToast('Network error.', 'error');
        this.disabled = false;
        this.textContent = 'Recover';
      });
    });
  });

  /* ── Form submit with loading ── */
  [markLostForm, addPenaltyForm].forEach(form => {
    form?.addEventListener('submit', function () {
      const btn = this.querySelector('[type=submit]');
      if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
    });
  });

  /* ── Escape key closes modal ── */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal(markLostModal);
      closeModal(addPenaltyModal);
    }
  });

  /* ── Helpers ── */
  function openModal(modal) {
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function setupSelectAll(all, checks) {
    if (!all) return;
    all.addEventListener('change', function () {
      checks.forEach(c => { c.checked = this.checked; });
    });
    checks.forEach(c => {
      c.addEventListener('change', () => {
        const checked  = [...checks].filter(x => x.checked).length;
        all.checked       = checked === checks.length;
        all.indeterminate = checked > 0 && checked < checks.length;
      });
    });
  }

  function getCsrf() {
    const m = document.querySelector('[name=csrfmiddlewaretoken]');
    return m ? m.value : '';
  }

  function showToast(msg, type = 'info') {
    const t = document.createElement('div');
    Object.assign(t.style, {
      position: 'fixed', bottom: '24px', right: '24px',
      padding: '12px 20px', borderRadius: '10px',
      fontFamily: "'DM Sans', sans-serif", fontSize: '13.5px', fontWeight: '500',
      color: '#fff',
      background: type === 'success' ? '#16a34a' : type === 'error' ? '#b91c1c' : '#2563eb',
      boxShadow: '0 8px 24px rgba(15,34,64,.2)',
      zIndex: '9999', opacity: '0', transform: 'translateY(12px)',
      transition: 'opacity .2s ease, transform .2s ease',
    });
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => { t.style.opacity = '1'; t.style.transform = 'translateY(0)'; });
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 250); }, 3500);
  }

})();
