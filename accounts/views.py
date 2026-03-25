import base64
import json
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_POST

from .models import (
    Library,
    LibraryRuleSettings,
    MemberSettings,
    SecuritySettings,
    NotificationSettings,
    AppearanceSettings,
)

# subscriptions app models (imported lazily to avoid circular issues)
def _get_subscription_models():
    from subscriptions.models import Subscription, Plan
    return Subscription, Plan
from .utils import generate_random_password, generate_username

# ── Email service ─────────────────────────────────────────────
# All email functions available:
#   send_account_credentials(email, password, username)
#   send_password_reset_email(user, new_password, lib_name, username)
#   send_member_confirmation_email(member)
#   send_member_reactivation_email(member)
#   send_clearance_confirmation_email(member)
#   send_overdue_reminder_email(member, overdue_transactions)
#   send_member_deletion_email(member_name, member_id, member_email)
try:
    from core import email_service
    EMAIL_ENABLED = True
except ImportError:
    email_service  = None
    EMAIL_ENABLED  = False


def _send_email(fn_name, *args, **kwargs):
    """
    Safe wrapper — calls email_service.<fn_name>(*args) and silently
    swallows any exception so an email failure never breaks a view.
    Returns True on success, False on failure / unavailable.
    """
    if not EMAIL_ENABLED or email_service is None:
        return False
    try:
        fn = getattr(email_service, fn_name)
        return fn(*args, **kwargs)
    except Exception as exc:
        print(f"[email_service] {fn_name} failed: {exc}")
        return False


# ── WhatsApp Business service ──────────────────────────────────
# All WhatsApp functions available:
#   send_account_credentials_whatsapp(phone, password, username)
#   send_password_reset_whatsapp(user, new_password, lib_name, username)
#   send_member_confirmation_whatsapp(member)
#   send_member_reactivation_whatsapp(member)
#   send_clearance_confirmation_whatsapp(member)
#   send_overdue_reminder_whatsapp(member, overdue_transactions)
#   send_member_deletion_whatsapp(member_name, member_id, member_phone)
try:
    from core import whatsapp_service
    WHATSAPP_ENABLED = True
except ImportError:
    whatsapp_service  = None
    WHATSAPP_ENABLED  = False


def _send_whatsapp(fn_name, *args, **kwargs):
    """
    Safe wrapper — calls whatsapp_service.<fn_name>(*args) and silently
    swallows any exception so a WhatsApp failure never breaks a view.
    Returns True on success, False on failure / unavailable.
    """
    if not WHATSAPP_ENABLED or whatsapp_service is None:
        return False
    try:
        fn = getattr(whatsapp_service, fn_name)
        return fn(*args, **kwargs)
    except Exception as exc:
        print(f"[whatsapp_service] {fn_name} failed: {exc}")
        return False


# ==========================================================
# 🔐 SIGN IN
# ==========================================================
def _post_login_redirect(user):
    """
    Central routing logic after a successful login.
    Priority order:
      1. Django superuser / staff  →  /superuser/  (SaaS admin dashboard)
      2. Library admin (has Library profile) →  /authentication/admin_dashboard/
      3. Fallback  →  /authentication/admin_dashboard/
    """
    if user.is_superuser or user.is_staff:
        return redirect("/superuser/")
    return redirect("/authentication/admin_dashboard/")


def view_signin(request):
    # Already logged in — route to the right dashboard
    if request.user.is_authenticated:
        return _post_login_redirect(request.user)

    if request.method == "POST":
        username    = request.POST.get("username", "").strip()
        password    = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        if not username or not password:
            messages.error(request, "Please enter username and password.")
            return render(request, "accounts/sign_in.html")

        user = authenticate(request, username=username, password=password)
        if user:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated.")
                return render(request, "accounts/sign_in.html")

            login(request, user)
            if remember_me:
                request.session.set_expiry(timedelta(days=7))
            else:
                request.session.set_expiry(0)
            messages.success(request, "Login successful.")
            return _post_login_redirect(user)

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/sign_in.html")


# ==========================================================
# 🚪 LOGOUT
# ==========================================================
@login_required
def view_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("/authentication/sign_in/")


# ==========================================================
# 📝 REGISTER LIBRARY
# ==========================================================
def register_library(request):
    if request.method == "POST":
        p = request.POST

        library_name    = p.get("library_name",           "").strip()
        institute_name  = p.get("institute_name",          "").strip()
        institute_type  = p.get("institute_type",          "").strip()
        institute_email = p.get("institute_email",         "").strip().lower()
        phone_number    = p.get("phone_number",            "").strip()
        address         = p.get("address",                 "").strip()
        district        = p.get("district",                "").strip()
        state           = p.get("state",                   "").strip()
        country         = p.get("country",                 "").strip()
        admin_full_name = p.get("admin_full_name",         "").strip()
        password        = p.get("admin_password",          "")
        confirm_pw      = p.get("admin_confirm_password",  "")
        declaration     = p.get("declaration")

        # ── Required field check ──────────────────────────────────
        required = {
            "Library name":       library_name,
            "Library type":       institute_type,
            "Official email":     institute_email,
            "Address":            address,
            "District":           district,
            "State":              state,
            "Country":            country,
            "Administrator name": admin_full_name,
            "Password":           password,
            "Confirm password":   confirm_pw,
        }
        missing = [label for label, val in required.items() if not val]
        if missing:
            messages.error(request, f"Please fill in: {', '.join(missing)}.")
            return render(request, "accounts/sign_up.html")

        if not declaration:
            messages.error(request, "You must accept the declaration to register.")
            return render(request, "accounts/sign_up.html")

        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", institute_email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, "accounts/sign_up.html")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "accounts/sign_up.html")

        if password != confirm_pw:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/sign_up.html")

        if User.objects.filter(email=institute_email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "accounts/sign_up.html")

        if Library.objects.filter(institute_email=institute_email).exists():
            messages.error(request, "A library with this email is already registered.")
            return render(request, "accounts/sign_up.html")

        valid_types = {c[0] for c in Library.INSTITUTE_TYPE_CHOICES}
        if institute_type not in valid_types:
            messages.error(request, "Invalid library type selected.")
            return render(request, "accounts/sign_up.html")

        if institute_type == "Institution" and not institute_name:
            messages.error(request, "Institution name is required for Institutional Libraries.")
            return render(request, "accounts/sign_up.html")

        # ── Logo validation (optional) ────────────────────────────
        logo_data = None
        logo_mime = None
        if "library_logo" in request.FILES:
            logo_file = request.FILES["library_logo"]
            if logo_file.content_type not in ("image/jpeg", "image/png"):
                messages.error(request, "Logo must be a JPG or PNG image.")
                return render(request, "accounts/sign_up.html")
            if logo_file.size > 2 * 1024 * 1024:
                messages.error(request, "Logo file must be under 2 MB.")
                return render(request, "accounts/sign_up.html")
            logo_data = logo_file.read()
            logo_mime = logo_file.content_type

        name_parts = admin_full_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name  = name_parts[1] if len(name_parts) > 1 else ""

        # ── Create user + library atomically ─────────────────────
        try:
            with transaction.atomic():
                username = generate_username()
                attempts = 0
                while User.objects.filter(username=username).exists():
                    username = generate_username()
                    attempts += 1
                    if attempts > 20:
                        raise RuntimeError("Could not generate a unique username.")

                user = User.objects.create_user(
                    username=username,
                    email=institute_email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )

                Library.objects.create(
                    user=user,
                    library_name=library_name,
                    institute_name=institute_name,
                    institute_type=institute_type,
                    institute_email=institute_email,
                    phone_number=phone_number or None,
                    address=address,
                    district=district,
                    state=state,
                    country=country,
                    library_logo=logo_data,
                    library_logo_mime=logo_mime,
                )

        except IntegrityError:
            messages.error(request, "A library with this email is already registered.")
            return render(request, "accounts/sign_up.html")
        except Exception as e:
            import traceback; traceback.print_exc()
            messages.error(request, f"Registration failed: {e}")
            return render(request, "accounts/sign_up.html")

        # ── Email credentials to new admin ────────────────────────
        _send_email("send_account_credentials", institute_email, password, username)

        # ── WhatsApp credentials to new admin ─────────────────────
        # if phone_number:
        #     _send_whatsapp("send_account_credentials_whatsapp", phone_number, password, username)

        messages.success(request, f"✅ Library registered! Your login username is: {username}")
        return redirect("/authentication/sign_in/")

    return render(request, "accounts/sign_up.html")


# ==========================================================
# 🔑 FORGOT PASSWORD
# ==========================================================
def view_forget_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        user  = User.objects.filter(email=email).first()

        if user:
            new_password = generate_random_password()
            user.set_password(new_password)
            user.save()

            lib      = getattr(user, "library", None)
            lib_name = lib.library_name if lib else "Library"

            # send_password_reset_email(user, new_password, lib_name, username)
            _send_email("send_password_reset_email", user, new_password, lib_name, user.username)
            # _send_whatsapp("send_password_reset_whatsapp", user, new_password, lib_name, user.username)

        messages.success(request, "If this email exists, a new password has been sent.")
        return redirect("/authentication/sign_in/")

    return render(request, "accounts/forget_password.html")


# ==========================================================
# 🏛️ LIBRARY SETUP  (first-time onboarding)
# ==========================================================

_VALID_TIMEZONES = {
    "Asia/Kolkata", "Asia/Dhaka", "Asia/Kathmandu", "Asia/Colombo",
    "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo",
    "Europe/London", "Europe/Paris",
    "America/New_York", "America/Chicago", "America/Los_Angeles",
}

_VALID_DAYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}


@login_required
def library_setup_view(request):
    """
    First-time library configuration page.

    GET  – Render setup form. If already configured, redirect to dashboard.
    POST – Validate and save everything to LibraryRuleSettings.
           Borrow limits are also mirrored to MemberSettings.
           Notifications are saved to NotificationSettings.
    """
    library = _get_library_or_404(request)
    rules, _ = LibraryRuleSettings.objects.get_or_create(library=library)

    if _is_setup_complete(library, rules):
        return redirect("/authentication/admin_dashboard/")

    if request.method == "POST":
        errors = {}
        p = request.POST

        library_code         = p.get("library_code",          "").strip().upper()
        timezone_val         = p.get("timezone",              "").strip()
        student_borrow_limit = p.get("student_borrow_limit",  "").strip()
        teacher_borrow_limit = p.get("teacher_borrow_limit",  "").strip()
        max_books            = p.get("max_books_per_member",   "").strip()
        late_fine            = p.get("late_fine",              "").strip()
        working_days_raw     = p.get("working_days",           "").strip()

        # ── Validate timezone ─────────────────────────────────────
        if not timezone_val or timezone_val not in _VALID_TIMEZONES:
            errors["timezone"] = "Please select a valid time zone."

        # ── Validate student borrow limit ─────────────────────────
        sbl_val = _int(student_borrow_limit, None)
        if sbl_val is None or not (1 <= sbl_val <= 50):
            errors["student_borrow_limit"] = "Enter a value between 1 and 50."

        # ── Validate teacher borrow limit ─────────────────────────
        tbl_val = _int(teacher_borrow_limit, None)
        if tbl_val is None or not (1 <= tbl_val <= 50):
            errors["teacher_borrow_limit"] = "Enter a value between 1 and 50."

        # ── Validate max books per member ─────────────────────────
        mb_val = _int(max_books, None)
        if mb_val is None or not (1 <= mb_val <= 50):
            errors["max_books_per_member"] = "Enter a value between 1 and 50."

        # ── Validate late fine ────────────────────────────────────
        lf_val = _dec(late_fine, None)
        if lf_val is None or lf_val < 0:
            errors["late_fine"] = "Must be 0 or greater."

        # ── Validate working days ─────────────────────────────────
        days_list = [
            d.strip() for d in working_days_raw.split(",")
            if d.strip() in _VALID_DAYS
        ]
        if not days_list:
            errors["working_days"] = "Select at least one working day."

        # ── Validate library code (if user regenerated it) ────────
        if library_code and library_code != library.library_code:
            import re as _re
            if _re.match(r"^DG-[A-Z0-9]{4}$", library_code):
                if Library.objects.exclude(pk=library.pk).filter(library_code=library_code).exists():
                    errors["library_code"] = "This code is already in use. Click 'New' to generate another."
            else:
                errors["library_code"] = "Invalid code format."

        # ── Return errors ─────────────────────────────────────────
        if errors:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "errors": errors}, status=422)
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, "accounts/library_setup.html", _setup_ctx(library, rules))

        # ── Save everything to LibraryRuleSettings ────────────────
        try:
            with transaction.atomic():

                if library_code and library_code != library.library_code:
                    library.library_code = library_code

                # Core rule fields
                rules.student_borrow_limit  = sbl_val
                rules.teacher_borrow_limit  = tbl_val
                rules.max_books_per_member  = mb_val
                rules.late_fine             = lf_val
                rules.timezone              = timezone_val
                rules.working_days          = ",".join(days_list)
                rules.is_setup_complete     = True

                # Loan behaviour toggles
                rules.auto_fine             = p.get("auto_fine")             == "on"
                rules.allow_renewal         = p.get("allow_renewal")         == "on"
                rules.allow_partial_payment = p.get("allow_partial_payment") == "on"
                rules.auto_mark_lost        = p.get("auto_mark_lost")        == "on"
                rules.allow_advance_booking = p.get("allow_advance_booking") == "on"
                rules.save()

                # Mirror borrow limits + member permissions to MemberSettings
                member_cfg, _ = MemberSettings.objects.get_or_create(library=library)
                member_cfg.student_borrow_limit      = sbl_val
                member_cfg.teacher_borrow_limit      = tbl_val
                member_cfg.allow_self_registration   = p.get("allow_self_registration")   == "on"
                member_cfg.require_admin_approval    = p.get("require_admin_approval")    == "on"
                member_cfg.enable_member_id_download = p.get("enable_member_id_download") == "on"
                member_cfg.allow_profile_edit        = p.get("allow_profile_edit")        == "on"
                member_cfg.save()

                # Notification preferences
                notif, _ = NotificationSettings.objects.get_or_create(library=library)
                notif.email_overdue_reminder = p.get("email_overdue_reminder") == "on"
                notif.sms_reminder           = p.get("sms_reminder")           == "on"
                notif.monthly_usage_report   = p.get("monthly_usage_report")   == "on"
                notif.weekly_database_backup = p.get("weekly_database_backup") == "on"
                notif.daily_activity_summary = p.get("daily_activity_summary") == "on"
                notif.save()

                library.save()

        except Exception as exc:
            import traceback; traceback.print_exc()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "errors": {"__all__": str(exc)}}, status=500)
            messages.error(request, f"Setup failed: {exc}")
            return render(request, "accounts/library_setup.html", _setup_ctx(library, rules))

        # ── Success ───────────────────────────────────────────────
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "ok":      True,
                "code":    library.library_code,
                "redirect": "/authentication/admin_dashboard/",
            })

        messages.success(request, "✅ Library configured successfully! All modules are now active.")
        return redirect("/authentication/admin_dashboard/")

    # GET
    return render(request, "accounts/library_setup.html", _setup_ctx(library, rules))


# ── AJAX: regenerate library code ────────────────────────────
@login_required
@require_POST
def regenerate_library_code(request):
    import random, string
    library  = _get_library_or_404(request)
    chars    = string.ascii_uppercase.replace("I", "").replace("O", "") + "23456789"
    attempts = 0
    while True:
        code = "DG-" + "".join(random.choices(chars, k=4))
        if not Library.objects.filter(library_code=code).exists():
            break
        attempts += 1
        if attempts > 50:
            return JsonResponse({"ok": False, "error": "Could not generate code."}, status=500)
    return JsonResponse({"ok": True, "code": code})


def _is_setup_complete(library, rules):
    return getattr(rules, "is_setup_complete", False)


def _setup_ctx(library, rules):
    return {
        "library":      library,
        "rules":        rules,
        "timezone":     getattr(rules, "timezone",      "Asia/Kolkata"),
        "working_days": getattr(rules, "working_days",  "Mon,Tue,Wed,Thu,Fri"),
    }


# # ==========================================================
# # 🏠 ADMIN DASHBOARD
# # ==========================================================
# @login_required
# def admin_dashboard(request):
#     library  = _get_library_or_404(request)
#     rules_qs = LibraryRuleSettings.objects.filter(library=library).first()
#     if rules_qs and not _is_setup_complete(library, rules_qs):
#         return redirect("/authentication/library_setup/")

#     owner = library.user

#     from accounts.models import Library
#     from books.models import Book, Category
#     from members.models import Member
#     from transactions.models import Transaction

#     today            = date.today()
#     this_month_start = _first_of_month(today, months_back=0)
#     last_month_start = _first_of_month(today, months_back=1)
#     last_month_end   = this_month_start - timedelta(days=1)

#     if request.user.is_superuser:
#         total_libraries      = Library.objects.count()
#         libraries_this_month = Library.objects.filter(created_at__date__gte=this_month_start).count()
#         libraries_last_month = Library.objects.filter(
#             created_at__date__gte=last_month_start,
#             created_at__date__lte=last_month_end,
#         ).count()
#     else:
#         total_libraries = 1
#         libraries_this_month = libraries_last_month = 0
#     libraries_change = libraries_this_month - libraries_last_month

#     total_books  = Book.objects.filter(owner=owner).count()
#     books_change = (
#         Book.objects.filter(owner=owner, created_at__date__gte=this_month_start).count()
#         - Book.objects.filter(
#             owner=owner,
#             created_at__date__gte=last_month_start,
#             created_at__date__lte=last_month_end,
#         ).count()
#     )

#     total_members  = Member.objects.filter(owner=owner, status="active").count()
#     members_change = (
#         Member.objects.filter(owner=owner, date_joined__gte=this_month_start).count()
#         - Member.objects.filter(
#             owner=owner,
#             date_joined__gte=last_month_start,
#             date_joined__lte=last_month_end,
#         ).count()
#     )

#     base_txns           = Transaction.objects.for_library(library)
#     active_transactions = base_txns.filter(
#         status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE)
#     ).count()
#     transactions_change = (
#         base_txns.filter(issue_date__gte=this_month_start).count()
#         - base_txns.filter(
#             issue_date__gte=last_month_start,
#             issue_date__lte=last_month_end,
#         ).count()
#     )

#     count_map = {
#         row["status"]: row["cnt"]
#         for row in Member.objects.filter(owner=owner)
#             .values("status")
#             .annotate(cnt=Count("id"))
#     }
#     active_count   = count_map.get("active",   0)
#     passout_count  = count_map.get("passout",  0)
#     inactive_count = count_map.get("inactive", 0)
#     total_count    = active_count + passout_count + inactive_count

#     def _pct(n):
#         return round(n / total_count * 100, 1) if total_count else 0

#     stats = {
#         "active_count":        active_count,
#         "passout_count":       passout_count,
#         "inactive_count":      inactive_count,
#         "total_count":         total_count,
#         "active_percentage":   _pct(active_count),
#         "passout_percentage":  _pct(passout_count),
#         "inactive_percentage": _pct(inactive_count),
#     }

#     # ── Chart 1: Monthly Loans (last 6 months) ────────────────
#     _loan_labels_raw, _loan_data_raw = [], []
#     for i in range(5, -1, -1):
#         ms  = _first_of_month(today, months_back=i)
#         me  = _first_of_next_month(ms)
#         cnt = base_txns.filter(issue_date__gte=ms, issue_date__lt=me).count()
#         _loan_labels_raw.append(ms.strftime("%b %Y"))
#         _loan_data_raw.append(cnt)
#     loans_have_data = any(v > 0 for v in _loan_data_raw)

#     # ── Chart 2: Books by Category ────────────────────────────
#     cat_qs = (
#         Category.objects
#         .filter(owner=owner)
#         .annotate(cnt=Count("books"))
#         .filter(cnt__gt=0)
#         .order_by("-cnt")[:8]
#     )
#     _cat_labels_raw      = [c.name for c in cat_qs]
#     _cat_data_raw        = [c.cnt  for c in cat_qs]
#     categories_have_data = len(_cat_labels_raw) > 0

#     # ── Chart 3: New Members per day (last 7 days) ────────────
#     day_count_map = {
#         row["date_joined"]: row["cnt"]
#         for row in Member.objects.filter(
#             owner=owner,
#             date_joined__gte=today - timedelta(days=6),
#             date_joined__lte=today,
#         ).values("date_joined").annotate(cnt=Count("id"))
#     }
#     _day_labels_raw, _day_data_raw = [], []
#     for i in range(6, -1, -1):
#         d = today - timedelta(days=i)
#         _day_labels_raw.append(d.strftime("%a"))
#         _day_data_raw.append(day_count_map.get(d, 0))
#     members_chart_have_data = any(v > 0 for v in _day_data_raw)

#     # ── Chart 4: Members by Department ───────────────────────
#     dept_qs = (
#         Member.objects
#         .filter(owner=owner)
#         .values("department__name")
#         .annotate(cnt=Count("id"))
#         .order_by("-cnt")
#     )
#     _dept_labels_raw = [row["department__name"] or "No Department" for row in dept_qs]
#     _dept_data_raw   = [row["cnt"] for row in dept_qs]

#     # ── Recent Activity Feed ──────────────────────────────────
#     recent_activities = []
#     for txn in base_txns.select_related("member", "book").order_by("-created_at")[:5]:
#         if txn.status == Transaction.STATUS_RETURNED:
#             icon, color, title = "undo-alt",             "green",  f"Book returned: {txn.book.title}"
#         elif txn.status == Transaction.STATUS_OVERDUE:
#             icon, color, title = "exclamation-triangle",  "red",   f"Overdue: {txn.book.title}"
#         elif txn.status == Transaction.STATUS_LOST:
#             icon, color, title = "times-circle",          "red",   f"Lost book: {txn.book.title}"
#         else:
#             icon, color, title = "book",                  "blue",  f"Book issued: {txn.book.title}"
#         recent_activities.append({
#             "title":       title,
#             "description": f"{txn.member.first_name} {txn.member.last_name}",
#             "icon":        icon,
#             "color":       color,
#             "timestamp":   timesince(txn.created_at) + " ago",
#         })

#     for m in Member.objects.filter(owner=owner).order_by("-date_joined", "-id")[:3]:
#         joined_dt  = datetime.combine(m.date_joined, datetime.min.time())
#         role_label = m.get_role_display() if hasattr(m, "get_role_display") else ""
#         recent_activities.append({
#             "title":       f"New member: {m.first_name} {m.last_name}",
#             "description": f"ID: {m.member_id}  {role_label}".strip(),
#             "icon":        "user-plus",
#             "color":       "purple",
#             "timestamp":   timesince(joined_dt) + " ago",
#         })
#     recent_activities = recent_activities[:8]

#     recent_members = (
#         Member.objects
#         .filter(owner=owner)
#         .select_related("department")
#         .order_by("-date_joined", "-id")[:5]
#     )

#     library_logo_b64 = ""
#     if library.library_logo and library.library_logo_mime:
#         raw = base64.b64encode(bytes(library.library_logo)).decode("ascii")
#         library_logo_b64 = f"data:{library.library_logo_mime};base64,{raw}"

#     notification_count = base_txns.filter(status=Transaction.STATUS_OVERDUE).count()

#     return render(request, "dashboards/admin_dashboard.html", {
#         "total_libraries":     total_libraries,
#         "libraries_change":    libraries_change,
#         "total_books":         total_books,
#         "books_change":        books_change,
#         "total_members":       total_members,
#         "members_change":      members_change,
#         "active_transactions": active_transactions,
#         "transactions_change": transactions_change,
#         "stats":               stats,
#         "monthly_loan_labels": json.dumps(_loan_labels_raw)  if loans_have_data         else "",
#         "monthly_loan_data":   json.dumps(_loan_data_raw)    if loans_have_data         else "",
#         "category_labels":     json.dumps(_cat_labels_raw)   if categories_have_data    else "",
#         "category_data":       json.dumps(_cat_data_raw)     if categories_have_data    else "",
#         "member_day_labels":   json.dumps(_day_labels_raw)   if members_chart_have_data else "",
#         "member_day_data":     json.dumps(_day_data_raw)     if members_chart_have_data else "",
#         "department_labels":   json.dumps(_dept_labels_raw),
#         "department_data":     json.dumps(_dept_data_raw),
#         "recent_activities":   recent_activities,
#         "recent_members":      recent_members,
#         "library_logo_b64":    library_logo_b64,
#         "notification_count":  notification_count,
#     })


# ==========================================================
# ⚙️ SETTINGS PAGE
# ==========================================================
@login_required
def settings_view(request):
    try:
        library = Library.objects.get(user=request.user)
    except Library.DoesNotExist:
        messages.error(request, "No library found for your account.")
        return redirect("/authentication/admin_dashboard/")

    rules,         _ = LibraryRuleSettings.objects.get_or_create(library=library)
    member_cfg,    _ = MemberSettings.objects.get_or_create(library=library)
    security,      _ = SecuritySettings.objects.get_or_create(library=library)
    notifications, _ = NotificationSettings.objects.get_or_create(library=library)
    appearance,    _ = AppearanceSettings.objects.get_or_create(library=library)

    # ── Subscription (from subscriptions app) ────────────────────────────
    Subscription, Plan = _get_subscription_models()
    subscription = None
    try:
        subscription = library.subscription_detail
    except Exception:
        pass

    if request.method == "POST":
        section = request.POST.get("form_type", "").strip()

        # ── Profile ───────────────────────────────────────────────
        if section == "profile":
            user            = request.user
            user.first_name = request.POST.get("first_name", user.first_name).strip()
            user.last_name  = request.POST.get("last_name",  user.last_name).strip()
            user.email      = request.POST.get("email",      user.email).strip()
            user.save()

            library.library_name   = request.POST.get("library_name",   library.library_name).strip()
            library.institute_name = request.POST.get("institute_name", library.institute_name).strip()
            library.phone_number   = request.POST.get("phone_number",   library.phone_number or "").strip()
            library.address        = request.POST.get("address",        library.address).strip()

            _plan = subscription.plan if subscription else None
            _can_brand = _plan is None or _plan.allow_custom_branding
            if "library_logo" in request.FILES:
                if _can_brand:
                    logo_file                 = request.FILES["library_logo"]
                    library.library_logo      = logo_file.read()
                    library.library_logo_mime = logo_file.content_type
                else:
                    messages.warning(request, "Custom logo upload is not available on your current plan. Upgrade to unlock branding features.")
            elif request.POST.get("remove_logo") == "1":
                if _can_brand:
                    library.library_logo = library.library_logo_mime = None
                else:
                    messages.warning(request, "Custom branding changes are not available on your current plan.")
            library.save()
            messages.success(request, "Profile updated successfully.")

        # ── Security ──────────────────────────────────────────────
        elif section == "security":
            user       = request.user
            current_pw = request.POST.get("current_password", "")
            new_pw     = request.POST.get("new_password", "")
            confirm_pw = request.POST.get("confirm_password", "")

            if current_pw and new_pw and confirm_pw:
                if not user.check_password(current_pw):
                    messages.error(request, "Current password is incorrect.")
                elif new_pw != confirm_pw:
                    messages.error(request, "New passwords do not match.")
                elif len(new_pw) < 8:
                    messages.error(request, "Password must be at least 8 characters.")
                else:
                    user.set_password(new_pw)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password updated successfully.")
            else:
                messages.warning(request, "Please fill in all password fields.")

            security.two_factor_auth             = request.POST.get("two_factor_auth")             == "on"
            security.lock_after_failed_attempts  = request.POST.get("lock_after_failed_attempts")  == "on"
            security.force_password_reset        = request.POST.get("force_password_reset")        == "on"
            security.login_email_notification    = request.POST.get("login_email_notification")    == "on"
            security.allow_multiple_device_login = request.POST.get("allow_multiple_device_login") == "on"
            security.failed_login_attempts_limit = _int(
                request.POST.get("failed_login_attempts_limit"),
                security.failed_login_attempts_limit,
            )
            security.save()

        # ── System ────────────────────────────────────────────────
        elif section == "system":
            library.institute_email = request.POST.get("institute_email", library.institute_email).strip()
            library.phone_number    = request.POST.get("phone_number",    library.phone_number or "").strip()
            library.address         = request.POST.get("address",         library.address).strip()
            library.district        = request.POST.get("district",        library.district).strip()
            library.state           = request.POST.get("state",           library.state).strip()
            library.country         = request.POST.get("country",         library.country).strip()
            library.save()
            _plan = subscription.plan if subscription else None
            if _plan is None or _plan.allow_custom_branding:
                appearance.primary_color = request.POST.get("primary_color", appearance.primary_color).strip()
            appearance.save()
            messages.success(request, "System settings updated successfully.")

        # ── Notifications ─────────────────────────────────────────
        elif section == "notifications":
            _plan = subscription.plan if subscription else None
            # Only save email_overdue_reminder if the plan allows it
            if _plan is None or _plan.allow_email_reminders:
                notifications.email_overdue_reminder = request.POST.get("email_overdue_reminder") == "on"
            elif request.POST.get("email_overdue_reminder") == "on":
                messages.warning(request, "Email reminders are not included in your current plan. Upgrade to enable this feature.")
            # Only save sms_reminder if the plan allows it
            if _plan is None or _plan.allow_sms:
                notifications.sms_reminder = request.POST.get("sms_reminder") == "on"
            elif request.POST.get("sms_reminder") == "on":
                messages.warning(request, "SMS reminders are not included in your current plan. Upgrade to enable this feature.")
            notifications.monthly_usage_report   = request.POST.get("monthly_usage_report")   == "on"
            notifications.weekly_database_backup = request.POST.get("weekly_database_backup") == "on"
            notifications.daily_activity_summary = request.POST.get("daily_activity_summary") == "on"
            notifications.save()
            messages.success(request, "Notification preferences saved.")

        # ── Fine & Loans ──────────────────────────────────────────
        elif section == "fine":
            rules.max_books_per_member  = _int(request.POST.get("max_books_per_member"),  rules.max_books_per_member)
            rules.borrowing_period      = _int(request.POST.get("loan_period_days"),      rules.borrowing_period)
            rules.max_renewal_count     = _int(request.POST.get("renewal_limit"),         rules.max_renewal_count)
            rules.grace_period          = _int(request.POST.get("grace_period_days"),     rules.grace_period)
            rules.late_fine             = _dec(request.POST.get("fine_per_day"),          rules.late_fine)
            rules.auto_fine             = request.POST.get("auto_fine")             == "on"
            rules.allow_renewal         = request.POST.get("allow_renewal")         == "on"
            rules.allow_partial_payment = request.POST.get("allow_partial_payment") == "on"
            rules.auto_mark_lost        = request.POST.get("auto_mark_lost")        == "on"
            # Gate advance booking on the plan feature flag
            _plan = subscription.plan if subscription else None
            if _plan is None or _plan.allow_advance_booking:
                rules.allow_advance_booking = request.POST.get("allow_advance_booking") == "on"
            elif request.POST.get("allow_advance_booking") == "on":
                messages.warning(request, "Advance booking is not included in your current plan. Upgrade to enable this feature.")
            rules.save()
            messages.success(request, "Loan & fine settings saved.")

        # ── Members ───────────────────────────────────────────────
        elif section == "members":
            if library.institute_type == "Institution":
                member_cfg.student_borrow_limit      = _int(request.POST.get("student_borrow_limit"),     member_cfg.student_borrow_limit)
                member_cfg.teacher_borrow_limit      = _int(request.POST.get("teacher_borrow_limit"),     member_cfg.teacher_borrow_limit)
            else:
                member_cfg.member_borrow_limit       = _int(request.POST.get("member_borrow_limit"),      member_cfg.member_borrow_limit)
            member_cfg.membership_validity_days  = _int(request.POST.get("membership_validity_days"), member_cfg.membership_validity_days)
            member_cfg.allow_self_registration   = request.POST.get("allow_self_registration")   == "on"
            member_cfg.require_admin_approval    = request.POST.get("require_admin_approval")    == "on"
            member_cfg.enable_member_id_download = request.POST.get("enable_member_id_download") == "on"
            member_cfg.allow_profile_edit        = request.POST.get("allow_profile_edit")        == "on"
            member_cfg.save()
            # Keep LibraryRuleSettings in sync
            rules.student_borrow_limit = member_cfg.student_borrow_limit
            rules.teacher_borrow_limit = member_cfg.teacher_borrow_limit
            rules.save()
            messages.success(request, "Member settings saved.")

        # ── Subscription ──────────────────────────────────────────
        # Librarians may only toggle active/inactive.
        # Plan, expiry, and status are superuser-only fields.
        elif section == "subscription":
            Subscription, Plan = _get_subscription_models()

            if subscription is None:
                messages.error(request, "No subscription record found for this library.")
                return redirect("/authentication/settings/")

            wants_active = request.POST.get("sub_active") == "on"

            if wants_active and not subscription.is_active:
                # Block reactivation if the plan has expired — admin must renew first
                if subscription.expiry_date < timezone.now().date():
                    messages.error(
                        request,
                        "Your subscription has expired and cannot be reactivated here. "
                        "Please renew your plan first."
                    )
                    return redirect("/authentication/settings/")
                subscription.status = Subscription.STATUS_ACTIVE
                subscription.save(update_fields=["status", "updated_at"])
                messages.success(request, "Subscription activated.")
            elif not wants_active and subscription.is_active:
                subscription.status = Subscription.STATUS_CANCELLED
                subscription.save(update_fields=["status", "updated_at"])
                messages.success(request, "Subscription deactivated. Library access is now suspended.")
            else:
                messages.info(request, "No changes made to subscription.")

        else:
            messages.warning(request, f"Unknown settings section: '{section}'.")

        return redirect("/authentication/settings/")

    # ── GET: build context ────────────────────────────────────────
    notification_list = [
        {"key": "email_overdue_reminder", "label": "Email Overdue Reminder",  "description": "Send email reminders when a loan becomes overdue.", "enabled": notifications.email_overdue_reminder},
        {"key": "sms_reminder",           "label": "SMS Reminders",            "description": "Send SMS reminders for due and overdue books.",    "enabled": notifications.sms_reminder},
        {"key": "monthly_usage_report",   "label": "Monthly Usage Report",     "description": "Receive a monthly summary report via email.",       "enabled": notifications.monthly_usage_report},
        {"key": "weekly_database_backup", "label": "Weekly Database Backup",   "description": "Get notified when weekly backup completes.",        "enabled": notifications.weekly_database_backup},
        {"key": "daily_activity_summary", "label": "Daily Activity Summary",   "description": "Receive a daily digest of library activity.",       "enabled": notifications.daily_activity_summary},
    ]

    system_settings = _Proxy({
        "org_name":       library.library_name,
        "institute_name": library.institute_name,
        "org_email":      library.institute_email,
        "org_phone":      library.phone_number or "",
        "org_address":    library.address,
        "district":       library.district,
        "state":          library.state,
        "country":        library.country,
        "primary_color":  appearance.primary_color,
    })

    loan_settings = _Proxy({
        "max_books_per_member":  rules.max_books_per_member,
        "loan_period_days":      rules.borrowing_period,
        "renewal_limit":         rules.max_renewal_count,
        "grace_period_days":     rules.grace_period,
        "fine_per_day":          rules.late_fine,
        "max_fine":              0,
        "waiver_percentage":     0,
        "auto_fine":             rules.auto_fine,
        "allow_renewal":         rules.allow_renewal,
        "allow_partial_payment": rules.allow_partial_payment,
        "auto_mark_lost":        rules.auto_mark_lost,
        "allow_advance_booking": rules.allow_advance_booking,
    })

    library_logo_b64 = None
    if library.library_logo:
        mime    = library.library_logo_mime or "image/png"
        encoded = base64.b64encode(bytes(library.library_logo)).decode("utf-8")
        library_logo_b64 = f"data:{mime};base64,{encoded}"

    # ── Plan feature flags for template gating ───────────────────────────
    plan = subscription.plan if subscription else None

    return render(request, "accounts/settings.html", {
        "library":               library,
        "rules":                 rules,
        "member_cfg":            member_cfg,
        "security":              security,
        "notifications":         notifications,
        "appearance":            appearance,
        "subscription":          subscription,
        "plan":                  plan,
        "today_date":            timezone.now().date(),
        "system_settings":       system_settings,
        "loan_settings":         loan_settings,
        "notification_settings": notification_list,
        "library_logo_b64":      library_logo_b64,
        "active_sessions":       [],
    })


# ==========================================================
# HELPERS
# ==========================================================

def _get_library_or_404(request):
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


def _first_of_month(ref_date, months_back=0):
    m, y = ref_date.month - months_back, ref_date.year
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def _first_of_next_month(d):
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _dec(value, fallback=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class _Proxy:
    """Dict → dot-accessible object for template context."""
    def __init__(self, data: dict):
        for k, v in data.items():
            setattr(self, k, v)