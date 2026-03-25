"""
members/forms.py
────────────────
Forms for the members app.

Key features
────────────
• MemberForm  – handles select-or-create for Department, Course,
                AcademicYear and Semester; owner-scoped querysets.
• DepartmentForm, CourseForm, AcademicYearForm, SemesterForm – simple
  CRUD forms with owner-scoped uniqueness validation.

Photo handling
──────────────
Because Member.photo is now a BinaryField (not an ImageField), photos are
NOT handled by Django's form/model machinery automatically.  Instead:

  • The form exposes a plain `photo_upload` FileField (accepts image/*).
  • `clean_photo_upload` validates size and MIME type.
  • `save_with_create` / `_BaseMemberForm.save_with_create` reads the raw
    bytes and writes them to member.photo / member.photo_mime_type.
  • To clear an existing photo, a separate `clear_photo` BooleanField is
    provided (replaces the ClearableFileInput behaviour from ImageField).

Role-specific forms (StudentMemberForm, TeacherMemberForm, GeneralMemberForm)
are defined at the bottom of this file (previously a separate role_forms.py).
"""

import io
from django import forms
from django.core.exceptions import ValidationError

from .models import Member, Department, Course, AcademicYear, Semester


# ──────────────────────────────────────────────────────────────────────────────
# Shared widget helpers
# ──────────────────────────────────────────────────────────────────────────────

def _text(placeholder="", **kw):
    return forms.TextInput(attrs={"class": "form-control", "placeholder": placeholder, **kw})


def _select(**kw):
    return forms.Select(attrs={"class": "form-control", **kw})


def _textarea(placeholder="", rows=3, **kw):
    return forms.Textarea(attrs={"class": "form-control", "rows": rows, "placeholder": placeholder, **kw})


def _number(placeholder="", **kw):
    return forms.NumberInput(attrs={"class": "form-control", "placeholder": placeholder, **kw})


def _email(placeholder="", **kw):
    return forms.EmailInput(attrs={"class": "form-control", "placeholder": placeholder, **kw})


def _date(**kw):
    return forms.DateInput(attrs={"class": "form-control", "type": "date", **kw})


def _file(**kw):
    return forms.FileInput(attrs={"class": "form-control", "accept": "image/*", **kw})


# ──────────────────────────────────────────────────────────────────────────────
# Photo compression helper
# ──────────────────────────────────────────────────────────────────────────────

def _compress_photo(upload_file, max_size=(400, 400), quality=85):
    """
    Read an uploaded image file, resize it to fit within max_size,
    and return (jpeg_bytes, "image/jpeg").

    Requires Pillow: pip install Pillow

    Falls back to raw bytes + original content_type if Pillow is not installed.
    """
    # Always seek to the start — Django may have read the file during validation
    try:
        upload_file.seek(0)
    except Exception:
        pass

    try:
        from PIL import Image
        img = Image.open(upload_file)
        img.load()  # Force full read before the file handle is used elsewhere
        # Convert palette / RGBA images to RGB so we can save as JPEG
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except ImportError:
        # Pillow not installed — store original bytes unchanged
        upload_file.seek(0)
        return upload_file.read(), getattr(upload_file, "content_type", "image/jpeg")


# ══════════════════════════════════════════════════════════════════════════════
# MemberForm  (legacy / generic — kept for backward compatibility)
# ══════════════════════════════════════════════════════════════════════════════

class MemberForm(forms.ModelForm):
    """
    Generic member create / edit form (non-role-specific).

    Extra (non-model) fields
    ─────────────────────────
    new_department  – free-text; creates a Department on the fly if set.
    new_course      – free-text; creates a Course on the fly if set.
    new_year        – free-text; creates an AcademicYear on the fly if set.
    new_semester    – free-text; creates a Semester on the fly if set.
    photo_upload    – FileField for uploading a new photo (stored as blob).
    clear_photo     – BooleanField to remove the existing photo.

    These are processed in save_with_create().
    """

    # ── Extra "create" fields ─────────────────────────────────────────────────
    new_department = forms.CharField(
        required=False,
        widget=_text("e.g. Computer Science"),
        label="Create new department",
    )
    new_course = forms.CharField(
        required=False,
        widget=_text("e.g. B.Sc. Honours"),
        label="Create new course",
    )
    new_year = forms.CharField(
        required=False,
        widget=_text("e.g. 3rd Year"),
        label="Create new academic year",
    )
    new_semester = forms.CharField(
        required=False,
        widget=_text("e.g. Semester 5"),
        label="Create new semester",
    )

    # ── Photo fields (blob-based) ─────────────────────────────────────────────
    photo_upload = forms.FileField(
        required=False,
        widget=_file(),
        label="Photo",
        help_text="Upload a JPG, PNG, GIF or WebP image (max 5 MB).",
    )
    clear_photo = forms.BooleanField(
        required=False,
        initial=False,
        label="Remove existing photo",
    )

    class Meta:
        model = Member
        # photo and photo_mime_type are intentionally excluded from Meta.fields
        # — they are handled manually via photo_upload / clear_photo above.
        fields = [
            "role",
            "first_name", "last_name", "email", "phone",
            "alternate_phone", "guardian_phone",
            "date_of_birth", "gender", "address",
            "department",
            "course",
            "year", "semester",
            "roll_number", "admission_year", "status",
            "specialization", "academic_notes",
        ]
        widgets = {
            "role":            _select(),
            "first_name":      _text("Enter first name"),
            "last_name":       _text("Enter last name"),
            "email":           forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter email address"}),
            "phone":           _text("10-digit number", maxlength="10"),
            "alternate_phone": _text("Optional alternate 10-digit number", maxlength="10"),
            "guardian_phone":  _text("Parent / guardian 10-digit number", maxlength="10"),
            "date_of_birth":   forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "gender":          _select(),
            "address":         _textarea("Enter address"),
            "department":      _select(),
            "course":          _select(),
            "year":            _select(),
            "semester":        _select(),
            "roll_number":     _text("e.g. CS2024001"),
            "admission_year":  _number("e.g. 2024", min="2000", max="2100"),
            "status":          _select(),
            "specialization":  _text("e.g. Machine Learning, Finance…"),
            "academic_notes":  _textarea("Any additional academic information…", rows=2),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            self.fields["department"].queryset = (
                Department.objects.filter(owner=user).order_by("name")
            )
            self.fields["course"].queryset = (
                Course.objects.filter(owner=user).order_by("name")
            )
            self.fields["year"].queryset = (
                AcademicYear.objects.filter(owner=user).order_by("order", "name")
            )
            self.fields["semester"].queryset = (
                Semester.objects.filter(owner=user).order_by("order", "name")
            )
        else:
            for f in ("department", "course", "year", "semester"):
                self.fields[f].queryset = self.fields[f].queryset.none()

        # All FK fields optional
        for f in ("department", "course", "year", "semester"):
            self.fields[f].required = False

    # ── Field-level validation ────────────────────────────────────────────────

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not self.user:
            raise ValidationError("User context required for validation.")
        qs = Member.objects.filter(owner=self.user, email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A member with this email already exists in your library."
            )
        return email

    def _validate_phone(self, field_name):
        phone = self.cleaned_data.get(field_name)
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_phone(self):
        return self._validate_phone("phone")

    def clean_photo_upload(self):
        """Validate uploaded photo size and MIME type."""
        photo = self.cleaned_data.get("photo_upload")
        if photo:
            if hasattr(photo, "size") and photo.size > 5 * 1024 * 1024:
                raise ValidationError("Photo size must be less than 5 MB.")
            valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if hasattr(photo, "content_type") and photo.content_type not in valid_types:
                raise ValidationError("Only JPG, PNG, GIF or WebP images are allowed.")
            # Rewind so save_with_create / _compress_photo can read from the start
            try:
                photo.seek(0)
            except Exception:
                pass
        return photo

    def clean(self):
        cleaned = super().clean()
        # Cross-field ownership check for FK fields
        for field, Model in (
            ("department", Department),
            ("course", Course),
            ("year", AcademicYear),
            ("semester", Semester),
        ):
            obj = cleaned.get(field)
            if obj and self.user and obj.owner != self.user:
                raise ValidationError(f"Invalid {field} selection.")
        return cleaned

    # ── Convenience save helper ───────────────────────────────────────────────

    def save_with_create(self, commit=True):
        """
        Extended save:
        - Resolves Department / Course / AcademicYear / Semester via
          select-or-create.
        - Handles photo blob: compresses + stores bytes, or clears on request.
        """
        if not self.user:
            raise ValueError("Cannot call save_with_create without a user.")

        member = super().save(commit=False)
        member.owner = self.user

        # ── Resolve Department FK ─────────────────────────────────────────────
        dept = self.cleaned_data.get("department")
        new_dept_name = (self.cleaned_data.get("new_department") or "").strip()
        if not dept and new_dept_name:
            dept = Department.objects.filter(
                owner=self.user, name__iexact=new_dept_name
            ).first()
            if not dept:
                dept = Department.objects.create(
                    owner=self.user,
                    name=new_dept_name,
                    code=new_dept_name[:20].upper().replace(" ", "_"),
                )
        member.department = dept

        # ── Resolve Course ────────────────────────────────────────────────────
        course = self.cleaned_data.get("course")
        new_course_name = (self.cleaned_data.get("new_course") or "").strip()
        if not course and new_course_name:
            course = Course.objects.filter(
                owner=self.user, name__iexact=new_course_name
            ).first()
            if not course:
                course = Course.objects.create(
                    owner=self.user,
                    name=new_course_name,
                    code=new_course_name[:20].upper().replace(" ", "_"),
                    duration=3,
                )
        member.course = course

        # ── Resolve AcademicYear ──────────────────────────────────────────────
        year = self.cleaned_data.get("year")
        new_year_name = (self.cleaned_data.get("new_year") or "").strip()
        if not year and new_year_name:
            year = AcademicYear.objects.filter(
                owner=self.user, name__iexact=new_year_name
            ).first()
            if not year:
                year = AcademicYear.objects.create(
                    owner=self.user, name=new_year_name,
                )
        member.year = year

        # ── Resolve Semester ──────────────────────────────────────────────────
        semester = self.cleaned_data.get("semester")
        new_semester_name = (self.cleaned_data.get("new_semester") or "").strip()
        if not semester and new_semester_name:
            semester = Semester.objects.filter(
                owner=self.user, name__iexact=new_semester_name
            ).first()
            if not semester:
                semester = Semester.objects.create(
                    owner=self.user, name=new_semester_name,
                )
        member.semester = semester

        # ── Handle photo blob ─────────────────────────────────────────────────
        photo_changed = False
        if self.cleaned_data.get("clear_photo"):
            member.photo = None
            member.photo_mime_type = ""
            photo_changed = True
        else:
            photo_file = self.cleaned_data.get("photo_upload")
            if photo_file:
                photo_bytes, mime = _compress_photo(photo_file)
                member.photo = photo_bytes
                member.photo_mime_type = mime
                photo_changed = True

        if commit:
            member.save()
            # BinaryField has editable=False by default — Django's UPDATE
            # omits it. Force-write photo columns whenever they changed.
            if photo_changed and member.pk:
                Member.objects.filter(pk=member.pk).update(
                    photo=member.photo,
                    photo_mime_type=member.photo_mime_type,
                )
        return member


# ──────────────────────────────────────────────────────────────────────────────
# Department form
# ──────────────────────────────────────────────────────────────────────────────

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description"]
        widgets = {
            "name":        _text("Enter department name"),
            "code":        _text("Enter department code"),
            "description": _textarea("Enter description (optional)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not self.user:
            raise ValidationError("User context required for validation.")
        qs = Department.objects.filter(owner=self.user, code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A department with this code already exists in your library."
            )
        return code


# ──────────────────────────────────────────────────────────────────────────────
# Course form
# ──────────────────────────────────────────────────────────────────────────────

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "code", "duration", "description"]
        widgets = {
            "name":        _text("Enter course name"),
            "code":        _text("Enter course code"),
            "duration":    _number("Duration in years", min="1", max="10"),
            "description": _textarea("Enter description (optional)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not self.user:
            raise ValidationError("User context required for validation.")
        qs = Course.objects.filter(owner=self.user, code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A course with this code already exists in your library."
            )
        return code


# ──────────────────────────────────────────────────────────────────────────────
# AcademicYear form
# ──────────────────────────────────────────────────────────────────────────────

class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ["name", "order"]
        widgets = {
            "name":  _text('e.g. "1st Year"'),
            "order": _number("Sort order (0 = first)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not self.user:
            raise ValidationError("User context required.")
        qs = AcademicYear.objects.filter(owner=self.user, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This academic year already exists.")
        return name


# ──────────────────────────────────────────────────────────────────────────────
# Semester form
# ──────────────────────────────────────────────────────────────────────────────

class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["name", "order"]
        widgets = {
            "name":  _text('e.g. "Semester 1"'),
            "order": _number("Sort order (0 = first)"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not self.user:
            raise ValidationError("User context required.")
        qs = Semester.objects.filter(owner=self.user, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This semester already exists.")
        return name


# ══════════════════════════════════════════════════════════════════════════════
# Role-specific forms  (previously role_forms.py)
# ══════════════════════════════════════════════════════════════════════════════
#
#   ┌──────────────────────┬─────────────────────────────────────────────────┐
#   │ Form                 │ Use for                                         │
#   ├──────────────────────┼─────────────────────────────────────────────────┤
#   │ StudentMemberForm    │ Students (role = "student")                     │
#   │ TeacherMemberForm    │ Teachers / Faculty (role = "teacher")           │
#   │ GeneralMemberForm    │ General / Govt / Rural / Urban (role="general") │
#   └──────────────────────┴─────────────────────────────────────────────────┘
#
# Usage in views:
#   form = StudentMemberForm(request.POST, request.FILES, user=request.user)
#   if form.is_valid():
#       member = form.save_with_create()   # role is set automatically
# ──────────────────────────────────────────────────────────────────────────────


class _BaseMemberForm(forms.ModelForm):
    """
    Common fields, validation, and save logic shared by all three role forms.

    Subclasses must:
    • Set MEMBER_ROLE to the appropriate role string.
    • Override Meta.fields to include only the fields relevant to that role.
    • Call super().__init__() and then apply any role-specific tweaks.
    """

    MEMBER_ROLE: str = ""  # overridden by each subclass

    # ── Select-or-create extras ───────────────────────────────────────────────
    new_department = forms.CharField(
        required=False,
        widget=_text("Type new department name…"),
        label="Or create a new department",
        help_text="Leave blank if you selected one above.",
    )
    new_course = forms.CharField(
        required=False,
        widget=_text("Type new course name…"),
        label="Or create a new course",
        help_text="Leave blank if you selected one above.",
    )
    new_year = forms.CharField(
        required=False,
        widget=_text("e.g. 3rd Year"),
        label="Or create a new academic year",
    )
    new_semester = forms.CharField(
        required=False,
        widget=_text("e.g. Semester 5"),
        label="Or create a new semester",
    )

    # ── Photo fields (blob-based) ─────────────────────────────────────────────
    photo_upload = forms.FileField(
        required=False,
        widget=_file(),
        label="Photo",
        help_text="Upload a JPG, PNG, GIF or WebP image (max 5 MB).",
    )
    clear_photo = forms.BooleanField(
        required=False,
        initial=False,
        label="Remove existing photo",
    )

    class Meta:
        model = Member
        # photo and photo_mime_type are handled via photo_upload / clear_photo.
        fields = [
            "first_name", "last_name", "email", "phone",
            "alternate_phone", "guardian_phone",
            "date_of_birth", "gender", "address",
            "department", "course", "year", "semester",
            "roll_number", "admission_year",
            "specialization", "academic_notes",
            "status",
        ]
        widgets = {
            "first_name":      _text("First name"),
            "last_name":       _text("Last name"),
            "email":           _email("email@example.com"),
            "phone":           _text("10-digit mobile number", maxlength="10"),
            "alternate_phone": _text("Alternate 10-digit number", maxlength="10"),
            "guardian_phone":  _text("Parent / guardian number", maxlength="10"),
            "date_of_birth":   _date(),
            "gender":          _select(),
            "address":         _textarea("Full postal address"),
            "department":      _select(),
            "course":          _select(),
            "year":            _select(),
            "semester":        _select(),
            "roll_number":     _text("e.g. CS2024001"),
            "admission_year":  _number("e.g. 2024", min="2000", max="2100"),
            "specialization":  _text("e.g. Machine Learning, Finance…"),
            "academic_notes":  _textarea("Additional remarks…", rows=2),
            "status":          _select(),
        }

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Restrict FK dropdowns to the current owner's data
        if user:
            self.fields["department"].queryset = (
                Department.objects.filter(owner=user).order_by("name")
            )
            if "course" in self.fields:
                self.fields["course"].queryset = (
                    Course.objects.filter(owner=user).order_by("name")
                )
            if "year" in self.fields:
                self.fields["year"].queryset = (
                    AcademicYear.objects.filter(owner=user).order_by("order", "name")
                )
            if "semester" in self.fields:
                self.fields["semester"].queryset = (
                    Semester.objects.filter(owner=user).order_by("order", "name")
                )
        else:
            for f in ("department", "course", "year", "semester"):
                if f in self.fields:
                    self.fields[f].queryset = self.fields[f].queryset.none()

        # All FK / optional fields are not required at the form level;
        # role-specific subclasses mark the ones they need as required.
        for f in ("department", "course", "year", "semester",
                  "alternate_phone", "guardian_phone",
                  "address",
                  "specialization", "academic_notes"):
            if f in self.fields:
                self.fields[f].required = False

    # ── Shared validation ─────────────────────────────────────────────────────

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not self.user:
            raise ValidationError("User context is required for validation.")
        qs = Member.objects.filter(owner=self.user, email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                "A member with this email already exists in your library."
            )
        return email

    def _validate_phone(self, field_name):
        phone = self.cleaned_data.get(field_name)
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            if len(phone) != 10:
                raise ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_phone(self):
        return self._validate_phone("phone")

    def clean_alternate_phone(self):
        return self._validate_phone("alternate_phone")

    def clean_guardian_phone(self):
        return self._validate_phone("guardian_phone")

    def clean_photo_upload(self):
        """Validate uploaded photo size and MIME type."""
        photo = self.cleaned_data.get("photo_upload")
        if photo:
            if hasattr(photo, "size") and photo.size > 5 * 1024 * 1024:
                raise ValidationError("Photo must be less than 5 MB.")
            valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if hasattr(photo, "content_type") and photo.content_type not in valid_types:
                raise ValidationError("Only JPG, PNG, GIF or WebP images are allowed.")
            # Rewind so save_with_create / _compress_photo can read from the start
            try:
                photo.seek(0)
            except Exception:
                pass
        return photo

    def clean(self):
        cleaned = super().clean()
        # Verify FK objects belong to this owner
        for field, Model in (
            ("department", Department),
            ("course",     Course),
            ("year",       AcademicYear),
            ("semester",   Semester),
        ):
            if field not in self.fields:
                continue
            obj = cleaned.get(field)
            if obj and self.user and obj.owner != self.user:
                raise ValidationError(f"Invalid {field} selection.")
        return cleaned

    # ── Save helper ───────────────────────────────────────────────────────────

    def save_with_create(self, commit=True):
        """
        Extended save that:
        • Auto-sets member.role to MEMBER_ROLE.
        • Auto-sets member.owner to self.user.
        • Resolves Department / Course / AcademicYear / Semester via
          select-or-create using the new_* fields.
        • Handles photo blob: compresses + stores bytes, or clears on request.
        """
        if not self.user:
            raise ValueError("Cannot call save_with_create without a user.")
        if not self.MEMBER_ROLE:
            raise NotImplementedError("Subclass must set MEMBER_ROLE.")

        member = super().save(commit=False)
        member.owner = self.user
        member.role  = self.MEMBER_ROLE

        # ── Department ────────────────────────────────────────────────────────
        dept          = self.cleaned_data.get("department")
        new_dept_name = (self.cleaned_data.get("new_department") or "").strip()
        if not dept and new_dept_name:
            dept = Department.objects.filter(
                owner=self.user, name__iexact=new_dept_name
            ).first()
            if not dept:
                dept = Department.objects.create(
                    owner=self.user,
                    name=new_dept_name,
                    code=new_dept_name[:20].upper().replace(" ", "_"),
                )
        member.department = dept

        # ── Course (students only; skipped if not in form) ───────────────────
        if "course" in self.fields:
            course          = self.cleaned_data.get("course")
            new_course_name = (self.cleaned_data.get("new_course") or "").strip()
            if not course and new_course_name:
                course = Course.objects.filter(
                    owner=self.user, name__iexact=new_course_name
                ).first()
                if not course:
                    course = Course.objects.create(
                        owner=self.user,
                        name=new_course_name,
                        code=new_course_name[:20].upper().replace(" ", "_"),
                        duration=3,
                    )
            member.course = course
        else:
            member.course = None

        # ── Academic Year ─────────────────────────────────────────────────────
        if "year" in self.fields:
            year          = self.cleaned_data.get("year")
            new_year_name = (self.cleaned_data.get("new_year") or "").strip()
            if not year and new_year_name:
                year = AcademicYear.objects.filter(
                    owner=self.user, name__iexact=new_year_name
                ).first()
                if not year:
                    year = AcademicYear.objects.create(
                        owner=self.user, name=new_year_name
                    )
            member.year = year
        else:
            member.year = None

        # ── Semester ──────────────────────────────────────────────────────────
        if "semester" in self.fields:
            semester          = self.cleaned_data.get("semester")
            new_semester_name = (self.cleaned_data.get("new_semester") or "").strip()
            if not semester and new_semester_name:
                semester = Semester.objects.filter(
                    owner=self.user, name__iexact=new_semester_name
                ).first()
                if not semester:
                    semester = Semester.objects.create(
                        owner=self.user, name=new_semester_name
                    )
            member.semester = semester
        else:
            member.semester = None

        # ── Photo blob ────────────────────────────────────────────────────────
        photo_changed = False
        if self.cleaned_data.get("clear_photo"):
            # User ticked "Remove existing photo"
            member.photo = None
            member.photo_mime_type = ""
            photo_changed = True
        else:
            photo_file = self.cleaned_data.get("photo_upload")
            if photo_file:
                photo_bytes, mime = _compress_photo(photo_file)
                member.photo = photo_bytes
                member.photo_mime_type = mime
                photo_changed = True
            # If no new file uploaded, leave existing photo untouched

        if commit:
            member.save()
            # BinaryField has editable=False by default, so Django's UPDATE
            # query omits it.  Force-write photo columns whenever they changed.
            if photo_changed and member.pk:
                Member.objects.filter(pk=member.pk).update(
                    photo=member.photo,
                    photo_mime_type=member.photo_mime_type,
                )
        return member


# ══════════════════════════════════════════════════════════════════════════════
# 1. Student Member Form
# ══════════════════════════════════════════════════════════════════════════════

class StudentMemberForm(_BaseMemberForm):
    """
    Registration / edit form for student members (role = "student").

    Required (beyond the standard personal fields):
    • Department  (select or create)
    • Course      (select or create)
    • Academic Year
    • Roll Number
    • Admission Year

    Optional:
    • Semester, Specialization, Academic Notes
    • Alternate Phone, Guardian Phone
    • Address, Photo
    """

    MEMBER_ROLE = "student"

    class Meta(_BaseMemberForm.Meta):
        fields = [
            # Personal
            "first_name", "last_name", "email", "phone",
            "alternate_phone", "guardian_phone",
            "date_of_birth", "gender", "address",
            # Academic
            "department", "course",
            "year", "semester",
            "roll_number", "admission_year",
            "specialization", "academic_notes",
            # Library
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ── Required academic fields for a student ────────────────────────────
        self.fields["department"].required     = False   # can use new_department
        self.fields["course"].required         = False   # can use new_course
        self.fields["year"].required           = False   # can use new_year
        self.fields["roll_number"].required    = True
        self.fields["admission_year"].required = True

        # ── Helpful labels / help text ────────────────────────────────────────
        self.fields["guardian_phone"].label    = "Guardian / Parent Phone"
        self.fields["roll_number"].label       = "Roll Number"
        self.fields["admission_year"].label    = "Admission Year"
        self.fields["specialization"].label    = "Specialization / Elective"
        self.fields["academic_notes"].label    = "Academic Notes"
        self.fields["department"].help_text    = (
            "Select an existing department or type a new one below."
        )
        self.fields["course"].help_text = (
            "Select an existing course or type a new one below."
        )
        self.fields["year"].help_text = (
            "Select an existing year label or type a new one below."
        )

    def clean(self):
        cleaned = super().clean()

        # At least one of department / new_department must be supplied
        if not cleaned.get("department") and not (cleaned.get("new_department") or "").strip():
            self.add_error("department", "Please select or enter a department.")

        # At least one of course / new_course must be supplied
        if not cleaned.get("course") and not (cleaned.get("new_course") or "").strip():
            self.add_error("course", "Please select or enter a course.")

        return cleaned


# ══════════════════════════════════════════════════════════════════════════════
# 2. Teacher / Faculty Member Form
# ══════════════════════════════════════════════════════════════════════════════

class TeacherMemberForm(_BaseMemberForm):
    """
    Registration / edit form for teaching / faculty members (role = "teacher").

    Teacher-specific extras:
    • designation  – free-text job title (e.g. "Assistant Professor").
      Stored in the `specialization` model field (no schema change needed).
    • employee_id  – optional staff ID.
      Stored in the `roll_number` model field (no schema change needed).

    Excluded compared to StudentMemberForm:
    • course, year, semester  – academic-year progression fields irrelevant
      for faculty.
    • guardian_phone          – not applicable.
    • admission_year          – not applicable.
    • roll_number             – repurposed as employee_id below.
    """

    MEMBER_ROLE = "teacher"

    # ── Teacher-specific (non-model) fields ───────────────────────────────────
    designation = forms.CharField(
        required=False,
        max_length=200,
        widget=_text("e.g. Assistant Professor, HOD, Librarian…"),
        label="Designation / Post",
        help_text="Stored in the Specialization field.",
    )
    employee_id = forms.CharField(
        required=False,
        max_length=50,
        widget=_text("Optional staff / employee ID"),
        label="Employee ID",
        help_text="Stored in the Roll Number field.",
    )

    class Meta(_BaseMemberForm.Meta):
        fields = [
            # Personal
            "first_name", "last_name", "email", "phone",
            "alternate_phone",
            "date_of_birth", "gender", "address",
            # Professional
            "department",
            "academic_notes",
            # Library
            "status",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].label     = "Department / Faculty"
        self.fields["academic_notes"].label = "Additional Notes"
        self.fields["department"].help_text = (
            "Select an existing department or type a new one below."
        )

        # Populate designation / employee_id from instance on edit
        if self.instance and self.instance.pk:
            self.fields["designation"].initial = self.instance.specialization or ""
            self.fields["employee_id"].initial = self.instance.roll_number or ""

    def save_with_create(self, commit=True):
        # Map extra fields → model fields before the base save runs
        self.instance.specialization = (
            self.cleaned_data.get("designation") or ""
        ).strip()
        self.instance.roll_number = (
            self.cleaned_data.get("employee_id") or ""
        ).strip() or None

        return super().save_with_create(commit=commit)


# ══════════════════════════════════════════════════════════════════════════════
# 3. General Member Form  (Government / Rural / Urban)
# ══════════════════════════════════════════════════════════════════════════════

class GeneralMemberForm(_BaseMemberForm):
    """
    Registration / edit form for general / community members (role = "general").

    Extra (non-model) fields:
    • occupation   – what the person does. Stored in `specialization`.
    • area_type    – Rural / Urban / Peri-urban.
      Prepended to `academic_notes` (e.g. "[Urban] Notes…").
    • govt_id      – optional government-issued ID number.
      Stored in `roll_number` (max 50 chars).
    • notes        – general notes. Combined with area_type in academic_notes.
    """

    MEMBER_ROLE = "general"

    AREA_CHOICES = [
        ("",           "– Select area type –"),
        ("urban",      "Urban"),
        ("rural",      "Rural"),
        ("peri_urban", "Peri-Urban"),
        ("other",      "Other"),
    ]

    # ── General-member-specific extra fields ──────────────────────────────────
    occupation = forms.CharField(
        required=False,
        max_length=200,
        widget=_text("e.g. Government Teacher, Farmer, Shopkeeper…"),
        label="Occupation",
        help_text="Stored in the Specialization field.",
    )
    area_type = forms.ChoiceField(
        required=False,
        choices=AREA_CHOICES,
        widget=_select(),
        label="Area Type",
        help_text="Rural / Urban classification.",
    )
    govt_id = forms.CharField(
        required=False,
        max_length=50,
        widget=_text("Aadhaar / Voter ID / PAN / Other govt. ID"),
        label="Government ID Number",
        help_text="Stored in the Roll Number field.",
    )
    notes = forms.CharField(
        required=False,
        widget=_textarea("Any other relevant information…", rows=3),
        label="Notes",
        help_text="General notes about this member.",
    )

    class Meta(_BaseMemberForm.Meta):
        fields = [
            # Personal
            "first_name", "last_name", "email", "phone",
            "alternate_phone",
            "date_of_birth", "gender", "address",
            # Affiliation (optional)
            "department",
            # Library
            "status",
        ]
        widgets = {
            **_BaseMemberForm.Meta.widgets,
            "address": _textarea("House No., Village/Town, District, State, PIN", rows=3),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].label     = "Organisation / Institution (optional)"
        self.fields["department"].help_text = (
            "Leave blank for community / general members with no institution, "
            "or select / create one if applicable."
        )
        self.fields["alternate_phone"].label = "Alternate Contact Number"

        # Populate extra fields from instance on edit
        if self.instance and self.instance.pk:
            self.fields["occupation"].initial = self.instance.specialization or ""
            self.fields["govt_id"].initial    = self.instance.roll_number or ""

            # Parse area_type out of academic_notes if stored as "[area_type] …"
            import re
            notes_raw = self.instance.academic_notes or ""
            m = re.match(r"^\[([^\]]+)\]\s*", notes_raw)
            if m:
                stored_area = m.group(1).lower().replace("-", "_").replace(" ", "_")
                self.fields["area_type"].initial = stored_area
                self.fields["notes"].initial     = notes_raw[m.end():]
            else:
                self.fields["notes"].initial = notes_raw

    def save_with_create(self, commit=True):
        import re

        # ── Map extra fields → model fields ───────────────────────────────────
        self.instance.specialization = (
            self.cleaned_data.get("occupation") or ""
        ).strip() or None

        self.instance.roll_number = (
            self.cleaned_data.get("govt_id") or ""
        ).strip() or None

        # Pack area_type + notes → academic_notes
        area  = self.cleaned_data.get("area_type", "").strip()
        notes = (self.cleaned_data.get("notes") or "").strip()
        if area:
            label = dict(self.AREA_CHOICES).get(area, area).capitalize()
            self.instance.academic_notes = f"[{label}] {notes}".strip()
        else:
            self.instance.academic_notes = notes or None

        return super().save_with_create(commit=commit)