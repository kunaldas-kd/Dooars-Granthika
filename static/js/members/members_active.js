/**
 * members/members_active.js
 * ─────────────────────────
 * Active members page JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * members.js handles: search, table sort, filter reset, delete.
 * This file adds any active-page-specific behaviour.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // ── Row click → detail page ───────────────────────────────────────────────
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', (e) => {
      if (e.target.closest('.table-actions')) return;
      const viewLink = row.querySelector('.action-icon.view');
      if (viewLink) window.location.href = viewLink.href;
    });
  });

});
