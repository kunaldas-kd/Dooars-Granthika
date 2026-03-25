// LibNexa - Home Page Animations

document.addEventListener('DOMContentLoaded', function() {
  // Initialize animations
  initializeAnimations();
  initializeStatsCounter();
  initializeScrollAnimations();
});

/**
 * Initialize page animations
 */
function initializeAnimations() {
  // Add animation delay to stat boxes
  const statBoxes = document.querySelectorAll('.stat-box');
  statBoxes.forEach((box, index) => {
    box.style.setProperty('--stat-index', index);
  });

  // Add hover effect to feature items
  const featureItems = document.querySelectorAll('.feature-item');
  featureItems.forEach((item, index) => {
    item.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-10px) scale(1.03)';
    });

    item.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });
}

/**
 * Animated counter for stats
 */
function initializeStatsCounter() {
  const statNumbers = document.querySelectorAll('.stat-number');
  const observerOptions = {
    threshold: 0.5,
    rootMargin: '0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const target = entry.target;
        const finalValue = target.textContent.trim();

        // Skip fallback "—" values — nothing to animate
        if (finalValue === '—' || finalValue === '') {
          observer.unobserve(target);
          return;
        }

        // Detect suffix flags from the live value (e.g. "1,234+" or "99.9%")
        const hasPercent = finalValue.includes('%');
        const hasPlus    = finalValue.includes('+');
        const hasComma   = finalValue.includes(',');

        // Strip everything except digits and dots to get the numeric part
        const numericValue = parseFloat(finalValue.replace(/[^0-9.]/g, ''));

        if (!isNaN(numericValue) && numericValue > 0) {
          animateCounter(target, 0, numericValue, 2000, hasPercent, hasPlus, hasComma);
        }

        observer.unobserve(target);
      }
    });
  }, observerOptions);

  statNumbers.forEach(stat => observer.observe(stat));
}

/**
 * Animate counter from start to end value
 */
function animateCounter(element, start, end, duration, hasPercent = false, hasPlus = false, hasComma = false) {
  const startTime = performance.now();
  const isDecimal = end % 1 !== 0;

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Easing function (easeOutQuart)
    const easeProgress = 1 - Math.pow(1 - progress, 4);
    
    let currentValue = start + (end - start) * easeProgress;
    
    // Format the number
    let displayValue;
    if (isDecimal) {
      displayValue = currentValue.toFixed(1);
    } else {
      displayValue = Math.floor(currentValue).toString();
      if (hasComma) {
        displayValue = displayValue.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      }
    }
    
    // Add suffix
    if (hasPlus) displayValue += '+';
    if (hasPercent) displayValue += '%';
    
    element.textContent = displayValue;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

/**
 * Initialize scroll-triggered animations
 */
function initializeScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
      }
    });
  }, observerOptions);

  // Observe sections
  const sections = document.querySelectorAll('.features-section, .stats-section, .cta-section');
  sections.forEach(section => observer.observe(section));
}

/**
 * Smooth scroll to sections
 */
function smoothScrollTo(targetId) {
  const target = document.querySelector(targetId);
  if (target) {
    const headerOffset = 80;
    const elementPosition = target.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
}

/**
 * Button loading state
 */
function setLoading(buttonId, isLoading) {
  const button = document.getElementById(buttonId);
  if (!button) return;

  if (isLoading) {
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<span class="loading"></span> Loading...';
    button.style.opacity = '0.7';
  } else {
    button.disabled = false;
    button.innerHTML = button.dataset.originalText || button.innerHTML;
    button.style.opacity = '1';
  }
}

/**
 * Parallax effect for hero image
 */
window.addEventListener('scroll', () => {
  const heroImage = document.querySelector('.hero-image');
  if (heroImage && window.innerWidth > 768) {
    const scrolled = window.pageYOffset;
    const rate = scrolled * 0.3;
    heroImage.style.transform = `translateY(${rate}px)`;
  }
});

/**
 * Feature card tilt effect
 */
function initializeTiltEffect() {
  const cards = document.querySelectorAll('.feature-item');
  
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const rotateX = (y - centerY) / 10;
      const rotateY = (centerX - x) / 10;
      
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-10px)`;
    });
    
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateY(0)';
    });
  });
}

// Initialize tilt effect when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeTiltEffect);
} else {
  initializeTiltEffect();
}