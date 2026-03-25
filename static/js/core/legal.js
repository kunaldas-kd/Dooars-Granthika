// LibNexa - Legal Pages Animations (Privacy & Terms)

document.addEventListener('DOMContentLoaded', function() {
  initializeLegalAnimations();
  initializeReadingProgress();
  initializeSmoothScroll();
  initializeTableOfContents();
  initializeScrollToTop();
});

/**
 * Initialize legal page animations
 */
function initializeLegalAnimations() {
  // Add index to legal sections for staggered animation
  const sections = document.querySelectorAll('.legal-section');
  sections.forEach((section, index) => {
    section.style.setProperty('--section-index', index);
  });

  // Add scroll reveal for sections
  initializeScrollReveal();
  
  // Add interactive section highlighting
  initializeSectionHighlight();
}

/**
 * Initialize scroll reveal animations
 */
function initializeScrollReveal() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        
        // Animate list items
        const listItems = entry.target.querySelectorAll('li');
        listItems.forEach((item, index) => {
          setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
          }, index * 50);
        });
      }
    });
  }, observerOptions);

  const sections = document.querySelectorAll('.legal-section');
  sections.forEach(section => observer.observe(section));
}

/**
 * Initialize section highlight on hover
 */
function initializeSectionHighlight() {
  const sections = document.querySelectorAll('.legal-section');
  
  sections.forEach(section => {
    section.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px)';
      this.style.paddingLeft = '1.5rem';
      this.style.borderLeft = '4px solid #00c006';
      this.style.background = 'rgba(0, 192, 6, 0.02)';
      this.style.borderRadius = '0 12px 12px 0';
    });

    section.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.paddingLeft = '';
      this.style.borderLeft = '';
      this.style.background = '';
      this.style.borderRadius = '';
    });
  });
}

/**
 * Initialize reading progress bar
 */
function initializeReadingProgress() {
  // Create progress bar if it doesn't exist
  let progressBar = document.querySelector('.reading-progress');
  if (!progressBar) {
    progressBar = document.createElement('div');
    progressBar.className = 'reading-progress';
    document.body.appendChild(progressBar);
  }

  // Update progress on scroll
  window.addEventListener('scroll', updateReadingProgress);
  updateReadingProgress(); // Initial call
}

/**
 * Update reading progress bar
 */
function updateReadingProgress() {
  const progressBar = document.querySelector('.reading-progress');
  if (!progressBar) return;

  const windowHeight = window.innerHeight;
  const documentHeight = document.documentElement.scrollHeight - windowHeight;
  const scrolled = window.pageYOffset;
  const progress = (scrolled / documentHeight) * 100;

  progressBar.style.width = Math.min(progress, 100) + '%';
}

/**
 * Initialize smooth scroll for anchor links
 */
function initializeSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const target = document.querySelector(targetId);
      if (target) {
        const headerOffset = 80;
        const elementPosition = target.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });

        // Highlight target section
        highlightSection(target);
      }
    });
  });
}

/**
 * Highlight section temporarily
 */
function highlightSection(section) {
  section.style.background = 'rgba(0, 192, 6, 0.1)';
  section.style.borderLeft = '4px solid #00c006';
  section.style.borderRadius = '0 12px 12px 0';
  section.style.padding = '1rem 1rem 1rem 1.5rem';
  
  setTimeout(() => {
    section.style.background = '';
    section.style.borderLeft = '';
    section.style.borderRadius = '';
    section.style.padding = '';
  }, 2000);
}

/**
 * Generate and initialize table of contents
 */
function initializeTableOfContents() {
  const headings = document.querySelectorAll('.legal-section h2');
  if (headings.length === 0) return;

  // Check if TOC already exists
  let toc = document.querySelector('.toc');
  if (!toc) {
    toc = createTableOfContents(headings);
    const container = document.querySelector('.legal-container');
    if (container) {
      container.insertBefore(toc, container.firstChild);
    }
  }

  // Highlight current section in TOC
  initializeTOCHighlight(headings);
}

/**
 * Create table of contents element
 */
function createTableOfContents(headings) {
  const toc = document.createElement('div');
  toc.className = 'toc';
  
  const title = document.createElement('h3');
  title.textContent = 'Table of Contents';
  toc.appendChild(title);
  
  const list = document.createElement('ul');
  
  headings.forEach((heading, index) => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    
    // Create ID if it doesn't exist
    if (!heading.id) {
      heading.id = `section-${index + 1}`;
    }
    
    a.href = `#${heading.id}`;
    a.textContent = heading.textContent;
    a.dataset.sectionIndex = index;
    
    li.appendChild(a);
    list.appendChild(li);
  });
  
  toc.appendChild(list);
  return toc;
}

/**
 * Highlight current section in TOC based on scroll position
 */
function initializeTOCHighlight(headings) {
  const tocLinks = document.querySelectorAll('.toc a');
  
  const observerOptions = {
    threshold: 0.5,
    rootMargin: '-100px 0px -50% 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        tocLinks.forEach(link => {
          link.style.fontWeight = '';
          link.style.color = '';
        });
        
        const activeLink = document.querySelector(`.toc a[href="#${id}"]`);
        if (activeLink) {
          activeLink.style.fontWeight = '700';
          activeLink.style.color = '#00c006';
        }
      }
    });
  }, observerOptions);

  headings.forEach(heading => observer.observe(heading));
}

/**
 * Initialize scroll to top button
 */
function initializeScrollToTop() {
  // Create scroll to top button
  const scrollBtn = document.createElement('button');
  scrollBtn.className = 'scroll-to-top';
  scrollBtn.innerHTML = '↑';
  scrollBtn.title = 'Scroll to top';
  scrollBtn.style.cssText = `
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 50px;
    height: 50px;
    background: linear-gradient(135deg, #00c006, #00a005);
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 1.5rem;
    cursor: pointer;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0, 192, 6, 0.3);
  `;

  document.body.appendChild(scrollBtn);

  // Show/hide button based on scroll position
  window.addEventListener('scroll', () => {
    if (window.pageYOffset > 300) {
      scrollBtn.style.opacity = '1';
      scrollBtn.style.visibility = 'visible';
    } else {
      scrollBtn.style.opacity = '0';
      scrollBtn.style.visibility = 'hidden';
    }
  });

  // Scroll to top on click
  scrollBtn.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });

  // Hover effect
  scrollBtn.addEventListener('mouseenter', function() {
    this.style.transform = 'scale(1.1) translateY(-5px)';
    this.style.boxShadow = '0 8px 20px rgba(0, 192, 6, 0.4)';
  });

  scrollBtn.addEventListener('mouseleave', function() {
    this.style.transform = 'scale(1)';
    this.style.boxShadow = '0 4px 12px rgba(0, 192, 6, 0.3)';
  });
}

/**
 * Add copy-to-clipboard functionality for important sections
 */
function initializeCopyFeature() {
  const sections = document.querySelectorAll('.legal-section');
  
  sections.forEach(section => {
    const heading = section.querySelector('h2');
    if (!heading) return;

    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-section-btn';
    copyBtn.innerHTML = '📋';
    copyBtn.title = 'Copy section content';
    copyBtn.style.cssText = `
      margin-left: 1rem;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 1.2rem;
      opacity: 0;
      transition: opacity 0.3s ease;
    `;

    heading.appendChild(copyBtn);

    section.addEventListener('mouseenter', () => {
      copyBtn.style.opacity = '0.6';
    });

    section.addEventListener('mouseleave', () => {
      copyBtn.style.opacity = '0';
    });

    copyBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const text = section.innerText;
      
      try {
        await navigator.clipboard.writeText(text);
        copyBtn.innerHTML = '✓';
        copyBtn.style.color = '#00c006';
        
        setTimeout(() => {
          copyBtn.innerHTML = '📋';
          copyBtn.style.color = '';
        }, 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    });
  });
}

initializeCopyFeature();

/**
 * Add last updated animation
 */
function animateLastUpdated() {
  const lastUpdated = document.querySelector('.page-header p');
  if (!lastUpdated) return;

  setInterval(() => {
    lastUpdated.style.animation = 'none';
    setTimeout(() => {
      lastUpdated.style.animation = 'pulse 1s ease-out';
    }, 10);
  }, 5000);
}

animateLastUpdated();

/**
 * Print page functionality
 */
function initializePrintButton() {
  const container = document.querySelector('.legal-container');
  if (!container) return;

  const printBtn = document.createElement('button');
  printBtn.className = 'print-btn';
  printBtn.innerHTML = '🖨️ Print This Page';
  printBtn.style.cssText = `
    display: block;
    margin: 2rem auto 0;
    padding: 1rem 2rem;
    background: linear-gradient(135deg, #2c3e50, #34495e);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
  `;

  printBtn.addEventListener('click', () => {
    window.print();
  });

  printBtn.addEventListener('mouseenter', function() {
    this.style.background = 'linear-gradient(135deg, #00c006, #00a005)';
    this.style.transform = 'translateY(-3px)';
    this.style.boxShadow = '0 8px 20px rgba(0, 192, 6, 0.3)';
  });

  printBtn.addEventListener('mouseleave', function() {
    this.style.background = 'linear-gradient(135deg, #2c3e50, #34495e)';
    this.style.transform = 'translateY(0)';
    this.style.boxShadow = '';
  });

  container.appendChild(printBtn);
}

initializePrintButton();