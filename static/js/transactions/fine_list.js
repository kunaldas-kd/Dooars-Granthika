/* ============================================================
   fine_list.js
   ============================================================ */

(function () {
  'use strict';

  /* ── Tab Toggle ── */
  const tabBtns = document.querySelectorAll('.tab-toggle__btn');
  const fineRows = document.querySelectorAll('.fine-row');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      tabBtns.forEach(b => b.classList.remove('tab-toggle__btn--active'));
      this.classList.add('tab-toggle__btn--active');

      const filter = this.dataset.filter;
      fineRows.forEach(row => {
        const status = row.dataset.fineStatus;
        row.style.display = (filter === 'all' || status === filter) ? '' : 'none';
      });
    });
  });

  /* ── Select All ── */
  const selectAll = document.getElementById('selectAll');
  const rowChecks = document.querySelectorAll('.row-check');
  const bulkBar   = document.getElementById('bulkActionsBar');
  const selCount  = document.getElementById('selectedCount');

  function updateBulk() {
    const n = [...rowChecks].filter(c => c.checked).length;
    if (bulkBar)  bulkBar.hidden  = n === 0;
    if (selCount) selCount.textContent = n;
  }

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      const visible = [...rowChecks].filter(c => c.closest('tr').style.display !== 'none');
      visible.forEach(c => { c.checked = this.checked; c.closest('tr').classList.toggle('table-row--selected', this.checked); });
      updateBulk();
    });
  }

  rowChecks.forEach(cb => {
    cb.addEventListener('change', function () {
      this.closest('tr').classList.toggle('table-row--selected', this.checked);
      const all = [...rowChecks];
      if (selectAll) {
        selectAll.checked = all.every(c => c.checked);
        selectAll.indeterminate = all.some(c => c.checked) && !all.every(c => c.checked);
      }
      updateBulk();
    });
  });

  /* ── Bulk Mark Paid ── */
  const bulkMarkPaid = document.getElementById('bulkMarkPaidBtn');
  if (bulkMarkPaid) {
    bulkMarkPaid.addEventListener('click', function () {
      const ids = [...rowChecks].filter(c => c.checked).map(c => c.value);
      if (!ids.length) return;
      if (!confirm(`Mark ${ids.length} fine(s) as paid?`)) return;

      fetch('/transactions/fines/bulk-mark-paid/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showToast(`${ids.length} fine(s) marked as paid.`, 'success');
          setTimeout(() => window.location.reload(), 1000);
        } else {
          showToast(data.error || 'Error occurred.', 'error');
        }
      })
      .catch(() => showToast('Network error.', 'error'));
    });
  }

  /* ── Bulk Waive ── */
  const bulkWaive = document.getElementById('bulkWaiveBtn');
  if (bulkWaive) {
    bulkWaive.addEventListener('click', function () {
      const ids = [...rowChecks].filter(c => c.checked).map(c => c.value);
      if (!ids.length) return;
      if (!confirm(`Waive ${ids.length} fine(s)? This cannot be undone.`)) return;
      showToast(`Waiving ${ids.length} fine(s)…`, 'info');
    });
  }

  /* ── Mark Paid Modal ── */
  const markPaidModal   = document.getElementById('markPaidModal');
  const markPaidForm    = document.getElementById('markPaidForm');
  const markPaidFineId  = document.getElementById('markPaidFineId');
  const markPaidAmount  = document.getElementById('markPaidAmountDisplay');
  const closeMarkPaid   = document.getElementById('closeMarkPaidModal');
  const cancelMarkPaid  = document.getElementById('cancelMarkPaid');
  const markPaidBackdrop = document.getElementById('markPaidBackdrop');

  document.querySelectorAll('.action-btn--pay').forEach(btn => {
    btn.addEventListener('click', function () {
      const id     = this.dataset.id;
      const amount = this.dataset.amount;

      markPaidFineId.value = id;
      if (markPaidAmount) markPaidAmount.textContent = `₹${parseFloat(amount).toFixed(2)}`;
      if (markPaidForm)   markPaidForm.action = markPaidForm.action.replace(/\/\d+\/$/, `/${id}/`);

      openModal(markPaidModal);
    });
  });

  [closeMarkPaid, cancelMarkPaid, markPaidBackdrop].forEach(el => {
    el?.addEventListener('click', () => closeModal(markPaidModal));
  });

  /* ── Waive individual fine ── */
  document.querySelectorAll('.action-btn--waive').forEach(btn => {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      if (!confirm('Waive this fine? This action cannot be undone.')) return;

      this.disabled = true;
      this.textContent = 'Waiving…';

      fetch(`/transactions/fines/${id}/waive/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showToast('Fine waived successfully.', 'success');
          const row = this.closest('tr');
          row.style.opacity = '0.4';
          setTimeout(() => window.location.reload(), 900);
        } else {
          showToast(data.error || 'Error.', 'error');
          this.disabled = false;
          this.textContent = 'Waive';
        }
      })
      .catch(() => {
        showToast('Network error.', 'error');
        this.disabled = false;
        this.textContent = 'Waive';
      });
    });
  });

  /* ── Escape closes modal ── */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal(markPaidModal);
  });

  /* ── Animate summary tiles ── */
  document.querySelectorAll('.fine-summary-tile').forEach((tile, i) => {
    tile.style.opacity = '0';
    tile.style.transform = 'translateY(16px)';
    tile.style.transition = `opacity .3s ease ${i * 70}ms, transform .3s ease ${i * 70}ms`;
    requestAnimationFrame(() => { tile.style.opacity = '1'; tile.style.transform = 'translateY(0)'; });
  });

  /* ── Sort headers ── */
  document.querySelectorAll('.th-sortable').forEach(th => {
    th.addEventListener('click', function () {
      const col = this.dataset.sort;
      const url = new URL(window.location.href);
      const cur = url.searchParams.get('sort');
      url.searchParams.set('sort', cur === col ? '-' + col : col);
      window.location.href = url.toString();
    });
  });

  /* ── Form submit loader ── */
  markPaidForm?.addEventListener('submit', function () {
    const btn = this.querySelector('[type=submit]');
    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
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
