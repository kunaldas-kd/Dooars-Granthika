/* ============================================================
   transaction_list.js
   ============================================================ */

(function () {
  'use strict';

  /* ── Select All ── */
  const selectAll = document.getElementById('selectAll');
  const rowChecks = document.querySelectorAll('.row-check');

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      rowChecks.forEach(cb => {
        cb.checked = this.checked;
        cb.closest('tr').classList.toggle('table-row--selected', this.checked);
      });
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
    });
  });

  /* ── Sort ── */
  const sortableThs = document.querySelectorAll('.th-sortable');
  sortableThs.forEach(th => {
    th.addEventListener('click', function () {
      const col = this.dataset.sort;
      const url = new URL(window.location.href);
      const current = url.searchParams.get('sort');
      url.searchParams.set('sort', current === col ? '-' + col : col);
      window.location.href = url.toString();
    });
  });

  /* ── Search Clear ── */
  const clearSearch = document.getElementById('clearSearch');
  if (clearSearch) {
    clearSearch.addEventListener('click', function () {
      const url = new URL(window.location.href);
      url.searchParams.delete('q');
      window.location.href = url.toString();
    });
  }

  /* ── Per Page ── */
  const perPageSelect = document.getElementById('perPageSelect');
  if (perPageSelect) {
    perPageSelect.addEventListener('change', function () {
      const url = new URL(window.location.href);
      url.searchParams.set('per_page', this.value);
      url.searchParams.set('page', '1');
      window.location.href = url.toString();
    });
  }

  /* ── Auto-submit filter on status change ── */
  const statusFilter = document.getElementById('statusFilter');
  if (statusFilter) {
    statusFilter.addEventListener('change', function () {
      document.getElementById('filterForm').submit();
    });
  }

  /* ── Row highlight on hover (already CSS, add keyboard focus) ── */
  const tableRows = document.querySelectorAll('.data-table tbody tr');
  tableRows.forEach(row => {
    row.setAttribute('tabindex', '0');
    row.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        const viewLink = this.querySelector('.action-btn--view');
        if (viewLink) viewLink.click();
      }
    });
  });

  /* ── Export ── */
  const exportBtn = document.getElementById('exportBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', function () {
      const url = new URL(window.location.href);
      url.searchParams.set('export', 'csv');
      window.location.href = url.toString();
    });
  }

  /* ── Animate rows in ── */
  const rows = document.querySelectorAll('.data-table tbody tr');
  rows.forEach((row, i) => {
    row.style.opacity = '0';
    row.style.transform = 'translateY(8px)';
    row.style.transition = `opacity .2s ease ${i * 30}ms, transform .2s ease ${i * 30}ms`;
    requestAnimationFrame(() => {
      row.style.opacity = '1';
      row.style.transform = 'translateY(0)';
    });
  });

})();