/**
 * members/members_passout.js
 * ──────────────────────────
 * Passout members page — decoration only.
 * Depends on: members.js
 *
 * JS role here:
 *   ✓ Highlight rows where clearance badge is pending (decoration)
 *
 * members.js handles: search, sort, filter reset, badge colours, row click.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // Highlight rows with a pending clearance badge
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    if (row.querySelector('.status-badge.pending')) {
      row.style.borderLeft = '3px solid #f59e0b';
    }
  });

});
