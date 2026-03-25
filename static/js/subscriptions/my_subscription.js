/* subscriptions/static/subscriptions/js/my_subscription.js */
document.addEventListener('DOMContentLoaded', () => {

  /* ── Days ring ─────────────────────────────────────────────── */
  const ring = document.getElementById('daysRing');
  const prog = document.getElementById('ringProg');
  if (ring && prog) {
    const days  = parseInt(ring.dataset.days, 10)  || 0;
    const total = parseInt(ring.dataset.total, 10) || 30;
    const pct   = Math.min(days / total, 1);
    const circ  = 2 * Math.PI * 34; // r=34
    const offset = circ * (1 - pct);
    requestAnimationFrame(() => {
      setTimeout(() => { prog.style.strokeDashoffset = offset; }, 150);
    });
  }

  /* ── Usage meters ──────────────────────────────────────────── */
  const fills = document.querySelectorAll('.meter-fill');
  const pcts  = document.querySelectorAll('.meter-pct');
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      fills.forEach((fill, i) => {
        const val = parseFloat(fill.style.getPropertyValue('--val')) || 0;
        const max = parseFloat(fill.style.getPropertyValue('--max')) || 1;
        const pct = Math.min(val / max * 100, 100);
        fill.style.width = pct + '%';
        if (pcts[i]) {
          // count-up
          let start = 0;
          const step = pct / 30;
          const t = setInterval(() => {
            start = Math.min(start + step, pct);
            pcts[i].textContent = Math.round(start) + '%';
            if (start >= pct) clearInterval(t);
          }, 30);
        }
      });
      io.disconnect();
    });
  }, { threshold: 0.2 });

  const metersSection = document.querySelector('.usage-meters');
  if (metersSection) io.observe(metersSection);
  else fills.forEach(f => { f.style.width = '0%'; }); // init hidden

  /* ── Payment rows stagger ──────────────────────────────────── */
  document.querySelectorAll('.pay-row').forEach((row, i) => {
    row.style.opacity = '0';
    row.style.transform = 'translateX(-8px)';
    row.style.transition = `opacity .3s ${i*50}ms, transform .3s ${i*50}ms`;
    setTimeout(() => {
      row.style.opacity = '1';
      row.style.transform = 'none';
    }, 200 + i * 50);
  });

});
