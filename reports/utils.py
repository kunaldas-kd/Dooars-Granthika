"""
reports/utils.py

Shared data-fetching / aggregation helpers consumed by views and CSV export.
All functions are tenant-scoped: they receive a Library instance and never
touch another tenant's data.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import (
    Avg, Count, DecimalField, F, FloatField, Q, Sum,
    ExpressionWrapper,
)
from django.db.models.functions import TruncMonth, TruncWeek


# ─────────────────────────────────────────────────────────────────────────────
# Date range helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_date(value, fallback):
    """Convert a string 'YYYY-MM-DD' to a date; return *fallback* on failure."""
    if value:
        try:
            from datetime import datetime
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    return fallback


def resolve_date_range(request_GET, default_days=30):
    """
    Return (date_from, date_to) from GET params or last *default_days* days.
    """
    today    = date.today()
    date_to  = _parse_date(request_GET.get("date_to"),  today)
    date_from = _parse_date(request_GET.get("date_from"), today - timedelta(days=default_days))
    return date_from, date_to


# ─────────────────────────────────────────────────────────────────────────────
# Overview / Dashboard report
# ─────────────────────────────────────────────────────────────────────────────

def get_overview_stats(library):
    """
    High-level KPIs displayed on the reports landing page.
    Returns a plain dict — safe to pass directly into a template context.
    """
    from finance.models import Fine
    from transactions.models import Transaction
    from books.models import Book
    from members.models import Member

    owner = library.user

    txn_qs  = Transaction.objects.for_library(library)
    fine_qs = Fine.objects.for_library(library)

    total_books     = Book.objects.filter(owner=owner).count()
    total_members   = Member.objects.filter(owner=owner).count()
    active_members  = Member.objects.filter(owner=owner, status="active").count()

    total_issued    = txn_qs.filter(status=Transaction.STATUS_ISSUED).count()
    total_overdue   = txn_qs.filter(status=Transaction.STATUS_OVERDUE).count()
    total_returned  = txn_qs.filter(status=Transaction.STATUS_RETURNED).count()
    total_lost      = txn_qs.filter(status=Transaction.STATUS_LOST).count()
    total_txns      = txn_qs.count()

    fines_collected = (
        fine_qs
        .filter(status=Fine.STATUS_PAID)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    )
    fines_pending   = (
        fine_qs
        .filter(status=Fine.STATUS_UNPAID)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    )

    return {
        "total_books":     total_books,
        "total_members":   total_members,
        "active_members":  active_members,
        "total_issued":    total_issued,
        "total_overdue":   total_overdue,
        "total_returned":  total_returned,
        "total_lost":      total_lost,
        "total_txns":      total_txns,
        "fines_collected": fines_collected,
        "fines_pending":   fines_pending,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Transactions report
# ─────────────────────────────────────────────────────────────────────────────

def get_transaction_report(library, date_from, date_to, status=None):
    """
    Returns a filtered, annotated queryset of transactions within the date range.
    """
    from transactions.models import Transaction

    qs = (
        Transaction.objects.for_library(library)
        .select_related("member", "book")
        .filter(issue_date__gte=date_from, issue_date__lte=date_to)
    )
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-issue_date")


def get_monthly_issue_trend(library, months=12):
    """
    Returns list of {month: date, issued: int} for the last *months* months.
    Suitable for rendering a line chart.
    """
    from transactions.models import Transaction

    since = date.today().replace(day=1) - timedelta(days=30 * (months - 1))
    rows  = (
        Transaction.objects.for_library(library)
        .filter(issue_date__gte=since)
        .annotate(month=TruncMonth("issue_date"))
        .values("month")
        .annotate(issued=Count("id"))
        .order_by("month")
    )
    return list(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Books report
# ─────────────────────────────────────────────────────────────────────────────

def get_book_report(library, date_from, date_to, category_id=None):
    """
    Books with their issue counts over the period, sorted by popularity.
    Returns a list of dicts: {book, issue_count, available_copies, ...}
    """
    from transactions.models import Transaction
    from books.models import Book

    owner = library.user

    # Count issues per book within the date range
    txn_counts = (
        Transaction.objects.for_library(library)
        .filter(issue_date__gte=date_from, issue_date__lte=date_to)
        .values("book_id")
        .annotate(issue_count=Count("id"))
    )
    count_map = {row["book_id"]: row["issue_count"] for row in txn_counts}

    qs = Book.objects.filter(owner=owner).select_related("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    result = []
    for book in qs.order_by("title"):
        result.append({
            "book":             book,
            "issue_count":      count_map.get(book.pk, 0),
            "available_copies": book.available_copies,
            "total_copies":     book.total_copies,
            "stock_status":     book.stock_status,
        })
    result.sort(key=lambda r: r["issue_count"], reverse=True)
    return result


def get_most_popular_books(library, limit=10):
    """Top *limit* books by total issues across all time."""
    from transactions.models import Transaction
    from books.models import Book

    owner = library.user

    rows = (
        Transaction.objects.for_library(library)
        .values("book_id", "book__title", "book__author")
        .annotate(issue_count=Count("id"))
        .order_by("-issue_count")[:limit]
    )
    return list(rows)


def get_least_borrowed_books(library, limit=10):
    """Books that have NEVER been borrowed or borrowed the fewest times."""
    from transactions.models import Transaction
    from books.models import Book

    owner = library.user

    issued_ids = set(
        Transaction.objects.for_library(library).values_list("book_id", flat=True)
    )
    never = list(
        Book.objects.filter(owner=owner)
        .exclude(pk__in=issued_ids)
        .select_related("category")
        .order_by("title")[:limit]
    )
    return never


# ─────────────────────────────────────────────────────────────────────────────
# Members report
# ─────────────────────────────────────────────────────────────────────────────

def get_member_report(library, date_from, date_to, role=None, status=None):
    """
    Members with loan and fine summaries. Returns list of dicts.
    """
    from finance.models import Fine
    from transactions.models import Transaction
    from members.models import Member

    owner = library.user

    qs = Member.objects.filter(owner=owner).select_related("department", "course", "year", "semester")
    if role:
        qs = qs.filter(role=role)
    if status:
        qs = qs.filter(status=status)

    # Bulk-fetch loan counts for the date range in one query
    loan_counts = {
        row["member_id"]: row["cnt"]
        for row in Transaction.objects.for_library(library)
        .filter(issue_date__gte=date_from, issue_date__lte=date_to)
        .values("member_id")
        .annotate(cnt=Count("id"))
    }

    # Bulk-fetch unpaid fine totals
    fine_totals = {
        row["transaction__member_id"]: row["total"]
        for row in Fine.objects.for_library(library)
        .filter(status=Fine.STATUS_UNPAID)
        .values("transaction__member_id")
        .annotate(total=Sum("amount", output_field=DecimalField()))
    }

    # Current active loans count (no date restriction)
    active_counts = {
        row["member_id"]: row["cnt"]
        for row in Transaction.objects.for_library(library)
        .filter(status__in=(Transaction.STATUS_ISSUED, Transaction.STATUS_OVERDUE))
        .values("member_id")
        .annotate(cnt=Count("id"))
    }

    result = []
    for m in qs.order_by("first_name", "last_name"):
        result.append({
            "member":         m,
            "loans_in_range": loan_counts.get(m.pk, 0),
            "active_loans":   active_counts.get(m.pk, 0),
            "unpaid_fines":   fine_totals.get(m.pk, Decimal("0.00")),
        })
    return result


def get_top_borrowers(library, limit=10):
    """Members with the most total transactions."""
    from transactions.models import Transaction

    rows = (
        Transaction.objects.for_library(library)
        .values("member_id", "member__first_name", "member__last_name", "member__member_id")
        .annotate(loan_count=Count("id"))
        .order_by("-loan_count")[:limit]
    )
    return list(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Fines report
# ─────────────────────────────────────────────────────────────────────────────

def get_fine_report(library, date_from, date_to, fine_status=None):
    """
    Fines created within the date range.  Returns an annotated queryset.
    """
    from finance.models import Fine

    qs = (
        Fine.objects.for_library(library)
        .select_related("transaction__member", "transaction__book")
        .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    )
    if fine_status:
        qs = qs.filter(status=fine_status)
    return qs.order_by("-created_at")


def get_fine_summary(library, date_from, date_to):
    """
    Aggregate fine totals by status for the given period.
    """
    from finance.models import Fine

    qs = Fine.objects.for_library(library).filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    agg = qs.aggregate(
        total_amount   = Sum("amount"),
        paid_amount    = Sum("amount", filter=Q(status=Fine.STATUS_PAID)),
        unpaid_amount  = Sum("amount", filter=Q(status=Fine.STATUS_UNPAID)),
        waived_amount  = Sum("amount", filter=Q(status=Fine.STATUS_WAIVED)),
        total_count    = Count("id"),
        paid_count     = Count("id", filter=Q(status=Fine.STATUS_PAID)),
        unpaid_count   = Count("id", filter=Q(status=Fine.STATUS_UNPAID)),
    )
    # Replace None with zero
    for k in agg:
        if agg[k] is None:
            agg[k] = Decimal("0.00") if "amount" in k else 0
    return agg


# ─────────────────────────────────────────────────────────────────────────────
# Overdue report
# ─────────────────────────────────────────────────────────────────────────────

def get_overdue_report(library):
    """
    All currently overdue transactions, ordered by most days overdue first.
    Returns queryset.
    """
    from transactions.models import Transaction

    return (
        Transaction.objects.for_library(library)
        .select_related("member", "book")
        .filter(status=Transaction.STATUS_OVERDUE)
        .order_by("due_date")
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inventory / Stock report
# ─────────────────────────────────────────────────────────────────────────────

def get_inventory_report(library, category_id=None):
    """
    Full inventory with stock status per book.
    """
    from books.models import Book

    qs = Book.objects.filter(owner=library.user).select_related("category")
    if category_id:
        qs = qs.filter(category_id=category_id)
    return qs.order_by("category__name", "title")


def get_stock_summary(library):
    """
    Returns {available: int, low_stock: int, out_of_stock: int} counts.
    """
    from books.models import Book

    qs     = Book.objects.filter(owner=library.user)
    total  = qs.count()
    out    = qs.filter(available_copies=0).count()
    low    = qs.filter(available_copies__gt=0, available_copies__lte=3).count()
    avail  = total - out - low
    return {"available": avail, "low_stock": low, "out_of_stock": out, "total": total}