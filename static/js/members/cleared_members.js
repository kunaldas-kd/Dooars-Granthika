/**
 * members/cleared_members.js
 * ──────────────────────────
 * Cleared members page — button UX only.
 * Depends on: members.js
 *
 * JS role here:
 *   ✓ Spinner on the download certificate button
 *   ✓ Trigger browser file download from the URL Django returns
 *
 * Certificate generation logic lives in the Django view.
 */

'use strict';

/**
 * Download the clearance certificate PDF for a member.
 * @param {number} memberId
 */
function downloadClearanceCertificate(memberId) {
  const url = `/members/${memberId}/clearance-certificate/`;
  const btn = document.querySelector(`[onclick="downloadClearanceCertificate(${memberId})"]`);

  if (btn) {
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  fetch(url, { method: 'GET' })
    .then((resp) => {
      if (!resp.ok) throw new Error(`Could not generate certificate (status ${resp.status}).`);
      return resp.blob();
    })
    .then((blob) => {
      const objectUrl = URL.createObjectURL(new Blob([blob], { type: blob.type || 'application/pdf' }));
      const a         = document.createElement('a');
      a.href          = objectUrl;
      a.download      = `clearance_certificate_${memberId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
      showToast('Certificate downloaded!', 'success');
    })
    .catch((err) => {
      console.error('downloadClearanceCertificate error:', err);
      showToast('Failed to download certificate. Please try again.', 'error');
    })
    .finally(() => {
      if (btn) {
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-download"></i>';
      }
    });
}

window.downloadClearanceCertificate = downloadClearanceCertificate;
