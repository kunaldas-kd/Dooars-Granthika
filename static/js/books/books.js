/* =============================================================
   book_form.js  —  Dooars Granthika  |  Add / Edit Book form
   Place at:  static/js/books/book_form.js

   Depends on:  books.js  (loaded before this file)
   Django context values are injected via data-* attributes on
   <div id="bookFormMeta"> in the template.
   ============================================================= */

"use strict";

(function () {

  /* ── Read Django-rendered context from the DOM ── */
  const meta       = document.getElementById("bookFormMeta");
  const importStep = meta ? meta.dataset.importStep : "";   // "preview" | ""


  /* ─────────────────────────────────────────────────────────
     1.  TAB SWITCHING  (Manual Entry  /  Import from Excel)
  ───────────────────────────────────────────────────────── */

  const tabBtns   = document.querySelectorAll(".form-tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  function activateTab(name) {
    tabBtns.forEach(function (b) {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    tabPanels.forEach(function (p) {
      p.classList.toggle("active", p.id === "tab-" + name);
    });
  }

  tabBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      activateTab(btn.dataset.tab);
    });
  });

  /* Auto-open the import tab when the server returned a preview */
  if (importStep === "preview") {
    activateTab("import");
  }


  /* ─────────────────────────────────────────────────────────
     2.  MANUAL TAB — new-category live hint
  ───────────────────────────────────────────────────────── */

  var catDrop = document.getElementById("id_category");
  var newCat  = document.getElementById("id_new_category");
  var hint    = document.getElementById("newCatHint");

  if (catDrop && newCat && hint) {

    catDrop.addEventListener("change", function () {
      if (catDrop.value) {
        newCat.value = "";
        hideHint();
      }
    });

    newCat.addEventListener("input", function () {
      var v = this.value.trim();
      if (v) {
        catDrop.value = "";
        checkDuplicate(v);
      } else {
        hideHint();
      }
    });

    function existingCatNames() {
      return Array.from(catDrop.options)
        .filter(function (o) { return o.value; })
        .map(function (o) { return o.text.trim().toLowerCase(); });
    }

    function checkDuplicate(v) {
      if (existingCatNames().includes(v.toLowerCase())) {
        showHint("↩ Will reuse existing category", "#1a6fd4", "#e0edff");
      } else {
        showHint("✦ New category will be created", "#059669", "#dcfce7");
      }
    }

    function showHint(text, color, bg) {
      hint.textContent        = text;
      hint.style.color        = color;
      hint.style.background   = bg;
      hint.style.display      = "inline-block";
    }

    function hideHint() {
      hint.style.display = "none";
    }
  }


  /* ─────────────────────────────────────────────────────────
     3.  COVER IMAGE — live preview
  ───────────────────────────────────────────────────────── */

  var coverInput       = document.getElementById("id_cover_image");
  var coverPreviewImg  = document.getElementById("coverPreviewImg");
  var coverPlaceholder = document.getElementById("coverPlaceholder");
  var coverFilenameWrap = document.getElementById("coverFilenameWrap");
  var coverFilenameTxt  = document.getElementById("coverFilenameTxt");
  var coverClearBtn     = document.getElementById("coverClearBtn");
  var coverOverlay      = coverPreviewImg
                          ? coverPreviewImg.parentElement.querySelector(".cover-preview-overlay")
                          : null;

  function showCoverPreview(file) {
    if (!file || !coverPreviewImg) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      coverPreviewImg.src          = e.target.result;
      coverPreviewImg.style.display = "block";
      if (coverPlaceholder) coverPlaceholder.style.display = "none";
      if (coverOverlay)     coverOverlay.style.display     = "";
    };
    reader.readAsDataURL(file);
  }

  function resetCoverPreview() {
    if (!coverPreviewImg) return;
    /* Restore to whatever the server originally rendered */
    var origSrc = coverPreviewImg.dataset.origSrc || "";
    if (origSrc) {
      coverPreviewImg.src           = origSrc;
      coverPreviewImg.style.display = "block";
      if (coverPlaceholder) coverPlaceholder.style.display = "none";
    } else {
      coverPreviewImg.style.display = "none";
      if (coverPlaceholder) coverPlaceholder.style.display = "";
      if (coverOverlay)     coverOverlay.style.display     = "none";
    }
    if (coverFilenameWrap) coverFilenameWrap.style.display = "none";
    if (coverFilenameTxt)  coverFilenameTxt.textContent    = "";
  }

  /* Stash the original src so we can restore on cancel */
  if (coverPreviewImg && coverPreviewImg.src) {
    coverPreviewImg.dataset.origSrc = coverPreviewImg.src;
  }

  if (coverInput) {
    coverInput.addEventListener("change", function () {
      if (this.files && this.files[0]) {
        var file = this.files[0];
        showCoverPreview(file);
        if (coverFilenameTxt)  coverFilenameTxt.textContent    = file.name;
        if (coverFilenameWrap) coverFilenameWrap.style.display = "flex";
      }
    });
  }

  if (coverClearBtn) {
    coverClearBtn.addEventListener("click", function () {
      if (coverInput) {
        /* Reset the file input */
        coverInput.value = "";
        /* Dispatch change so any other listeners know */
        coverInput.dispatchEvent(new Event("change"));
      }
      resetCoverPreview();
    });
  }

  /* Make the whole preview pane clickable to trigger file picker */
  var coverPane = document.getElementById("coverPreviewPane");
  if (coverPane && coverInput) {
    coverPane.style.cursor = "pointer";
    coverPane.addEventListener("click", function (e) {
      if (e.target !== coverInput && !coverClearBtn.contains(e.target)) {
        coverInput.click();
      }
    });
  }


  /* ─────────────────────────────────────────────────────────
     4.  IMPORT TAB — drag-and-drop + file name display
  ───────────────────────────────────────────────────────── */

  var uploadZone  = document.getElementById("uploadZone");
  var excelInput  = document.getElementById("excelFileInput");
  var filenameWrap = document.getElementById("uploadFilename");
  var filenameTxt  = document.getElementById("uploadFilenameTxt");
  var previewBtn   = document.getElementById("uploadPreviewBtn");

  function setSelectedFile(file) {
    if (filenameTxt)  filenameTxt.textContent    = file.name;
    if (filenameWrap) filenameWrap.style.display = "block";
    if (previewBtn)   previewBtn.disabled        = false;
  }

  if (excelInput) {
    excelInput.addEventListener("change", function () {
      if (this.files.length) setSelectedFile(this.files[0]);
    });
  }

  if (uploadZone) {
    uploadZone.addEventListener("dragover", function (e) {
      e.preventDefault();
      uploadZone.classList.add("drag-over");
    });

    uploadZone.addEventListener("dragleave", function () {
      uploadZone.classList.remove("drag-over");
    });

    uploadZone.addEventListener("drop", function (e) {
      e.preventDefault();
      uploadZone.classList.remove("drag-over");
      if (e.dataTransfer.files.length) {
        excelInput.files = e.dataTransfer.files;
        setSelectedFile(e.dataTransfer.files[0]);
      }
    });
  }


  /* ─────────────────────────────────────────────────────────
     5.  IMPORT PREVIEW — select-all checkbox sync
  ───────────────────────────────────────────────────────── */

  var selectAllChk = document.getElementById("selectAllChk");
  var rowChks      = Array.from(document.querySelectorAll(".row-chk"));

  function syncSelectAll() {
    if (!selectAllChk || !rowChks.length) return;
    var checkedCount = rowChks.filter(function (c) { return c.checked; }).length;
    selectAllChk.checked       = checkedCount === rowChks.length;
    selectAllChk.indeterminate = checkedCount > 0 && checkedCount < rowChks.length;
  }

  if (selectAllChk && rowChks.length) {
    syncSelectAll();

    selectAllChk.addEventListener("change", function () {
      rowChks.forEach(function (c) { c.checked = selectAllChk.checked; });
    });

    rowChks.forEach(function (c) {
      c.addEventListener("change", syncSelectAll);
    });
  }


  /* ─────────────────────────────────────────────────────────
     6.  IMPORT CONFIRM — prevent double-submit
  ───────────────────────────────────────────────────────── */

  var confirmForm = document.getElementById("importConfirmForm");
  var confirmBtn  = document.getElementById("confirmImportBtn");

  if (confirmForm && confirmBtn) {
    confirmForm.addEventListener("submit", function () {
      confirmBtn.disabled   = true;
      confirmBtn.innerHTML  = '<i class="fas fa-spinner fa-spin"></i> Importing…';
    });
  }

})();

/* =============================================================
   books.js  —  Dooars Granthika  |  Books module shared JS
   Place at:  static/js/books/books.js

   Handles:
     1. Animated stat counters  (data-count attributes)
     2. Animated progress bars  (data-width attributes)
     3. Client-side table sort  (books list page)
     4. Client-side search highlight
   ============================================================= */

"use strict";

(function () {

  /* ─────────────────────────────────────────────────────────
     1.  STAT COUNTER ANIMATION
         Counts up from 0 to [data-count] over ~900 ms.
  ───────────────────────────────────────────────────────── */

  function animateCounters() {
    var counters = document.querySelectorAll("[data-count]");
    if (!counters.length) return;

    counters.forEach(function (el) {
      var target   = parseInt(el.getAttribute("data-count"), 10);
      if (isNaN(target)) return;

      var duration = 900;
      var start    = performance.now();

      function step(now) {
        var elapsed  = now - start;
        var progress = Math.min(elapsed / duration, 1);
        var eased    = 1 - Math.pow(1 - progress, 3);   // ease-out cubic
        el.textContent = Math.round(eased * target);
        if (progress < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }


  /* ─────────────────────────────────────────────────────────
     2.  PROGRESS BAR ANIMATION
         Transitions each [data-width] segment from 0 → N%.
         The slight delay lets the browser paint width:0%
         before the CSS transition fires.
  ───────────────────────────────────────────────────────── */

  function animateProgressBars() {
    var segments = document.querySelectorAll("[data-width]");
    if (!segments.length) return;

    setTimeout(function () {
      segments.forEach(function (el) {
        var w = parseFloat(el.getAttribute("data-width"));
        if (!isNaN(w)) el.style.width = w + "%";
      });
    }, 120);
  }


  /* ─────────────────────────────────────────────────────────
     3.  CLIENT-SIDE TABLE SORT
         Click any <th data-sort-col="N"> to sort by column N.
  ───────────────────────────────────────────────────────── */

  function initTableSort() {
    var tables = document.querySelectorAll(".books-table");
    tables.forEach(function (table) {
      var ths   = table.querySelectorAll("thead th[data-sort-col]");
      var tbody = table.querySelector("tbody");
      if (!ths.length || !tbody) return;

      var currentCol = null, ascending = true;

      ths.forEach(function (th) {
        th.addEventListener("click", function () {
          var col = parseInt(th.getAttribute("data-sort-col"), 10);
          if (currentCol === col) { ascending = !ascending; }
          else { currentCol = col; ascending = true; }

          ths.forEach(function (h) { h.classList.remove("sorted"); });
          th.classList.add("sorted");

          var rows = Array.from(tbody.querySelectorAll("tr"));
          rows.sort(function (a, b) {
            var at = a.cells[col] ? a.cells[col].textContent.trim() : "";
            var bt = b.cells[col] ? b.cells[col].textContent.trim() : "";
            var an = parseFloat(at.replace(/[^0-9.\-]/g, ""));
            var bn = parseFloat(bt.replace(/[^0-9.\-]/g, ""));
            var res = (!isNaN(an) && !isNaN(bn))
              ? an - bn
              : at.localeCompare(bt, undefined, { sensitivity: "base" });
            return ascending ? res : -res;
          });
          rows.forEach(function (r) { tbody.appendChild(r); });
        });
      });
    });
  }


  /* ─────────────────────────────────────────────────────────
     4.  LIVE SEARCH HIGHLIGHT
         Wraps matching text in <mark> in title cells.
  ───────────────────────────────────────────────────────── */

  function initSearchHighlight() {
    var input = document.querySelector(".search-input");
    if (!input) return;

    function highlight(q) {
      document.querySelectorAll(".book-title-cell").forEach(function (cell) {
        var plain = cell.getAttribute("data-plain") || cell.textContent;
        if (!cell.getAttribute("data-plain")) cell.setAttribute("data-plain", plain);
        if (!q) { cell.textContent = plain; return; }
        var re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
        cell.innerHTML = plain.replace(re, "<mark>$1</mark>");
      });
    }

    if (input.value.trim()) highlight(input.value.trim());
    input.addEventListener("input", function () { highlight(this.value.trim()); });
  }


  /* ─────────────────────────────────────────────────────────
     INIT
  ───────────────────────────────────────────────────────── */

  function init() {
    animateCounters();
    animateProgressBars();
    initTableSort();
    initSearchHighlight();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();