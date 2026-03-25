/**
 * members/member_detail.js
 * ────────────────────────
 * Member detail page — decoration and button UX only.
 * Depends on: members.js  (loaded first — provides initDeleteButtons, showToast)
 *
 * JS role here:
 *   ✓ Click member ID → copy to clipboard
 *   ✓ Highlight overdue transaction rows
 *   ✓ Smooth-scroll to transactions section
 *
 * Delete button (.delete-member-btn) is wired by initDeleteButtons() in
 * members.js — no duplicate handler needed here.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  // ── Copy member ID to clipboard on click ──────────────────────────────────
  const memberIdEl = document.querySelector('.value-mono');
  if (memberIdEl) {
    memberIdEl.style.cursor = 'pointer';
    memberIdEl.title        = 'Click to copy';
    memberIdEl.addEventListener('click', () => {
      navigator.clipboard?.writeText(memberIdEl.textContent.trim())
        .then(() => showToast('Member ID copied!', 'info'))
        .catch(() => showToast('Could not copy.', 'error'));
    });
  }


  // ── Highlight overdue transaction rows ────────────────────────────────────
  document.querySelectorAll('.members-table tbody tr').forEach((row) => {
    const badge = row.querySelector('.status-badge');
    if (badge && badge.textContent.trim().toLowerCase().includes('overdue')) {
      row.style.background = '#fff7ed';
    }
  });


  // ── Smooth-scroll to transactions section ─────────────────────────────────
  document.querySelector('a[href="#transactions"]')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelector('.members-table-container')?.scrollIntoView({ behavior: 'smooth' });
  });

});