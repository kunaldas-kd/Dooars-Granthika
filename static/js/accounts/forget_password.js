/**
 * forget_password.js — Dooars Granthika
 * Handles form validation, submission UX, and feedback for the
 * Forgot Password page.
 */

(function () {
  "use strict";

  /* ── DOM refs ── */
  const form       = document.getElementById("forgotPasswordForm");
  const emailInput = document.getElementById("email");
  const submitBtn  = document.getElementById("submitBtn");
  const statusMsg  = document.getElementById("status-msg");
  const formGroup  = emailInput?.closest(".form-group");
  const errorSmall = formGroup?.querySelector(".error-message");

  if (!form || !emailInput || !submitBtn) return; // safety guard

  /* ── Helpers ── */

  /**
   * Simple RFC5322-lite email check.
   * @param {string} val
   * @returns {boolean}
   */
  function isValidEmail(val) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(val.trim());
  }

  /**
   * Show an inline error on the email field.
   * @param {string} msg
   */
  function showFieldError(msg) {
    formGroup.classList.add("has-error");
    if (errorSmall) errorSmall.textContent = msg;
    // Shake the input wrapper for tactile feedback
    const wrapper = formGroup.querySelector(".input-wrapper");
    wrapper.classList.remove("shake");
    // Force reflow so the animation replays
    void wrapper.offsetWidth;
    wrapper.classList.add("shake");
    wrapper.addEventListener("animationend", () => wrapper.classList.remove("shake"), { once: true });
  }

  /** Clear inline error state */
  function clearFieldError() {
    formGroup.classList.remove("has-error");
    if (errorSmall) errorSmall.textContent = "Enter the email associated with your account";
  }

  /**
   * Update the global status banner.
   * @param {string} msg
   * @param {'info'|'success'|'error'} type
   */
  function setStatus(msg, type = "info") {
    statusMsg.textContent = msg;
    statusMsg.className = "status " + type;
  }

  /** Set button into loading state */
  function setLoading(loading) {
    submitBtn.disabled = loading;
    submitBtn.classList.toggle("loading", loading);
  }

  /* ── Inject progress bar into DOM ── */
  const progressWrap = document.createElement("div");
  progressWrap.className = "progress-bar-wrap";
  const progressBar = document.createElement("div");
  progressBar.className = "progress-bar";
  progressWrap.appendChild(progressBar);
  form.insertBefore(progressWrap, form.firstChild);

  /**
   * Animate the progress bar from 0 → target% over `duration` ms.
   * @param {number} target   0-100
   * @param {number} duration ms
   * @returns {Promise<void>}
   */
  function animateProgress(target, duration = 400) {
    return new Promise((resolve) => {
      progressWrap.classList.add("active");
      progressBar.style.width = target + "%";
      setTimeout(resolve, duration + 50);
    });
  }

  /** Reset the progress bar */
  function resetProgress() {
    progressBar.style.width = "0%";
    setTimeout(() => progressWrap.classList.remove("active"), 300);
  }

  /* ── Inject success state markup ── */
  const successEl = document.createElement("div");
  successEl.className = "success-checkmark";
  successEl.innerHTML = `
    <div class="check-circle">✓</div>
    <div class="success-title">Email Sent!</div>
    <p class="success-msg" id="successEmailMsg">
      We've sent a password reset link to your email address.<br>
      Check your inbox and follow the instructions.
    </p>
  `;
  form.parentNode.insertBefore(successEl, form.nextSibling);

  /** Show the success state, hiding form elements */
  function showSuccess(email) {
    const msgEl = document.getElementById("successEmailMsg");
    if (msgEl) {
      msgEl.innerHTML = `We've sent a password reset link to <strong>${escapeHtml(email)}</strong>.<br>Check your inbox (and spam folder) for further instructions.`;
    }
    form.style.display = "none";
    successEl.classList.add("visible");
    setStatus("Reset link sent successfully!", "success");
  }

  /** Minimal HTML escaper */
  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  /* ── Live validation ── */
  emailInput.addEventListener("input", () => {
    if (formGroup.classList.contains("has-error")) {
      if (isValidEmail(emailInput.value)) clearFieldError();
    }
  });

  emailInput.addEventListener("blur", () => {
    const val = emailInput.value.trim();
    if (val && !isValidEmail(val)) {
      showFieldError("Please enter a valid email address.");
    }
  });

  /* ── Form submission ── */
  form.addEventListener("submit", async function (e) {
    // Always prevent default; Django will handle the POST on valid submit
    // but we enhance the UX before the real request fires.
    const email = emailInput.value.trim();

    /* Client-side validation */
    if (!email) {
      e.preventDefault();
      showFieldError("Email address is required.");
      emailInput.focus();
      return;
    }

    if (!isValidEmail(email)) {
      e.preventDefault();
      showFieldError("Please enter a valid email address.");
      emailInput.focus();
      return;
    }

    /* Clear any previous errors */
    clearFieldError();
    setStatus("", "info");

    /* Enhance submission with loading UX */
    e.preventDefault(); // intercept to show progress, then re-submit
    setLoading(true);

    try {
      await animateProgress(35, 300);
      await animateProgress(70, 400);

      /* Perform the actual fetch POST to Django */
      const formData = new FormData(form);
      const response = await fetch(form.action || window.location.href, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: formData,
      });

      await animateProgress(100, 250);

      if (response.ok) {
        /* Django may return JSON or HTML depending on your view.
           We check for JSON first; otherwise treat any 2xx as success. */
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          const data = await response.json();
          if (data.success === false) {
            throw new Error(data.message || "Something went wrong. Please try again.");
          }
        }
        // Show success state
        setTimeout(() => {
          setLoading(false);
          showSuccess(email);
          resetProgress();
        }, 200);
      } else {
        throw new Error("Server error (" + response.status + "). Please try again.");
      }
    } catch (err) {
      /* Network or server failure — degrade gracefully */
      setLoading(false);
      resetProgress();
      setStatus(err.message || "Unable to send reset link. Please check your connection.", "error");
    }
  });

  /* ── Auto-dismiss Django messages after 6 s ── */
  if (statusMsg && statusMsg.textContent.trim()) {
    setTimeout(() => {
      statusMsg.style.transition = "opacity 0.5s ease";
      statusMsg.style.opacity = "0";
      setTimeout(() => {
        statusMsg.textContent = "";
        statusMsg.style.opacity = "";
        statusMsg.className = "status";
      }, 500);
    }, 6000);
  }

  /* ── Autofocus with smooth scroll-into-view on mobile ── */
  if (window.innerWidth < 768) {
    emailInput.addEventListener("focus", () => {
      setTimeout(() => emailInput.scrollIntoView({ behavior: "smooth", block: "center" }), 320);
    });
  }

})();