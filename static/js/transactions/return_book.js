/* ============================================================
   return_book.js
   ============================================================ */

(function () {
  'use strict';

  const CIRCUMFERENCE = 213.63;

  /* ── DOM refs ── */
  const conditionOptions  = document.getElementById('conditionOptions');
  const damageChargeGroup = document.getElementById('damageChargeGroup');
  const lostChargeGroup   = document.getElementById('lostChargeGroup');
  const returnForm        = document.getElementById('returnForm');
  const confirmBtn        = document.getElementById('confirmReturnBtn');

  /* Hidden fields that actually submit */
  const damageHidden = document.getElementById('damageCharge');
  const lostHidden   = document.getElementById('lostCharge');

  /* Display labels */
  const damageAmountLabel = document.getElementById('damageChargeAmountLabel');
  const lostAmountLabel   = document.getElementById('lostChargeAmountLabel');

  /* Override rows */
  const damageOverrideBtn = document.getElementById('damageOverrideBtn');
  const damageOverrideRow = document.getElementById('damageOverrideRow');
  const damageOverrideInp = document.getElementById('damageChargeOverride');
  const damageResetBtn    = document.getElementById('damageResetBtn');

  const lostOverrideBtn   = document.getElementById('lostOverrideBtn');
  const lostOverrideRow   = document.getElementById('lostOverrideRow');
  const lostOverrideInp   = document.getElementById('lostChargeOverride');
  const lostResetBtn      = document.getElementById('lostResetBtn');

  /* Hidden field — carries updated book price to the view.
     Blank = no change to Book.price in the DB.              */
  const bookPriceOverrideField = document.getElementById('bookPriceOverride');

  /* Baseline overdue fine from sidebar meter */
  const baseFine = parseFloat(
    document.querySelector('.fine-meter__amount')
      ?.textContent?.replace('₹', '').trim() || '0'
  );

  /* ── Helpers ── */
  function bookPrice(hiddenEl) {
    return parseFloat(hiddenEl?.dataset.bookPrice || '0') || 0;
  }

  function fmt(n) {
    return '₹' + (parseFloat(n) || 0).toFixed(2);
  }

  /* ── Wire up override toggle for one pair ── */
  function wireOverride(overrideBtn, overrideRow, overrideInp, resetBtn, hiddenEl, amountLabel) {
    if (!overrideBtn) return;

    /* "different price?" clicked — hide button, show input row */
    overrideBtn.addEventListener('click', function () {
      overrideInp.value  = hiddenEl.value;
      overrideRow.hidden = false;
      overrideBtn.hidden = true;
      overrideInp.focus();
      overrideInp.select();
    });

    /* Typing — update label + hidden charge + bookPriceOverride */
    overrideInp.addEventListener('input', function () {
      const val = Math.max(0, parseFloat(overrideInp.value) || 0);
      hiddenEl.value          = val.toFixed(2);
      amountLabel.textContent = fmt(val);
      if (bookPriceOverrideField)
        bookPriceOverrideField.value = val > 0 ? val.toFixed(2) : '';
      const cond = document.querySelector('input[name="condition"]:checked')?.value || 'good';
      renderButton(cond);
      animateMeter(calcTotal(cond));
    });

    /* "reset" — revert to book price, hide row, show button */
    resetBtn.addEventListener('click', function () {
      const bp = bookPrice(hiddenEl);
      hiddenEl.value          = bp.toFixed(2);
      amountLabel.textContent = fmt(bp);
      overrideRow.hidden      = true;
      overrideBtn.hidden      = false;
      overrideInp.value       = '';
      if (bookPriceOverrideField)
        bookPriceOverrideField.value = '';
      const cond = document.querySelector('input[name="condition"]:checked')?.value || 'good';
      renderButton(cond);
      animateMeter(calcTotal(cond));
    });
  }

  wireOverride(damageOverrideBtn, damageOverrideRow, damageOverrideInp, damageResetBtn, damageHidden, damageAmountLabel);
  wireOverride(lostOverrideBtn,   lostOverrideRow,   lostOverrideInp,   lostResetBtn,   lostHidden,   lostAmountLabel);

  /* ── calcTotal ── */
  function calcTotal(condition) {
    let charge = 0;
    if (condition === 'damaged' && damageHidden)
      charge = Math.max(0, parseFloat(damageHidden.value) || 0);
    else if (condition === 'lost' && lostHidden)
      charge = Math.max(0, parseFloat(lostHidden.value) || 0);
    return baseFine + charge;
  }

  /* ── renderButton ── */
  function renderButton(condition) {
    if (!confirmBtn) return;
    const charge = calcTotal(condition) - baseFine;
    const badge  = charge > 0
      ? `<span class="btn-amount-badge">₹${charge.toFixed(2)}</span>`
      : '';

    if (condition === 'damaged') {
      confirmBtn.className = 'btn btn--pay btn--lg';
      confirmBtn.innerHTML = `
        <svg viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M10 3a7 7 0 1 1 0 14A7 7 0 0 1 10 3z" stroke="currentColor" stroke-width="1.75"/>
          <path d="M7 10l2 2 4-4" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Pay &amp; Mark Damaged ${badge}
        <svg viewBox="0 0 16 16" fill="none" width="13" height="13" style="margin-left:4px;opacity:.75">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;

    } else if (condition === 'lost') {
      confirmBtn.className = 'btn btn--pay btn--pay--lost btn--lg';
      confirmBtn.innerHTML = `
        <svg viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M10 3L3 17h14L10 3z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
          <path d="M10 9v4M10 15v.5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>
        </svg>
        Pay &amp; Mark Lost ${badge}
        <svg viewBox="0 0 16 16" fill="none" width="13" height="13" style="margin-left:4px;opacity:.75">
          <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;

    } else {
      confirmBtn.className = 'btn btn--success btn--lg';
      confirmBtn.innerHTML = `
        <svg viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M3 10l5 5 9-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Confirm Return`;
    }
  }

  /* ── updateUI ── */
  function updateUI() {
    const condition = document.querySelector('input[name="condition"]:checked')?.value || 'good';
    if (damageChargeGroup) damageChargeGroup.hidden = condition !== 'damaged';
    if (lostChargeGroup)   lostChargeGroup.hidden   = condition !== 'lost';
    renderButton(condition);
    animateMeter(calcTotal(condition));
  }

  if (conditionOptions) {
    conditionOptions.addEventListener('change', function (e) {
      if (e.target.type === 'radio') updateUI();
    });
  }

  /* ── Fine meter ── */
  function animateMeter(amount) {
    const fill = document.querySelector('.fine-meter__fill');
    if (!fill) return;
    const pct    = Math.min(100, ((amount || 0) / 500) * 100);
    const offset = CIRCUMFERENCE - (pct / 100) * CIRCUMFERENCE;
    fill.style.transition       = 'stroke-dashoffset 0.55s ease';
    fill.style.strokeDashoffset = offset;
  }

  setTimeout(() => animateMeter(baseFine), 200);

  /* ── Submit guard ── */
  if (returnForm) {
    returnForm.addEventListener('submit', function () {
      if (confirmBtn) {
        confirmBtn.disabled      = true;
        confirmBtn.style.opacity = '0.72';
        confirmBtn.innerHTML     = `
          <svg viewBox="0 0 20 20" fill="none" width="15" height="15"
               style="animation:spin .7s linear infinite;vertical-align:middle">
            <path d="M10 2a8 8 0 1 1-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg> Processing…`;
      }
    });
  }

  updateUI();

})();