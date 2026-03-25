/* ============================================================
   overdue_list.js
   ============================================================ */

(function () {
  'use strict';

  /* ── Dismiss Alert ── */
  const dismissAlert = document.getElementById('dismissAlert');
  const overdueAlert = document.querySelector('.overdue-alert');
  if (dismissAlert && overdueAlert) {
    dismissAlert.addEventListener('click', function () {
      overdueAlert.style.transition = 'opacity .2s ease, transform .2s ease, max-height .3s ease';
      overdueAlert.style.opacity = '0';
      overdueAlert.style.transform = 'translateY(-6px)';
      overdueAlert.style.maxHeight = overdueAlert.offsetHeight + 'px';
      requestAnimationFrame(() => {
        overdueAlert.style.maxHeight = '0';
        overdueAlert.style.marginBottom = '0';
        overdueAlert.style.paddingTop = '0';
        overdueAlert.style.paddingBottom = '0';
      });
      setTimeout(() => overdueAlert.remove(), 350);
    });
  }

  /* ── Select All ── */
  const selectAll = document.getElementById('selectAll');
  const rowChecks = document.querySelectorAll('.row-check');
  const bulkActionsBar = document.getElementById('bulkActionsBar');
  const selectedCount  = document.getElementById('selectedCount');

  function updateBulkBar() {
    const checked = [...rowChecks].filter(c => c.checked).length;
    if (bulkActionsBar) bulkActionsBar.hidden = checked === 0;
    if (selectedCount)  selectedCount.textContent = checked;
  }

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      rowChecks.forEach(cb => {
        cb.checked = this.checked;
        cb.closest('tr').classList.toggle('table-row--selected', this.checked);
      });
      updateBulkBar();
    });
  }

  rowChecks.forEach(cb => {
    cb.addEventListener('change', function () {
      this.closest('tr').classList.toggle('table-row--selected', this.checked);
      const allChecked = [...rowChecks].every(c => c.checked);
      const anyChecked = [...rowChecks].some(c => c.checked);
      if (selectAll) {
        selectAll.checked = allChecked;
        selectAll.indeterminate = anyChecked && !allChecked;
      }
      updateBulkBar();
    });
  });

  /* ── Send Reminder ── */
  document.querySelectorAll('.action-btn--notify').forEach(btn => {
    btn.addEventListener('click', function () {
      const id     = this.dataset.id;
      const member = this.dataset.member;
      const orig   = this.innerHTML;

      this.disabled = true;
      this.innerHTML = '✓ Sent';
      this.style.background = 'var(--success-bg)';
      this.style.color       = 'var(--success-text)';
      this.style.borderColor = 'var(--success-border)';

      fetch(`/transactions/${id}/send-reminder/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
      })
      .then(r => r.json())
      .then(data => {
        showToast(data.success ? `Reminder sent to ${member}` : (data.error || 'Failed to send'), data.success ? 'success' : 'error');
      })
      .catch(() => showToast('Network error.', 'error'))
      .finally(() => {
        setTimeout(() => {
          this.disabled = false;
          this.innerHTML = orig;
          this.style.background = '';
          this.style.color = '';
          this.style.borderColor = '';
        }, 3000);
      });
    });
  });

  /* ── Bulk Notify ── */
  const bulkNotifyBtn = document.getElementById('bulkNotifyBtn');
  if (bulkNotifyBtn) {
    bulkNotifyBtn.addEventListener('click', function () {
      const ids = [...rowChecks].filter(c => c.checked).map(c => c.value);
      if (!ids.length) return;
      showToast(`Sending reminders to ${ids.length} members…`, 'info');
    });
  }

  /* ── Bulk Mark Lost ── */
  const bulkMarkLostBtn = document.getElementById('bulkMarkLostBtn');
  if (bulkMarkLostBtn) {
    bulkMarkLostBtn.addEventListener('click', function () {
      const ids = [...rowChecks].filter(c => c.checked).map(c => c.value);
      if (!ids.length) return;
      if (!confirm(`Mark ${ids.length} transaction(s) as lost? This cannot be undone.`)) return;
      showToast(`Marking ${ids.length} transactions as lost…`, 'info');
    });
  }

  /* ── Sort click ── */
  document.querySelectorAll('.th-sortable').forEach(th => {
    th.addEventListener('click', function () {
      const url = new URL(window.location.href);
      url.searchParams.set('sort', '-overdue_days');
      window.location.href = url.toString();
    });
  });

  /* ── Animate overdue bars ── */
  setTimeout(() => {
    document.querySelectorAll('.overdue-bar__fill').forEach(bar => {
      const target = bar.style.width;
      bar.style.width = '0%';
      requestAnimationFrame(() => {
        bar.style.transition = 'width .6s cubic-bezier(.4,0,.2,1)';
        bar.style.width = target;
      });
    });
  }, 100);

  /* ── Helpers ── */
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
