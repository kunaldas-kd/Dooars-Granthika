/**
 * finance_reports.js
 * File: static/js/finance/finance_reports.js
 *
 * Reads data from the <script id="fin-data" type="application/json"> tag
 * injected by the Django template, then builds all Chart.js charts.
 * No Django template syntax here — pure browser JavaScript.
 */

(function () {
  'use strict';

  /* ── 1. Read data from the JSON bridge tag ──────────────────────────────── */
  const dataEl = document.getElementById('fin-data');
  if (!dataEl) {
    console.warn('[finance_reports] #fin-data element not found — charts skipped.');
    return;
  }

  let finData;
  try {
    finData = JSON.parse(dataEl.textContent);
  } catch (e) {
    console.error('[finance_reports] Failed to parse #fin-data JSON:', e);
    return;
  }

  const {
    monthlyLabels = [],
    monthlyData   = [],
    totalIncome   = 0,
    totalExpenses = 0,
    pendingFines  = 0,
  } = finData;


  /* ── 2. Chart.js shared defaults ───────────────────────────────────────── */
  Chart.defaults.font.family = "'DM Sans', sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = '#94a3b8';

  const TOOLTIP_DEFAULTS = {
    backgroundColor: '#1e293b',
    titleColor:      '#e2e8f0',
    bodyColor:       '#94a3b8',
    padding:         10,
    cornerRadius:    8,
  };

  /** Format a number as Indian-locale rupee string */
  function rupee(val) {
    return '\u20B9' + Number(val).toLocaleString('en-IN');
  }

  /** Shorten large numbers for axis labels */
  function shortRupee(val) {
    if (val >= 100000) return '\u20B9' + (val / 100000).toFixed(1) + 'L';
    if (val >= 1000)   return '\u20B9' + (val / 1000).toFixed(0)   + 'k';
    return '\u20B9' + val;
  }


  /* ── 3. Monthly Collection Bar Chart ───────────────────────────────────── */
  const monthlyCanvas = document.getElementById('monthlyChart');
  if (monthlyCanvas) {
    const ctx  = monthlyCanvas.getContext('2d');
    const last = monthlyData.length - 1;

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: monthlyLabels,
        datasets: [{
          label: 'Income',
          data:  monthlyData,
          /* Highlight the most recent month in solid blue */
          backgroundColor: monthlyData.map((_, i) =>
            i === last ? '#2563eb' : 'rgba(37,99,235,.50)'
          ),
          borderRadius:    6,
          borderSkipped:   false,
          maxBarThickness: 38,
        }],
      },
      options: {
        responsive:          true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            ...TOOLTIP_DEFAULTS,
            callbacks: {
              title: items => items[0].label,
              label: item  => '  ' + rupee(item.parsed.y),
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
  }


  /* ── 4. Period Breakdown Donut ──────────────────────────────────────────── */
  const donutCanvas = document.getElementById('breakdownChart');
  if (donutCanvas) {
    const ctx     = donutCanvas.getContext('2d');
    const hasData = (totalIncome + totalExpenses + pendingFines) > 0;

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Income', 'Expenses', 'Pending Fines'],
        datasets: [{
          data: hasData
            ? [totalIncome, totalExpenses, pendingFines]
            : [1, 0, 0],
          backgroundColor: hasData
            ? ['#10b981', '#ef4444', '#f59e0b']
            : ['#e2e8f0', '#e2e8f0', '#e2e8f0'],
          borderWidth:  3,
          borderColor:  '#ffffff',
          hoverOffset:  6,
        }],
      },
      options: {
        responsive:          true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: hasData,
            ...TOOLTIP_DEFAULTS,
            callbacks: {
              label: item => '  ' + rupee(item.parsed),
            },
          },
        },
      },
    });
  }

})();
