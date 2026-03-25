// LibNexa - Contact Page Animations

document.addEventListener('DOMContentLoaded', function() {
  initializeContactAnimations();
  initializeFormValidation();
  initializeFormAnimation();
  initializeQuickHelpCards();
});

/**
 * Initialize contact page animations
 */
function initializeContactAnimations() {
  // Add index to form groups for staggered animation
  const formGroups = document.querySelectorAll('.form-group');
  formGroups.forEach((group, index) => {
    group.style.setProperty('--group-index', index);
  });

  // Add index to contact info items
  const infoItems = document.querySelectorAll('.contact-info-item');
  infoItems.forEach((item, index) => {
    item.style.setProperty('--info-index', index);
  });

  // Add index to quick help cards
  const helpCards = document.querySelectorAll('.quick-help-card');
  helpCards.forEach((card, index) => {
    card.style.setProperty('--help-index', index);
  });

  // Initialize interactive elements
  initializeInteractiveIcons();
}

/**
 * Interactive icon animations
 */
function initializeInteractiveIcons() {
  const icons = document.querySelectorAll('.contact-icon, .help-icon');
  
  icons.forEach(icon => {
    icon.addEventListener('mouseenter', function() {
      this.style.animation = 'none';
      setTimeout(() => {
        this.style.animation = 'bounce 0.6s ease-out';
      }, 10);
    });
  });
}

/**
 * Form validation with visual feedback
 */
function initializeFormValidation() {
  const form = document.getElementById('contactForm');
  if (!form) return;

  const inputs = form.querySelectorAll('.form-input, .form-select, .form-textarea');
  
  inputs.forEach(input => {
    // Add focus animation
    input.addEventListener('focus', function() {
      this.parentElement.classList.add('focused');
      animateLabel(this);
    });

    input.addEventListener('blur', function() {
      this.parentElement.classList.remove('focused');
      validateInput(this);
    });

    // Real-time validation
    input.addEventListener('input', function() {
      if (this.value.length > 0) {
        validateInput(this);
      }
    });
  });
}

/**
 * Animate label on focus
 */
function animateLabel(input) {
  const label = input.previousElementSibling;
  if (label && label.tagName === 'LABEL') {
    label.style.animation = 'labelFloat 0.3s ease-out';
  }
}

/**
 * Validate individual input
 */
function validateInput(input) {
  const value = input.value.trim();
  let isValid = true;

  // Remove previous validation classes
  input.classList.remove('valid', 'invalid');

  // Validation rules
  if (input.hasAttribute('required') && value === '') {
    isValid = false;
  } else if (input.type === 'email' && value !== '') {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    isValid = emailRegex.test(value);
  } else if (input.type === 'tel' && value !== '') {
    const phoneRegex = /^[+]?[\d\s-()]+$/;
    isValid = phoneRegex.test(value);
  }

  // Add validation class
  if (value !== '') {
    input.classList.add(isValid ? 'valid' : 'invalid');
  }

  // Add visual feedback
  if (isValid && value !== '') {
    addCheckmark(input);
  } else if (!isValid && value !== '') {
    addErrorIcon(input);
  } else {
    removeIcons(input);
  }

  return isValid;
}

/**
 * Add checkmark icon
 */
function addCheckmark(input) {
  removeIcons(input);
  const checkmark = document.createElement('span');
  checkmark.className = 'validation-icon valid-icon';
  checkmark.textContent = '✓';
  checkmark.style.cssText = `
    position: absolute;
    right: 15px;
    top: 50%;
    transform: translateY(-50%) scale(0);
    color: #00c006;
    font-weight: bold;
    animation: checkmarkPop 0.3s ease-out forwards;
  `;
  input.parentElement.style.position = 'relative';
  input.parentElement.appendChild(checkmark);
}

/**
 * Add error icon
 */
function addErrorIcon(input) {
  removeIcons(input);
  const errorIcon = document.createElement('span');
  errorIcon.className = 'validation-icon error-icon';
  errorIcon.textContent = '✕';
  errorIcon.style.cssText = `
    position: absolute;
    right: 15px;
    top: 50%;
    transform: translateY(-50%) scale(0);
    color: #ef0000;
    font-weight: bold;
    animation: errorShake 0.5s ease-out forwards;
  `;
  input.parentElement.style.position = 'relative';
  input.parentElement.appendChild(errorIcon);
}

/**
 * Remove validation icons
 */
function removeIcons(input) {
  const icons = input.parentElement.querySelectorAll('.validation-icon');
  icons.forEach(icon => icon.remove());
}

/**
 * Initialize form animation
 */
function initializeFormAnimation() {
  const form = document.getElementById('contactForm');
  if (!form) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    // Validate all fields
    const inputs = form.querySelectorAll('.form-input[required], .form-select[required], .form-textarea[required]');
    let allValid = true;
    
    inputs.forEach(input => {
      if (!validateInput(input)) {
        allValid = false;
      }
    });

    if (!allValid) {
      shakeForm(form);
      return;
    }

    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading-spinner"></span> Sending...';
    submitBtn.style.background = 'linear-gradient(135deg, #718096, #4a5568)';
    
    try {
      const formData = new FormData(form);
      const response = await fetch(form.action || window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      
      if (response.ok) {
        showSuccessAnimation();
        form.reset();
        removeAllIcons();
      } else {
        showErrorAnimation();
      }
    } catch (error) {
      console.error('Error:', error);
      showErrorAnimation();
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
      submitBtn.style.background = '';
    }
  });
}

/**
 * Shake form on validation error
 */
function shakeForm(form) {
  form.style.animation = 'shake 0.5s ease-out';
  setTimeout(() => {
    form.style.animation = '';
  }, 500);
}

/**
 * Remove all validation icons
 */
function removeAllIcons() {
  const icons = document.querySelectorAll('.validation-icon');
  icons.forEach(icon => icon.remove());
}

/**
 * Show success animation
 */
function showSuccessAnimation() {
  const successMessage = document.createElement('div');
  successMessage.className = 'success-message';
  successMessage.innerHTML = `
    <div class="success-content">
      <span class="success-icon">✓</span>
      <h3>Message Sent!</h3>
      <p>Thank you for contacting us. We'll get back to you soon.</p>
    </div>
  `;
  successMessage.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) scale(0);
    background: white;
    padding: 3rem;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 192, 6, 0.3);
    z-index: 10000;
    text-align: center;
    animation: successPop 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
  `;

  document.body.appendChild(successMessage);

  setTimeout(() => {
    successMessage.style.animation = 'successFade 0.5s ease-out forwards';
    setTimeout(() => successMessage.remove(), 500);
  }, 3000);
}

/**
 * Show error animation
 */
function showErrorAnimation() {
  const errorMessage = document.createElement('div');
  errorMessage.className = 'error-message';
  errorMessage.innerHTML = `
    <div class="error-content">
      <span class="error-icon">✕</span>
      <h3>Oops!</h3>
      <p>Sorry, there was an error sending your message. Please try again.</p>
    </div>
  `;
  errorMessage.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) scale(0);
    background: white;
    padding: 3rem;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(239, 0, 0, 0.3);
    z-index: 10000;
    text-align: center;
    animation: errorPop 0.5s ease-out forwards;
  `;

  document.body.appendChild(errorMessage);

  setTimeout(() => {
    errorMessage.style.animation = 'errorFade 0.5s ease-out forwards';
    setTimeout(() => errorMessage.remove(), 500);
  }, 3000);
}

/**
 * Initialize quick help cards
 */
function initializeQuickHelpCards() {
  const cards = document.querySelectorAll('.quick-help-card');
  
  cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-10px) scale(1)';
    });

    card.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });

    // Add click ripple effect
    card.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        border-radius: 50%;
        background: rgba(0, 192, 6, 0.3);
        transform: scale(0);
        animation: ripple 0.6s ease-out;
        pointer-events: none;
      `;

      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });
  });
}

// Add necessary CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes labelFloat {
    0% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-5px);
    }
    100% {
      transform: translateY(0);
    }
  }
  
  @keyframes checkmarkPop {
    0% {
      transform: translateY(-50%) scale(0);
    }
    50% {
      transform: translateY(-50%) scale(1.2);
    }
    100% {
      transform: translateY(-50%) scale(1);
    }
  }
  
  @keyframes errorShake {
    0%, 100% {
      transform: translateY(-50%) translateX(0) scale(1);
    }
    25% {
      transform: translateY(-50%) translateX(-5px) scale(1);
    }
    75% {
      transform: translateY(-50%) translateX(5px) scale(1);
    }
  }
  
  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-10px); }
    75% { transform: translateX(10px); }
  }
  
  @keyframes successPop {
    to {
      transform: translate(-50%, -50%) scale(1);
    }
  }
  
  @keyframes successFade {
    to {
      opacity: 0;
      transform: translate(-50%, -50%) scale(0.8);
    }
  }
  
  @keyframes errorPop {
    0% {
      transform: translate(-50%, -50%) scale(0);
    }
    50% {
      transform: translate(-50%, -50%) scale(1.1);
    }
    100% {
      transform: translate(-50%, -50%) scale(1);
    }
  }
  
  @keyframes errorFade {
    to {
      opacity: 0;
      transform: translate(-50%, -50%) scale(0.8);
    }
  }
  
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
  
  .loading-spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .success-icon,
  .error-icon {
    display: inline-block;
    width: 60px;
    height: 60px;
    line-height: 60px;
    font-size: 2rem;
    border-radius: 50%;
    margin-bottom: 1rem;
  }
  
  .success-icon {
    background: linear-gradient(135deg, #00c006, #00a005);
    color: white;
  }
  
  .error-icon {
    background: linear-gradient(135deg, #ef0000, #d10000);
    color: white;
  }
  
  .form-input.valid,
  .form-select.valid,
  .form-textarea.valid {
    border-color: #00c006;
  }
  
  .form-input.invalid,
  .form-select.invalid,
  .form-textarea.invalid {
    border-color: #ef0000;
  }
`;
document.head.appendChild(style);