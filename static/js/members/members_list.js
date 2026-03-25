/**
 * members/members_list.js
 * ───────────────────────
 * All-members list page JavaScript.
 * Depends on: members.js (loaded before this file in the template).
 *
 * members.js already wires:
 *   - #memberSearch  → live table row filter
 *   - #resetFilters  → form reset + URL clear
 *   - #membersTable th[data-sortable] → column sort
 *   - .delete-member-btn → confirm + postAction() delete
 *
 * This file adds any list-page-specific behaviour.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // ── Row click → detail page (skip if user clicks an action button/link) ────
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    row.style.cursor = 'pointer';
    row.addEventListener('click', (e) => {
      // Don't navigate when clicking action icons
      if (e.target.closest('.table-actions')) return;
      const viewLink = row.querySelector('.action-icon.view');
      if (viewLink) window.location.href = viewLink.href;
    });
  });

  // ── Status badge colour refresh (in case CSS is delayed) ──────────────────
  // Already handled by CSS; no JS needed.

});
