/**
 * Sign In Authentication
 */

// ===========================
// Message Display
// ===========================
function showMessage(message, type = "success") {
  const msgBox = document.getElementById("status-msg");
  if (msgBox) {
    msgBox.textContent = message;
    msgBox.className = `status ${type}`;
    setTimeout(() => {
      msgBox.textContent = "";
      msgBox.className = "status";
    }, type === "success" ? 8000 : 5000);
  }
}

// ===========================
// Login
// ===========================
async function login() {
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  const savePasswordCheckbox = document.getElementById("savePassword");
  const loginBtn = document.getElementById("loginBtn");
  const btnText = loginBtn?.querySelector(".btn-text");
  const spinner = loginBtn?.querySelector(".loading-spinner");

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();
  const savePassword = savePasswordCheckbox?.checked ?? false;

  if (!username || !password) {
    showMessage("⚠️ Please enter User ID and Password!", "warning");
    return;
  }

  if (btnText) btnText.textContent = "Logging in...";
  if (spinner) spinner.style.display = "inline-block";
  if (loginBtn) loginBtn.disabled = true;

  try {
    if (window.pywebview?.api?.login) {
      const response = await window.pywebview.api.login(username, password, savePassword);
      if (response === true) {
        showMessage("✅ Login Successful!", "success");
      } else {
        showMessage("❌ Login Failed: " + response, "error");
      }
    } else {
      // Django fallback — submit form normally
      document.getElementById("loginForm")?.submit();
    }
  } catch (error) {
    console.error("Login error:", error);
    showMessage("❌ Login Error: " + error.message, "error");
  } finally {
    if (btnText) btnText.textContent = "Sign In";
    if (spinner) spinner.style.display = "none";
    if (loginBtn) loginBtn.disabled = false;
  }
}

// ===========================
// Go Back (PyWebView)
// ===========================
function goBack() {
  if (window.pywebview?.api?.go_back) {
    window.pywebview.api.go_back();
  } else {
    window.history.back();
  }
}

// ===========================
// Init
// ===========================
document.addEventListener("DOMContentLoaded", function () {
  console.log("sign_in.js loaded");

  const loginBtn = document.getElementById("loginBtn");

  // PyWebView: intercept click; Django: let form submit naturally
  if (loginBtn && window.pywebview) {
    loginBtn.addEventListener("click", function (e) {
      e.preventDefault();
      login();
    });
  }
});