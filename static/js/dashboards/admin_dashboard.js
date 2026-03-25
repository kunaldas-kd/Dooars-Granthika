// ============================================================
// admin_dashboard.js - Enhanced Dashboard JavaScript
// Charts, animations, search, and interactive features
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
  
  // ═══════════════════════════════════════════════
  // 1. CHART CONFIGURATIONS & INITIALIZATION
  // ═══════════════════════════════════════════════
  
  // Blue-White Color Palette
  const colors = {
    primary: '#3b82f6',
    primaryLight: '#60a5fa',
    primaryDark: '#2563eb',
    success: '#10b981',
    successLight: '#34d399',
    warning: '#f59e0b',
    warningLight: '#fbbf24',
    danger: '#ef4444',
    dangerLight: '#f87171',
    purple: '#8b5cf6',
    purpleLight: '#a78bfa',
    info: '#3b82f6',
    infoLight: '#60a5fa',
  };

  // Enhanced Chart.js Default Configuration
  Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  Chart.defaults.color = '#6b7280';
  Chart.defaults.borderColor = '#e5e7eb';
  
  // ───────────────────────────────────────────
  // Loans Trend Chart (Line Chart)
  // ───────────────────────────────────────────
  const loansChartCanvas = document.getElementById('loansChart');
  if (loansChartCanvas && monthlyLoanLabels && monthlyLoanData) {
    const ctx = loansChartCanvas.getContext('2d');
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.15)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.01)');
    
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: monthlyLoanLabels,
        datasets: [{
          label: 'Books Issued',
          data: monthlyLoanData,
          borderColor: colors.primary,
          backgroundColor: gradient,
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: colors.primary,
          pointBorderWidth: 3,
          pointHoverBackgroundColor: colors.primary,
          pointHoverBorderColor: '#ffffff',
          pointHoverBorderWidth: 3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: 'rgba(30, 41, 59, 0.95)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            borderColor: colors.primary,
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            cornerRadius: 10,
            displayColors: false,
            callbacks: {
              label: function(context) {
                return `${context.parsed.y} books issued`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0,
              font: {
                size: 12
              },
              color: '#6b7280'
            },
            grid: {
              color: 'rgba(229, 231, 235, 0.6)',
              drawBorder: false
            }
          },
          x: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              font: {
                size: 12
              },
              color: '#6b7280'
            }
          }
        },
        interaction: {
          intersect: false,
          mode: 'index'
        }
      }
    });
  }

  // ───────────────────────────────────────────
  // Category Distribution Chart (Doughnut Chart)
  // ───────────────────────────────────────────
  const categoryChartCanvas = document.getElementById('categoryChart');
  if (categoryChartCanvas && categoryLabels && categoryData) {
    const ctx = categoryChartCanvas.getContext('2d');
    
    // Generate vibrant colors for categories
    const categoryColors = [
      colors.primary,
      colors.success,
      colors.warning,
      colors.purple,
      colors.info,
      colors.danger,
      colors.primaryLight,
      colors.successLight,
    ];
    
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: categoryLabels,
        datasets: [{
          data: categoryData,
          backgroundColor: categoryColors,
          borderColor: '#ffffff',
          borderWidth: 3,
          hoverOffset: 15,
          hoverBorderColor: '#ffffff',
          hoverBorderWidth: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              padding: 16,
              font: {
                size: 13,
                weight: '500'
              },
              color: '#6b7280',
              usePointStyle: true,
              pointStyle: 'circle',
              generateLabels: function(chart) {
                const data = chart.data;
                if (data.labels.length && data.datasets.length) {
                  return data.labels.map((label, i) => {
                    const value = data.datasets[0].data[i];
                    const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                    const percentage = ((value / total) * 100).toFixed(1);
                    
                    return {
                      text: `${label} (${percentage}%)`,
                      fillStyle: data.datasets[0].backgroundColor[i],
                      hidden: false,
                      index: i
                    };
                  });
                }
                return [];
              }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(30, 41, 59, 0.95)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            borderColor: colors.primary,
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            cornerRadius: 10,
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} books (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  // ═══════════════════════════════════════════════
  // 2. GLOBAL SEARCH FUNCTIONALITY
  // ═══════════════════════════════════════════════
  
  const searchInput = document.getElementById('globalSearch');
  const searchClear = document.getElementById('searchClear');
  
  if (searchInput && searchClear) {
    // Clear button functionality
    searchClear.addEventListener('click', function() {
      searchInput.value = '';
      searchInput.focus();
      performSearch('');
    });
    
    // Search on input
    searchInput.addEventListener('input', function(e) {
      const query = e.target.value.trim();
      performSearch(query);
    });
    
    // Search on Enter key
    searchInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const query = e.target.value.trim();
        if (query.length > 0) {
          // Redirect to search results page
          window.location.href = `/search/?q=${encodeURIComponent(query)}`;
        }
      }
    });
  }
  
  function performSearch(query) {
    if (query.length === 0) {
      // Reset any filtered views
      return;
    }
    
    if (query.length < 2) {
      return; // Wait for at least 2 characters
    }
    
    console.log('Searching for:', query);
    // Implement your search logic here
    // Example: Fetch search results from API
  }

  // ═══════════════════════════════════════════════
  // 3. KPI CARD ANIMATIONS
  // ═══════════════════════════════════════════════
  
  const kpiCards = document.querySelectorAll('.kpi-card');
  
  kpiCards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      card.style.transition = 'all 0.5s ease-out';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, index * 100);
  });

  // ═══════════════════════════════════════════════
  // 4. NOTIFICATION SCROLL PAUSE ON HOVER
  // ═══════════════════════════════════════════════
  
  const notificationsList = document.getElementById('notificationsList');
  
  if (notificationsList) {
    notificationsList.addEventListener('mouseenter', function() {
      this.style.animationPlayState = 'paused';
    });
    
    notificationsList.addEventListener('mouseleave', function() {
      this.style.animationPlayState = 'running';
    });
  }

  // ═══════════════════════════════════════════════
  // 5. QUICK ACTION BUTTON EFFECTS
  // ═══════════════════════════════════════════════
  
  const actionButtons = document.querySelectorAll('.action-btn');
  
  actionButtons.forEach(button => {
    button.addEventListener('mouseenter', function(e) {
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      
      this.appendChild(ripple);
      
      setTimeout(() => ripple.remove(), 600);
    });
  });

  // ═══════════════════════════════════════════════
  // 6. TABLE SORTING
  // ═══════════════════════════════════════════════
  
  const tableHeaders = document.querySelectorAll('.overdue-table th');
  
  tableHeaders.forEach((header, index) => {
    header.style.cursor = 'pointer';
    header.style.userSelect = 'none';
    
    header.addEventListener('click', function() {
      sortTable(index);
    });
  });
  
  function sortTable(columnIndex) {
    const table = document.querySelector('.overdue-table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Determine sort direction
    const currentSort = table.dataset.sortColumn;
    const currentDirection = table.dataset.sortDirection || 'asc';
    
    let direction = 'asc';
    if (currentSort === String(columnIndex)) {
      direction = currentDirection === 'asc' ? 'desc' : 'asc';
    }
    
    // Sort rows
    rows.sort((a, b) => {
      const aValue = a.cells[columnIndex].textContent.trim();
      const bValue = b.cells[columnIndex].textContent.trim();
      
      // Try to parse as numbers
      const aNum = parseFloat(aValue.replace(/[^\d.-]/g, ''));
      const bNum = parseFloat(bValue.replace(/[^\d.-]/g, ''));
      
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return direction === 'asc' ? aNum - bNum : bNum - aNum;
      }
      
      // String comparison
      return direction === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
    
    // Update sort indicators
    table.dataset.sortColumn = columnIndex;
    table.dataset.sortDirection = direction;
    
    // Visual feedback
    tableHeaders.forEach((th, idx) => {
      th.classList.remove('sorted-asc', 'sorted-desc');
      if (idx === columnIndex) {
        th.classList.add(direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
      }
    });
  }

  // // ═══════════════════════════════════════════════
  // // 7. ANIMATE NUMBERS ON SCROLL (Counter Animation)
  // // ═══════════════════════════════════════════════
  
  // function animateValue(element, start, end, duration) {
  //   const range = end - start;
  //   const increment = range / (duration / 16); // 60fps
  //   let current = start;
    
  //   const timer = setInterval(() => {
  //     current += increment;
  //     if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
  //       current = end;
  //       clearInterval(timer);
  //     }
      
  //     // Format number based on content
  //     if (element.textContent.includes('₹')) {
  //       element.textContent = '₹' + Math.round(current).toLocaleString('en-IN');
  //     } else {
  //       element.textContent = Math.round(current).toLocaleString('en-IN');
  //     }
  //   }, 16);
  // }
  
  // // Intersection Observer for counter animation
  // const counterObserver = new IntersectionObserver((entries) => {
  //   entries.forEach(entry => {
  //     if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
  //       const value = parseFloat(entry.target.textContent.replace(/,/g, '').replace('₹', ''));
  //       if (!isNaN(value) && value > 0) {
  //         animateValue(entry.target, 0, value, 1000);
  //         entry.target.classList.add('animated');
  //       }
  //     }
  //   });
  // }, { threshold: 0.5 });
  
  // // Observe KPI values
  // document.querySelectorAll('.kpi-value, .finance-value').forEach(element => {
  //   counterObserver.observe(element);
  // });

  // ═══════════════════════════════════════════════
  // 8. RESPONSIVE CHART RESIZE
  // ═══════════════════════════════════════════════
  
  let resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      console.log('Window resized - charts adjusted');
    }, 250);
  });

  // ═══════════════════════════════════════════════
  // 9. KEYBOARD SHORTCUTS
  // ═══════════════════════════════════════════════
  
  document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      if (searchInput) {
        searchInput.focus();
      }
    }
    
    // Escape to clear search
    if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.value = '';
      searchInput.blur();
      performSearch('');
    }
  });

  // ═══════════════════════════════════════════════
  // 10. SMOOTH SCROLL TO OVERDUE SECTION
  // ═══════════════════════════════════════════════
  
  const overdueLink = document.querySelector('a[href="#overdue-section"]');
  if (overdueLink) {
    overdueLink.addEventListener('click', function(e) {
      e.preventDefault();
      const section = document.getElementById('overdue-section');
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  // ═══════════════════════════════════════════════
  // INITIALIZATION COMPLETE
  // ═══════════════════════════════════════════════
  
  console.log('✓ Dashboard initialized successfully');
  console.log('✓ Charts rendered with blue-white theme');
  console.log('✓ Interactive features enabled');
  
});

// ═══════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════

// Format currency
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
}

// Format date
function formatDate(dateString) {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date);
}

// Debounce function for search
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Add ripple effect styles
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `
  .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(59, 130, 246, 0.3);
    pointer-events: none;
    transform: scale(0);
    animation: ripple 0.6s ease-out;
  }
  
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;
document.head.appendChild(rippleStyle);