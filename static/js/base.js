// LibNexa - Main JavaScript File
// Base functionality for all pages

document.addEventListener('DOMContentLoaded', function() {
  initializeNavigation();
  initializeButtonEffects();
  initializeHamburger();
  initializeScrollEffects();
});

/**
 * Initialize navigation functionality
 */
function initializeNavigation() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');
  
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href !== '#' && href !== '') {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          const headerOffset = 80;
          const elementPosition = target.getBoundingClientRect().top;
          const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
          window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
        }
      }
    });
  });
}

/**
 * Initialize button click effects
 */
function initializeButtonEffects() {
  const buttons = document.querySelectorAll('.btn');
  
  buttons.forEach(button => {
    button.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.classList.add('ripple-effect');

      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    });
  });
}

/**
 * Initialize hamburger menu toggle
 */
function initializeHamburger() {
  const hamburger = document.getElementById('hamburgerBtn');
  const nav = document.getElementById('mainNav');

  if (!hamburger || !nav) return;

  // Toggle on button click
  hamburger.addEventListener('click', function(e) {
    e.stopPropagation();
    const isOpen = nav.classList.toggle('mobile-open');
    hamburger.classList.toggle('open', isOpen);
    hamburger.setAttribute('aria-expanded', isOpen);
  });

  // Close when a nav link is clicked
  nav.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => closeMenu());
  });

  // Close when clicking outside
  document.addEventListener('click', function(e) {
    if (!hamburger.contains(e.target) && !nav.contains(e.target)) {
      closeMenu();
    }
  });

  // Close on Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeMenu();
  });

  function closeMenu() {
    nav.classList.remove('mobile-open');
    hamburger.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
  }
}

/**
 * Initialize scroll effects
 */
function initializeScrollEffects() {
  const header = document.querySelector('.main-header');
  if (!header) return;

  let lastScroll = 0;
  const SCROLL_DELTA = 10; // minimum px change to trigger hide/show
  
  window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    // Add shadow when scrolled
    if (currentScroll > 10) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }

    // Auto-hide only on desktop and only with meaningful scroll distance
    if (window.innerWidth > 768) {
      const scrollDiff = currentScroll - lastScroll;
      if (scrollDiff > SCROLL_DELTA && currentScroll > 150) {
        // Scrolling down past threshold — hide header
        header.style.transform = 'translateY(-100%)';
      } else if (scrollDiff < -SCROLL_DELTA || currentScroll <= 10) {
        // Scrolling up or near top — show header
        header.style.transform = 'translateY(0)';
      }
    } else {
      // Always show header on mobile
      header.style.transform = 'translateY(0)';
    }

    lastScroll = currentScroll <= 0 ? 0 : currentScroll;
  });
}

/**
 * Show loading state on buttons
 */
function setButtonLoading(button, isLoading) {
  if (!button) return;

  if (isLoading) {
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<span class="loading-spinner"></span> Loading...';
    button.style.opacity = '0.7';
  } else {
    button.disabled = false;
    button.innerHTML = button.dataset.originalText || button.innerHTML;
    button.style.opacity = '1';
  }
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <span class="notification-icon">${getNotificationIcon(type)}</span>
    <span class="notification-message">${message}</span>
    <button class="notification-close" onclick="this.parentElement.remove()">✕</button>
  `;

  document.body.appendChild(notification);
  setTimeout(() => notification.classList.add('show'), 10);
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 5000);
}

function getNotificationIcon(type) {
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  return icons[type] || icons.info;
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => { clearTimeout(timeout); func(...args); };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showNotification('Copied to clipboard!', 'success');
    return true;
  } catch (err) {
    showNotification('Failed to copy to clipboard', 'error');
    return false;
  }
}

function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Add CSS for dynamic elements
 */
const dynamicStyles = document.createElement('style');
dynamicStyles.textContent = `
  .ripple-effect {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple 0.6s ease-out;
    pointer-events: none;
  }
  @keyframes ripple {
    to { transform: scale(4); opacity: 0; }
  }
  .loading-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  .notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 10000;
    transform: translateX(400px);
    transition: transform 0.3s ease;
    max-width: 400px;
  }
  .notification.show { transform: translateX(0); }
  .notification-success { border-left: 4px solid #00c006; }
  .notification-error   { border-left: 4px solid #ef0000; }
  .notification-warning { border-left: 4px solid #ff9800; }
  .notification-info    { border-left: 4px solid #2c3e50; }
  .notification-icon { font-size: 1.5rem; font-weight: bold; }
  .notification-success .notification-icon { color: #00c006; }
  .notification-error   .notification-icon { color: #ef0000; }
  .notification-warning .notification-icon { color: #ff9800; }
  .notification-info    .notification-icon { color: #2c3e50; }
  .notification-message { flex: 1; color: #2c3e50; }
  .notification-close {
    background: none; border: none; font-size: 1.25rem; color: #4a5568;
    cursor: pointer; padding: 0; width: 24px; height: 24px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 4px; transition: background 0.2s;
  }
  .notification-close:hover { background: rgba(0,0,0,0.05); }
  .main-header.scrolled { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); }
  @media (max-width: 480px) {
    .notification { left: 10px; right: 10px; max-width: none; }
  }
`;
document.head.appendChild(dynamicStyles);

window.LibNexa = {
  setButtonLoading,
  showNotification,
  debounce,
  throttle,
  isInViewport,
  copyToClipboard,
  formatNumber
};