/* subscriptions/static/subscriptions/js/plans.js */
document.addEventListener('DOMContentLoaded', () => {

  /* Stagger card entrance (already done via CSS --i var, but
     pause until in view for cards below the fold) */
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.animationPlayState = 'running';
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll('.plan-card').forEach(c => {
    c.style.animationPlayState = 'paused';
    io.observe(c);
  });

  /* Ripple on CTA buttons */
  document.querySelectorAll('.btn-choose').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const r    = this.getBoundingClientRect();
      const rpl  = document.createElement('span');
      const size = Math.max(r.width, r.height);
      rpl.style.cssText = `
        position:absolute; border-radius:50%; pointer-events:none;
        width:${size}px; height:${size}px; transform:scale(0);
        left:${e.clientX - r.left - size/2}px;
        top:${e.clientY  - r.top  - size/2}px;
        background:rgba(255,255,255,.35);
        animation:rpl .5s linear;
      `;
      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(rpl);
      setTimeout(() => rpl.remove(), 600);
    });
  });

  if (!document.getElementById('rplKf')) {
    const s = document.createElement('style');
    s.id = 'rplKf';
    s.textContent = '@keyframes rpl{to{transform:scale(2.5);opacity:0}}';
    document.head.appendChild(s);
  }
});
