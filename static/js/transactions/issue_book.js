/**
 * issue_book.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Architecture
 * ────────────
 * Part 1 — Exact-ID lookup
 *   · Fires ONLY when a suggestion is selected, field is blurred, or Enter/Tab
 *     is pressed.  Does NOT fire on every keystroke.
 *   · Shows inline preview card + syncs sidebar cards.
 *   · Exposes window.triggerMemberLookup / window.triggerBookLookup for Part 2.
 *
 * Part 2 — Live-search suggestion dropdown
 *   · Fires on every keystroke (debounced 220 ms) against the search API.
 *   · Selecting a suggestion fills the input and calls triggerX for instant
 *     exact-ID lookup without going through blur.
 *   · Keyboard: ↑ ↓ navigate · Enter select · Escape close
 *
 * Globals required (set by the template before this file):
 *   window.LIBRARY_RULES      — { defaultLoanDays, fineRatePerDay,
 *                                  maxBorrowLimit,  maxRenewalCount,
 *                                  isInstitute,     studentBorrowLimit,
 *                                  teacherBorrowLimit }
 *   window.MEMBER_LOOKUP_URL  — member_lookup_api URL
 *   window.BOOK_LOOKUP_URL    — book_lookup_api URL
 *   window.MEMBER_SEARCH_URL  — member_search_api URL
 *   window.BOOK_SEARCH_URL    — book_search_api URL
 */

/* ═══════════════════════════════════════════════════════════════════════════
   PART 1 — Exact-ID lookup + sidebar sync
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const memberInput   = document.getElementById('memberIdInput');
  const memberStatus  = document.getElementById('memberIdStatus');
  const memberError   = document.getElementById('memberIdError');
  const memberRow     = memberInput?.closest('.id-field-input-row');
  const memberPreview = document.getElementById('memberPreview');

  const bookInput   = document.getElementById('bookCopyIdInput');
  const bookStatus  = document.getElementById('bookCopyIdStatus');
  const bookError   = document.getElementById('bookCopyIdError');
  const bookRow     = bookInput?.closest('.id-field-input-row');
  const bookPreview = document.getElementById('bookPreview');

  const submitBtn = document.getElementById('submitBtn');
  const form      = document.getElementById('issueBookForm');

  // ── State ─────────────────────────────────────────────────────────────────
  let memberValid = false;
  let bookValid   = false;

  // ── Icons ─────────────────────────────────────────────────────────────────
  const ICON_SPIN  = '<svg viewBox="0 0 20 20" fill="none" style="animation:spin 1s linear infinite"><path d="M10 3a7 7 0 1 1 0 14A7 7 0 0 1 10 3z" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" opacity=".3"/><path d="M10 3a7 7 0 0 1 7 7" stroke="#6366f1" stroke-width="2" stroke-linecap="round"/></svg><style>@keyframes spin{to{transform:rotate(360deg)}}</style>';
  const ICON_OK    = '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" fill="#10b981"/><path d="M7 10l2 2 4-4" stroke="#fff" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_FAIL  = '<svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" fill="#ef4444"/><path d="M8 8l4 4M12 8l-4 4" stroke="#fff" stroke-width="1.75" stroke-linecap="round"/></svg>';
  const ICON_BLANK = '';

  // ── Helpers ───────────────────────────────────────────────────────────────
  function setFieldState(row, statusEl, errorEl, state, errorMsg = '') {
    row.classList.toggle('is-valid',   state === 'ok');
    row.classList.toggle('is-invalid', state === 'error');
    statusEl.innerHTML = state === 'loading' ? ICON_SPIN
                       : state === 'ok'      ? ICON_OK
                       : state === 'error'   ? ICON_FAIL
                       : ICON_BLANK;
    if (errorEl) {
      errorEl.textContent = errorMsg;
      errorEl.classList.toggle('is-hidden', !errorMsg);
    }
  }

  function clearField(row, statusEl, errorEl) {
    setFieldState(row, statusEl, errorEl, 'idle');
  }

  // ── Member lookup ─────────────────────────────────────────────────────────
  function lookupMember(rawVal) {
    const val = rawVal.trim().toUpperCase();
    if (!val) {
      memberValid = false;
      clearField(memberRow, memberStatus, memberError);
      hideMemberPreview();
      syncSidebarMember(null);
      return;
    }
    setFieldState(memberRow, memberStatus, memberError, 'loading');
    fetch(`${window.MEMBER_LOOKUP_URL}?member_id=${encodeURIComponent(val)}`)
      .then(r => r.ok ? r.json() : r.text().then(t => { throw new Error(`Server ${r.status}: ${t.slice(0,120)}`); }))
      .then(data => {
        if (data.found) {
          memberValid = true;
          // Populate hidden form field with the member PK so Django validates correctly
          const hiddenMember = document.getElementById('id_member');
          if (hiddenMember) hiddenMember.value = data.pk;
          setFieldState(memberRow, memberStatus, memberError, 'ok');
          showMemberPreview(data);
          syncSidebarMember(data);
        } else {
          memberValid = false;
          const hiddenMember = document.getElementById('id_member');
          if (hiddenMember) hiddenMember.value = '';
          setFieldState(memberRow, memberStatus, memberError, 'error', data.error || 'Member not found.');
          hideMemberPreview();
          syncSidebarMember(null);
        }
      })
      .catch(err => {
        memberValid = false;
        const hiddenMember = document.getElementById('id_member');
        if (hiddenMember) hiddenMember.value = '';
        setFieldState(memberRow, memberStatus, memberError, 'error', err.message || 'Lookup failed.');
        hideMemberPreview();
      });
  }

  function showMemberPreview(d) {
    if (!memberPreview) return;
    const initial  = (d.name || '?')[0].toUpperCase();
    const photo    = document.getElementById('memberPreviewPhoto');
    const initial_ = document.getElementById('memberPreviewInitial');
    if (photo && initial_) {
      initial_.textContent = initial;
      if (d.photo_url) {
        photo.onerror = () => { photo.style.display = 'none'; initial_.style.display = 'flex'; };
        photo.src = d.photo_url; photo.style.display = 'block'; initial_.style.display = 'none';
      } else {
        photo.style.display = 'none'; initial_.style.display = 'flex';
      }
    }
    document.getElementById('memberPreviewName').textContent  = d.name || '—';
    document.getElementById('memberPreviewMeta').textContent  = [d.role, d.member_id].filter(Boolean).join(' · ');
    document.getElementById('memberPreviewLoans').textContent = d.active_loans ?? '—';
    document.getElementById('memberPreviewSlots').textContent = d.slots === -1 ? '∞' : (d.slots ?? '—');
    const finesEl = document.getElementById('memberPreviewFines');
    const fine = parseFloat(d.total_due || '0');
    finesEl.textContent = fine > 0 ? '₹' + fine.toFixed(2) : '₹0';
    finesEl.style.color = fine > 0 ? '#ef4444' : 'inherit';
    memberPreview.classList.remove('is-hidden');
  }
  function hideMemberPreview() { memberPreview?.classList.add('is-hidden'); }

  // ── Sidebar — member ──────────────────────────────────────────────────────
  function syncSidebarMember(d) {
    const empty   = document.getElementById('sidebarMemberEmpty');
    const details = document.getElementById('sidebarMemberDetails');
    if (!empty || !details) return;
    if (!d) { empty.style.display = ''; details.classList.add('is-hidden'); return; }
    empty.style.display = 'none'; details.classList.remove('is-hidden');
    const $ = id => document.getElementById(id);
    const ne = $('sidebarMemberName'),  te = $('sidebarMemberType'),
          ie = $('sidebarMemberId'),    le = $('sidebarActiveLoans'),
          ce = $('sidebarCanBorrow'),   de = $('sidebarTotalDue'),
          ee = $('sidebarMemberEmail');
    if (ne) ne.textContent = d.name       || '—';
    if (te) te.textContent = d.role        || '—';
    if (ie) ie.textContent = d.member_id   || '—';
    if (le) le.textContent = d.active_loans ?? '—';
    if (ce) ce.textContent = d.slots === -1 ? '∞' : (d.slots ?? '—');
    if (de) { const f = parseFloat(d.total_due || '0'); de.textContent = f > 0 ? '₹' + f.toFixed(2) : '₹0'; de.style.color = f > 0 ? '#ef4444' : 'inherit'; }
    if (ee) ee.textContent = d.email || '—';
    const photo = $('sidebarMemberPhoto'), initial = $('sidebarMemberInitial');
    if (photo && initial) {
      initial.textContent = (d.name || '?')[0].toUpperCase();
      if (d.photo_url) {
        photo.onerror = () => { photo.style.display = 'none'; initial.style.display = 'flex'; };
        photo.src = d.photo_url; photo.style.display = 'block'; initial.style.display = 'none';
      } else { photo.style.display = 'none'; initial.style.display = 'flex'; }
    }
  }

  // ── Book lookup ───────────────────────────────────────────────────────────
  function lookupBook(rawVal) {
    const val = rawVal.trim();
    if (!val) {
      bookValid = false;
      clearField(bookRow, bookStatus, bookError);
      hideBookPreview();
      syncSidebarBook(null);
      return;
    }
    setFieldState(bookRow, bookStatus, bookError, 'loading');
    fetch(`${window.BOOK_LOOKUP_URL}?book_id=${encodeURIComponent(val)}`)
      .then(r => r.ok ? r.json() : r.text().then(t => { throw new Error(`Server ${r.status}: ${t.slice(0,120)}`); }))
      .then(data => {
        if (data.found) {
          bookValid = true;
          // Populate hidden form fields with book PK and copy PK so Django validates correctly
          const hiddenBook = document.getElementById('id_book');
          if (hiddenBook) hiddenBook.value = data.pk;
          const hiddenCopy = document.getElementById('id_book_copy');
          if (hiddenCopy) hiddenCopy.value = data.copy_pk || '';
          setFieldState(bookRow, bookStatus, bookError, 'ok');
          showBookPreview(data);
          syncSidebarBook(data);
        } else {
          bookValid = false;
          const hiddenBook = document.getElementById('id_book');
          if (hiddenBook) hiddenBook.value = '';
          const hiddenCopy = document.getElementById('id_book_copy');
          if (hiddenCopy) hiddenCopy.value = '';
          setFieldState(bookRow, bookStatus, bookError, 'error', data.error || 'Book not found.');
          hideBookPreview();
          syncSidebarBook(null);
        }
      })
      .catch(err => {
        bookValid = false;
        const hiddenBook = document.getElementById('id_book');
        if (hiddenBook) hiddenBook.value = '';
        const hiddenCopy = document.getElementById('id_book_copy');
        if (hiddenCopy) hiddenCopy.value = '';
        setFieldState(bookRow, bookStatus, bookError, 'error', err.message || 'Lookup failed.');
        hideBookPreview();
      });
  }

  function _setBookCover(imgId, fbId, url) {
    const img = document.getElementById(imgId), fb = document.getElementById(fbId);
    if (!img || !fb) return;
    if (url) {
      img.onerror = () => { img.style.display = 'none'; fb.style.display = ''; };
      img.src = url; img.style.display = 'block'; fb.style.display = 'none';
    } else { img.style.display = 'none'; fb.style.display = ''; }
  }

  function showBookPreview(d) {
    if (!bookPreview) return;
    document.getElementById('bookPreviewTitle').textContent  = d.title  || '—';
    document.getElementById('bookPreviewAuthor').textContent = d.author || '—';
    document.getElementById('bookPreviewIsbn').textContent   = d.isbn ? 'ISBN: ' + d.isbn : '';
    _setBookCover('bookPreviewCover', 'bookPreviewCoverFallback', d.cover_url);
    const badge = document.getElementById('bookPreviewAvailBadge');
    if (badge) {
      const avail = parseInt(d.available_copies, 10) || 0;
      badge.textContent = avail > 0 ? avail + ' cop' + (avail === 1 ? 'y' : 'ies') + ' available' : 'No copies available';
      badge.className = 'avail-badge ' + (avail > 0 ? 'avail-badge--ok' : 'avail-badge--out');
    }
    bookPreview.classList.remove('is-hidden');
  }
  function hideBookPreview() { bookPreview?.classList.add('is-hidden'); }

  // ── Sidebar — book ────────────────────────────────────────────────────────
  function syncSidebarBook(d) {
    const empty = document.getElementById('sidebarBookEmpty'), details = document.getElementById('sidebarBookDetails');
    if (!empty || !details) return;
    if (!d) { empty.style.display = ''; details.classList.add('is-hidden'); return; }
    empty.style.display = 'none'; details.classList.remove('is-hidden');
    const $ = id => document.getElementById(id);
    const te = $('sidebarBookTitle'), ae = $('sidebarBookAuthor'), ie = $('sidebarBookIsbn'),
          ce = $('sidebarAvailCount'), fe = $('sidebarAvailFill'), we = $('noCopiesWarning'),
          cae = $('sidebarBookCategory'), cne = $('sidebarBookCategoryName');
    if (te) te.textContent = d.title  || '—';
    if (ae) ae.textContent = d.author || '—';
    if (ie) ie.textContent = d.isbn   ? 'ISBN ' + d.isbn : '';
    _setBookCover('sidebarBookCover', 'sidebarBookCoverFallback', d.cover_url);
    const avail = parseInt(d.available_copies, 10) || 0, total = parseInt(d.total_copies, 10) || 1;
    if (ce) ce.textContent = avail + ' / ' + total;
    if (fe) fe.style.width = Math.round((avail / total) * 100) + '%';
    if (we) we.classList.toggle('is-hidden', avail > 0);
    if (cae && cne && d.category) { cne.textContent = d.category; cae.classList.remove('is-hidden'); }
    else if (cae) cae.classList.add('is-hidden');
    const rules = window.LIBRARY_RULES || {}, banner = $('sidebarDueBanner'), de2 = $('sidebarDueDate'), dure = $('sidebarDuration');
    if (banner && de2 && rules.defaultLoanDays) {
      const due = new Date(); due.setDate(due.getDate() + rules.defaultLoanDays);
      de2.textContent = due.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
      if (dure) dure.textContent = rules.defaultLoanDays + ' days';
      banner.classList.remove('is-hidden');
    }
  }

  // ── Blur guard — prevents lookup firing when user clicks a suggestion ────
  // mousedown fires before blur, so we set a flag and clear it right after.
  let _dropClicked = false;
  [
    document.getElementById('memberSuggest'),
    document.getElementById('bookSuggest'),
  ].forEach(drop => {
    if (drop) {
      drop.addEventListener('mousedown', () => { _dropClicked = true; });
      drop.addEventListener('mouseup',   () => { setTimeout(() => { _dropClicked = false; }, 0); });
    }
  });

  // Lookup fires on: blur, Enter, Tab, or suggestion selection (triggerX).

  if (memberInput) {
    memberInput.addEventListener('input', () => {
      const v = memberInput.value.trim();
      if (!v) {
        memberValid = false; clearField(memberRow, memberStatus, memberError);
        hideMemberPreview(); syncSidebarMember(null);
      } else {
        clearField(memberRow, memberStatus, memberError); // clear stale error while typing
      }
    });
    memberInput.addEventListener('blur', () => {
      // Don't fire lookup if blur was caused by clicking a suggestion
      if (_dropClicked) return;
      if (memberInput.value.trim()) lookupMember(memberInput.value);
    });
    memberInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (memberInput.value.trim()) lookupMember(memberInput.value);
        setTimeout(() => bookInput?.focus(), 50);
      } else if (e.key === 'Tab' && memberInput.value.trim()) {
        lookupMember(memberInput.value);
      }
    });
    if (memberInput.value.trim()) lookupMember(memberInput.value); // POST-back
  }

  if (bookInput) {
    bookInput.addEventListener('input', () => {
      const v = bookInput.value.trim();
      if (!v) {
        bookValid = false; clearField(bookRow, bookStatus, bookError);
        hideBookPreview(); syncSidebarBook(null);
      } else {
        clearField(bookRow, bookStatus, bookError);
      }
    });
    bookInput.addEventListener('blur', () => {
      // Don't fire lookup if blur was caused by clicking a suggestion
      if (_dropClicked) return;
      if (bookInput.value.trim()) lookupBook(bookInput.value);
    });
    bookInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (bookInput.value.trim()) lookupBook(bookInput.value);
        setTimeout(() => { if (memberValid && bookValid) form?.submit(); }, 400);
      }
    });
    if (bookInput.value.trim()) lookupBook(bookInput.value); // POST-back
  }

  // ── Submit guard ──────────────────────────────────────────────────────────
  form?.addEventListener('submit', () => {
    if (submitBtn) {
      submitBtn.disabled  = true;
      submitBtn.innerHTML = '<svg viewBox="0 0 20 20" fill="none" style="animation:spin 1s linear infinite;width:16px;height:16px"><path d="M10 3a7 7 0 0 1 7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg> Issuing…';
    }
  });

  // ── Public API for Part 2 ─────────────────────────────────────────────────
  // Called by suggestion onSelect — fills input + fires lookup immediately,
  // bypassing blur so we get instant feedback.
  window.triggerMemberLookup = function (memberId) {
    if (!memberInput) return;
    memberInput.value = memberId;
    lookupMember(memberId);
  };
  window.triggerBookLookup = function (copyId) {
    if (!bookInput) return;
    bookInput.value = copyId;
    lookupBook(copyId);
  };

})();


/* ═══════════════════════════════════════════════════════════════════════════
   PART 2 — Live-search suggestion dropdowns
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  // ── Helpers ───────────────────────────────────────────────────────────────
  function debounce(fn, ms) {
    let t; return function (...a) { clearTimeout(t); t = setTimeout(() => fn.apply(this, a), ms); };
  }
  function esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function highlight(text, q) {
    if (!q) return esc(text);
    return esc(text).replace(new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')', 'gi'),
      '<span class="suggest-match">$1</span>');
  }

  // ── SuggestController ─────────────────────────────────────────────────────
  function SuggestController({ inputEl, dropEl, searchUrl, buildItems, onSelect, filterItems }) {
    let active = -1, abort = null;

    const open  = () => dropEl.classList.remove('is-hidden');
    const close = () => { dropEl.classList.add('is-hidden'); active = -1; };

    function setActive(i) {
      const els = dropEl.querySelectorAll('.suggest-item');
      els.forEach(el => el.classList.remove('is-active'));
      active = i;
      if (i >= 0 && i < els.length) { els[i].classList.add('is-active'); els[i].scrollIntoView({ block: 'nearest' }); }
    }

    function render(items, q) {
      active = -1;
      if (!items.length) { dropEl.innerHTML = '<div class="suggest-empty">No results found</div>'; open(); return; }
      dropEl.innerHTML = buildItems(items, q);
      dropEl.querySelectorAll('.suggest-item').forEach((el, i) => {
        el.addEventListener('mousedown', e => { e.preventDefault(); onSelect(items[i]); close(); });
        el.addEventListener('mousemove', () => setActive(i));
      });
      open();
    }

    async function search(q) {
      if (abort) abort.abort();
      abort = new AbortController();
      dropEl.innerHTML = '<div class="suggest-loading"><span class="suggest-spinner"></span>Searching…</div>'; open();
      try {
        const res  = await fetch(`${searchUrl}?q=${encodeURIComponent(q)}`, { signal: abort.signal, credentials: 'same-origin' });
        const data = await res.json();
        let results = data.results || [];

        // Apply per-controller match filter if provided
        if (typeof filterItems === 'function') {
          results = filterItems(results, q);
        }

        render(results, q);
      } catch (err) {
        if (err.name !== 'AbortError') { dropEl.innerHTML = '<div class="suggest-empty">Search failed.</div>'; open(); }
      }
    }

    const dSearch = debounce(search, 120);

    // Every keystroke → search
    inputEl.addEventListener('input', () => {
      const q = inputEl.value.trim();
      if (!q) { close(); return; }
      dSearch(q);
    });

    // Keyboard nav inside dropdown
    inputEl.addEventListener('keydown', e => {
      if (dropEl.classList.contains('is-hidden')) return;
      const els = dropEl.querySelectorAll('.suggest-item');
      if      (e.key === 'ArrowDown')  { e.preventDefault(); setActive(Math.min(active + 1, els.length - 1)); }
      else if (e.key === 'ArrowUp')    { e.preventDefault(); setActive(Math.max(active - 1, -1)); }
      else if (e.key === 'Enter' && active >= 0 && els[active]) {
        e.preventDefault(); els[active].dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      } else if (e.key === 'Escape')   { close(); }
    });

    // Close on outside click
    document.addEventListener('click', e => { if (!dropEl.contains(e.target) && e.target !== inputEl) close(); });

    // Re-open on refocus if query still present
    inputEl.addEventListener('focus', () => {
      const q = inputEl.value.trim();
      if (q && dropEl.classList.contains('is-hidden')) dSearch(q);
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  // Use DOMContentLoaded if DOM isn't ready yet, otherwise run immediately.
  // (Script is loaded at bottom of <body> so DOM is usually already parsed,
  //  causing DOMContentLoaded to have already fired — init would never run.)
  function _init() {
    const mInput = document.getElementById('memberIdInput'),
          mDrop  = document.getElementById('memberSuggest'),
          bInput = document.getElementById('bookCopyIdInput'),
          bDrop  = document.getElementById('bookSuggest');
    if (!mInput || !mDrop || !bInput || !bDrop) return;

    // ── Member suggest ────────────────────────────────────────────────────
    SuggestController({
      inputEl:   mInput,
      dropEl:    mDrop,
      searchUrl: window.MEMBER_SEARCH_URL,

      // No client-side filterItems — member_suggestions_api already filters
      // server-side by member_id / first_name / last_name icontains.

      buildItems(items, q) {
        return items.map(m => {
          const initial  = (m.name || '?')[0].toUpperCase();
          const due      = parseFloat(m.total_due || '0');
          const isActive = m.status === 'active';

          // Status badge
          let badgeCls   = 'suggest-item__badge suggest-item__badge--ok';
          let badgeLabel = 'Active';
          if (!isActive) {
            badgeCls   = 'suggest-item__badge suggest-item__badge--full';
            badgeLabel = m.status || 'Inactive';
          } else if (due > 0) {
            badgeCls   = 'suggest-item__badge suggest-item__badge--warn';
            badgeLabel = '₹' + due.toFixed(0) + ' due';
          }

          // Avatar: use photo BLOB if available, fall back to initial
          const initialSpan =
            `<span style="display:flex;width:100%;height:100%;align-items:center;
                          justify-content:center;border-radius:50%;
                          background:linear-gradient(135deg,#6366f1,#8b5cf6);
                          color:#fff;font-weight:700;font-size:0.85rem;">${initial}</span>`;
          const avatarInner = m.photo_url
            ? `<img src="${esc(m.photo_url)}" alt=""
                    style="width:100%;height:100%;object-fit:cover;border-radius:50%;"
                    onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
               <span style="display:none;width:100%;height:100%;align-items:center;
                            justify-content:center;border-radius:50%;
                            background:linear-gradient(135deg,#6366f1,#8b5cf6);
                            color:#fff;font-weight:700;font-size:0.85rem;">${initial}</span>`
            : initialSpan;

          return `<div class="suggest-item" role="option" tabindex="-1">
            <div class="suggest-item__avatar" style="overflow:hidden;">${avatarInner}</div>
            <div class="suggest-item__body">
              <span class="suggest-item__name">${highlight(m.member_id, q)}</span>
              <span class="suggest-item__meta">${esc(m.name)}</span>
            </div>
            <span class="${badgeCls}">${badgeLabel}</span>
          </div>`;
        }).join('');
      },

      onSelect(m) {
        if (typeof window.triggerMemberLookup === 'function') window.triggerMemberLookup(m.member_id);
        else { mInput.value = m.member_id; }
        mInput.focus();
      },
    });

    // ── Book suggest ──────────────────────────────────────────────────────
    SuggestController({
      inputEl:   bInput,
      dropEl:    bDrop,
      searchUrl: window.BOOK_SEARCH_URL,

      // Only show suggestions where typed query matches a copy_id
      filterItems(items, q) {
        const qUp = q.trim().toUpperCase();
        return items.filter(b =>
          b.copy_ids && b.copy_ids.some(c => c.toUpperCase().includes(qUp))
        );
      },

      buildItems(items, q) {
        return items.map(b => {
          const avail = b.available_copies || 0;
          let cls   = 'suggest-item__badge suggest-item__badge--ok';
          let label = avail + ' available';
          if      (avail === 0) { cls = 'suggest-item__badge suggest-item__badge--full'; label = 'No copies'; }
          else if (avail === 1) { cls = 'suggest-item__badge suggest-item__badge--warn'; label = '1 copy left'; }

          // Show the first copy_id that matches the query as the primary (bold) line
          const qUp = q.trim().toUpperCase();
          const matchedCopy = (b.copy_ids || []).find(c => c.toUpperCase().includes(qUp)) || b.copy_ids?.[0] || b.book_id || '';

          return `<div class="suggest-item" role="option" tabindex="-1">
            <div class="suggest-item__book-icon" style="overflow:hidden;flex-shrink:0;">
              ${b.cover_url
                ? `<img src="${esc(b.cover_url)}" alt=""
                        style="width:100%;height:100%;object-fit:cover;border-radius:4px;"
                        onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                   <span style="display:none;width:100%;height:100%;align-items:center;justify-content:center;">
                     <svg viewBox="0 0 20 20" fill="none"><rect x="3" y="2" width="14" height="16" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M7 7h6M7 10h6M7 13h4" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/></svg>
                   </span>`
                : `<svg viewBox="0 0 20 20" fill="none"><rect x="3" y="2" width="14" height="16" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M7 7h6M7 10h6M7 13h4" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/></svg>`
              }
            </div>
            <div class="suggest-item__body">
              <span class="suggest-item__name">${highlight(matchedCopy, q)}</span>
              <span class="suggest-item__meta">${esc(b.title)}${b.author ? ' · ' + esc(b.author) : ''}</span>
            </div>
            <span class="${cls}">${label}</span>
          </div>`;
        }).join('');
      },

      onSelect(b) {
        // Fill input with the specific copy_id that matched the query
        const q = bInput.value.trim().toUpperCase();
        const matchedCopy = (b.copy_ids || []).find(c => c.toUpperCase().includes(q))
                         || (b.copy_ids && b.copy_ids[0])
                         || b.book_id || '';
        if (typeof window.triggerBookLookup === 'function') window.triggerBookLookup(matchedCopy);
        else { bInput.value = matchedCopy; }
        bInput.focus();
      },
    });
  }

  // Run immediately if DOM is ready (script loaded at bottom of body),
  // otherwise wait for DOMContentLoaded.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

})();