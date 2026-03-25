/* ============================================================
   transaction_detail.js
   ============================================================ */

(function () {
  'use strict';

  /* ─────────────────────────────────────────────────────────
     Toast Notification
  ───────────────────────────────────────────────────────── */
  function showToast(message, type) {
    type = type || 'info';
    var toast = document.createElement('div');
    toast.textContent = message;
    Object.assign(toast.style, {
      position:     'fixed',
      bottom:       '24px',
      right:        '24px',
      padding:      '12px 20px',
      borderRadius: '10px',
      fontFamily:   "'DM Sans', sans-serif",
      fontSize:     '13.5px',
      fontWeight:   '500',
      color:        '#fff',
      background:   type === 'success' ? '#16a34a'
                  : type === 'error'   ? '#b91c1c'
                  :                      '#2563eb',
      boxShadow:    '0 8px 24px rgba(15,34,64,.2)',
      zIndex:       '9999',
      opacity:      '0',
      transform:    'translateY(12px)',
      transition:   'opacity .2s ease, transform .2s ease',
    });
    document.body.appendChild(toast);
    requestAnimationFrame(function () {
      toast.style.opacity   = '1';
      toast.style.transform = 'translateY(0)';
    });
    setTimeout(function () {
      toast.style.opacity   = '0';
      toast.style.transform = 'translateY(12px)';
      setTimeout(function () { toast.remove(); }, 250);
    }, 3200);
  }

  /* ─────────────────────────────────────────────────────────
     CSRF helper
  ───────────────────────────────────────────────────────── */
  function getCsrf() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  /* ─────────────────────────────────────────────────────────
     Renew Loan via AJAX (stays on page, shows toast result)
  ───────────────────────────────────────────────────────── */
  var renewForm = document.querySelector('form[action*="/renew/"]');
  if (renewForm) {
    var renewBtn     = renewForm.querySelector('[type=submit]');
    var renewBtnHTML = renewBtn ? renewBtn.innerHTML : '';

    renewForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (renewBtn) { renewBtn.disabled = true; renewBtn.innerHTML = 'Renewing&hellip;'; }

      fetch(renewForm.action + '?format=json', {
        method:  'POST',
        headers: { 'X-CSRFToken': getCsrf() },
      })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          showToast(data.message || 'Loan renewed successfully.', 'success');
          setTimeout(function () { window.location.reload(); }, 1800);
        } else {
          showToast(data.error || 'Could not renew loan.', 'error');
          if (renewBtn) { renewBtn.disabled = false; renewBtn.innerHTML = renewBtnHTML; }
        }
      })
      .catch(function () {
        showToast('Network error \u2014 please try again.', 'error');
        if (renewBtn) { renewBtn.disabled = false; renewBtn.innerHTML = renewBtnHTML; }
      });
    });
  }

  /* ─────────────────────────────────────────────────────────
     Book Cover Upload  (click cover → file picker → POST blob)
  ───────────────────────────────────────────────────────── */
  var coverInput    = document.getElementById('coverUploadInput');
  var coverImg      = document.getElementById('bookCoverImg');
  var coverFallback = document.getElementById('bookCoverFallback');

  if (coverInput) {
    coverInput.addEventListener('change', function () {
      var file = coverInput.files[0];
      if (!file) return;

      var uploadUrl = coverInput.dataset.uploadUrl;

      // Instant local preview before upload completes
      var reader = new FileReader();
      reader.onload = function (e) {
        coverImg.src = e.target.result;
        coverImg.style.display = 'block';
        if (coverFallback) coverFallback.style.display = 'none';
      };
      reader.readAsDataURL(file);

      var fd = new FormData();
      fd.append('cover', file);
      fd.append('csrfmiddlewaretoken', getCsrf());

      fetch(uploadUrl, { method: 'POST', body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            showToast('Cover image saved.', 'success');
            // Bust cache so subsequent page loads show the new image
            var base = coverImg.src.split('?')[0];
            coverImg.src = base + '?v=' + Date.now();
          } else {
            showToast(data.error || 'Upload failed.', 'error');
          }
        })
        .catch(function () {
          showToast('Network error \u2014 upload failed.', 'error');
        });
    });
  }

  /* ─────────────────────────────────────────────────────────
     Print cleanup
  ───────────────────────────────────────────────────────── */
  window.addEventListener('beforeprint', function () {
    document.querySelectorAll('.page-header__actions, .info-card__link').forEach(function (el) {
      el.dataset._pdisplay = el.style.display;
      el.style.display = 'none';
    });
  });
  window.addEventListener('afterprint', function () {
    document.querySelectorAll('.page-header__actions, .info-card__link').forEach(function (el) {
      el.style.display = el.dataset._pdisplay || '';
    });
  });

  /* ─────────────────────────────────────────────────────────
     Animate timeline steps (staggered slide-in from left)
  ───────────────────────────────────────────────────────── */
  document.querySelectorAll('.timeline-step').forEach(function (step, i) {
    step.style.opacity   = '0';
    step.style.transform = 'translateX(-10px)';
    step.style.transition =
      'opacity .25s ease ' + (i * 120) + 'ms, transform .25s ease ' + (i * 120) + 'ms';
    requestAnimationFrame(function () {
      step.style.opacity   = '1';
      step.style.transform = 'translateX(0)';
    });
  });

  /* ─────────────────────────────────────────────────────────
     Animate cards (staggered fade-up)
  ───────────────────────────────────────────────────────── */
  document.querySelectorAll('.info-card, .timeline-card, .fine-card, .table-card').forEach(function (card, i) {
    card.style.opacity   = '0';
    card.style.transform = 'translateY(14px)';
    card.style.transition =
      'opacity .3s ease ' + (i * 70) + 'ms, transform .3s ease ' + (i * 70) + 'ms';
    requestAnimationFrame(function () {
      card.style.opacity   = '1';
      card.style.transform = 'translateY(0)';
    });
  });

  /* ─────────────────────────────────────────────────────────
     Table row hover highlight
  ───────────────────────────────────────────────────────── */
  document.querySelectorAll('.table-row').forEach(function (row) {
    row.addEventListener('mouseenter', function () { row.classList.add('table-row--hovered'); });
    row.addEventListener('mouseleave', function () { row.classList.remove('table-row--hovered'); });
  });

})();