"""
members/admin.py
────────────────
Django admin registrations for the members app.
All admin classes enforce owner-based multi-tenancy:
  • list view  → only shows the current user's records
  • related FK dropdowns → filtered to current user's data
  • save       → auto-assigns owner on creation
  • change/delete permissions → limited to own records
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Department, Course, AcademicYear, Semester, Member, Transaction


# ──────────────────────────────────────────────────────────────────────────────
# Mixins
# ──────────────────────────────────────────────────────────────────────────────

class OwnerScopedMixin:
    """
    Re-usable mixin that scopes every admin action to request.user.
    Apply to any ModelAdmin whose model has an `owner` FK to User.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
        return obj.owner == request.user

    def has_delete_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
        return obj.owner == request.user


# ──────────────────────────────────────────────────────────────────────────────
# Lookup / Reference model admins
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(Department)
class DepartmentAdmin(OwnerScopedMixin, admin.ModelAdmin):
    list_display = ["name", "code", "owner", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(Course)
class CourseAdmin(OwnerScopedMixin, admin.ModelAdmin):
    list_display = ["name", "code", "duration", "owner", "created_at"]
    list_filter = ["duration", "created_at"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(AcademicYear)
class AcademicYearAdmin(OwnerScopedMixin, admin.ModelAdmin):
    list_display = ["name", "order", "owner", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name"]
    ordering = ["order", "name"]


@admin.register(Semester)
class SemesterAdmin(OwnerScopedMixin, admin.ModelAdmin):
    list_display = ["name", "order", "owner", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name"]
    ordering = ["order", "name"]


# ──────────────────────────────────────────────────────────────────────────────
# Member admin
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(Member)
class MemberAdmin(OwnerScopedMixin, admin.ModelAdmin):
    list_display = [
        "member_id",
        "full_name",
        "role_badge",
        "email",
        "phone",
        "department",
        "year",
        "semester",
        "status_badge",
        "clearance_badge",
        "owner",
        "date_joined",
    ]
    list_filter = [
        "role",
        "status",
        "clearance_status",
        "gender",
        "department",
        "course",
        "year",
        "semester",
        "date_joined",
    ]
    search_fields = [
        "member_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "roll_number",
    ]
    ordering = ["-date_joined"]
    readonly_fields = ["date_joined", "created_at", "updated_at"]

    fieldsets = (
        (
            "Owner Information",
            {"fields": ("owner",), "classes": ("collapse",)},
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "member_id",
                    "role",
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "alternate_phone",
                    "guardian_phone",
                    "date_of_birth",
                    "gender",
                    "address",
                    "photo",
                )
            },
        ),
        (
            "Academic Information",
            {
                "fields": (
                    "department",
                    "course",
                    "year",
                    "semester",
                    "roll_number",
                    "admission_year",
                    "specialization",
                    "academic_notes",
                )
            },
        ),
        (
            "Library Status",
            {
                "fields": (
                    "status",
                    "inactive_since",
                    "inactive_reason",
                    "clearance_status",
                    "clearance_date",
                    "cleared_by",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("date_joined", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Restrict FK dropdowns to current user's data."""
        owner_scoped = {
            "department": Department,
            "course": Course,
            "year": AcademicYear,
            "semester": Semester,
        }
        if db_field.name in owner_scoped and not request.user.is_superuser:
            kwargs["queryset"] = owner_scoped[db_field.name].objects.filter(
                owner=request.user
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ── Display helpers ───────────────────────────────────────────────────────
    # NOTE: full_name is a @property on the Member model — no need to redefine
    # it here. Django admin resolves it automatically from list_display.

    @admin.display(description="Role")
    def role_badge(self, obj):
        colors = {
            "student": "#3b82f6",
            "teacher": "#8b5cf6",
            "general": "#6b7280",
        }
        color = colors.get(obj.role, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.get_role_display(),
        )

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "active": "#10b981",
            "inactive": "#ef4444",
            "passout": "#f59e0b",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.passout_label,  # role-aware: Alumni / Ex-Teacher / Former Member
        )

    @admin.display(description="Clearance")
    def clearance_badge(self, obj):
        colors = {"cleared": "#10b981", "pending": "#f59e0b"}
        color = colors.get(obj.clearance_status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.get_clearance_status_display(),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Transaction admin
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(Transaction)
class TransactionAdmin(OwnerScopedMixin, admin.ModelAdmin):
    list_display = [
        "member",
        "book_title",
        "issue_date",
        "due_date",
        "return_date",
        "status_badge",
        "fine_amount",
        "fine_paid",
        "owner",
    ]
    list_filter = ["status", "fine_paid", "issue_date", "due_date", "return_date"]
    search_fields = [
        "member__first_name",
        "member__last_name",
        "member__member_id",
        "book_title",
        "book_author",
        "book_isbn",
    ]
    ordering = ["-issue_date"]
    readonly_fields = ["issue_date", "created_at", "updated_at"]

    fieldsets = (
        (
            "Owner Information",
            {"fields": ("owner",), "classes": ("collapse",)},
        ),
        (
            "Transaction Details",
            {"fields": ("member", "book_title", "book_author", "book_isbn")},
        ),
        (
            "Dates",
            {"fields": ("issue_date", "due_date", "return_date")},
        ),
        (
            "Status & Fines",
            {"fields": ("status", "fine_amount", "fine_paid")},
        ),
        (
            "Notes",
            {"fields": ("issue_notes", "return_notes")},
        ),
        (
            "Staff",
            {"fields": ("issued_by", "returned_to")},
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "member" and not request.user.is_superuser:
            kwargs["queryset"] = Member.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.owner = request.user
            if not obj.issued_by:
                obj.issued_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "issued": "#3b82f6",
            "returned": "#10b981",
            "overdue": "#ef4444",
            "lost": "#8b5cf6",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.get_status_display(),
        )