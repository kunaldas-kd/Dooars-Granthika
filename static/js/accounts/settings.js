'use strict';

document.addEventListener('DOMContentLoaded', () => {

  /* ─────────────────────────────────────────────
     Tab switching
     ───────────────────────────────────────────── */
  const tabs       = document.querySelectorAll('.settings-tab');
  const panels     = document.querySelectorAll('.settings-panel');
  const formTypeEl = document.getElementById('form_type');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;

      tabs.forEach(t   => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');

      const panel = document.getElementById(`tab-${target}`);
      if (panel) panel.classList.add('active');
    });
  });


  /* ─────────────────────────────────────────────
     Set form_type hidden field when any submit
     button is clicked — identifies which section
     was saved in the single POST handler.
     ───────────────────────────────────────────── */
  document.getElementById('settings-form')
    .addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-form]');
      if (btn && formTypeEl) {
        formTypeEl.value = btn.dataset.form;
      }
    });


  /* ─────────────────────────────────────────────
     Reopen the correct tab after a POST redirect
     (Django messages will be shown on the page;
      we store the active tab in sessionStorage)
     ───────────────────────────────────────────── */
  const savedTab = sessionStorage.getItem('settings_active_tab');

  if (savedTab) {
    const targetTab   = document.querySelector(`.settings-tab[data-tab="${savedTab}"]`);
    const targetPanel = document.getElementById(`tab-${savedTab}`);

    if (targetTab && targetPanel) {
      tabs.forEach(t   => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      targetTab.classList.add('active');
      targetPanel.classList.add('active');
    }

    sessionStorage.removeItem('settings_active_tab');
  }

  // Save active tab before form submits
  document.getElementById('settings-form').addEventListener('submit', () => {
    const activeTab = document.querySelector('.settings-tab.active');
    if (activeTab) {
      sessionStorage.setItem('settings_active_tab', activeTab.dataset.tab);
    }
  });


  /* ─────────────────────────────────────────────
     Avatar live preview
     ───────────────────────────────────────────── */
  const avatarInput = document.getElementById('avatar-upload');

  if (avatarInput) {
    avatarInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (ev) => {
        let preview = document.getElementById('avatar-preview');

        if (preview.tagName === 'DIV') {
          // Replace placeholder with real img
          const img     = document.createElement('img');
          img.id        = 'avatar-preview';
          img.className = 'avatar-img';
          img.alt       = 'Avatar';
          img.src       = ev.target.result;
          preview.replaceWith(img);
          preview = img;
        } else {
          preview.src = ev.target.result;
        }

        preview.style.animation = 'none';
        requestAnimationFrame(() => {
          preview.style.animation = 'avatar-pop 0.3s ease';
        });
      };

      reader.readAsDataURL(file);
    });
  }


  /* ─────────────────────────────────────────────
     Toast auto-dismiss
     ───────────────────────────────────────────── */
  document.querySelectorAll('.toast').forEach((toast, i) => {
    setTimeout(() => {
      toast.classList.add('hiding');
      toast.addEventListener('animationend', () => toast.remove(), { once: true });
    }, 3500 + i * 400);
  });


  /* ─────────────────────────────────────────────
     Staggered section fade-in (IntersectionObserver)
     ───────────────────────────────────────────── */
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('section-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.06 });

  document.querySelectorAll('.panel-section').forEach((el, i) => {
    el.style.transitionDelay = `${i * 55}ms`;
    el.classList.add('section-hidden');
    observer.observe(el);
  });


  /* ─────────────────────────────────────────────
     Mobile sidebar toggle
     ───────────────────────────────────────────── */
  const sidebar    = document.getElementById('sidebar');
  const menuToggle = document.getElementById('menu-toggle');

  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));

    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          e.target !== menuToggle) {
        sidebar.classList.remove('open');
      }
    });
  }

});


/* ─────────────────────────────────────────────
   Inject animation keyframes
   ───────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `
  @keyframes avatar-pop {
    0%   { transform: scale(0.85); opacity: 0.6; }
    70%  { transform: scale(1.05); }
    100% { transform: scale(1);    opacity: 1; }
  }

  .section-hidden {
    opacity: 0;
    transform: translateY(16px);
    transition: opacity 0.4s ease, transform 0.4s ease;
  }

  .section-visible {
    opacity: 1;
    transform: translateY(0);
  }
`;
document.head.appendChild(style);