"""
members/views.py
────────────────
All views for the members app.
Every queryset is filtered by `owner=request.user` (multi-tenancy).

Photo serving
─────────────
Member photos are stored as binary blobs (BinaryField) in MySQL.
Use the `member_photo` view to serve them:
    <img src="{% url 'members:member_photo' member.pk %}">
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum, F, ExpressionWrapper, IntegerField
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import json

from .models import Member, Department, Course, AcademicYear, Semester, Transaction
from .forms import (
    MemberForm, DepartmentForm, CourseForm, AcademicYearForm, SemesterForm,
    StudentMemberForm, TeacherMemberForm, GeneralMemberForm,
)

# Optional email service — graceful no-op if not wired yet
try:
    from core.email_service import send_member_confirmation_email
except ImportError:
    def send_member_confirmation_email(member):
        pass


# ── Role form map ─────────────────────────────────────────────────────────────
_ROLE_FORM_MAP = {
    "student": StudentMemberForm,
    "teacher": TeacherMemberForm,
    "general": GeneralMemberForm,
}


def _get_role_form(role):
    return _ROLE_FORM_MAP.get(role, StudentMemberForm)


def _get_institute_type(user):
    try:
        return user.library.institute_type or ""
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _owner_ctx(request):
    """Return the four lookup querysets that every list page needs."""
    return {
        "departments":    Department.objects.filter(owner=request.user),
        "courses":        Course.objects.filter(owner=request.user),
        "academic_years": AcademicYear.objects.filter(owner=request.user),
        "semesters":      Semester.objects.filter(owner=request.user),
    }


def _paginate(qs_or_list, request, per_page=20):
    paginator = Paginator(qs_or_list, per_page)
    page_obj  = paginator.get_page(request.GET.get("page"))
    return page_obj


def _pending_counts(member, owner):
    """
    Return (pending_books, pending_fines_decimal, lost_items) for one member.

    Queries the transactions app (Fine + Transaction scoped by library) as the
    authoritative source.  Falls back to the legacy members.Transaction model
    (scoped by owner) if the transactions app is unavailable.
    """
    library = None
    try:
        library = owner.library   # OneToOneField on accounts.Library
    except Exception:
        pass

    if library is not None:
        try:
            from transactions.models import (
                Transaction as TxnModel,
                Fine as FineModel,
            )
            from django.db.models import Sum as _Sum

            pending_books = TxnModel.objects.for_library(library).filter(
                member=member,
                status__in=[TxnModel.STATUS_ISSUED, TxnModel.STATUS_OVERDUE],
            ).count()

            lost_items = TxnModel.objects.for_library(library).filter(
                member=member,
                status=TxnModel.STATUS_LOST,
            ).count()

            # All unpaid fines: overdue + damage + lost-book penalties
            pending_fines = (
                FineModel.objects.for_library(library).filter(
                    transaction__member=member,
                    status=FineModel.STATUS_UNPAID,
                ).aggregate(total=_Sum("amount"))["total"]
                or 0
            )

            return pending_books, pending_fines, lost_items

        except Exception:
            pass   # transactions app unavailable — fall through

    # Legacy fallback: members.Transaction scoped by owner
    pending_books = Transaction.objects.filter(
        member=member, owner=owner, status__in=["issued", "overdue"]
    ).count()

    pending_fines = (
        Transaction.objects.filter(
            member=member, owner=owner, fine_paid=False
        ).aggregate(total=Sum("fine_amount"))["total"]
        or 0
    )

    lost_items = Transaction.objects.filter(
        member=member, owner=owner, status="lost"
    ).count()

    return pending_books, pending_fines, lost_items


def _wants_json(request):
    """True when the caller expects a JSON response (AJAX fetch)."""
    return (
        request.headers.get("Accept", "").startswith("application/json")
        or request.content_type == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def members_dashboard(request):
    members = Member.objects.filter(owner=request.user)

    total    = members.count()
    active   = members.filter(status="active").count()
    passout  = members.filter(status="passout").count()
    inactive = members.filter(status="inactive").count()

    def pct(n):
        return round(n / total * 100, 1) if total else 0

    stats = {
        "total_count":         total,
        "active_count":        active,
        "passout_count":       passout,
        "inactive_count":      inactive,
        "active_percentage":   pct(active),
        "passout_percentage":  pct(passout),
        "inactive_percentage": pct(inactive),
    }

    recent_members = members.order_by("-created_at")[:10]

    departments = (
        Department.objects.filter(owner=request.user)
        .annotate(member_count=Count("members"))
        .filter(member_count__gt=0)
    )

    context = {
        **stats,
        "stats":             stats,
        "recent_members":    recent_members,
        "department_labels": json.dumps([d.name for d in departments]),
        "department_data":   json.dumps([d.member_count for d in departments]),
    }
    return render(request, "members/members_dashboard.html", context)


# ──────────────────────────────────────────────────────────────────────────────
# Member list views
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def members_list(request):
    members = Member.objects.filter(owner=request.user).select_related(
        "department", "course", "year", "semester"
    )

    if request.GET.get("status"):
        members = members.filter(status=request.GET["status"])
    if request.GET.get("role"):
        members = members.filter(role=request.GET["role"])
    if request.GET.get("department"):
        members = members.filter(department_id=request.GET["department"])
    if request.GET.get("course"):
        members = members.filter(course_id=request.GET["course"])
    if request.GET.get("year"):
        members = members.filter(year_id=request.GET["year"])
    if request.GET.get("semester"):
        members = members.filter(semester_id=request.GET["semester"])

    search = request.GET.get("search", "").strip()
    if search:
        members = members.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
            | Q(email__icontains=search)    | Q(member_id__icontains=search)
            | Q(phone__icontains=search)    | Q(roll_number__icontains=search)
        )

    total_count = members.count()
    page_obj    = _paginate(members, request)
    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "total_count":  total_count,
    }
    return render(request, "members/members_list.html", context)


@login_required
def members_active(request):
    members = Member.objects.filter(
        owner=request.user, status="active"
    ).select_related("department", "course", "year", "semester")

    if request.GET.get("department"):
        members = members.filter(department_id=request.GET["department"])
    if request.GET.get("course"):
        members = members.filter(course_id=request.GET["course"])
    if request.GET.get("year"):
        members = members.filter(year_id=request.GET["year"])

    search = request.GET.get("search", "").strip()
    if search:
        members = members.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
            | Q(email__icontains=search)    | Q(member_id__icontains=search)
        )

    total_count = members.count()
    page_obj    = _paginate(members, request)
    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "total_count":  total_count,
    }
    return render(request, "members/members_active.html", context)


@login_required
def members_inactive(request):
    members = Member.objects.filter(
        owner=request.user, status="inactive"
    ).select_related("department", "course", "year", "semester")

    if request.GET.get("department"):
        members = members.filter(department_id=request.GET["department"])
    if request.GET.get("reason"):
        members = members.filter(inactive_reason__icontains=request.GET["reason"])
    if request.GET.get("year"):
        members = members.filter(year_id=request.GET["year"])

    total_count = members.count()
    page_obj    = _paginate(members, request)
    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "total_count":  total_count,
    }
    return render(request, "members/members_inactive.html", context)


@login_required
def members_passout(request):
    """Pass-out members with department / passout-year / clearance filtering."""
    members = Member.objects.filter(
        owner=request.user, status="passout"
    ).select_related("department", "course", "year", "semester")

    if request.GET.get("department"):
        members = members.filter(department_id=request.GET["department"])

    if request.GET.get("passout_year"):
        try:
            py = int(request.GET["passout_year"])
            members = members.annotate(
                computed_passout_year=ExpressionWrapper(
                    F("admission_year") + F("course__duration"),
                    output_field=IntegerField(),
                )
            ).filter(computed_passout_year=py)
        except (ValueError, TypeError):
            pass

    if request.GET.get("clearance"):
        members = members.filter(clearance_status=request.GET["clearance"])

    # Distinct passout years for the dropdown
    passout_years = (
        Member.objects.filter(owner=request.user, status="passout")
        .exclude(admission_year__isnull=True)
        .exclude(course__isnull=True)
        .annotate(
            passout_yr=ExpressionWrapper(
                F("admission_year") + F("course__duration"),
                output_field=IntegerField(),
            )
        )
        .values_list("passout_yr", flat=True)
        .distinct()
        .order_by("-passout_yr")
    )

    total_count = members.count()
    page_obj    = _paginate(members, request)

    context = {
        **_owner_ctx(request),
        "members":       page_obj,
        "page_obj":      page_obj,
        "is_paginated":  page_obj.has_other_pages(),
        "total_count":   total_count,
        "passout_years": passout_years,
    }
    return render(request, "members/members_passout.html", context)


# ──────────────────────────────────────────────────────────────────────────────
# Member CRUD
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk, owner=request.user)
    transactions = Transaction.objects.filter(
        member=member, owner=request.user
    ).order_by("-issue_date")[:10]

    # BinaryField is always truthy — check bytes length instead
    has_photo = bool(member.photo and bytes(member.photo))

    context = {
        "member":       member,
        "has_photo":    has_photo,
        "transactions": transactions,
    }
    return render(request, "members/member_detail.html", context)


@login_required
def member_add(request):
    institute_type = _get_institute_type(request.user)
    default_role   = "student" if institute_type == "private" else "general"

    if request.method == "POST":
        role      = request.POST.get("role", default_role)
        FormClass = _get_role_form(role)
        form      = FormClass(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            member = form.save_with_create()
            send_member_confirmation_email(member)
            messages.success(request, f"Member {member.full_name} added successfully!")
            return redirect("members:member_detail", pk=member.pk)
        messages.error(request, "Please correct the errors below.")
    else:
        form = _get_role_form(default_role)(user=request.user)

    context = {
        **_owner_ctx(request),
        "form":           form,
        "institute_type": institute_type,
    }
    return render(request, "members/member_add.html", context)


@login_required
def member_edit(request, pk):
    member         = get_object_or_404(Member, pk=pk, owner=request.user)
    institute_type = _get_institute_type(request.user)

    if request.method == "POST":
        role      = request.POST.get("role", member.role)
        FormClass = _get_role_form(role)
        form      = FormClass(request.POST, request.FILES, instance=member, user=request.user)
        if form.is_valid():
            member = form.save_with_create()
            messages.success(request, f"Member {member.full_name} updated successfully!")
            return redirect("members:member_detail", pk=member.pk)
        messages.error(request, "Please correct the errors below.")
    else:
        form = _get_role_form(member.role)(instance=member, user=request.user)

    context = {
        **_owner_ctx(request),
        "form":           form,
        "member":         member,
        "institute_type": institute_type,
    }
    return render(request, "members/member_edit.html", context)


@login_required
def member_delete(request, pk):
    """
    Delete a member record.

    • AJAX POST (Accept: application/json or X-Requested-With: XMLHttpRequest)
      → returns JSON { success, message, redirect_url }
      JS should navigate to redirect_url on success.

    • Regular HTML POST (form submit)
      → deletes and redirects to members_list with a Django message.

    • Any other method
      → redirects back to the detail page (safe fallback).
    """
    if request.method != "POST":
        return redirect("members:member_detail", pk=pk)

    member = get_object_or_404(Member, pk=pk, owner=request.user)
    name   = member.full_name
    json_resp = _wants_json(request)

    try:
        member.delete()
    except Exception as exc:
        if json_resp:
            return JsonResponse(
                {"success": False, "message": f"Could not delete member: {exc}"},
                status=500,
            )
        messages.error(request, f"Could not delete member: {exc}")
        return redirect("members:member_detail", pk=pk)

    msg = f"Member {name} deleted successfully!"

    if json_resp:
        from django.urls import reverse as _reverse
        return JsonResponse({
            "success":      True,
            "message":      msg,
            "redirect_url": _reverse("members:members_list"),
        })

    messages.success(request, msg)
    return redirect("members:members_list")


@login_required
def member_photo(request, pk):
    """
    Serve a member photo stored as BinaryField (LONGBLOB in MySQL).
    Must cast memoryview to bytes and check length — not truthiness.

    Cache strategy:
    • ETag is built from member.updated_at so the browser revalidates
      automatically after any edit (including a photo change).
    • max-age=0 + must-revalidate means the browser always checks the
      ETag before using its cached copy — no stale photo after an edit.
    """
    member = get_object_or_404(Member, pk=pk, owner=request.user)

    raw = member.photo
    if raw is None:
        return HttpResponse(status=404)

    photo_bytes = bytes(raw)
    if not photo_bytes:
        return HttpResponse(status=404)

    # Build a strong ETag from the member's last-update timestamp
    etag = f'"{pk}-{int(member.updated_at.timestamp())}"'

    # Respond 304 Not Modified if the browser's cached copy is still fresh
    if request.META.get("HTTP_IF_NONE_MATCH") == etag:
        return HttpResponse(status=304)

    mime = (member.photo_mime_type or "image/jpeg").strip() or "image/jpeg"
    response = HttpResponse(photo_bytes, content_type=mime)
    response["ETag"] = etag
    response["Cache-Control"] = "private, max-age=0, must-revalidate"
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Member actions
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def member_reactivate(request, pk):
    """
    Reactivate an inactive member.

    • AJAX POST → JSON { success, message }
    • Regular POST → redirect + Django message
    """
    if request.method != "POST":
        if _wants_json(request):
            return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)
        return redirect("members:members_inactive")

    member = get_object_or_404(Member, pk=pk, owner=request.user)
    member.status          = "active"
    member.inactive_since  = None
    member.inactive_reason = None
    member.save()

    msg = f"Member {member.full_name} reactivated successfully!"

    if _wants_json(request):
        from django.urls import reverse as _reverse
        return JsonResponse({
            "success":      True,
            "message":      msg,
            "redirect_url": _reverse("members:member_detail", kwargs={"pk": pk}),
        })

    messages.success(request, msg)
    return redirect("members:member_detail", pk=pk)


@login_required
def member_mark_cleared(request, pk):
    """
    Mark a member as cleared.
    • HTML form POST  → redirect + Django message
    • AJAX fetch with Accept: application/json → JSON { success, message }
    """
    if request.method != "POST":
        return redirect("members:pending_clearance")

    member = get_object_or_404(Member, pk=pk, owner=request.user)
    pending_books, pending_fines, _ = _pending_counts(member, request.user)
    json_resp = _wants_json(request)

    if pending_books == 0 and float(pending_fines) == 0:
        member.clearance_status = "cleared"
        member.clearance_date   = timezone.now()
        member.cleared_by       = request.user
        member.save()
        msg = f"{member.full_name} has been marked as cleared."
        if json_resp:
            return JsonResponse({"success": True, "message": msg})
        messages.success(request, msg)
        return redirect("members:member_detail", pk=pk)
    else:
        msg = (
            f"Cannot clear {member.full_name}. "
            f"Pending: {pending_books} book(s), ₹{pending_fines} in fines."
        )
        if json_resp:
            return JsonResponse({"success": False, "message": msg}, status=400)
        messages.error(request, msg)
        return redirect("members:member_detail", pk=pk)


@login_required
def send_reminder(request, pk):
    """Send a reminder — POST only, returns JSON { success, message }."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)

    member = get_object_or_404(Member, pk=pk, owner=request.user)
    pending_books, pending_fines, lost_items = _pending_counts(member, request.user)

    # TODO: plug in actual e-mail / SMS here
    parts = []
    if pending_books:
        parts.append(f"{pending_books} unreturned book(s)")
    if float(pending_fines) > 0:
        parts.append(f"₹{pending_fines:.2f} in unpaid fines")
    if lost_items:
        parts.append(f"{lost_items} lost item(s)")

    detail = "; ".join(parts) if parts else "no outstanding items"
    return JsonResponse({
        "success": True,
        "message": f"Reminder sent to {member.full_name} ({detail}).",
    })


# ──────────────────────────────────────────────────────────────────────────────
# Clearance views
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def clearance_check(request):
    """
    GET  → render the search page.
    POST → return JSON consumed by clearance_check.js.
    """
    if request.method == "POST":
        query = (request.POST.get("member_id") or "").strip()
        try:
            member = (
                Member.objects.filter(owner=request.user)
                .filter(Q(member_id=query) | Q(phone=query))
                .select_related("department")
                .first()
            )
            if not member:
                return JsonResponse({"success": False, "message": "Member not found."})

            pending_books, pending_fines, _ = _pending_counts(member, request.user)
            is_cleared = (pending_books == 0 and float(pending_fines) == 0)

            payload = {
                "pk":               member.pk,
                "member_id":        member.member_id,
                "full_name":        member.full_name,
                "email":            member.email or "",
                "phone":            member.phone or "",
                "department":       member.department.name if member.department else None,
                "role":             member.get_role_display(),
                "status":           member.status,
                "clearance_status": member.clearance_status,
                "pending_books":    pending_books,
                "pending_fines":    float(pending_fines),
                "is_cleared":       is_cleared,
                "clearance_date":   (
                    member.clearance_date.strftime("%d %b %Y")
                    if member.clearance_date else None
                ),
            }
            return JsonResponse({"success": True, "data": payload})

        except Exception as exc:
            return JsonResponse({"success": False, "message": str(exc)}, status=500)

    # GET — pass departments context so the page renders cleanly
    return render(request, "members/clearance_check.html", _owner_ctx(request))


@login_required
def cleared_members(request):
    """Members whose clearance_status == 'cleared'."""
    members = Member.objects.filter(
        owner=request.user, clearance_status="cleared"
    ).select_related("department", "cleared_by").order_by("-clearance_date")

    if request.GET.get("department"):
        members = members.filter(department_id=request.GET["department"])

    now = timezone.now()
    date_filter = request.GET.get("clearance_date")
    if date_filter == "today":
        members = members.filter(clearance_date__date=now.date())
    elif date_filter == "week":
        members = members.filter(clearance_date__gte=now - timedelta(days=7))
    elif date_filter == "month":
        members = members.filter(clearance_date__gte=now - timedelta(days=30))
    elif date_filter == "year":
        members = members.filter(clearance_date__gte=now - timedelta(days=365))

    if request.GET.get("member_type"):
        members = members.filter(status=request.GET["member_type"])

    total_count = members.count()
    page_obj    = _paginate(members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "total_count":  total_count,
    }
    return render(request, "members/cleared_members.html", context)


@login_required
def pending_clearance(request):
    """Members with outstanding books or unpaid fines."""
    base_qs = Member.objects.filter(
        owner=request.user, clearance_status="pending"
    ).select_related("department")

    # Annotate pending data in Python to keep owner-scoping simple
    pending_members = []
    for member in base_qs:
        pending_books, pending_fines, lost_items = _pending_counts(member, request.user)

        if pending_books > 0 or float(pending_fines) > 0 or lost_items > 0:
            oldest = (
                Transaction.objects.filter(
                    member=member, owner=request.user,
                    status__in=["issued", "overdue"],
                ).order_by("issue_date").first()
            )
            member.pending_books   = pending_books
            member.total_fine      = pending_fines
            member.pending_damages = 0
            member.pending_lost    = lost_items
            member.days_pending    = (
                (timezone.now().date() - oldest.issue_date.date()).days
                if oldest else 0
            )
            pending_members.append(member)

    # Post-annotation filters
    if request.GET.get("department"):
        try:
            did = int(request.GET["department"])
            pending_members = [m for m in pending_members if m.department_id == did]
        except (ValueError, TypeError):
            pass

    issue_type = request.GET.get("issue_type")
    if issue_type == "books":
        pending_members = [m for m in pending_members if m.pending_books > 0]
    elif issue_type == "fines":
        pending_members = [m for m in pending_members if float(m.total_fine) > 0]
    elif issue_type == "damages":
        pending_members = [m for m in pending_members if m.pending_damages > 0]
    elif issue_type == "lost":
        pending_members = [m for m in pending_members if m.pending_lost > 0]

    priority = request.GET.get("priority")
    if priority == "high":
        pending_members = [m for m in pending_members if m.days_pending > 30]
    elif priority == "medium":
        pending_members = [m for m in pending_members if 15 < m.days_pending <= 30]
    elif priority == "low":
        pending_members = [m for m in pending_members if m.days_pending <= 15]

    stats = {
        "unreturned_books": sum(m.pending_books for m in pending_members),
        "total_fines":      round(sum(float(m.total_fine) for m in pending_members), 2),
        "overdue_books":    Transaction.objects.filter(
            owner=request.user, status="overdue"
        ).count(),
    }

    total_count = len(pending_members)
    page_obj    = _paginate(pending_members, request)

    context = {
        **_owner_ctx(request),
        "members":      page_obj,
        "page_obj":     page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "total_count":  total_count,
        "stats":        stats,
    }
    return render(request, "members/pending_clearance.html", context)


@login_required
def clearance_certificate(request, pk):
    """
    Generate and stream a library clearance certificate PDF.
    Uses the full institutional-letter layout from clearance_certificate.py.
    Falls back to plain text if ReportLab is not installed.
    Only members with clearance_status == 'cleared' get a certificate.
    """
    member = get_object_or_404(
        Member, pk=pk, owner=request.user, clearance_status="cleared"
    )

    library = None
    try:
        library = request.user.library
    except Exception:
        pass

    try:
        from .clearance_certificate import build_clearance_pdf
        pdf_bytes, filename = build_clearance_pdf(member, library)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except ImportError:
        cleared_by = "System"
        if member.cleared_by:
            cleared_by = member.cleared_by.get_full_name() or member.cleared_by.username

        lines = [
            "LIBRARY CLEARANCE CERTIFICATE",
            "=" * 44,
            f"Institution  : {getattr(library, 'name', 'Library') if library else 'Library'}",
            f"Member Name  : {member.full_name}",
            f"Member ID    : {member.member_id}",
            f"Role         : {member.get_role_display()}",
            f"Department   : {member.department.name if member.department else 'N/A'}",
            f"Clearance    : {member.clearance_date.strftime('%d %B %Y') if member.clearance_date else 'N/A'}",
            f"Cleared By   : {cleared_by}",
            "=" * 44,
            "All library obligations have been settled.",
        ]
        filename = f"clearance_{member.member_id}.txt"
        response = HttpResponse("\n".join(lines).encode(), content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("members:member_detail", pk=pk)


@login_required
def issue_clearance(request, pk):
    """
    Issue final library clearance for a cleared member.

    Blocking conditions — clearance is REFUSED if ANY of the following exist:
      • Active Transaction (status=issued / overdue) in the transactions app
      • Lost Transaction (status=lost) with no resolved MissingBook
      • Unpaid Fine in the Fine ledger (overdue / damage / lost-book penalty)

    Two-step AJAX flow (Accept: application/json):
      Step 1  POST { confirm: false }
              → Runs full blocking check.  Returns JSON { success, ready, message }
                or { success: false, message, blocking } on failure.
      Step 2  POST { confirm: true }
              → Commits: clearance_status=cleared, status=passout, saves member.
                Returns { success, certificate_url } so JS opens the PDF.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)

    member = get_object_or_404(Member, pk=pk, owner=request.user)

    # Parse body — support JSON body and form POST
    confirm = False
    try:
        body    = json.loads(request.body or "{}")
        confirm = bool(body.get("confirm", False))
    except (json.JSONDecodeError, ValueError):
        confirm = request.POST.get("confirm") == "true"

    # ── Full blocking check using the transactions app ────────────────────────
    blocking = _build_blocking_reasons(member, request.user)

    if blocking["has_blocking"]:
        lines = []
        if blocking["active_loans"]:
            lines.append(
                f"{blocking['active_loans']} unreturned/overdue book(s) must be returned first."
            )
        if blocking["lost_items"]:
            lines.append(
                f"{blocking['lost_items']} lost item(s) — penalty must be resolved."
            )
        if blocking["unpaid_fine"] > 0:
            lines.append(
                f"₹{blocking['unpaid_fine']:.2f} in unpaid fines must be cleared."
            )

        return JsonResponse({
                "success": False,
                "message": "Cannot issue clearance. Outstanding obligations:\n• " 
                        + "\n• ".join(lines),
                "blocking": blocking,
            }, status=400)

    # All clear
    if not confirm:
        # Step 1: preflight only — no DB write
        return JsonResponse({
            "success":        True,
            "ready":          True,
            "message": (
                f"{member.full_name} has no pending books, fines, or lost-item obligations. "
                "Confirm to issue the certificate and move them to Passout."
            ),
            "current_status": member.status,
        })

    # Step 2: commit
    now = timezone.now()
    if member.clearance_status != "cleared":
        member.clearance_status = "cleared"
        member.clearance_date   = now
        member.cleared_by       = request.user

    member.status = "passout"
    member.save()

    from django.urls import reverse as _reverse
    cert_url = _reverse("members:clearance_certificate", kwargs={"pk": member.pk})

    return JsonResponse({
        "success":         True,
        "message":         f"Clearance issued. {member.full_name} has been moved to Passout.",
        "certificate_url": cert_url,
        "member_id":       member.member_id,
        "full_name":       member.full_name,
    })


def _build_blocking_reasons(member, owner):
    """
    Query BOTH the transactions app (authoritative) AND the legacy
    members.Transaction model for any obligation that blocks clearance.

    Returns a dict:
      {
        has_blocking: bool,
        active_loans: int,   # issued + overdue books
        lost_items:   int,   # lost books not yet resolved
        unpaid_fine:  float, # total unpaid Fine amount (₹)
        source:       str,   # 'transactions_app' | 'legacy'
      }
    """
    from decimal import Decimal as _D

    library = None
    try:
        library = owner.library
    except Exception:
        pass

    if library is not None:
        try:
            from transactions.models import (
                Transaction as TxnModel,
                Fine        as FineModel,
            )
            from django.db.models import Sum as _Sum

            active_loans = TxnModel.objects.for_library(library).filter(
                member=member,
                status__in=[TxnModel.STATUS_ISSUED, TxnModel.STATUS_OVERDUE],
            ).count()

            lost_items = TxnModel.objects.for_library(library).filter(
                member=member,
                status=TxnModel.STATUS_LOST,
            ).count()

            unpaid_fine = float(
                FineModel.objects.for_library(library).filter(
                    transaction__member=member,
                    status=FineModel.STATUS_UNPAID,
                ).aggregate(total=_Sum("amount"))["total"]
                or _D("0.00")
            )

            return {
                "has_blocking": active_loans > 0 or lost_items > 0 or unpaid_fine > 0,
                "active_loans":  active_loans,
                "lost_items":    lost_items,
                "unpaid_fine":   unpaid_fine,
                "source":        "transactions_app",
            }
        except Exception:
            pass   # fall through to legacy

    # Legacy fallback
    active_loans = Transaction.objects.filter(
        member=member, owner=owner, status__in=["issued", "overdue"]
    ).count()

    lost_items = Transaction.objects.filter(
        member=member, owner=owner, status="lost"
    ).count()

    unpaid_fine = float(
        Transaction.objects.filter(
            member=member, owner=owner, fine_paid=False
        ).aggregate(total=Sum("fine_amount"))["total"]
        or 0
    )

    return {
        "has_blocking": active_loans > 0 or lost_items > 0 or unpaid_fine > 0,
        "active_loans":  active_loans,
        "lost_items":    lost_items,
        "unpaid_fine":   unpaid_fine,
        "source":        "legacy",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Lookup management
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def department_list(request):
    departments = Department.objects.filter(owner=request.user)
    if request.method == "POST":
        form = DepartmentForm(request.POST, user=request.user)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.owner = request.user
            dept.save()
            messages.success(request, f"Department '{dept.name}' created.")
            return redirect("members:department_list")
    else:
        form = DepartmentForm(user=request.user)
    return render(request, "members/department_list.html", {"departments": departments, "form": form})


@login_required
def department_delete(request, pk):
    if request.method == "POST":
        dept = get_object_or_404(Department, pk=pk, owner=request.user)
        dept.delete()
        messages.success(request, "Department deleted.")
    return redirect("members:department_list")


@login_required
def course_list(request):
    courses = Course.objects.filter(owner=request.user)
    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            messages.success(request, f"Course '{course.name}' created.")
            return redirect("members:course_list")
    else:
        form = CourseForm(user=request.user)
    return render(request, "members/course_list.html", {"courses": courses, "form": form})


@login_required
def course_delete(request, pk):
    if request.method == "POST":
        course = get_object_or_404(Course, pk=pk, owner=request.user)
        course.delete()
        messages.success(request, "Course deleted.")
    return redirect("members:course_list")


@login_required
def academic_year_list(request):
    years = AcademicYear.objects.filter(owner=request.user)
    if request.method == "POST":
        form = AcademicYearForm(request.POST, user=request.user)
        if form.is_valid():
            yr = form.save(commit=False)
            yr.owner = request.user
            yr.save()
            messages.success(request, f"Academic year '{yr.name}' created.")
            return redirect("members:academic_year_list")
    else:
        form = AcademicYearForm(user=request.user)
    return render(request, "members/academic_year_list.html", {"years": years, "form": form})


@login_required
def academic_year_delete(request, pk):
    if request.method == "POST":
        yr = get_object_or_404(AcademicYear, pk=pk, owner=request.user)
        yr.delete()
        messages.success(request, "Academic year deleted.")
    return redirect("members:academic_year_list")


@login_required
def semester_list(request):
    semesters = Semester.objects.filter(owner=request.user)
    if request.method == "POST":
        form = SemesterForm(request.POST, user=request.user)
        if form.is_valid():
            sem = form.save(commit=False)
            sem.owner = request.user
            sem.save()
            messages.success(request, f"Semester '{sem.name}' created.")
            return redirect("members:semester_list")
    else:
        form = SemesterForm(user=request.user)
    return render(request, "members/semester_list.html", {"semesters": semesters, "form": form})


@login_required
def semester_delete(request, pk):
    if request.method == "POST":
        sem = get_object_or_404(Semester, pk=pk, owner=request.user)
        sem.delete()
        messages.success(request, "Semester deleted.")
    return redirect("members:semester_list")