import base64
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import models as db_models
from django.db.models import (
    Case, Count, DecimalField, ExpressionWrapper,
    F, Sum, Value, When,
)
from django.db.models.functions import Greatest
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.timesince import timesince


# ==========================================================
# 🏠 ADMIN DASHBOARD
# ==========================================================
@login_required
def admin_dashboard(request):
    from accounts.models import Library, LibraryRuleSettings
    from books.models import Book, BookCopy, Category
    from members.models import Member
    from transactions.models import Transaction

    library = _get_library_or_404(request)
    print(f"DEBUG [dashboard] library={library}, user={request.user}")

    rules_qs = LibraryRuleSettings.objects.filter(library=library).first()
    print(f"DEBUG [rules] rules_qs={rules_qs}, is_setup_complete={getattr(rules_qs, 'is_setup_complete', None)}")
    if rules_qs and not getattr(rules_qs, "is_setup_complete", False):
        return redirect("accounts:library_setup")

    owner = library.user
    today            = date.today()
    this_month_start = _first_of_month(today, months_back=0)
    last_month_start = _first_of_month(today, months_back=1)
    last_month_end   = this_month_start - timedelta(days=1)
    print(f"DEBUG [dates] today={today}, this_month_start={this_month_start}, last_month_start={last_month_start}, last_month_end={last_month_end}")

    Transaction.sync_overdue_for_library(library)
    print(f"DEBUG [overdue-sync] sync_overdue_for_library called for library={library}")

    # ── Library count ─────────────────────────────────────────
    if request.user.is_superuser:
        total_libraries      = Library.objects.count()
        libraries_this_month = Library.objects.filter(
            created_at__date__gte=this_month_start
        ).count()
        libraries_last_month = Library.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end,
        ).count()
    else:
        total_libraries = 1
        libraries_this_month = libraries_last_month = 0
    libraries_change = libraries_this_month - libraries_last_month
    print(f"DEBUG [libraries] total={total_libraries}, this_month={libraries_this_month}, last_month={libraries_last_month}, change={libraries_change}")

    # ── Books ─────────────────────────────────────────────────
    total_books = (
        Book.objects.filter(owner=owner)
        .aggregate(total=Sum("available_copies"))["total"]
        or 0
    )
    books_this_month = Book.objects.filter(
        owner=owner, created_at__date__gte=this_month_start
    ).count()
    books_last_month = Book.objects.filter(
        owner=owner,
        created_at__date__gte=last_month_start,
        created_at__date__lte=last_month_end,
    ).count()
    books_change = books_this_month - books_last_month
    print(f"DEBUG [books] total={total_books}, this_month={books_this_month}, last_month={books_last_month}, change={books_change}")

    # ── Members ───────────────────────────────────────────────
    # FIX 1: date_joined is a DateTimeField — use __date__ lookup to avoid
    # naive datetime RuntimeWarning when timezone support is active.
    total_members      = Member.objects.filter(owner=owner, status="active").count()
    members_this_month = Member.objects.filter(
        owner=owner,
        date_joined__date__gte=this_month_start,
    ).count()
    members_last_month = Member.objects.filter(
        owner=owner,
        date_joined__date__gte=last_month_start,
        date_joined__date__lte=last_month_end,
    ).count()
    members_change = members_this_month - members_last_month
    print(f"DEBUG [members] total_active={total_members}, this_month={members_this_month}, last_month={members_last_month}, change={members_change}")

    # ── Transactions ──────────────────────────────────────────
    base_txns = Transaction.objects.for_library(library)
    print(f"DEBUG [transactions] base_txns total count={base_txns.count()}")

    active_transactions = base_txns.filter(
        status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE)
    ).count()

    txns_this_month = base_txns.filter(issue_date__gte=this_month_start).count()
    txns_last_month = base_txns.filter(
        issue_date__gte=last_month_start,
        issue_date__lte=last_month_end,
    ).count()
    transactions_change = txns_this_month - txns_last_month
    print(f"DEBUG [transactions] active={active_transactions}, this_month={txns_this_month}, last_month={txns_last_month}, change={transactions_change}")

    # ── Member status breakdown ───────────────────────────────
    count_map = {
        row["status"]: row["cnt"]
        for row in Member.objects.filter(owner=owner)
            .values("status")
            .annotate(cnt=Count("id"))
    }
    print(f"DEBUG [member-status] count_map={count_map}")
    active_count   = count_map.get("active",   0)
    passout_count  = count_map.get("passout",  0)
    inactive_count = count_map.get("inactive", 0)
    total_count    = active_count + passout_count + inactive_count

    def _pct(n):
        return round(n / total_count * 100, 1) if total_count else 0

    stats = {
        "active_count":        active_count,
        "passout_count":       passout_count,
        "inactive_count":      inactive_count,
        "total_count":         total_count,
        "active_percentage":   _pct(active_count),
        "passout_percentage":  _pct(passout_count),
        "inactive_percentage": _pct(inactive_count),
    }
    print(f"DEBUG [member-stats] {stats}")

    # ── Chart 1: Monthly Loans (last 6 months) ────────────────
    _loan_labels_raw, _loan_data_raw = [], []
    for i in range(5, -1, -1):
        ms  = _first_of_month(today, months_back=i)
        me  = _first_of_next_month(ms)
        cnt = base_txns.filter(issue_date__gte=ms, issue_date__lt=me).count()
        _loan_labels_raw.append(ms.strftime("%b %Y"))
        _loan_data_raw.append(cnt)
    loans_have_data = any(v > 0 for v in _loan_data_raw)
    print(f"DEBUG [chart-loans] labels={_loan_labels_raw}, data={_loan_data_raw}, has_data={loans_have_data}")

    # ── Chart 2: Books by Category ────────────────────────────
    # Book.category FK declares related_name="books", so "books" is correct.
    cat_qs = (
        Category.objects
        .filter(owner=owner)
        .annotate(cnt=Count("books"))
        .filter(cnt__gt=0)
        .order_by("-cnt")[:8]
    )
    _cat_labels_raw      = [c.name for c in cat_qs]
    _cat_data_raw        = [c.cnt  for c in cat_qs]
    categories_have_data = len(_cat_labels_raw) > 0
    print(f"DEBUG [chart-categories] labels={_cat_labels_raw}, data={_cat_data_raw}, has_data={categories_have_data}")

    # ── Chart 3: New Members per day (last 7 days) ────────────
    # FIX 2: use __date__ lookup so DateTimeField comparison uses date only,
    # avoiding naive datetime warnings. Key is also date_joined__date now.
    day_count_map = {
        row["date_joined__date"]: row["cnt"]
        for row in Member.objects.filter(
            owner=owner,
            date_joined__date__gte=today - timedelta(days=6),
            date_joined__date__lte=today,
        ).values("date_joined__date").annotate(cnt=Count("id"))
    }
    _day_labels_raw, _day_data_raw = [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        _day_labels_raw.append(d.strftime("%a"))
        _day_data_raw.append(day_count_map.get(d, 0))
    members_chart_have_data = any(v > 0 for v in _day_data_raw)
    print(f"DEBUG [chart-members-daily] labels={_day_labels_raw}, data={_day_data_raw}, has_data={members_chart_have_data}")

    # ── Chart 4: Members by Department ───────────────────────
    dept_qs = (
        Member.objects
        .filter(owner=owner)
        .values("department__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )
    _dept_labels_raw = [row["department__name"] or "No Department" for row in dept_qs]
    _dept_data_raw   = [row["cnt"] for row in dept_qs]
    dept_have_data   = len(_dept_labels_raw) > 0
    print(f"DEBUG [chart-departments] labels={_dept_labels_raw}, data={_dept_data_raw}, has_data={dept_have_data}")

    # ── Chart 5: Member Status (pie) ──────────────────────────
    status_have_data = total_count > 0
    print(f"DEBUG [chart-status] total_count={total_count}, has_data={status_have_data}")

    # ── Overdue & Fines ───────────────────────────────────────
    overdue_qs = (
        base_txns
        .filter(status=Transaction.STATUS_OVERDUE)
        .select_related("member", "book")
        .order_by("due_date")
    )
    overdue_count   = overdue_qs.count()
    due_today_count = base_txns.filter(
        due_date=today,
        status=Transaction.STATUS_ISSUED,
    ).count()
    print(f"DEBUG [overdue] overdue_count={overdue_count}, due_today_count={due_today_count}")

    # FIX 3: Replaced ORM date-arithmetic expression (_fine_expr) with
    # the model's own fine_amount @property — the single source of truth
    # used everywhere else in the app.  The ORM approach cast timedelta to
    # IntegerField which returns microseconds on some backends, giving
    # crore-level totals.
    total_fines_pending = Decimal("0.00")
    for txn in base_txns.filter(status=Transaction.STATUS_OVERDUE, fine_paid=False):
        total_fines_pending += Decimal(str(txn.fine_amount or 0))
    total_fines_pending = total_fines_pending.quantize(Decimal("0.01"))

    total_fines_collected = Decimal("0.00")
    for txn in base_txns.filter(fine_paid=True):
        total_fines_collected += Decimal(str(txn.fine_amount or 0))
    total_fines_collected = total_fines_collected.quantize(Decimal("0.01"))

    # FIX 4: fine_amount is a read-only @property — assigning to it raises
    # AttributeError.  Use display_fine instead for the template column.
    # days_overdue computed directly from date fields via timedelta.days.
    overdue_transactions = []
    for txn in overdue_qs[:10]:
        txn.days_overdue = max(0, (today - txn.due_date).days)
        txn.display_fine = Decimal(str(txn.fine_amount or 0)).quantize(Decimal("0.01"))
        overdue_transactions.append(txn)

    print(f"DEBUG [fines] collected={total_fines_collected}, pending={total_fines_pending}")

    # ── Recent Activity Feed ──────────────────────────────────
    recent_activities = []
    for txn in base_txns.select_related("member", "book").order_by("-created_at")[:5]:
        if txn.status == Transaction.STATUS_RETURNED:
            icon, color, title = "undo-alt",             "green",  f"Book returned: {txn.book.title}"
        elif txn.status == Transaction.STATUS_OVERDUE:
            icon, color, title = "exclamation-triangle", "red",    f"Overdue: {txn.book.title}"
        elif txn.status == Transaction.STATUS_LOST:
            icon, color, title = "times-circle",         "red",    f"Lost book: {txn.book.title}"
        else:
            icon, color, title = "book",                 "blue",   f"Book issued: {txn.book.title}"
        recent_activities.append({
            "title":       title,
            "description": f"{txn.member.first_name} {txn.member.last_name}",
            "icon":        icon,
            "color":       color,
            "timestamp":   timesince(txn.created_at) + " ago",
        })

    for m in Member.objects.filter(owner=owner).order_by("-date_joined", "-id")[:3]:
        joined_dt  = datetime.combine(m.date_joined, datetime.min.time())
        role_label = m.get_role_display() if hasattr(m, "get_role_display") else ""
        recent_activities.append({
            "title":       f"New member: {m.first_name} {m.last_name}",
            "description": f"ID: {m.member_id}  {role_label}".strip(),
            "icon":        "user-plus",
            "color":       "purple",
            "timestamp":   timesince(joined_dt) + " ago",
        })
    recent_activities = recent_activities[:8]
    print(f"DEBUG [activity] recent_activities count={len(recent_activities)}")

    recent_members = (
        Member.objects
        .filter(owner=owner)
        .select_related("department")
        .order_by("-date_joined", "-id")[:5]
    )
    print(f"DEBUG [recent-members] count={recent_members.count()}")

    # ── Library logo ──────────────────────────────────────────
    library_logo_b64 = ""
    if library.library_logo and library.library_logo_mime:
        raw_data = library.library_logo
        if isinstance(raw_data, memoryview):
            raw_data = raw_data.tobytes()
        elif not isinstance(raw_data, bytes):
            raw_data = bytes(raw_data)
        raw = base64.b64encode(raw_data).decode("ascii")
        library_logo_b64 = f"data:{library.library_logo_mime};base64,{raw}"
    print(f"DEBUG [logo] has_logo={bool(library_logo_b64)}, mime={getattr(library, 'library_logo_mime', None)}")

    notification_count = overdue_count
    print(f"DEBUG [notifications] notification_count={notification_count}")
    print("DEBUG [dashboard] render complete — passing context to template")
    context = {
        # ── Section 1: Library Overview ──────────────────────
        "total_libraries":       total_libraries,
        "libraries_change":      libraries_change,
        "total_books":           total_books,
        "books_change":          books_change,
        "total_members":         total_members,
        "members_change":        members_change,
        "active_transactions":   active_transactions,
        "transactions_change":   transactions_change,

        # ── Section 2: Membership Stats ──────────────────────
        "stats":                 stats,

        # ── Section 4: Charts ────────────────────────────────
        "monthly_loan_labels":   json.dumps(_loan_labels_raw) if loans_have_data         else "",
        "monthly_loan_data":     json.dumps(_loan_data_raw)   if loans_have_data         else "",
        "category_labels":       json.dumps(_cat_labels_raw)  if categories_have_data    else "",
        "category_data":         json.dumps(_cat_data_raw)    if categories_have_data    else "",
        "member_day_labels":     json.dumps(_day_labels_raw)  if members_chart_have_data else "",
        "member_day_data":       json.dumps(_day_data_raw)    if members_chart_have_data else "",
        "department_labels":     json.dumps(_dept_labels_raw) if dept_have_data else "[]",
        "department_data":       json.dumps(_dept_data_raw)   if dept_have_data else "[]",
        "status_have_data":      status_have_data,

        # ── Section 5: Overdue & Fines ───────────────────────
        "overdue_count":         overdue_count,
        "overdue_transactions":  overdue_transactions,
        "total_fines_pending":   total_fines_pending,
        "total_fines_collected": total_fines_collected,
        "due_today_count":       due_today_count,

        # ── Section 6: Recent Activity & Members ─────────────
        "recent_activities":     recent_activities,
        "recent_members":        recent_members,

        # ── UI ───────────────────────────────────────────────
        "library_logo_b64":      library_logo_b64,
        "notification_count":    notification_count,
    }
    return render(request, "dashboards/admin_dashboard.html", context)


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