/**
 * members/members_inactive.js
 * ───────────────────────────
 * Inactive members page — button UX only.
 * Depends on: members.js  (getCsrfToken, showToast)
 *
 * JS role here:
 *   ✓ reactivateMember(pk) — POST to reactivate URL, show toast, navigate
 *
 * Called directly from the template:
 *   <button onclick="reactivateMember({{ member.id }})">
 */

'use strict';

/**
 * Reactivate a member via AJAX.
 * On success: fades the row out, then navigates to the member detail page.
 * On failure: shows an error toast and re-enables the button.
 *
 * @param {number} pk  Django member primary key
 */
function reactivateMember(pk) {
  const url = `/members/${pk}/reactivate/`;
  const btn = document.querySelector(`[onclick="reactivateMember(${pk})"]`);

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  fetch(url, {
    method:  'POST',
    headers: {
      'Accept':      'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
  })
    .then((resp) => resp.json().then((data) => ({ ok: resp.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.success) {
        showToast(data.message || 'Member reactivated!', 'success');
        const row = btn ? btn.closest('tr') : null;
        if (row) {
          row.style.transition = 'opacity 0.4s';
          row.style.opacity    = '0';
          setTimeout(() => {
            row.remove();
            if (data.redirect_url) {
              setTimeout(() => { window.location.href = data.redirect_url; }, 300);
            }
          }, 420);
        } else if (data.redirect_url) {
          setTimeout(() => { window.location.href = data.redirect_url; }, 800);
        }
      } else {
        showToast(data.message || 'Could not reactivate member.', 'error');
        if (btn) {
          btn.disabled  = false;
          btn.innerHTML = '<i class="fas fa-redo"></i>';
        }
      }
    })
    .catch(() => {
      showToast('Network error. Please try again.', 'error');
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-redo"></i>';
      }
    });
}

window.reactivateMember = reactivateMember;