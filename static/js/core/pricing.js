// Dooars Granthika — Pricing Page

document.addEventListener('DOMContentLoaded', function () {
  initStaggeredIndexes();
  initPriceCounter();
  initFAQ();
  initCardTilt();
  initRippleButtons();
  addSparkleToBadge();
});

/* ── 1. Staggered CSS variable indexes ───────────────────────────────────── */
function initStaggeredIndexes() {
  document.querySelectorAll('.pricing-card').forEach((card, i) => {
    card.style.setProperty('--card-index', i);
    card.querySelectorAll('.pricing-features li').forEach((li, j) => {
      li.style.setProperty('--feature-index', j);
    });
  });

  document.querySelectorAll('.faq-item').forEach((item, i) => {
    item.style.setProperty('--faq-index', i);
  });
}

/* ── 2. Count-up animation for prices ────────────────────────────────────── */
function initPriceCounter() {
  const priceEls = document.querySelectorAll('.price .amount');
  if (!priceEls.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      observer.unobserve(entry.target);

      const el  = entry.target;
      const raw = el.textContent.trim();

      // Skip non-numeric values like "Free" or "Custom"
      const num = parseFloat(raw.replace(/[^0.00-9.00]/g, ''), 10);
      if (isNaN(num) || num === 0) return;

      animateCount(el, 0, num, 1200);
    });
  }, { threshold: 0.5 });

  priceEls.forEach(el => observer.observe(el));
}

function animateCount(el, from, to, duration) {
  const start = performance.now();

  function tick(now) {
    const progress    = Math.min((now - start) / duration, 1);
    const eased       = 1 - Math.pow(1 - progress, 4); // easeOutQuart
    const current     = Math.floor(from + (to - from) * eased);
    el.textContent    = current.toLocaleString('en-IN');
    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = to.toLocaleString('en-IN');
  }

  requestAnimationFrame(tick);
}

/* ── 3. FAQ accordion ────────────────────────────────────────────────────── */
function initFAQ() {
  document.querySelectorAll('.faq-item').forEach(item => {
    const answer = item.querySelector('p');
    if (!answer) return;

    // Prepare for smooth height transition
    answer.style.overflow   = 'hidden';
    answer.style.maxHeight  = answer.scrollHeight + 'px'; // visible by default
    answer.style.transition = 'max-height 0.35s ease, opacity 0.35s ease';

    item.style.cursor = 'pointer';

    item.addEventListener('click', () => {
      const isOpen = item.classList.contains('expanded');

      // Close all others
      document.querySelectorAll('.faq-item.expanded').forEach(open => {
        open.classList.remove('expanded');
        const p = open.querySelector('p');
        if (p) { p.style.maxHeight = '0'; p.style.opacity = '0'; }
      });

      if (!isOpen) {
        item.classList.add('expanded');
        answer.style.maxHeight = answer.scrollHeight + 'px';
        answer.style.opacity   = '1';
      }
    });

    // Start all open (collapse on first interaction is fine)
    item.classList.add('expanded');
    answer.style.opacity = '1';
  });
}

/* ── 4. 3D tilt on non-featured cards only ───────────────────────────────── */
function initCardTilt() {
  // Skip featured card — its CSS hover already does a vertical lift
  document.querySelectorAll('.pricing-card:not(.featured)').forEach(card => {
    card.addEventListener('mousemove', function (e) {
      if (window.innerWidth <= 768) return;

      const rect    = this.getBoundingClientRect();
      const x       = e.clientX - rect.left;
      const y       = e.clientY - rect.top;
      const rotateX = ((y - rect.height / 2) / 20).toFixed(2);
      const rotateY = ((rect.width  / 2 - x) / 20).toFixed(2);

      this.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-10px)`;
    });

    card.addEventListener('mouseleave', function () {
      this.style.transform = '';
    });
  });
}

/* ── 5. Ripple effect on CTA buttons ─────────────────────────────────────── */
function initRippleButtons() {
  document.querySelectorAll('.pricing-btn').forEach(btn => {
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';

    btn.addEventListener('click', function (e) {
      const rect   = this.getBoundingClientRect();
      const size   = Math.max(rect.width, rect.height);
      const x      = e.clientX - rect.left - size / 2;
      const y      = e.clientY - rect.top  - size / 2;

      const ripple = document.createElement('span');
      Object.assign(ripple.style, {
        position     : 'absolute',
        width        : size + 'px',
        height       : size + 'px',
        left         : x + 'px',
        top          : y + 'px',
        borderRadius : '50%',
        background   : 'rgba(255,255,255,0.45)',
        transform    : 'scale(0)',
        animation    : 'dg-ripple 0.55s ease-out forwards',
        pointerEvents: 'none',
      });

      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    });
  });
}

/* ── 6. Sparkle on featured badge ────────────────────────────────────────── */
function addSparkleToBadge() {
  const badge = document.querySelector('.featured-badge');
  if (!badge) return;

  badge.style.position = 'relative';
  badge.style.overflow = 'visible';

  setInterval(() => {
    const spark = document.createElement('span');
    spark.textContent = '✦';
    Object.assign(spark.style, {
      position      : 'absolute',
      top           : '50%',
      left          : Math.random() * 100 + '%',
      fontSize      : '10px',
      color         : 'rgba(255,255,255,0.85)',
      transform     : 'translate(-50%,-50%) scale(0)',
      animation     : 'dg-sparkle 0.9s ease-out forwards',
      pointerEvents : 'none',
    });
    badge.appendChild(spark);
    setTimeout(() => spark.remove(), 900);
  }, 1800);
}

/* ── Injected keyframes ───────────────────────────────────────────────────── */
const _style = document.createElement('style');
_style.textContent = `
  @keyframes dg-ripple {
    to { transform: scale(4); opacity: 0; }
  }
  @keyframes dg-sparkle {
    0%   { opacity: 1; transform: translate(-50%,-50%) scale(0); }
    50%  { opacity: 1; transform: translate(-50%,-50%) scale(1.2); }
    100% { opacity: 0; transform: translate(-50%,-70%) scale(0.5); }
  }
`;
document.head.appendChild(_style);