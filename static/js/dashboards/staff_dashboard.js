/* =============================================================
   staff_dashboard.js — Dark Luxury Glass Redesign
   static/js/dashboard/staff_dashboard.js
   ============================================================= */

(function () {
  'use strict';

  /* ── Staggered entrance animation ── */
  function initEntrances() {
    const targets = document.querySelectorAll(
      '.stat-card, .action-tile, .panel, .section'
    );
    targets.forEach(function (el, i) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(18px)';
      el.style.transition =
        'opacity 0.45s cubic-bezier(0.21,1.02,0.73,1) ' + (i * 0.04) + 's, ' +
        'transform 0.45s cubic-bezier(0.21,1.02,0.73,1) ' + (i * 0.04) + 's';

      // Trigger after a single paint
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
        });
      });
    });
  }

  /* ── Animated counters ── */
  function animateValue(el, target, duration) {
    var start = null;
    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var eased    = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      el.textContent = Math.round(eased * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function initCounters() {
    var values = document.querySelectorAll('.stat-card__value');
    if (!values.length) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          var n = parseInt(e.target.textContent.replace(/\D/g, ''), 10) || 0;
          if (n > 0) animateValue(e.target, n, 1200);
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });

    values.forEach(function (el) { io.observe(el); });
  }

  /* ── Weekly chart ── */
  function initChart() {
    var d = window.STAFF_DASHBOARD_DATA;
    if (!d || !d.weeklyChart.enabled) return;

    var canvas = document.getElementById('weeklyChart');
    if (!canvas) return;

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: d.weeklyChart.labels,
        datasets: [
          {
            label: 'Issued',
            data: d.weeklyChart.issued,
            backgroundColor: 'rgba(99,102,241,0.15)',
            borderColor: '#818cf8',
            borderWidth: 2,
            borderRadius: 8,
            borderSkipped: false,
            hoverBackgroundColor: 'rgba(99,102,241,0.28)',
          },
          {
            label: 'Returned',
            data: d.weeklyChart.returned,
            backgroundColor: 'rgba(16,185,129,0.12)',
            borderColor: '#34d399',
            borderWidth: 2,
            borderRadius: 8,
            borderSkipped: false,
            hoverBackgroundColor: 'rgba(16,185,129,0.22)',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        animation: {
          duration: 900,
          easing: 'easeOutQuart',
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              font: { size: 11, family: "'Instrument Sans', sans-serif", weight: '600' },
              color: '#4a5568',
              padding: 18,
              usePointStyle: true,
              pointStyleWidth: 8,
            },
          },
          tooltip: {
            backgroundColor: '#0d1220',
            titleColor: '#f0f4ff',
            bodyColor: '#8b9cbf',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10,
            titleFont: { family: "'Instrument Sans', sans-serif", weight: '700', size: 12 },
            bodyFont:  { family: "'Instrument Sans', sans-serif", size: 11 },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
            ticks: {
              color: '#4a5568',
              font: { size: 10, family: "'Fira Code', monospace" },
              stepSize: 1,
              padding: 8,
            },
            border: { display: false },
          },
          x: {
            grid: { display: false },
            ticks: {
              color: '#4a5568',
              font: { size: 11, family: "'Instrument Sans', sans-serif", weight: '500' },
              padding: 6,
            },
            border: { display: false },
          },
        },
      },
    });
  }

  /* ── Stat card micro-interaction: click ripple ── */
  function initRipples() {
    document.querySelectorAll('.stat-card').forEach(function (card) {
      card.addEventListener('click', function (e) {
        var ripple = document.createElement('span');
        var rect   = card.getBoundingClientRect();
        var size   = Math.max(rect.width, rect.height);

        ripple.style.cssText = [
          'position:absolute',
          'border-radius:50%',
          'pointer-events:none',
          'width:' + size + 'px',
          'height:' + size + 'px',
          'left:' + (e.clientX - rect.left - size / 2) + 'px',
          'top:' + (e.clientY - rect.top  - size / 2) + 'px',
          'background:rgba(255,255,255,0.06)',
          'transform:scale(0)',
          'animation:rippleOut 0.5s ease-out forwards',
        ].join(';');

        card.appendChild(ripple);
        setTimeout(function () { ripple.remove(); }, 500);
      });
    });

    // Inject keyframe once
    if (!document.getElementById('rippleKF')) {
      var style = document.createElement('style');
      style.id = 'rippleKF';
      style.textContent = '@keyframes rippleOut{to{transform:scale(2.5);opacity:0}}';
      document.head.appendChild(style);
    }
  }

  /* ── Init ── */
  function init() {
    initEntrances();
    initCounters();
    initChart();
    initRipples();
  }

  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();

})();