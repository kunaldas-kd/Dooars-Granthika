// ============================================================
// dashboard_base.js - Base Dashboard JavaScript
// Sidebar navigation, mobile menu, and common functionality
// ============================================================

document.addEventListener('DOMContentLoaded', function() {

  // ═══════════════════════════════════════════════
  // 0. DESKTOP SIDEBAR COLLAPSE TOGGLE
  // ═══════════════════════════════════════════════

  const collapseBtn = document.getElementById('sidebarCollapseBtn');
  const sidebarEl   = document.querySelector('.sidebar');
  const COLLAPSED_KEY = 'sidebar_collapsed';

  function setSidebarCollapsed(collapsed) {
    if (!sidebarEl) return;
    if (collapsed) {
      sidebarEl.classList.add('collapsed');
      document.body.classList.add('sidebar-collapsed-desktop');
      localStorage.setItem(COLLAPSED_KEY, '1');
    } else {
      sidebarEl.classList.remove('collapsed');
      document.body.classList.remove('sidebar-collapsed-desktop');
      localStorage.removeItem(COLLAPSED_KEY);
    }
  }

  // Restore state from last visit (desktop only)
  // Apply instantly (no transition flash) by briefly disabling transitions
  if (window.innerWidth > 968 && localStorage.getItem(COLLAPSED_KEY) === '1') {
    if (sidebarEl) sidebarEl.classList.add('no-transition');
    const mc = document.querySelector('.main-content');
    if (mc) mc.classList.add('no-transition');
    setSidebarCollapsed(true);
    // Re-enable transitions on next frame
    requestAnimationFrame(() => {
      if (sidebarEl) sidebarEl.classList.remove('no-transition');
      if (mc) mc.classList.remove('no-transition');
    });
  }

  if (collapseBtn) {
    collapseBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      // Only works on desktop — mobile uses the overlay pattern
      if (window.innerWidth > 968) {
        const isCollapsed = sidebarEl && sidebarEl.classList.contains('collapsed');
        setSidebarCollapsed(!isCollapsed);
      }
    });
  }

  // Reset collapse state on resize to mobile
  window.addEventListener('resize', function () {
    if (window.innerWidth <= 968 && sidebarEl) {
      sidebarEl.classList.remove('collapsed');
      document.body.classList.remove('sidebar-collapsed-desktop');
    }
  });


  
  const sidebar = document.querySelector('.sidebar');
  const hamburgerBtn = document.getElementById('hamburgerBtn');
  const sidebarOpenTrigger = document.getElementById('sidebarOpenTrigger');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const body = document.body;
  
  // Function to open sidebar
  function openSidebar() {
    if (sidebar) {
      sidebar.classList.add('open');
      body.classList.remove('sidebar-closed');
    }
    if (sidebarOverlay) {
      sidebarOverlay.classList.add('visible');
    }
    if (hamburgerBtn) {
      hamburgerBtn.innerHTML = '<i class="fas fa-times"></i>';
    }
  }
  
  // Function to close sidebar
  function closeSidebar() {
    if (sidebar) {
      sidebar.classList.remove('open');
      body.classList.add('sidebar-closed');
    }
    if (sidebarOverlay) {
      sidebarOverlay.classList.remove('visible');
    }
    if (hamburgerBtn) {
      hamburgerBtn.innerHTML = '<i class="fas fa-bars"></i>';
    }
  }
  
  // Toggle sidebar from hamburger button (inside sidebar)
  if (hamburgerBtn) {
    hamburgerBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      closeSidebar();
    });
  }
  
  // Open sidebar from fixed trigger button (mobile only)
  if (sidebarOpenTrigger) {
    sidebarOpenTrigger.addEventListener('click', function(e) {
      e.stopPropagation();
      openSidebar();
    });
  }
  
  // Close sidebar when clicking overlay
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeSidebar);
  }
  
  // Close sidebar when clicking nav links (mobile)
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', function() {
      if (window.innerWidth <= 968) {
        setTimeout(closeSidebar, 150);
      }
    });
  });
  
  // Initialize sidebar state based on screen size
  function initializeSidebarState() {
    if (window.innerWidth <= 968) {
      body.classList.add('sidebar-closed');
      closeSidebar();
    } else {
      body.classList.remove('sidebar-closed');
      if (sidebar) {
        sidebar.classList.remove('open');
      }
      if (sidebarOverlay) {
        sidebarOverlay.classList.remove('visible');
      }
    }
  }
  
  // Initialize on load
  initializeSidebarState();
  
  // Handle window resize
  let resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(initializeSidebarState, 250);
  });

  // ═══════════════════════════════════════════════
  // 2. ACTIVE NAV ITEM HIGHLIGHTING
  // ═══════════════════════════════════════════════
  
  const currentPath = window.location.pathname;
  
  navItems.forEach(item => {
    const href = item.getAttribute('href');
    if (href && currentPath.includes(href)) {
      item.classList.add('active');
    }
  });

  // ═══════════════════════════════════════════════
  // 3. AUTO-DISMISS MESSAGES
  // ═══════════════════════════════════════════════
  
  const messages = document.querySelectorAll('.message');
  
  messages.forEach(message => {
    const closeBtn = message.querySelector('.message-close');
    
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        message.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
          message.remove();
        }, 300);
      });
    }
    
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
      if (message.parentElement) {
        message.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
          message.remove();
        }, 300);
      }
    }, 8000);
  });

  // ═══════════════════════════════════════════════
  // 4. NOTIFICATION BAR AUTO-DISMISS
  // ═══════════════════════════════════════════════
  
  const notifBar = document.getElementById('siteNotifBar');
  
  if (notifBar) {
    const closeBtn = notifBar.querySelector('.site-notif-bar__close');
    
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        notifBar.style.animation = 'slideOutTop 0.3s ease-out';
        setTimeout(() => {
          notifBar.remove();
        }, 300);
      });
    }
  }

  // // ═══════════════════════════════════════════════
  // // 5. SMOOTH SCROLL TO TOP
  // // ═══════════════════════════════════════════════
  
  // // Create scroll-to-top button if it doesn't exist
  // let scrollTopBtn = document.getElementById('scrollTopBtn');
  
  // if (!scrollTopBtn) {
  //   scrollTopBtn = document.createElement('button');
  //   scrollTopBtn.id = 'scrollTopBtn';
  //   scrollTopBtn.className = 'scroll-top-btn';
  //   scrollTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
  //   scrollTopBtn.setAttribute('aria-label', 'Scroll to top');
  //   document.body.appendChild(scrollTopBtn);
    
  //   // Add styles
  //   const style = document.createElement('style');
  //   style.textContent = `
  //     .scroll-top-btn {
  //       position: fixed;
  //       bottom: 32px;
  //       right: 32px;
  //       width: 48px;
  //       height: 48px;
  //       border-radius: 50%;
  //       background: var(--ink-accent);
  //       color: white;
  //       border: none;
  //       font-size: 18px;
  //       cursor: pointer;
  //       opacity: 0;
  //       visibility: hidden;
  //       transform: translateY(20px);
  //       transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  //       box-shadow: 0 8px 16px rgba(26, 111, 212, 0.3);
  //       z-index: 500;
  //     }
      
  //     .scroll-top-btn.visible {
  //       opacity: 1;
  //       visibility: visible;
  //       transform: translateY(0);
  //     }
      
  //     .scroll-top-btn:hover {
  //       background: var(--ink-deep);
  //       transform: translateY(-3px);
  //       box-shadow: 0 12px 24px rgba(26, 111, 212, 0.4);
  //     }
      
  //     .scroll-top-btn:active {
  //       transform: translateY(0);
  //     }
      
  //     @media (max-width: 640px) {
  //       .scroll-top-btn {
  //         bottom: 24px;
  //         right: 24px;
  //         width: 44px;
  //         height: 44px;
  //         font-size: 16px;
  //       }
  //     }
  //   `;
  //   document.head.appendChild(style);
  // }
  
  // Show/hide scroll-to-top button
  function toggleScrollTopButton() {
    if (window.pageYOffset > 300) {
      scrollTopBtn.classList.add('visible');
    } else {
      scrollTopBtn.classList.remove('visible');
    }
  }
  
  // Scroll to top on click
  scrollTopBtn.addEventListener('click', function() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
  
  // Check on scroll
  window.addEventListener('scroll', toggleScrollTopButton);
  toggleScrollTopButton(); // Check initial state

  // ═══════════════════════════════════════════════
  // 6. LOADING ANIMATION FOR LINKS
  // ═══════════════════════════════════════════════
  
  const links = document.querySelectorAll('a:not([target="_blank"])');
  
  links.forEach(link => {
    link.addEventListener('click', function(e) {
      // Only for internal links
      const href = this.getAttribute('href');
      if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
        // Add loading class to body
        document.body.classList.add('page-loading');
      }
    });
  });

  // ═══════════════════════════════════════════════
  // 7. LAZY LOADING IMAGES
  // ═══════════════════════════════════════════════
  
  const lazyImages = document.querySelectorAll('img[data-src]');
  
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
          img.classList.add('loaded');
          observer.unobserve(img);
        }
      });
    });
    
    lazyImages.forEach(img => imageObserver.observe(img));
  } else {
    // Fallback for browsers that don't support IntersectionObserver
    lazyImages.forEach(img => {
      img.src = img.dataset.src;
      img.removeAttribute('data-src');
    });
  }

  // ═══════════════════════════════════════════════
  // 8. KEYBOARD SHORTCUTS
  // ═══════════════════════════════════════════════
  
  document.addEventListener('keydown', function(e) {
    // ESC to close sidebar on mobile
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      closeSidebar();
    }
    
    // Alt + M to toggle sidebar on mobile
    if (e.altKey && e.key === 'm') {
      e.preventDefault();
      if (window.innerWidth <= 968) {
        if (sidebar.classList.contains('open')) {
          closeSidebar();
        } else {
          openSidebar();
        }
      }
    }
  });

  // ═══════════════════════════════════════════════
  // 9. TOOLTIPS (Optional Enhancement)
  // ═══════════════════════════════════════════════
  
  const tooltipElements = document.querySelectorAll('[data-tooltip]');
  
  tooltipElements.forEach(element => {
    element.addEventListener('mouseenter', function(e) {
      const tooltipText = this.getAttribute('data-tooltip');
      
      const tooltip = document.createElement('div');
      tooltip.className = 'tooltip';
      tooltip.textContent = tooltipText;
      document.body.appendChild(tooltip);
      
      const rect = this.getBoundingClientRect();
      tooltip.style.cssText = `
        position: fixed;
        top: ${rect.top - tooltip.offsetHeight - 8}px;
        left: ${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px;
        background: rgba(10, 22, 40, 0.95);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        z-index: 1000;
        pointer-events: none;
        white-space: nowrap;
        animation: fadeIn 0.2s ease-out;
      `;
      
      this._tooltip = tooltip;
    });
    
    element.addEventListener('mouseleave', function() {
      if (this._tooltip) {
        this._tooltip.remove();
        this._tooltip = null;
      }
    });
  });

  // ═══════════════════════════════════════════════
  // 10. FORM VALIDATION ENHANCEMENT
  // ═══════════════════════════════════════════════
  
  const forms = document.querySelectorAll('form[data-validate]');
  
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;
      
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.classList.add('error');
          
          // Remove error class on input
          field.addEventListener('input', function() {
            this.classList.remove('error');
          }, { once: true });
        }
      });
      
      if (!isValid) {
        e.preventDefault();
        
        // Show error message
        const errorMsg = document.createElement('div');
        errorMsg.className = 'message message--error';
        errorMsg.innerHTML = `
          <i class="fas fa-exclamation-circle"></i>
          Please fill in all required fields
          <button class="message-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
          </button>
        `;
        
        const container = document.querySelector('.messages-container') || 
                         document.querySelector('.content-area');
        
        if (container) {
          container.insertBefore(errorMsg, container.firstChild);
          
          // Auto-remove after 5 seconds
          setTimeout(() => {
            errorMsg.remove();
          }, 5000);
        }
      }
    });
  });

  // ═══════════════════════════════════════════════
  // 11. COPY TO CLIPBOARD FUNCTIONALITY
  // ═══════════════════════════════════════════════
  
  const copyButtons = document.querySelectorAll('[data-copy]');
  
  copyButtons.forEach(button => {
    button.addEventListener('click', function() {
      const textToCopy = this.getAttribute('data-copy');
      
      navigator.clipboard.writeText(textToCopy).then(() => {
        // Show success feedback
        const originalText = this.textContent;
        this.textContent = 'Copied!';
        this.classList.add('success');
        
        setTimeout(() => {
          this.textContent = originalText;
          this.classList.remove('success');
        }, 2000);
      }).catch(err => {
        console.error('Failed to copy:', err);
      });
    });
  });

  // ═══════════════════════════════════════════════
  // 12. DETECT SLOW CONNECTION
  // ═══════════════════════════════════════════════
  
  if ('connection' in navigator) {
    const connection = navigator.connection;
    
    if (connection && connection.effectiveType) {
      if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
        console.warn('Slow connection detected - consider reducing image quality');
        
        // Optionally show a notification
        const slowConnectionNotice = document.createElement('div');
        slowConnectionNotice.className = 'message message--warning';
        slowConnectionNotice.innerHTML = `
          <i class="fas fa-wifi"></i>
          Slow connection detected. Loading may take longer.
          <button class="message-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
          </button>
        `;
        
        const contentArea = document.querySelector('.content-area');
        if (contentArea) {
          contentArea.insertBefore(slowConnectionNotice, contentArea.firstChild);
        }
      }
    }
  }

  // ═══════════════════════════════════════════════
  // INITIALIZATION COMPLETE
  // ═══════════════════════════════════════════════
  
  console.log('✓ Dashboard base initialized');
  console.log('✓ Sidebar navigation ready');
  console.log('✓ Common features enabled');
  
});

// ═══════════════════════════════════════════════
// GLOBAL UTILITY FUNCTIONS
// ═══════════════════════════════════════════════

// Show loading spinner
window.showLoading = function() {
  const loader = document.createElement('div');
  loader.id = 'globalLoader';
  loader.innerHTML = `
    <div style="
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 255, 255, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      backdrop-filter: blur(4px);
    ">
      <div style="
        width: 48px;
        height: 48px;
        border: 4px solid #e2e8f0;
        border-top-color: #1a6fd4;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      "></div>
    </div>
  `;
  document.body.appendChild(loader);
  
  // Add spin animation if not exists
  if (!document.getElementById('spinAnimation')) {
    const style = document.createElement('style');
    style.id = 'spinAnimation';
    style.textContent = `
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
  }
};

// Hide loading spinner
window.hideLoading = function() {
  const loader = document.getElementById('globalLoader');
  if (loader) {
    loader.remove();
  }
};

// Show toast notification
window.showToast = function(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `message message--${type}`;
  toast.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
    ${message}
    <button class="message-close" onclick="this.parentElement.remove()">
      <i class="fas fa-times"></i>
    </button>
  `;
  
  let container = document.querySelector('.messages-container');
  
  if (!container) {
    container = document.createElement('div');
    container.className = 'messages-container';
    const contentArea = document.querySelector('.content-area') || document.body;
    contentArea.insertBefore(container, contentArea.firstChild);
  }
  
  container.appendChild(toast);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    toast.style.animation = 'slideOutRight 0.3s ease-out';
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 5000);
};