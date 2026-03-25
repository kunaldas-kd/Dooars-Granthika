/* subscriptions/static/subscriptions/js/checkout.js */
document.addEventListener('DOMContentLoaded', () => {

  /* Payment method selection */
  const items  = document.querySelectorAll('.method-item');
  const hidden = document.getElementById('paymentMethodInput');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('method-active'));
      item.classList.add('method-active');
      const r = item.querySelector('input[type=radio]');
      if (r) { r.checked = true; if (hidden) hidden.value = r.value; }
    });
  });

  /* Loading state on submit */
  const form    = document.getElementById('checkoutForm');
  const btn     = document.getElementById('confirmBtn');
  const label   = document.getElementById('btnLabel');
  const spinner = document.getElementById('btnSpinner');
  if (form && btn) {
    form.addEventListener('submit', () => {
      btn.disabled = true;
      if (label)   label.classList.add('hidden');
      if (spinner) spinner.classList.remove('hidden');
    });
  }
});
