/**
 * members/member_edit.js
 * ──────────────────────
 * Edit-member page — form field UX only.
 * Depends on: members.js
 *
 * JS role here:
 *   ✓ Role card selection + show/hide student/teacher/general sections
 *   ✓ Dynamic field labels and placeholders per role
 *   ✓ Select-or-create mutual exclusivity
 *   ✓ Phone & email UX validation
 *   ✓ Photo change preview
 *   ✓ Disable hidden department selects before submit
 *   ✓ DOB max-date (today)
 *   ✓ Admission year range
 *   ✓ Submit button loading spinner
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {

  const $ = id => document.getElementById(id);


  // ── Role switching ────────────────────────────────────────────────────────

  function applyRole(role) {
    document.querySelectorAll('.student-only').forEach(el => {
      el.style.display = role === 'student' ? '' : 'none';
    });
    document.querySelectorAll('.teacher-only').forEach(el => {
      el.style.display = role === 'teacher' ? '' : 'none';
    });
    document.querySelectorAll('.general-only').forEach(el => {
      el.style.display = role === 'general' ? '' : 'none';
    });

    const stuWrap = $('status-student-wrapper');
    const othWrap = $('status-other-wrapper');
    const stuSel  = stuWrap?.querySelector('select');
    const othSel  = othWrap?.querySelector('select');

    if (role === 'student') {
      if (stuWrap) stuWrap.style.display = '';
      if (othWrap) othWrap.style.display = 'none';
      if (stuSel)  stuSel.name           = 'status';
      if (othSel)  othSel.name           = '_status_disabled';
    } else {
      if (stuWrap) stuWrap.style.display = 'none';
      if (othWrap) othWrap.style.display = '';
      if (othSel)  othSel.name           = 'status';
      if (stuSel)  stuSel.name           = '_status_disabled';
    }

    const deptStu = $('department');
    const deptTea = $('department_teacher');
    const deptGen = $('orgDept');
    if (deptStu) deptStu.disabled = role !== 'student';
    if (deptTea) deptTea.disabled = role !== 'teacher';
    if (deptGen) deptGen.disabled = role !== 'general';

    document.querySelectorAll('.role-option').forEach(opt => {
      opt.classList.toggle('selected', opt.dataset.role === role);
    });
  }

  document.querySelectorAll('.role-option').forEach(label => {
    label.addEventListener('click', function () {
      const radio = this.querySelector('input[type="radio"]');
      if (radio) { radio.checked = true; applyRole(radio.value); }
    });
  });

  const checked = document.querySelector('input[name="role"]:checked');
  applyRole(checked ? checked.value : 'student');


  // ── Dynamic labels and placeholders ──────────────────────────────────────

  const SECTION_TITLES = {
    student: 'Academic Information',
    teacher: 'Professional Information',
    general: 'Additional Information',
  };

  const ROLE_LABELS = {
    'roll-label':  { student: 'Roll Number',              teacher: 'Employee ID',              general: 'Government ID'  },
    'spec-label':  { student: 'Specialization / Subject', teacher: 'Designation / Post',       general: 'Occupation'     },
    'notes-label': { student: 'Notes / Remarks',          teacher: 'Notes / Remarks',          general: 'Notes / Remarks'},
    'dept-star':   { student: '*',                        teacher: '*',                        general: ''               },
  };

  const ROLE_PLACEHOLDERS = {
    'rollNumber':     { student: 'e.g. CS2024001',                  teacher: 'e.g. EMP-2024-001',              general: 'Aadhaar / Voter ID / PAN…'   },
    'specialization': { student: 'e.g. Machine Learning, Finance…', teacher: 'e.g. Assistant Professor, HOD…', general: 'e.g. Farmer, Govt. Teacher…' },
  };

  function applyRoleLabels(role) {
    const titleEl = $('academicSectionTitle');
    if (titleEl) titleEl.textContent = SECTION_TITLES[role] || 'Academic Information';

    document.querySelectorAll('.student-field').forEach(el => {
      el.style.display = role === 'student' ? '' : 'none';
    });
    document.querySelectorAll('.general-field').forEach(el => {
      el.style.display = role === 'general' ? '' : 'none';
    });

    const guardianWrapper = $('guardian-phone-wrapper');
    if (guardianWrapper) guardianWrapper.style.display = role === 'student' ? '' : 'none';

    Object.entries(ROLE_LABELS).forEach(([id, map]) => {
      const el = document.getElementById(id);
      if (el && map[role] !== undefined) el.textContent = map[role];
    });

    Object.entries(ROLE_PLACEHOLDERS).forEach(([id, map]) => {
      const el = document.getElementById(id);
      if (el && map[role]) el.placeholder = map[role];
    });
  }

  document.querySelectorAll('.role-option').forEach(label => {
    label.addEventListener('click', function () {
      document.querySelectorAll('.role-option').forEach(l => l.classList.remove('selected'));
      this.classList.add('selected');
      applyRoleLabels(this.dataset.role);
    });
  });

  const checkedRadio = document.querySelector('input[name="role"]:checked');
  if (checkedRadio) applyRoleLabels(checkedRadio.value);


  // ── Select-or-create ──────────────────────────────────────────────────────

  initSelectOrCreate();


  // ── Phone & email UX validation ───────────────────────────────────────────

  initPhoneValidation([
    { id: 'phone',          required: true  },
    { id: 'alternatePhone', required: false },
    { id: 'guardianPhone',  required: false },
  ]);

  initEmailValidation('email');


  // ── DOB — prevent future dates ────────────────────────────────────────────

  const dob = $('dateOfBirth');
  if (dob) dob.setAttribute('max', new Date().toISOString().split('T')[0]);


  // ── Admission year range ──────────────────────────────────────────────────

  const admYear = $('admissionYear');
  if (admYear) {
    const y = new Date().getFullYear();
    admYear.setAttribute('min', '1990');
    admYear.setAttribute('max', String(y));
  }


  // ── Photo change preview ──────────────────────────────────────────────────

  const photoInput    = $('memberPhoto');
  const previewDiv    = $('photoPreview');
  const fileInputWrap = photoInput?.closest('.file-input-wrapper');

  photoInput?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      showToast('Please select a valid image (JPG, PNG, GIF).', 'error');
      e.target.value = '';
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast('Image must be 5 MB or less.', 'error');
      e.target.value = '';
      return;
    }

    // Update label text to show chosen filename
    const labelSpan = fileInputWrap?.querySelector('.file-input-text span');
    if (labelSpan) labelSpan.textContent = file.name;

    const reader  = new FileReader();
    reader.onload = (evt) => {
      if (!previewDiv) return;
      previewDiv.innerHTML = '';

      const wrapper = document.createElement('div');
      wrapper.style.cssText = 'position:relative;display:inline-block;';

      const img = document.createElement('img');
      img.src   = evt.target.result;
      img.alt   = 'New photo preview';
      img.style.cssText = 'max-width:200px;max-height:200px;border-radius:8px;border:2px solid #e5e7eb;display:block;';

      // Remove/clear button on the preview
      const clearBtn = document.createElement('button');
      clearBtn.type      = 'button';
      clearBtn.title     = 'Remove selected photo';
      clearBtn.innerHTML = '<i class="fas fa-times"></i>';
      clearBtn.style.cssText =
        'position:absolute;top:6px;right:6px;width:26px;height:26px;border-radius:50%;' +
        'border:none;background:rgba(0,0,0,.55);color:white;font-size:.7rem;cursor:pointer;' +
        'display:flex;align-items:center;justify-content:center;transition:background .2s;';
      clearBtn.onmouseenter = () => { clearBtn.style.background = '#ef4444'; };
      clearBtn.onmouseleave = () => { clearBtn.style.background = 'rgba(0,0,0,.55)'; };
      clearBtn.addEventListener('click', () => {
        photoInput.value = '';
        previewDiv.innerHTML = '';
        previewDiv.classList.remove('active');
        if (labelSpan) labelSpan.textContent = 'Change photo';
      });

      wrapper.appendChild(img);
      wrapper.appendChild(clearBtn);
      previewDiv.appendChild(wrapper);
      previewDiv.classList.add('active');
    };
    reader.readAsDataURL(file);
  });


  // ── Submit spinner ────────────────────────────────────────────────────────

  $('memberForm')?.addEventListener('submit', () => {
    const btn = $('submitBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…'; }
  });

});