"""
reports/views.py

All views are tenant-scoped to request.user.library.

URL namespace: "reports"

Views
─────
  overview              GET  /reports/
  transaction_report    GET  /reports/transactions/
  book_report           GET  /reports/books/
  member_report         GET  /reports/members/
  fine_report           GET  /reports/fines/
  overdue_report        GET  /reports/overdue/
  inventory_report      GET  /reports/inventory/

  export_transactions   GET  /reports/export/transactions/
  export_books          GET  /reports/export/books/
  export_members        GET  /reports/export/members/
  export_fines          GET  /reports/export/fines/
  export_overdue        GET  /reports/export/overdue/
  export_inventory      GET  /reports/export/inventory/
"""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render

from .utils import (
    get_book_report,
    get_fine_report,
    get_fine_summary,
    get_inventory_report,
    get_least_borrowed_books,
    get_member_report,
    get_monthly_issue_trend,
    get_most_popular_books,
    get_overdue_report,
    get_overview_stats,
    get_stock_summary,
    get_top_borrowers,
    get_transaction_report,
    resolve_date_range,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_or_404(request):
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


# ─────────────────────────────────────────────────────────────────────────────
# CSV helper
# ─────────────────────────────────────────────────────────────────────────────

def _csv_response(filename, headers, rows):
    """
    Build and return a StreamingHttpResponse-style CSV download.
    *rows* should be an iterable of lists/tuples parallel to *headers*.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


# ─────────────────────────────────────────────────────────────────────────────
# 1. Overview
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def overview(request):
    library = _get_library_or_404(request)

    stats  = get_overview_stats(library)
    trend  = get_monthly_issue_trend(library, months=12)
    top_10 = get_most_popular_books(library, limit=10)
    top_borrowers = get_top_borrowers(library, limit=5)

    return render(request, "reports/overview.html", {
        **stats,
        "monthly_trend":  trend,
        "popular_books":  top_10,
        "top_borrowers":  top_borrowers,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 2. Transaction Report
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def transaction_report(request):
    library = _get_library_or_404(request)

    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    status   = request.GET.get("status", "").strip()

    transactions = get_transaction_report(library, date_from, date_to, status or None)

    # Summary counts for the period
    from transactions.models import Transaction as TxnModel
    period_qs = TxnModel.objects.for_library(library).filter(
        issue_date__gte=date_from, issue_date__lte=date_to
    )
    summary = {
        "total":    period_qs.count(),
        "issued":   period_qs.filter(status=TxnModel.STATUS_ISSUED).count(),
        "returned": period_qs.filter(status=TxnModel.STATUS_RETURNED).count(),
        "overdue":  period_qs.filter(status=TxnModel.STATUS_OVERDUE).count(),
        "lost":     period_qs.filter(status=TxnModel.STATUS_LOST).count(),
    }

    from django.core.paginator import Paginator
    paginator    = Paginator(transactions, 25)
    transactions = paginator.get_page(request.GET.get("page", 1))

    return render(request, "reports/transaction_report.html", {
        "transactions": transactions,
        "summary":      summary,
        "date_from":    date_from,
        "date_to":      date_to,
        "status":       status,
        "status_choices": [
            ("",         "All"),
            ("issued",   "Issued"),
            ("returned", "Returned"),
            ("overdue",  "Overdue"),
            ("lost",     "Lost"),
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# 3. Book Report
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def book_report(request):
    library = _get_library_or_404(request)

    from books.models import Category
    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    category_id = request.GET.get("category", "").strip()

    books        = get_book_report(library, date_from, date_to, category_id or None)
    least_borrow = get_least_borrowed_books(library, limit=10)
    stock        = get_stock_summary(library)
    categories   = Category.objects.filter(owner=library.user).order_by("name")

    return render(request, "reports/book_report.html", {
        "books":        books,
        "least_borrow": least_borrow,
        "stock":        stock,
        "categories":   categories,
        "date_from":    date_from,
        "date_to":      date_to,
        "category_id":  category_id,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 4. Member Report
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_report(request):
    library = _get_library_or_404(request)

    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    role   = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    members       = get_member_report(library, date_from, date_to, role or None, status or None)
    top_borrowers = get_top_borrowers(library, limit=10)

    return render(request, "reports/member_report.html", {
        "members":      members,
        "top_borrowers": top_borrowers,
        "date_from":    date_from,
        "date_to":      date_to,
        "role":         role,
        "status":       status,
        "role_choices": [
            ("",        "All Roles"),
            ("student", "Student"),
            ("teacher", "Teacher"),
            ("general", "General"),
        ],
        "status_choices": [
            ("",        "All Statuses"),
            ("active",  "Active"),
            ("inactive","Inactive"),
            ("passout", "Passed Out"),
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fine Report
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def fine_report(request):
    library = _get_library_or_404(request)

    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    fine_status = request.GET.get("fine_status", "").strip()

    fines   = get_fine_report(library, date_from, date_to, fine_status or None)
    summary = get_fine_summary(library, date_from, date_to)

    from django.core.paginator import Paginator
    paginator = Paginator(fines, 25)
    fines     = paginator.get_page(request.GET.get("page", 1))

    return render(request, "reports/fine_report.html", {
        "fines":       fines,
        "summary":     summary,
        "date_from":   date_from,
        "date_to":     date_to,
        "fine_status": fine_status,
        "status_choices": [
            ("",       "All"),
            ("unpaid", "Unpaid"),
            ("paid",   "Paid"),
            ("waived", "Waived"),
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# 6. Overdue Report
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def overdue_report(request):
    library  = _get_library_or_404(request)

    from transactions.models import Transaction
    Transaction.sync_overdue_for_library(library)

    overdues = get_overdue_report(library)

    total_fine = sum(
        (t.fine_amount for t in overdues),
        Decimal("0.00"),
    )

    return render(request, "reports/overdue_report.html", {
        "overdues":   overdues,
        "total_fine": total_fine,
        "today":      date.today(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# 7. Inventory Report
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def inventory_report(request):
    library = _get_library_or_404(request)

    from books.models import Category
    category_id = request.GET.get("category", "").strip()

    books      = get_inventory_report(library, category_id or None)
    stock      = get_stock_summary(library)
    categories = Category.objects.filter(owner=library.user).order_by("name")

    return render(request, "reports/inventory_report.html", {
        "books":       books,
        "stock":       stock,
        "categories":  categories,
        "category_id": category_id,
    })


# ─────────────────────────────────────────────────────────────────────────────
# CSV Export Views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def export_transactions(request):
    library = _get_library_or_404(request)
    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    status   = request.GET.get("status", "").strip()

    qs = get_transaction_report(library, date_from, date_to, status or None)

    headers = [
        "Txn ID", "Member ID", "Member Name", "Book Title", "Author",
        "ISBN", "Issue Date", "Due Date", "Return Date",
        "Status", "Fine Amount (₹)", "Fine Paid",
    ]

    def rows():
        for t in qs:
            yield [
                t.transaction_id,
                t.member.member_id,
                f"{t.member.first_name} {t.member.last_name}",
                t.book.title,
                t.book.author,
                t.book.isbn,
                t.issue_date,
                t.due_date,
                t.return_date or "",
                t.get_status_display(),
                t.fine_amount,
                "Yes" if t.fine_paid else "No",
            ]

    filename = f"transactions_{date_from}_{date_to}.csv"
    return _csv_response(filename, headers, rows())


@login_required
def export_books(request):
    library = _get_library_or_404(request)
    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    category_id = request.GET.get("category", "").strip()

    books = get_book_report(library, date_from, date_to, category_id or None)

    headers = [
        "Book ID", "Title", "Author", "ISBN", "Category",
        "Publisher", "Year", "Language", "Edition",
        "Total Copies", "Available Copies", "Issued Copies",
        "Stock Status", "Issues in Period", "Shelf Location",
    ]

    def rows():
        for r in books:
            b = r["book"]
            yield [
                b.book_id,
                b.title,
                b.author,
                b.isbn,
                b.category.name if b.category else "",
                b.publisher,
                b.publication_year or "",
                b.language,
                b.edition,
                b.total_copies,
                b.available_copies,
                b.issued_copies,
                r["stock_status"],
                r["issue_count"],
                b.shelf_location,
            ]

    filename = f"books_{date_from}_{date_to}.csv"
    return _csv_response(filename, headers, rows())


@login_required
def export_members(request):
    library = _get_library_or_404(request)
    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    role   = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    members = get_member_report(library, date_from, date_to, role or None, status or None)

    headers = [
        "Member ID", "First Name", "Last Name", "Role", "Email", "Phone",
        "Department", "Course", "Status", "Date Joined",
        "Loans in Period", "Active Loans", "Unpaid Fines (₹)",
    ]

    def rows():
        for r in members:
            m = r["member"]
            yield [
                m.member_id,
                m.first_name,
                m.last_name,
                m.get_role_display(),
                m.email,
                m.phone,
                m.department.name if m.department else "",
                m.course.name if m.course else "",
                m.get_status_display(),
                m.date_joined,
                r["loans_in_range"],
                r["active_loans"],
                r["unpaid_fines"],
            ]

    filename = f"members_{date_from}_{date_to}.csv"
    return _csv_response(filename, headers, rows())


@login_required
def export_fines(request):
    library = _get_library_or_404(request)
    date_from, date_to = resolve_date_range(request.GET, default_days=30)
    fine_status = request.GET.get("fine_status", "").strip()

    qs = get_fine_report(library, date_from, date_to, fine_status or None)

    headers = [
        "Fine ID", "Txn ID", "Member ID", "Member Name",
        "Book Title", "Fine Type", "Amount (₹)", "Status",
        "Paid Date", "Payment Method", "Created",
    ]

    def rows():
        for f in qs:
            m = f.transaction.member if f.transaction else None
            yield [
                f.fine_id,
                f.transaction_id_snapshot,
                m.member_id if m else f.member_id_snapshot,
                f"{m.first_name} {m.last_name}" if m else f.member_name,
                f.transaction.book.title if f.transaction else f.book_title,
                f.get_fine_type_display(),
                f.amount,
                f.get_status_display(),
                f.paid_date or "",
                f.get_payment_method_display() if f.payment_method else "",
                f.created_at.date(),
            ]

    filename = f"fines_{date_from}_{date_to}.csv"
    return _csv_response(filename, headers, rows())


@login_required
def export_overdue(request):
    library = _get_library_or_404(request)

    from transactions.models import Transaction
    Transaction.sync_overdue_for_library(library)

    qs = get_overdue_report(library)

    headers = [
        "Txn ID", "Member ID", "Member Name", "Book Title", "Author",
        "Issue Date", "Due Date", "Overdue Days", "Fine (₹)", "Fine Paid",
    ]

    def rows():
        for t in qs:
            yield [
                t.transaction_id,
                t.member.member_id,
                f"{t.member.first_name} {t.member.last_name}",
                t.book.title,
                t.book.author,
                t.issue_date,
                t.due_date,
                t.overdue_days,
                t.fine_amount,
                "Yes" if t.fine_paid else "No",
            ]

    return _csv_response("overdue_books.csv", headers, rows())


@login_required
def export_inventory(request):
    library = _get_library_or_404(request)
    category_id = request.GET.get("category", "").strip()

    qs = get_inventory_report(library, category_id or None)

    headers = [
        "Book ID", "Title", "Author", "ISBN", "Category",
        "Publisher", "Year", "Language", "Edition",
        "Total Copies", "Available Copies", "Issued Copies",
        "Stock Status", "Shelf Location",
    ]

    def rows():
        for b in qs:
            yield [
                b.book_id,
                b.title,
                b.author,
                b.isbn,
                b.category.name if b.category else "",
                b.publisher,
                b.publication_year or "",
                b.language,
                b.edition,
                b.total_copies,
                b.available_copies,
                b.issued_copies,
                b.stock_status,
                b.shelf_location,
            ]

    return _csv_response("inventory.csv", headers, rows())