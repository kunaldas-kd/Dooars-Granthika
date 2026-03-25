/**
 * library_setup.js
 * Handles: live preview sync, day toggles, form validation,
 *          AJAX code regen, AJAX submit, success modal.
 *
 * Borrow-limit fields are shown/hidden based on institute_type:
 *   "Institution"  → Student Borrow Limit + Teacher/Faculty Limit
 *   anything else  → Max Books / Member
 */

document.addEventListener("DOMContentLoaded", function () {

  // ── Element references ──────────────────────────────────────
  const form         = document.getElementById("setupForm");
  const activateBtn  = document.getElementById("activateBtn");
  const btnInner     = activateBtn?.querySelector(".btn-inner");
  const btnLoading   = activateBtn?.querySelector(".btn-loading");
  const successModal = document.getElementById("successModal");
  const modalCode    = document.getElementById("modalCode");
  const modalGoDash  = document.getElementById("modalGoDash");
  const regenBtn     = document.getElementById("regenBtn");
  const codeInput    = document.getElementById("libraryCode");

  // Institute type from server
  const instituteType = (document.getElementById("instituteType")?.value || "").trim();
  const isInstitution = instituteType === "Institution";

  // ── CSRF ─────────────────────────────────────────────────────
  function getCookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : null;
  }
  const csrfToken = getCookie("csrftoken");

  // ── Show / hide borrow-limit fields by institute type ────────
  function applyInstituteType() {
    const fgSbl = document.getElementById("fg-sbl");
    const fgTbl = document.getElementById("fg-tbl");
    const fgMb  = document.getElementById("fg-mb");

    const sblInput = document.getElementById("studentBorrowLimit");
    const tblInput = document.getElementById("teacherBorrowLimit");
    const mbInput  = document.getElementById("maxBooks");

    if (isInstitution) {
      // Show student + teacher limits; hide generic max
      if (fgSbl) fgSbl.style.display = "";
      if (fgTbl) fgTbl.style.display = "";
      if (fgMb)  fgMb.style.display  = "none";

      if (sblInput) sblInput.setAttribute("required", "required");
      if (tblInput) tblInput.setAttribute("required", "required");
      if (mbInput)  mbInput.removeAttribute("required");
    } else {
      // Show generic max; hide role-specific limits
      if (fgSbl) fgSbl.style.display = "none";
      if (fgTbl) fgTbl.style.display = "none";
      if (fgMb)  fgMb.style.display  = "";

      if (mbInput)  mbInput.setAttribute("required", "required");
      if (sblInput) sblInput.removeAttribute("required");
      if (tblInput) tblInput.removeAttribute("required");
    }
  }

  applyInstituteType(); // run immediately on page load

  // ── Working day toggles ─────────────────────────────────────
  const dayBtns          = document.querySelectorAll(".day-btn");
  const workingDaysInput = document.getElementById("workingDaysInput");

  dayBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      btn.classList.toggle("selected");
      syncWorkingDays();
      updatePreview();
      clearFieldError("fg-days");
    });
  });

  function syncWorkingDays() {
    const sel = [...document.querySelectorAll(".day-btn.selected")].map(b => b.dataset.day);
    workingDaysInput.value = sel.join(",");
  }

  // ── AJAX: Regen library code ─────────────────────────────────
  if (regenBtn && codeInput) {
    regenBtn.addEventListener("click", async () => {
      regenBtn.disabled = true;
      regenBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      try {
        const res  = await fetch("/authentication/library_setup/regen_code/", {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await res.json();
        if (data.ok) {
          codeInput.value           = data.code;
          updatePreview();
          regenBtn.innerHTML        = '<i class="fas fa-check"></i>';
          regenBtn.style.background = "var(--success)";
          regenBtn.style.color      = "#fff";
          setTimeout(() => {
            regenBtn.innerHTML        = '<i class="fas fa-sync-alt"></i>';
            regenBtn.style.background = "";
            regenBtn.style.color      = "";
            regenBtn.disabled         = false;
          }, 1200);
        } else {
          showToast("Could not generate a new code. Try again.", "error");
          regenBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
          regenBtn.disabled  = false;
        }
      } catch {
        showToast("Network error. Try again.", "error");
        regenBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
        regenBtn.disabled  = false;
      }
    });
  }

  // ── Live Preview ─────────────────────────────────────────────
  function updatePreview() {
    // Library Code
    const svCode = document.getElementById("sv-code");
    if (svCode && codeInput) svCode.textContent = codeInput.value || "DG-XXXX";

    // Timezone
    const tzEl = document.getElementById("timezone");
    const svTz = document.getElementById("sv-tz");
    if (svTz && tzEl) {
      const opt = tzEl.options[tzEl.selectedIndex];
      svTz.textContent = opt?.value ? opt.text.split(" — ")[0] : "—";
    }

    if (isInstitution) {
      // Student Borrow Limit
      const sblEl = document.getElementById("studentBorrowLimit");
      const svSbl = document.getElementById("sv-sbl");
      if (svSbl && sblEl) {
        const v = parseInt(sblEl.value);
        svSbl.textContent = isNaN(v) ? "— books" : v + " book" + (v === 1 ? "" : "s");
      }

      // Teacher Borrow Limit
      const tblEl = document.getElementById("teacherBorrowLimit");
      const svTbl = document.getElementById("sv-tbl");
      if (svTbl && tblEl) {
        const v = parseInt(tblEl.value);
        svTbl.textContent = isNaN(v) ? "— books" : v + " book" + (v === 1 ? "" : "s");
      }

      // Hide the generic max row in preview
      const svMbRow = document.getElementById("sv-mb-row");
      if (svMbRow) svMbRow.style.display = "none";

    } else {
      // Max Books per Member
      const mbEl = document.getElementById("maxBooks");
      const svMb = document.getElementById("sv-mb");
      if (svMb && mbEl) {
        const v = parseInt(mbEl.value);
        svMb.textContent = isNaN(v) ? "— books" : v + " book" + (v === 1 ? "" : "s");
      }

      // Hide the role-specific rows in preview
      const svSblRow = document.getElementById("sv-sbl-row");
      const svTblRow = document.getElementById("sv-tbl-row");
      if (svSblRow) svSblRow.style.display = "none";
      if (svTblRow) svTblRow.style.display = "none";
    }

    // Late Fine
    const lfEl = document.getElementById("lateFine");
    const svLf = document.getElementById("sv-lf");
    if (svLf && lfEl) {
      const v = parseFloat(lfEl.value);
      svLf.textContent = isNaN(v) ? "—" : (v === 0 ? "Disabled" : "₹" + v.toFixed(2) + "/day");
    }

    // Working Days
    const svDays = document.getElementById("sv-days");
    if (svDays) {
      const sel = [...document.querySelectorAll(".day-btn.selected")].map(b => b.dataset.day);
      svDays.textContent = sel.length ? sel.join(", ") : "—";
    }
  }

  // Attach preview listeners
  ["timezone", "studentBorrowLimit", "teacherBorrowLimit", "maxBooks", "lateFine"].forEach(id => {
    document.getElementById(id)?.addEventListener("input",  updatePreview);
    document.getElementById(id)?.addEventListener("change", updatePreview);
  });

  updatePreview();

  // ── Validation ───────────────────────────────────────────────
  // Validators are built dynamically based on institute type
  function getValidators() {
    const base = [
      { groupId: "fg-tz", inputId: "timezone", check: v => v && v !== "" },
      { groupId: "fg-lf", inputId: "lateFine", check: v => { const n = parseFloat(v); return !isNaN(n) && n >= 0; } },
    ];

    if (isInstitution) {
      base.push(
        { groupId: "fg-sbl", inputId: "studentBorrowLimit", check: v => { const n = parseInt(v); return !isNaN(n) && n >= 1 && n <= 50; } },
        { groupId: "fg-tbl", inputId: "teacherBorrowLimit", check: v => { const n = parseInt(v); return !isNaN(n) && n >= 1 && n <= 50; } }
      );
    } else {
      base.push(
        { groupId: "fg-mb", inputId: "maxBooks", check: v => { const n = parseInt(v); return !isNaN(n) && n >= 1 && n <= 50; } }
      );
    }

    return base;
  }

  function validateField({ groupId, inputId, check }) {
    const group = document.getElementById(groupId);
    const input = document.getElementById(inputId);
    if (!group || !input) return true;
    const ok = check(input.value);
    group.classList.toggle("error", !ok);
    group.classList.toggle("valid",  ok);
    return ok;
  }

  function validateAll() {
    let ok = getValidators().every(v => validateField(v));

    const selectedDays = document.querySelectorAll(".day-btn.selected");
    const daysGroup    = document.getElementById("fg-days");
    const daysErr      = document.getElementById("err-days");
    if (selectedDays.length === 0) {
      daysGroup?.classList.add("error");
      if (daysErr) daysErr.style.display = "block";
      ok = false;
    } else {
      daysGroup?.classList.remove("error");
      if (daysErr) daysErr.style.display = "none";
    }
    return ok;
  }

  function clearFieldError(groupId) {
    document.getElementById(groupId)?.classList.remove("error");
  }

  function applyServerErrors(errors) {
    const fieldMap = {
      timezone:             "fg-tz",
      student_borrow_limit: "fg-sbl",
      teacher_borrow_limit: "fg-tbl",
      max_books_per_member: "fg-mb",
      late_fine:            "fg-lf",
      working_days:         "fg-days",
    };
    Object.entries(errors).forEach(([field, msg]) => {
      const gid = fieldMap[field];
      if (gid) {
        document.getElementById(gid)?.classList.add("error");
        const shortKey = gid.replace("fg-", "");
        const errEl = document.getElementById("err-" + shortKey);
        if (errEl) { errEl.textContent = msg; errEl.style.display = "block"; }
      } else {
        showToast(msg, "error");
      }
    });
    form?.querySelector(".field-group.error")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // Attach blur/input validators
  getValidators().forEach(({ groupId, inputId, check }) => {
    const input = document.getElementById(inputId);
    input?.addEventListener("blur", () => validateField({ groupId, inputId, check }));
    input?.addEventListener("input", () => {
      if (document.getElementById(groupId)?.classList.contains("error")) {
        validateField({ groupId, inputId, check });
      }
    });
  });

  // ── AJAX Submit ──────────────────────────────────────────────
  form?.addEventListener("submit", async function (e) {
    e.preventDefault();

    if (!validateAll()) {
      form.querySelector(".field-group.error")?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    setLoading(true);

    try {
      const res  = await fetch(form.action || window.location.href, {
        method:  "POST",
        headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" },
        body:    new FormData(form),
      });
      const data = await res.json();

      if (data.ok) {
        showSuccessModal(data.code);
      } else {
        if (data.errors && Object.keys(data.errors).length) {
          applyServerErrors(data.errors);
        } else {
          showToast("Setup failed. Please try again.", "error");
        }
        setLoading(false);
      }
    } catch (err) {
      console.error("Setup submit error:", err);
      showToast("Network error. Please check your connection.", "error");
      setLoading(false);
    }
  });

  function setLoading(on) {
    if (btnInner)    btnInner.style.display   = on ? "none" : "flex";
    if (btnLoading)  btnLoading.style.display = on ? "flex"  : "none";
    if (activateBtn) activateBtn.disabled     = on;
  }

  // ── Success modal ────────────────────────────────────────────
  function showSuccessModal(code) {
    if (modalCode) modalCode.textContent = code || codeInput?.value || "DG-XXXX";
    successModal?.classList.add("show");
    successModal?.setAttribute("aria-hidden", "false");
  }

  modalGoDash?.addEventListener("click", () => {
    window.location.href = "/authentication/admin_dashboard/";
  });

  successModal?.addEventListener("click", e => {
    if (e.target === successModal) successModal.classList.remove("show");
  });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && successModal?.classList.contains("show")) {
      successModal.classList.remove("show");
    }
  });

  // ── Toast ────────────────────────────────────────────────────
  function showToast(message, type = "info") {
    document.getElementById("setup-toast")?.remove();
    const colors = { success: "var(--success)", error: "var(--error)", info: "var(--ink-accent)" };
    const toast  = document.createElement("div");
    toast.id = "setup-toast";
    toast.style.cssText = `
      position:fixed; bottom:28px; left:50%;
      transform:translateX(-50%) translateY(20px);
      background:var(--bg-card); color:var(--text-primary);
      border:1px solid var(--border-light);
      border-left:4px solid ${colors[type] || colors.info};
      border-radius:8px; padding:13px 22px;
      font-size:13.5px; font-weight:500;
      box-shadow:var(--shadow-lg); z-index:999;
      opacity:0; transition:opacity .25s ease,transform .25s ease;
      font-family:'Inter',sans-serif; max-width:420px; text-align:center;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => {
      toast.style.opacity   = "1";
      toast.style.transform = "translateX(-50%) translateY(0)";
    });
    setTimeout(() => {
      toast.style.opacity   = "0";
      toast.style.transform = "translateX(-50%) translateY(10px)";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

});