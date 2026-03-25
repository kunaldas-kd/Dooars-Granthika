// LibNexa - About Page Animations

document.addEventListener('DOMContentLoaded', function() {
  initializeAboutAnimations();
  initializeScrollReveal();
  initializeParallax();
});

/**
 * Initialize about page specific animations
 */
function initializeAboutAnimations() {
  // Add index to value items for staggered animation
  const valueItems = document.querySelectorAll('.value-item');
  valueItems.forEach((item, index) => {
    item.style.setProperty('--item-index', index);
    
    // Add hover effect enhancement
    item.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-10px) scale(1)';
    });
    
    item.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });

  // Add index to team members for staggered animation
  const teamMembers = document.querySelectorAll('.team-member');
  teamMembers.forEach((member, index) => {
    member.style.setProperty('--member-index', index);
  });

  // Add interactive hover effect to team avatars
  initializeAvatarAnimations();
}

/**
 * Initialize avatar animations
 */
function initializeAvatarAnimations() {
  const avatars = document.querySelectorAll('.member-avatar');
  
  avatars.forEach(avatar => {
    const parent = avatar.closest('.team-member');
    
    parent.addEventListener('mouseenter', function() {
      avatar.style.transform = 'scale(1.1) rotate(5deg)';
    });
    
    parent.addEventListener('mouseleave', function() {
      avatar.style.transform = 'scale(1) rotate(0deg)';
    });

    // Add click animation
    avatar.addEventListener('click', function(e) {
      e.stopPropagation();
      this.style.animation = 'none';
      setTimeout(() => {
        this.style.animation = 'pulse 0.6s ease-out';
      }, 10);
    });
  });
}

/**
 * Initialize scroll-triggered reveal animations
 */
function initializeScrollReveal() {
  const observerOptions = {
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        
        // Trigger content animations
        const contentParagraphs = entry.target.querySelectorAll('.card-content p');
        contentParagraphs.forEach((p, index) => {
          setTimeout(() => {
            p.style.opacity = '1';
            p.style.transform = 'translateY(0)';
          }, index * 100);
        });
        
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // Observe all sections
  const sections = document.querySelectorAll('.content-section');
  sections.forEach(section => observer.observe(section));

  // Observe cards
  const cards = document.querySelectorAll('.content-card, .value-item, .team-member');
  cards.forEach(card => observer.observe(card));
}

/**
 * Initialize parallax effects
 */
function initializeParallax() {
  if (window.innerWidth <= 768) return; // Disable on mobile

  window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    
    // Parallax for value items
    const valueItems = document.querySelectorAll('.value-item');
    valueItems.forEach((item, index) => {
      const speed = 0.1 + (index % 3) * 0.05;
      const yPos = -(scrolled * speed);
      item.style.transform = `translateY(${yPos}px)`;
    });
  });
}

/**
 * Add magnetic effect to CTA button
 */
function initializeMagneticButton() {
  const ctaButton = document.querySelector('.cta-section .btn');
  if (!ctaButton) return;

  const ctaSection = document.querySelector('.cta-section');
  
  ctaSection.addEventListener('mousemove', (e) => {
    const rect = ctaButton.getBoundingClientRect();
    const buttonCenterX = rect.left + rect.width / 2;
    const buttonCenterY = rect.top + rect.height / 2;
    
    const distanceX = e.clientX - buttonCenterX;
    const distanceY = e.clientY - buttonCenterY;
    const distance = Math.sqrt(distanceX * distanceX + distanceY * distanceY);
    
    if (distance < 150) {
      const pullStrength = (150 - distance) / 150;
      const pullX = distanceX * pullStrength * 0.3;
      const pullY = distanceY * pullStrength * 0.3;
      
      ctaButton.style.transform = `translate(${pullX}px, ${pullY}px)`;
    } else {
      ctaButton.style.transform = 'translate(0, 0)';
    }
  });
  
  ctaSection.addEventListener('mouseleave', () => {
    ctaButton.style.transform = 'translate(0, 0)';
  });
}

// Initialize magnetic button effect
initializeMagneticButton();

/**
 * Add card flip effect on click (optional enhancement)
 */
function initializeCardFlip() {
  const valueItems = document.querySelectorAll('.value-item');
  
  valueItems.forEach(item => {
    let isFlipped = false;
    
    item.addEventListener('click', function() {
      if (!isFlipped) {
        this.style.transform = 'rotateY(180deg)';
        isFlipped = true;
      } else {
        this.style.transform = 'rotateY(0deg)';
        isFlipped = false;
      }
    });
  });
}

/**
 * Animate section title underline
 */
function animateSectionTitles() {
  const titles = document.querySelectorAll('.section-title');
  const observerOptions = {
    threshold: 0.5
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const title = entry.target;
        title.style.animation = 'fadeInDown 0.8s ease-out forwards';
        observer.unobserve(title);
      }
    });
  }, observerOptions);

  titles.forEach(title => observer.observe(title));
}

animateSectionTitles();

/**
 * Add smooth scroll behavior for anchor links
 */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});

/**
 * Add ripple effect on card click
 */
function createRipple(event) {
  const card = event.currentTarget;
  const ripple = document.createElement('span');
  const rect = card.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const x = event.clientX - rect.left - size / 2;
  const y = event.clientY - rect.top - size / 2;

  ripple.style.width = ripple.style.height = size + 'px';
  ripple.style.left = x + 'px';
  ripple.style.top = y + 'px';
  ripple.classList.add('ripple');

  card.appendChild(ripple);

  setTimeout(() => {
    ripple.remove();
  }, 600);
}

// Add ripple CSS dynamically
const style = document.createElement('style');
style.textContent = `
  .value-item, .team-member {
    position: relative;
    overflow: hidden;
  }
  
  .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(0, 192, 6, 0.3);
    transform: scale(0);
    animation: ripple-animation 0.6s ease-out;
    pointer-events: none;
  }
  
  @keyframes ripple-animation {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Add ripple effect to interactive elements
document.querySelectorAll('.value-item, .team-member').forEach(element => {
  element.addEventListener('click', createRipple);
});