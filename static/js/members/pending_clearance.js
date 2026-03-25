/**
 * members/pending_clearance.js
 * ────────────────────────────
 * Pending clearance page — button UX only.
 * Depends on: members.js  (provides getCsrfToken, postAction, showToast)
 *
 * JS role:
 *   ✓ sendReminder()  – POST to send-reminder, show toast
 *   ✓ markCleared()   – POST to mark-cleared with Accept: application/json,
 *                        animate row out on success
 *   ✓ Highlight high-priority rows (decoration)
 */

'use strict';

/**
 * Send a reminder — POST, show response message as toast.
 * @param {number} memberId  (the Django pk integer)
 */
function sendReminder(memberId) {
  const url = `/members/${memberId}/send-reminder/`;
  const btn = document.querySelector(`[onclick="sendReminder(${memberId})"]`);

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  postAction(url)
    .then((resp) => {
      if (!resp.ok) throw new Error('Server error ' + resp.status);
      return resp.json();
    })
    .then((data) => showToast(data.message || 'Reminder sent!', 'success'))
    .catch(() => showToast('Failed to send reminder. Please try again.', 'error'))
    .finally(() => {
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-bell"></i>';
      }
    });
}

window.sendReminder = sendReminder;


/**
 * Mark a member as cleared via AJAX.
 * Sends Accept: application/json so the view returns JSON instead of a redirect.
 * On success the table row fades out.
 * @param {number} memberId  (the Django pk integer)
 */
function markCleared(memberId) {
  const url = `/members/${memberId}/mark-cleared/`;
  const btn = document.querySelector(`[onclick="markCleared(${memberId})"]`);
  const row = btn ? btn.closest('tr') : null;

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  fetch(url, {
    method:  'POST',
    headers: {
      'Accept':       'application/json',
      'X-CSRFToken':  getCsrfToken(),
    },
  })
    .then((resp) => resp.json().then((data) => ({ ok: resp.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.success) {
        showToast(data.message || 'Member cleared!', 'success');
        if (row) {
          row.style.transition = 'opacity 0.4s, transform 0.4s';
          row.style.opacity    = '0';
          row.style.transform  = 'translateX(20px)';
          setTimeout(() => {
            row.remove();
            _decrementCount();
          }, 420);
        }
      } else {
        showToast(data.message || 'Could not clear member.', 'error');
        if (btn) {
          btn.disabled  = false;
          btn.innerHTML = '<i class="fas fa-check"></i>';
        }
      }
    })
    .catch(() => {
      showToast('Network error. Please try again.', 'error');
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-check"></i>';
      }
    });
}

window.markCleared = markCleared;


/** Update the header count after a row is removed. */
function _decrementCount() {
  const tbody    = document.querySelector('#membersTable tbody');
  if (!tbody) return;
  const remaining = tbody.querySelectorAll('tr').length;

  // Update table header "Pending Clearance List (N)"
  const header = document.querySelector('.members-table-container .table-header h2');
  if (header) {
    header.textContent = header.textContent.replace(/\(\d+\)/, `(${remaining})`);
  }
}


document.addEventListener('DOMContentLoaded', () => {

  // Highlight rows with high-priority pending days
  document.querySelectorAll('#membersTable tbody tr').forEach((row) => {
    if (row.querySelector('.days-high')) {
      row.style.background = '#fff7ed';
    }
  });

});