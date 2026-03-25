/**
 * profit_loss.js
 * File: static/js/finance/profit_loss.js
 */
(function () {
  'use strict';

  const dataEl = document.getElementById('pl-data');
  if (!dataEl) return;

  let d;
  try { d = JSON.parse(dataEl.textContent); }
  catch (e) { console.error('[profit_loss] JSON parse error:', e); return; }

  Chart.defaults.font.family = "'DM Sans', sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = '#94a3b8';

  const TOOLTIP = {
    backgroundColor: '#1e293b',
    titleColor:      '#e2e8f0',
    bodyColor:       '#94a3b8',
    padding:         10,
    cornerRadius:    8,
  };

  function rupee(v) {
    return '\u20B9' + Number(v).toLocaleString('en-IN');
  }

  function shortRupee(v) {
    if (v >= 100000) return '\u20B9' + (v / 100000).toFixed(1) + 'L';
    if (v >= 1000)   return '\u20B9' + (v / 1000).toFixed(0)   + 'k';
    return '\u20B9' + v;
  }

  const canvas = document.getElementById('plChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.labels,
      datasets: [
        {
          label:           'Income',
          data:            d.income,
          borderColor:     '#10b981',
          backgroundColor: 'rgba(16,185,129,.10)',
          borderWidth:     2.5,
          pointBackgroundColor: '#10b981',
          pointRadius:     4,
          pointHoverRadius: 6,
          tension:         0.35,
          fill:            true,
        },
        {
          label:           'Expenses',
          data:            d.expenses,
          borderColor:     '#ef4444',
          backgroundColor: 'rgba(239,68,68,.08)',
          borderWidth:     2.5,
          pointBackgroundColor: '#ef4444',
          pointRadius:     4,
          pointHoverRadius: 6,
          tension:         0.35,
          fill:            true,
        },
      ],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display:  true,
          position: 'top',
          labels: {
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 18,
            font: { size: 12 },
          },
        },
        tooltip: {
          ...TOOLTIP,
          callbacks: {
            label: ctx => '  ' + ctx.dataset.label + ':  ' + rupee(ctx.parsed.y),
          },
        },
      },
      scales: {
        x: {
          grid:   { display: false },
          border: { display: false },
          ticks:  { maxRotation: 40, font: { size: 11 } },
        },
        y: {
          grid:   { color: '#f1f5f9' },
          border: { display: false, dash: [4, 4] },
          ticks:  { callback: shortRupee },
        },
      },
    },
  });

})();
