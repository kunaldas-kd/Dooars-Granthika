/**
 * Sign Up / Registration Authentication
 * Django POST only — no pywebview dependency.
 */

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const phoneRegex  = /^[+\d][\d\s\-().]{6,19}$/;

const FIELD_IDS = [
  "libraryName", "instituteType", "instituteEmail",
  "phoneNumber", "address", "district", "state", "country"
];

// instituteName validated separately (conditional on instituteType)
const OPTIONAL_FIELDS = ["phoneNumber"];

// ===========================
// Message Display
// ===========================
function showMessage(message, type = "success") {
  const msgBox = document.getElementById("status-msg");
  if (!msgBox) return;
  msgBox.textContent = message;
  msgBox.className = `status ${type}`;
  setTimeout(() => {
    msgBox.textContent = "";
    msgBox.className = "status";
  }, type === "success" ? 8000 : 5000);
}

// ===========================
// Field Validation
// ===========================
function validateField(fieldId) {
  const field = document.getElementById(fieldId);
  const group = document.getElementById(fieldId + "-group");
  if (!field || !group) return true;

  const value      = field.value.trim();
  const isOptional = OPTIONAL_FIELDS.includes(fieldId);
  let   isValid    = true;

  if (!value) {
    if (isOptional) {
      group.classList.remove("error", "success");
      return true;
    }
    isValid = false;
  } else if (fieldId === "instituteType") {
    isValid = value !== "";
  } else if (fieldId === "instituteEmail") {
    isValid = emailRegex.test(value);
  } else if (fieldId === "phoneNumber") {
    isValid = phoneRegex.test(value);
  }

  group.classList.toggle("error",   !isValid);
  group.classList.toggle("success",  isValid);
  return isValid;
}

// ===========================
// Password Validation
// ===========================
function validatePasswords() {
  const pw   = document.getElementById("adminPassword");
  const cpw  = document.getElementById("adminConfirmPassword");
  const pwG  = document.getElementById("adminPassword-group");
  const cpwG = document.getElementById("adminConfirmPassword-group");
  let valid  = true;

  if (!pw?.value || pw.value.length < 8) {
    pwG?.classList.add("error");
    pwG?.classList.remove("success");
    valid = false;
  } else {
    pwG?.classList.remove("error");
    pwG?.classList.add("success");
  }

  if (!cpw?.value || cpw.value !== pw?.value) {
    cpwG?.classList.add("error");
    cpwG?.classList.remove("success");
    valid = false;
  } else {
    cpwG?.classList.remove("error");
    cpwG?.classList.add("success");
  }

  return valid;
}

// ===========================
// Admin Name Validation
// ===========================
function validateAdminFullName() {
  const field = document.getElementById("adminFullName");
  const group = document.getElementById("adminFullName-group");
  if (!field || !group) return true;
  const isValid = field.value.trim().length > 0;
  group.classList.toggle("error",   !isValid);
  group.classList.toggle("success",  isValid);
  return isValid;
}

// ===========================
// Institution Name Validation
// (only when type === Institution)
// ===========================
function validateInstituteName() {
  const group = document.getElementById("instituteName-group");
  if (!group || group.style.display === "none") return true;
  const field   = document.getElementById("instituteName");
  const isValid = field?.value.trim().length > 0;
  group.classList.toggle("error",   !isValid);
  group.classList.toggle("success",  isValid);
  return isValid;
}

// ===========================
// Declaration Validation
// ===========================
function validateDeclaration() {
  const checkbox = document.getElementById("declaration");
  const box      = document.getElementById("declaration-group");
  if (!checkbox || !box) return true;
  const isChecked = checkbox.checked;
  box.classList.toggle("error", !isChecked);
  return isChecked;
}

// ===========================
// Full Form Validation
// ===========================
function validateForm() {
  const main        = FIELD_IDS.every(id => validateField(id));
  const instName    = validateInstituteName();
  const name        = validateAdminFullName();
  const pw          = validatePasswords();
  const declaration = validateDeclaration();
  return main && instName && name && pw && declaration;
}

// ===========================
// Reset Button State
// ===========================
function resetButton() {
  const btn     = document.getElementById("registerBtn");
  const btnText = btn?.querySelector(".btn-text");
  if (!btn) return;
  btn.disabled = false;
  btn.classList.remove("loading");
  if (btnText) btnText.textContent = "Create Library Account";
}

// ===========================
// Init
// ===========================
document.addEventListener("DOMContentLoaded", function () {
  console.log("sign_up.js loaded");

  // ── Logo upload: live preview + validation ────────────────────
  const logoInput    = document.getElementById("libraryLogo");
  const logoPreview  = document.getElementById("logoPreview");
  const logoWrap     = document.getElementById("logoPreviewWrap");
  const logoFileName = document.getElementById("logoFileName");
  const logoError    = document.getElementById("logoError");

  logoInput?.addEventListener("change", function () {
    const file = this.files[0];
    logoError.classList.remove("visible");

    if (!file) {
      logoFileName.textContent = "No file chosen";
      logoWrap.classList.remove("has-upload");
      return;
    }

    // Validate type
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      logoError.classList.add("visible");
      this.value = "";
      logoFileName.textContent = "No file chosen";
      logoWrap.classList.remove("has-upload");
      return;
    }

    // Validate size (2 MB)
    if (file.size > 2 * 1024 * 1024) {
      logoError.classList.add("visible");
      this.value = "";
      logoFileName.textContent = "No file chosen";
      logoWrap.classList.remove("has-upload");
      return;
    }

    // Show preview
    logoFileName.textContent = file.name;
    logoWrap.classList.add("has-upload");
    const reader = new FileReader();
    reader.onload = e => { logoPreview.src = e.target.result; };
    reader.readAsDataURL(file);
  });

  // ── Main fields: blur + live re-validation ────────────────────
  FIELD_IDS.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.addEventListener("blur", () => validateField(fieldId));
    field.addEventListener("input", () => {
      if (document.getElementById(fieldId + "-group")?.classList.contains("error")) {
        validateField(fieldId);
      }
    });
  });

  // ── Password fields ───────────────────────────────────────────
  ["adminPassword", "adminConfirmPassword"].forEach(id => {
    const field = document.getElementById(id);
    field?.addEventListener("blur",  validatePasswords);
    field?.addEventListener("input", () => {
      if (document.getElementById(id + "-group")?.classList.contains("error")) {
        validatePasswords();
      }
    });
  });

  // ── Admin full name ───────────────────────────────────────────
  const nameField = document.getElementById("adminFullName");
  nameField?.addEventListener("blur",  validateAdminFullName);
  nameField?.addEventListener("input", () => {
    if (document.getElementById("adminFullName-group")?.classList.contains("error")) {
      validateAdminFullName();
    }
  });

  // ── Institution name ──────────────────────────────────────────
  const instField = document.getElementById("instituteName");
  instField?.addEventListener("blur",  validateInstituteName);
  instField?.addEventListener("input", () => {
    if (document.getElementById("instituteName-group")?.classList.contains("error")) {
      validateInstituteName();
    }
  });

  // ── Declaration checkbox ──────────────────────────────────────
  document.getElementById("declaration")
    ?.addEventListener("change", () => {
      if (document.getElementById("declaration-group")?.classList.contains("error")) {
        validateDeclaration();
      }
    });

  // ── Institute type → show / hide institution name ─────────────
  const instituteType      = document.getElementById("instituteType");
  const instituteNameGroup = document.getElementById("instituteName-group");
  const instituteNameInput = document.getElementById("instituteName");

  if (instituteType && instituteNameGroup && instituteNameInput) {
    // Hidden on load
    instituteNameGroup.style.display = "none";

    instituteType.addEventListener("change", function () {
      if (this.value === "Institution") {
        instituteNameGroup.style.display = "block";
      } else {
        instituteNameGroup.style.display = "none";
        instituteNameInput.value = "";
        instituteNameGroup.classList.remove("error", "success");
      }
    });
  }

  // ── Form submit ───────────────────────────────────────────────
  document.getElementById("registrationForm")
    ?.addEventListener("submit", function (e) {
      e.preventDefault();

      if (!validateForm()) {
        showMessage("⚠️ Please fix the errors above before submitting.", "error");
        document.querySelector(".form-group.error")
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }

      // Loading state
      const btn     = document.getElementById("registerBtn");
      const btnText = btn?.querySelector(".btn-text");
      if (btn)     btn.disabled = true;
      if (btn)     btn.classList.add("loading");
      if (btnText) btnText.textContent = "Registering...";

      // Native Django POST
      this.submit();
    });
});