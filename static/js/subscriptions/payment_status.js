/* subscriptions/static/subscriptions/js/payment_status.js */
document.addEventListener('DOMContentLoaded', () => {

  const card = document.getElementById('psCard');
  if (!card) return;

  /* ── Confetti on success ────────────────────────────────── */
  if (card.classList.contains('ps-success')) {
    const wrap   = document.getElementById('confettiWrap');
    const colors = ['#1d4ed8','#16a34a','#d97706','#7c3aed','#ec4899','#ea580c'];
    if (wrap) {
      for (let i = 0; i < 55; i++) {
        const p = document.createElement('div');
        p.className = 'confetti-p';
        const size = 6 + Math.random() * 8;
        p.style.cssText = `
          left: ${Math.random() * 100}%;
          width: ${size}px; height: ${size}px;
          background: ${colors[i % colors.length]};
          border-radius: ${Math.random() > .5 ? '50%' : '2px'};
          animation-duration: ${1.2 + Math.random() * 1.4}s;
          animation-delay: ${Math.random() * .8}s;
        `;
        wrap.appendChild(p);
      }
      setTimeout(() => wrap.innerHTML = '', 4000);
    }
  }

  /* ── Auto-refresh countdown for pending ─────────────────── */
  const refreshNote = document.getElementById('refreshNote');
  if (card.classList.contains('ps-pending') && refreshNote) {
    let n = 10;
    const t = setInterval(() => {
      n--;
      refreshNote.textContent = `Refreshing in ${n}s…`;
      if (n <= 0) { clearInterval(t); window.location.reload(); }
    }, 1000);
  }

  /* ── Copy payment ID on click ───────────────────────────── */
  const copyId = document.getElementById('copyId');
  if (copyId) {
    copyId.addEventListener('click', () => {
      navigator.clipboard.writeText(copyId.textContent.trim()).then(() => {
        const orig = copyId.textContent;
        copyId.textContent = 'Copied!';
        copyId.style.color = '#16a34a';
        setTimeout(() => { copyId.textContent = orig; copyId.style.color = ''; }, 1800);
      });
    });
  }
});
