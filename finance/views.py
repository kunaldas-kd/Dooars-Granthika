# finance/views.py
# ─────────────────────────────────────────────────────────────────────────────
# All views for the finance app.
#
# Naming conventions
# ──────────────────
#   _get_library_or_404(request) — scoped helper; raises Http404 if no library
#   _month_range(n)              — returns (year, month) tuples for chart data
#
# Every view is @login_required and tenant-scoped to request.user.library.
# ─────────────────────────────────────────────────────────────────────────────

import csv
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Expense, Fine, Payment, generate_receipt_number


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_library_or_404(request):
    """Return the Library linked to the logged-in user, or raise Http404."""
    try:
        return request.user.library
    except Exception:
        raise Http404("No library associated with this account.")


def _month_range(n: int = 12):
    """
    Return a list of (year, month) tuples for the last *n* calendar months,
    ordered oldest first.
    """
    today = date.today()
    months = []
    for i in range(n - 1, -1, -1):
        d = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        months.append((d.year, d.month))
    return months


# ─────────────────────────────────────────────────────────────────────────────
# Library Logo  (binary-serving)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def library_logo(request):
    """
    Serve the library logo stored as a BinaryField / LONGBLOB in the Library
    model (accounts app).  Scoped to the authenticated user — no PK needed.
    """
    library = _get_library_or_404(request)

    # Support both `logo` (accounts model) and `library_logo` field names
    raw = getattr(library, "library_logo", None) or getattr(library, "logo", None)
    if raw is None:
        return HttpResponse(status=404)

    logo_bytes = bytes(raw)
    if not logo_bytes:
        return HttpResponse(status=404)

    mime_type = (
        getattr(library, "library_logo_mime", None)
        or getattr(library, "logo_mime_type", None)
        or "image/jpeg"
    ).strip() or "image/jpeg"

    response = HttpResponse(logo_bytes, content_type=mime_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Process Payment  — shows fine details and the cash / online payment form
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def process_payment(request):
    """
    GET ?fine_id=<id>   — pre-load a specific fine.
    GET ?member_id=<pk> — pre-load all unpaid fines for a member.
    GET (no params)     — show the member selector.
    """
    library = _get_library_or_404(request)

    fine_id   = request.GET.get("fine_id") or request.POST.get("fine_id")
    member_id = request.GET.get("member_id") or request.POST.get("member_id")

    fine             = None
    member           = None
    all_unpaid_fines = []
    total_fine       = Decimal("0.00")

    # ── Fine lookup ───────────────────────────────────────────────────────────
    if fine_id:
        try:
            fine = (
                Fine.objects
                .for_library(library)
                .select_related("transaction__member", "transaction__book")
                .get(fine_id=fine_id)
            )
            member = fine.transaction.member if fine.transaction else None
        except Fine.DoesNotExist:
            pass  # fine_id from a different library — silently ignore

    # ── Member lookup (fallback) ──────────────────────────────────────────────
    elif member_id:
        from members.models import Member
        try:
            member = Member.objects.get(pk=member_id, owner=library.user)
        except Member.DoesNotExist:
            pass

    # ── Collect all unpaid fines for the resolved member ─────────────────────
    if member:
        all_unpaid_fines = (
            Fine.objects
            .for_library(library)
            .filter(transaction__member=member, status=Fine.STATUS_UNPAID)
            .select_related("transaction__book")
            .order_by("-created_at")
        )
        total_fine = (
            all_unpaid_fines.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        )
        if fine is None and all_unpaid_fines.exists():
            fine = all_unpaid_fines.first()

    # ── Members who have at least one unpaid fine (for the dropdown) ──────────
    from members.models import Member
    members_with_fines = (
        Member.objects
        .filter(
            owner=library.user,
            issue_transactions__library=library,
            issue_transactions__fines__status=Fine.STATUS_UNPAID,
        )
        .distinct()
        .order_by("first_name", "last_name")
    )

    # ── Check whether the member has a stored photo ───────────────────────────
    member_has_photo = False
    if member:
        raw_photo = getattr(member, "photo", None)
        if raw_photo is not None:
            try:
                member_has_photo = len(bytes(raw_photo)) > 0
            except Exception:
                member_has_photo = False

    return render(request, "finance/process_payment.html", {
        "fine":                   fine,
        "member":                 member,
        "member_has_photo":       member_has_photo,
        "all_unpaid_fines":       all_unpaid_fines,
        "total_fine":             total_fine,
        "fine_id":                fine.fine_id if fine else "",
        "member_id":              member.pk if member else "",
        "members_with_fines":     members_with_fines,
        "payment_method_choices": Fine.PAYMENT_METHOD_CHOICES,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cash Payment  (POST only — creates Payment + marks fines paid)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def cash_payment(request):
    """
    POST fields
    ───────────
    fine_id   — the Fine.fine_id being settled
    pay_all   — "1"  → settle ALL unpaid fines for the member
    method    — "cash" | "online" | "upi" | "card"  (default: "cash")
    transaction_ref — optional reference / UTR for online transfers
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    library = _get_library_or_404(request)

    fine_id         = request.POST.get("fine_id", "").strip()
    pay_all         = request.POST.get("pay_all") == "1"
    method          = request.POST.get("method", Payment.METHOD_CASH)
    transaction_ref = request.POST.get("transaction_ref", "").strip()

    # ── Resolve the primary fine ──────────────────────────────────────────────
    fine = get_object_or_404(
        Fine.objects.for_library(library).select_related(
            "transaction__member", "transaction__book"
        ),
        fine_id=fine_id,
    )
    member = fine.transaction.member

    # ── Decide which fines to settle ──────────────────────────────────────────
    if pay_all:
        fines_to_pay = (
            Fine.objects
            .for_library(library)
            .filter(transaction__member=member, status=Fine.STATUS_UNPAID)
        )
    else:
        fines_to_pay = (
            Fine.objects
            .for_library(library)
            .filter(pk=fine.pk, status=Fine.STATUS_UNPAID)
        )

    total_amount = fines_to_pay.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    if total_amount == Decimal("0.00"):
        messages.warning(request, "No unpaid fines to collect.")
        return redirect(
            reverse("finance:process_payment") + f"?fine_id={fine.fine_id}"
        )

    # ── Create the Payment record ─────────────────────────────────────────────
    receipt_number = generate_receipt_number(library)
    is_online = method in (Payment.METHOD_ONLINE, Payment.METHOD_UPI, Payment.METHOD_CARD)

    payment = Payment.objects.create(
        fine               = fine,
        amount             = total_amount,
        method             = method,
        status             = Payment.STATUS_SUCCESS,
        receipt_number     = receipt_number,
        collected_by       = request.user.get_full_name() or request.user.username,
        library            = library,
        transaction_date   = timezone.now(),
        gateway_order_id   = transaction_ref if is_online else "",
        gateway_payment_id = transaction_ref if is_online else "",
    )

    # ── Mark fines as paid + sync transactions ────────────────────────────────
    txn_ids = list(fines_to_pay.values_list("transaction_id", flat=True))
    today   = date.today()

    fines_to_pay.update(
        status         = Fine.STATUS_PAID,
        paid_date      = today,
        payment_method = method,
        payment_ref    = transaction_ref or receipt_number,
    )

    try:
        from transactions.models import Transaction
        Transaction.objects.filter(pk__in=txn_ids).update(
            fine_paid      = True,
            fine_paid_date = today,
        )
    except Exception:
        pass  # transactions app may not be installed in all envs

    messages.success(
        request,
        f"₹{total_amount} collected from "
        f"{member.first_name} {member.last_name}. "
        f"Receipt: {receipt_number}",
    )
    return redirect("finance:payment_receipt", payment_id=payment.pk)


# ─────────────────────────────────────────────────────────────────────────────
# Payment Receipt
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payment_receipt(request, payment_id):
    """Render a printable receipt for a given Payment."""
    library = _get_library_or_404(request)

    payment = get_object_or_404(
        Payment.objects.select_related(
            "fine__transaction__member",
            "fine__transaction__book",
            "library",
        ),
        pk=payment_id,
        library=library,
    )

    txn    = None
    member = None
    fines  = []

    if payment.fine:
        txn    = payment.fine.transaction
        member = txn.member if txn else None

        # Gather all fines settled in the same payment batch (same receipt ref)
        if member and payment.fine.paid_date and payment.fine.payment_ref:
            fines = list(
                Fine.objects
                .for_library(library)
                .filter(
                    transaction__member = member,
                    paid_date           = payment.fine.paid_date,
                    payment_ref         = payment.fine.payment_ref,
                    status              = Fine.STATUS_PAID,
                )
                .select_related("transaction__book")
                .order_by("created_at")
            )
        else:
            fines = [payment.fine]

    library_name = (
        getattr(library, "library_name", None)
        or getattr(library, "name", None)
        or "Dooars Granthika"
    )

    # Logo URL — only set when the library actually has binary logo data
    raw_logo   = getattr(library, "library_logo", None) or getattr(library, "logo", None)
    logo_bytes = bytes(raw_logo) if raw_logo is not None else b""
    library_logo_url = (
        request.build_absolute_uri(reverse("finance:library_logo"))
        if logo_bytes else None
    )

    # Check if the member has a stored profile photo
    member_has_photo = False
    if member:
        raw_photo = getattr(member, "photo", None)
        if raw_photo is not None:
            try:
                member_has_photo = len(bytes(raw_photo)) > 0
            except Exception:
                pass

    return render(request, "finance/payment_receipt.html", {
        "payment":          payment,
        "transaction":      txn,
        "member":           member,
        "fines":            fines,
        "library_name":     library_name,
        "library_logo_url": library_logo_url,
        "member_has_photo": member_has_photo,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Confirm Recovery  (fine detail + action buttons)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def confirm_recovery(request):
    """
    GET ?fine_id=<id>  — render the confirm_recovery template for a fine.

    Used as a step between "view fine" and "process payment" so librarians
    can review the details before collecting cash.
    """
    library = _get_library_or_404(request)
    fine_id = request.GET.get("fine_id") or request.POST.get("fine_id")

    if not fine_id:
        raise Http404("fine_id is required.")

    fine = get_object_or_404(
        Fine.objects.for_library(library).select_related(
            "transaction__member", "transaction__book"
        ),
        fine_id=fine_id,
    )

    return render(request, "finance/confirm_recovery.html", {
        "fine":   fine,
        "member": fine.transaction.member if fine.transaction else None,
        "book":   fine.transaction.book   if fine.transaction else None,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Waive Fine  (POST only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def waive_fine(request, fine_id):
    """Mark a fine as waived (no payment collected)."""
    if request.method != "POST":
        return redirect("transactions:fine_list")

    library = _get_library_or_404(request)
    fine = get_object_or_404(
        Fine.objects.for_library(library).select_related("transaction__member"),
        pk=fine_id,
    )

    if fine.status == Fine.STATUS_UNPAID:
        fine.status    = Fine.STATUS_WAIVED
        fine.paid_date = date.today()
        fine.save(update_fields=["status", "paid_date", "updated_at"])
        messages.success(
            request,
            f"Fine of ₹{fine.amount} waived for "
            f"{fine.transaction.member.first_name} "
            f"{fine.transaction.member.last_name}.",
        )
    else:
        messages.warning(request, "Only unpaid fines can be waived.")

    return redirect(request.POST.get("next") or "transactions:fine_list")


# ─────────────────────────────────────────────────────────────────────────────
# Online Payment — Razorpay order creation
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def create_online_order(request):
    """
    GET/POST ?fine_id=<id>

    Creates a Razorpay order and returns JSON:
        { order_id, amount (paise), key_id, fine_id, member }
    """
    library = _get_library_or_404(request)
    fine_id = request.GET.get("fine_id") or request.POST.get("fine_id")

    fine = get_object_or_404(
        Fine.objects.for_library(library), fine_id=fine_id
    )

    try:
        import razorpay
        ps = library.payment_settings
        if not ps.is_configured():
            return JsonResponse({"error": "Payment gateway not configured."}, status=400)

        client       = razorpay.Client(auth=(ps.key_id, ps.key_secret))
        amount_paise = int(fine.amount * 100)
        order        = client.order.create({
            "amount":   amount_paise,
            "currency": "INR",
            "receipt":  fine.fine_id,
        })

        return JsonResponse({
            "order_id": order["id"],
            "amount":   amount_paise,
            "key_id":   ps.key_id,
            "fine_id":  fine.fine_id,
            "member":   fine.member_name,
        })

    except ImportError:
        return JsonResponse({"error": "razorpay package is not installed."}, status=500)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Online Payment — success callback
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def payment_success(request):
    """
    Handles the Razorpay callback after a successful online payment.
    Query params: razorpay_order_id, razorpay_payment_id, fine_id
    """
    library             = _get_library_or_404(request)
    razorpay_order_id   = request.GET.get("razorpay_order_id", "")
    razorpay_payment_id = request.GET.get("razorpay_payment_id", "")
    fine_id             = request.GET.get("fine_id", "")

    fine = get_object_or_404(Fine.objects.for_library(library), fine_id=fine_id)

    receipt_number = generate_receipt_number(library)
    payment = Payment.objects.create(
        fine               = fine,
        amount             = fine.amount,
        method             = Payment.METHOD_ONLINE,
        status             = Payment.STATUS_PENDING,
        receipt_number     = receipt_number,
        library            = library,
        gateway_order_id   = razorpay_order_id,
        gateway_payment_id = razorpay_payment_id,
        collected_by       = request.user.get_full_name() or request.user.username,
    )
    payment.mark_success(gateway_payment_id=razorpay_payment_id)

    return redirect("finance:payment_receipt", payment_id=payment.pk)


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay Webhook
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def razorpay_webhook(request, library_id):
    """
    Webhook endpoint: POST /finance/webhook/razorpay/<library_id>/

    Verifies the Razorpay webhook signature (if webhook_secret is configured)
    and transitions pending payments to SUCCESS on "payment.captured" events.
    """
    from accounts.models import Library

    try:
        library = Library.objects.get(pk=library_id)
        ps      = library.payment_settings
    except Exception:
        return HttpResponse(status=404)

    try:
        payload   = json.loads(request.body)
        signature = request.headers.get("X-Razorpay-Signature", "")

        # Optional signature verification
        if ps.webhook_secret and signature:
            import hmac, hashlib
            expected = hmac.new(
                ps.webhook_secret.encode(),
                request.body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                return HttpResponse(status=400)

        event = payload.get("event", "")
        if event == "payment.captured":
            pid = payload["payload"]["payment"]["entity"]["id"]
            updated = Payment.objects.filter(
                gateway_payment_id = pid,
                status             = Payment.STATUS_PENDING,
            ).update(status=Payment.STATUS_SUCCESS)

            if updated:
                # Also mark associated fines as paid
                payments = Payment.objects.filter(
                    gateway_payment_id=pid, status=Payment.STATUS_SUCCESS
                )
                for p in payments:
                    if p.fine_id:
                        Fine.objects.filter(
                            pk=p.fine_id, status=Fine.STATUS_UNPAID
                        ).update(status=Fine.STATUS_PAID, paid_date=date.today())

    except Exception:
        pass  # never return 5xx to Razorpay

    return HttpResponse(status=200)


# ─────────────────────────────────────────────────────────────────────────────
# Member Fine Summary  (self-service)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_fine_summary(request):
    """
    Shows all unpaid fines for the logged-in user's library account.
    Intended for member self-service portals.
    """
    library = _get_library_or_404(request)

    unpaid = (
        Fine.objects
        .for_library(library)
        .filter(status=Fine.STATUS_UNPAID)
        .select_related("transaction__member", "transaction__book")
        .order_by("-created_at")
    )
    total = unpaid.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    return render(request, "finance/member_fine_summary.html", {
        "fines": unpaid,
        "total": total,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Income List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def income_list(request):
    """
    Paginated list of all successful payments (income).

    Filters: ?q= ?method= ?from_date= ?to_date= ?export=csv
    """
    library = _get_library_or_404(request)

    qs = (
        Payment.objects
        .filter(library=library, status=Payment.STATUS_SUCCESS)
        .select_related("fine__transaction__member", "fine__transaction__book")
        .order_by("-transaction_date")
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    method    = request.GET.get("method", "").strip()
    from_date = request.GET.get("from_date", "").strip()
    to_date   = request.GET.get("to_date", "").strip()
    q         = request.GET.get("q", "").strip()

    if method:
        qs = qs.filter(method=method)
    if from_date:
        qs = qs.filter(transaction_date__date__gte=from_date)
    if to_date:
        qs = qs.filter(transaction_date__date__lte=to_date)
    if q:
        qs = qs.filter(
            Q(receipt_number__icontains=q)
            | Q(member_name__icontains=q)
            | Q(member_id_snapshot__icontains=q)
            | Q(fine__transaction__member__first_name__icontains=q)
            | Q(fine__transaction__member__last_name__icontains=q)
        )

    # ── Aggregate stats ───────────────────────────────────────────────────────
    stats = qs.aggregate(
        total_income  = Sum("amount"),
        cash_income   = Sum("amount", filter=Q(method=Payment.METHOD_CASH)),
        online_income = Sum("amount", filter=Q(method__in=[
            Payment.METHOD_ONLINE, Payment.METHOD_UPI, Payment.METHOD_CARD,
        ])),
        total_count   = Count("id"),
    )
    total_income  = stats["total_income"]  or Decimal("0.00")
    cash_income   = stats["cash_income"]   or Decimal("0.00")
    online_income = stats["online_income"] or Decimal("0.00")
    total_count   = stats["total_count"]   or 0

    # ── CSV export ─────────────────────────────────────────────────────────────
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="income.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Receipt", "Member", "Member ID", "Book", "Fine Type", "Method", "Amount"])
        for p in qs:
            try:
                m     = p.fine.transaction.member
                mname = f"{m.first_name} {m.last_name}"
                mid   = m.member_id
                btitle = p.fine.transaction.book.title
            except Exception:
                mname  = p.member_name or ""
                mid    = p.member_id_snapshot or ""
                btitle = p.book_title or ""
            writer.writerow([
                p.transaction_date.strftime("%d %b %Y"),
                p.receipt_number or "",
                mname,
                mid,
                btitle,
                p.fine_type_snapshot or "",
                p.get_method_display(),
                p.amount,
            ])
        return response

    return render(request, "finance/income_list.html", {
        "payments":      qs,
        "total_income":  total_income,
        "cash_income":   cash_income,
        "online_income": online_income,
        "total_count":   total_count,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Expense List
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def expense_list(request):
    """List all expenses for the library. Supports CSV export."""
    library = _get_library_or_404(request)

    expenses = (
        Expense.objects
        .filter(library=library)
        .order_by("-date", "-created_at")
    )
    total_expense = expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="expenses.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Description", "Category", "Amount", "Recorded By", "Notes"])
        for e in expenses:
            writer.writerow([
                e.date, e.description,
                e.get_category_display() if e.category else "",
                e.amount,
                e.recorded_by,
                e.notes,
            ])
        return response

    return render(request, "finance/expense_list.html", {
        "expenses":      expenses,
        "total_expense": total_expense,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Add / Edit Expense
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def add_expense(request, expense_id=None):
    """
    GET  — render the add/edit form.
    POST — create or update an Expense record.

    expense_id being non-None triggers edit mode.
    """
    library = _get_library_or_404(request)
    expense = None

    if expense_id:
        expense = get_object_or_404(Expense, pk=expense_id, library=library)

    if request.method == "POST":
        amount_raw  = request.POST.get("amount", "").strip()
        description = request.POST.get("description", "").strip()
        category    = request.POST.get("category", "")
        notes       = request.POST.get("notes", "").strip()
        exp_date    = request.POST.get("date") or date.today().isoformat()

        # ── Validate ──────────────────────────────────────────────────────────
        if not amount_raw or not description:
            messages.error(request, "Amount and description are required.")
        else:
            try:
                amount = Decimal(amount_raw)
                if amount <= 0:
                    raise ValueError("Amount must be positive.")
            except Exception:
                messages.error(request, "Enter a valid positive amount.")
                amount = None

            if amount is not None:
                if expense:
                    expense.amount      = amount
                    expense.description = description
                    expense.category    = category
                    expense.notes       = notes
                    expense.date        = exp_date
                    expense.save()
                    messages.success(request, "Expense updated.")
                else:
                    Expense.objects.create(
                        library     = library,
                        amount      = amount,
                        description = description,
                        category    = category,
                        notes       = notes,
                        date        = exp_date,
                        recorded_by = request.user.get_full_name() or request.user.username,
                    )
                    messages.success(request, "Expense recorded.")
                return redirect("finance:expense_list")

    return render(request, "finance/add_expense.html", {
        "expense":    expense,
        "today":      date.today().isoformat(),
        "categories": Expense.CATEGORY_CHOICES,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Delete Expense
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def delete_expense(request, expense_id):
    """POST — permanently delete an expense record."""
    library = _get_library_or_404(request)
    expense = get_object_or_404(Expense, pk=expense_id, library=library)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")

    return redirect("finance:expense_list")


# ─────────────────────────────────────────────────────────────────────────────
# Finance Reports Overview  (name: finance:overview)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def finance_reports(request):
    """
    Main finance dashboard.

    Supports period filter: ?period=this_month|last_month|this_year
    Supports CSV export:    ?export=csv
    """
    library = _get_library_or_404(request)

    # ── Period filter ─────────────────────────────────────────────────────────
    period = request.GET.get("period", "this_month")
    import datetime
    from calendar import month_name
    today  = datetime.date.today()
    print(today)
    if period == "last_month":
        first_day = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day  = today.replace(day=1) - timedelta(days=1)
        period_label = f"{month_name[first_day.month]} {first_day.year}"

    elif period == "this_year":
        first_day = today.replace(month=1, day=1)
        last_day  = today
        period_label = f"{today.year}"

    else:  # this_month
        first_day = today.replace(day=1)
        last_day  = today
        period_label = f"{month_name[today.month]} {today.year}"

    payments = Payment.objects.filter(
        library  = library,
        status   = Payment.STATUS_SUCCESS,
        transaction_date__date__gte = first_day,
        transaction_date__date__lte = last_day,
    )
    expenses = Expense.objects.filter(
        library  = library,
        date__gte = first_day,
        date__lte = last_day,
    )

    total_income   = payments.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    total_expenses = expenses.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    net_surplus    = total_income - total_expenses

    pending_fines = (
        Fine.objects
        .for_library(library)
        .filter(status=Fine.STATUS_UNPAID)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    )

    # ── 12-month bar chart data ───────────────────────────────────────────────
    months       = _month_range(12)
    labels       = []
    monthly_data = []
    for yr, mo in months:
        labels.append(date(yr, mo, 1).strftime("%b %Y"))
        amt = (
            Payment.objects
            .filter(
                library  = library,
                status   = Payment.STATUS_SUCCESS,
                transaction_date__year  = yr,
                transaction_date__month = mo,
            )
            .aggregate(t=Sum("amount"))["t"] or 0
        )
        monthly_data.append(float(amt))

    # ── CSV export ─────────────────────────────────────────────────────────────
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="finance_overview.csv"'
        writer = csv.writer(response)
        writer.writerow(["Period", "Total Income", "Total Expenses", "Net Surplus", "Pending Fines"])
        print(period)
        writer.writerow([period, total_income, total_expenses, net_surplus, pending_fines])
        return response

    return render(request, "finance/finance_reports.html", {
        "period":         period_label,
        "total_income":   total_income,
        "total_expenses": total_expenses,
        "net_surplus":    net_surplus,
        "pending_fines":  pending_fines,
        "monthly_labels": json.dumps(labels),
        "monthly_data":   json.dumps(monthly_data),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Daily Collection
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def daily_collection(request):
    """
    Show all successful payments collected on a specific date.

    Filter: ?date=YYYY-MM-DD  (defaults to today)
    """
    library  = _get_library_or_404(request)
    date_str = request.GET.get("date", date.today().isoformat())

    try:
        selected_date = date.fromisoformat(date_str)
    except ValueError:
        selected_date = date.today()
        date_str      = selected_date.isoformat()

    payments = (
        Payment.objects
        .filter(
            library  = library,
            status   = Payment.STATUS_SUCCESS,
            transaction_date__date = selected_date,
        )
        .select_related("fine__transaction__member", "fine__transaction__book")
        .order_by("-transaction_date")
    )

    stats = payments.aggregate(
        day_total    = Sum("amount"),
        cash_total   = Sum("amount", filter=Q(method=Payment.METHOD_CASH)),
        online_total = Sum("amount", filter=Q(method__in=[
            Payment.METHOD_ONLINE, Payment.METHOD_UPI, Payment.METHOD_CARD,
        ])),
    )

    return render(request, "finance/daily_collection.html", {
        "payments":      payments,
        "day_total":     stats["day_total"]    or Decimal("0.00"),
        "cash_total":    stats["cash_total"]   or Decimal("0.00"),
        "online_total":  stats["online_total"] or Decimal("0.00"),
        "selected_date": selected_date,
        "report_date":   date_str,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Cash Book
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def cash_book(request):
    """
    Chronological ledger showing all income (credits) and expenses (debits)
    with a running balance.

    Supports CSV export: ?export=csv
    """
    library  = _get_library_or_404(request)

    payments = (
        Payment.objects
        .filter(library=library, status=Payment.STATUS_SUCCESS)
        .select_related("fine__transaction__member")
        .order_by("transaction_date")
    )
    expenses = Expense.objects.filter(library=library).order_by("date")

    # ── Build unified chronological entries list ───────────────────────────────
    entries = []

    for p in payments:
        try:
            m     = p.fine.transaction.member
            mname = f"{m.first_name} {m.last_name}".strip()
        except Exception:
            mname = p.member_name or ""
        entries.append({
            "entry_type":  "credit",
            "date":        p.transaction_date.date(),
            "description": f"Fine payment — {mname}",
            "amount":      p.amount,
            "ref":         p.receipt_number or "",
        })

    for e in expenses:
        entries.append({
            "entry_type":  "debit",
            "date":        e.date,
            "description": e.description,
            "amount":      e.amount,
            "ref":         e.get_category_display() if e.category else "",
        })

    entries.sort(key=lambda x: x["date"])

    # ── Running balance ────────────────────────────────────────────────────────
    balance = Decimal("0.00")
    for entry in entries:
        if entry["entry_type"] == "credit":
            balance += entry["amount"]
        else:
            balance -= entry["amount"]
        entry["running_balance"] = balance

    total_credits   = sum(e["amount"] for e in entries if e["entry_type"] == "credit")
    total_debits    = sum(e["amount"] for e in entries if e["entry_type"] == "debit")
    closing_balance = total_credits - total_debits

    # ── CSV export ─────────────────────────────────────────────────────────────
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="cash_book.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Type", "Description", "Reference", "Amount", "Running Balance"])
        for e in entries:
            writer.writerow([
                e["date"], e["entry_type"], e["description"],
                e["ref"], e["amount"], e["running_balance"],
            ])
        return response

    return render(request, "finance/cash_book.html", {
        "entries":         entries,
        "total_credits":   total_credits,
        "total_debits":    total_debits,
        "closing_balance": closing_balance,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Profit & Loss
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def profit_loss(request):
    """
    All-time profit & loss report with a 12-month income vs expenses chart.
    """
    library = _get_library_or_404(request)

    total_income = (
        Payment.objects
        .filter(library=library, status=Payment.STATUS_SUCCESS)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    )
    total_expense = (
        Expense.objects.filter(library=library)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    )
    net_surplus = total_income - total_expense

    # ── Income breakdown by fine type ─────────────────────────────────────────
    income_breakdown = []
    for ftype, label in Fine.FINE_TYPE_CHOICES:
        amt = (
            Fine.objects
            .for_library(library)
            .filter(fine_type=ftype, status=Fine.STATUS_PAID)
            .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        )
        if amt > 0:
            income_breakdown.append({"label": label, "amount": amt})

    # ── Expense breakdown by category ─────────────────────────────────────────
    expense_breakdown = []
    for cat, label in Expense.CATEGORY_CHOICES:
        amt = (
            Expense.objects
            .filter(library=library, category=cat)
            .aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        )
        if amt > 0:
            expense_breakdown.append({"label": label, "amount": amt})

    # ── 12-month chart data ───────────────────────────────────────────────────
    months         = _month_range(12)
    chart_labels   = []
    chart_income   = []
    chart_expenses = []

    for yr, mo in months:
        chart_labels.append(date(yr, mo, 1).strftime("%b %Y"))
        inc = (
            Payment.objects
            .filter(
                library  = library,
                status   = Payment.STATUS_SUCCESS,
                transaction_date__year  = yr,
                transaction_date__month = mo,
            )
            .aggregate(t=Sum("amount"))["t"] or 0
        )
        exp = (
            Expense.objects
            .filter(library=library, date__year=yr, date__month=mo)
            .aggregate(t=Sum("amount"))["t"] or 0
        )
        chart_income.append(float(inc))
        chart_expenses.append(float(exp))

    return render(request, "finance/profit_loss.html", {
        "total_income":      total_income,
        "total_expense":     total_expense,
        "net_surplus":       net_surplus,
        "income_breakdown":  income_breakdown,
        "expense_breakdown": expense_breakdown,
        "chart_labels":      json.dumps(chart_labels),
        "chart_income":      json.dumps(chart_income),
        "chart_expenses":    json.dumps(chart_expenses),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def audit_log(request):
    """
    Paginated, filterable log of all Payment records.

    Filters: ?from_date= ?to_date= ?method= ?status= ?q= ?export=csv
    """
    library = _get_library_or_404(request)

    qs = (
        Payment.objects
        .filter(library=library)
        .select_related("fine__transaction__member", "fine__transaction__book")
        .order_by("-transaction_date")
    )

    from_date = request.GET.get("from_date", "").strip()
    to_date   = request.GET.get("to_date",   "").strip()
    method    = request.GET.get("method",    "").strip()
    status    = request.GET.get("status",    "").strip()
    q         = request.GET.get("q",         "").strip()

    if from_date:
        qs = qs.filter(transaction_date__date__gte=from_date)
    if to_date:
        qs = qs.filter(transaction_date__date__lte=to_date)
    if method:
        qs = qs.filter(method=method)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(receipt_number__icontains=q)
            | Q(gateway_payment_id__icontains=q)
            | Q(collected_by__icontains=q)
            | Q(member_name__icontains=q)
            | Q(member_id_snapshot__icontains=q)
            | Q(book_title__icontains=q)
            | Q(fine__transaction__member__first_name__icontains=q)
            | Q(fine__transaction__member__last_name__icontains=q)
            | Q(fine__transaction__member__member_id__icontains=q)
            | Q(fine__transaction__book__title__icontains=q)
        )

    # ── CSV export ─────────────────────────────────────────────────────────────
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Date", "Time", "Receipt/ID", "Member", "Member ID",
            "Book", "Method", "Collected By", "Status", "Amount",
        ])
        for p in qs:
            try:
                member = p.fine.transaction.member
                book   = p.fine.transaction.book
                mname  = f"{member.first_name} {member.last_name}"
                mid    = member.member_id
                btitle = book.title
            except Exception:
                mname  = p.member_name or ""
                mid    = p.member_id_snapshot or ""
                btitle = p.book_title or ""
            writer.writerow([
                p.transaction_date.strftime("%d %b %Y"),
                p.transaction_date.strftime("%H:%M"),
                p.receipt_number or p.gateway_payment_id or "",
                mname, mid, btitle,
                p.get_method_display(),
                p.collected_by or "",
                p.status,
                p.amount,
            ])
        return response

    # ── Aggregate stats for the summary strip ─────────────────────────────────
    all_stats = qs.aggregate(
        total_collected = Sum("amount", filter=Q(status=Payment.STATUS_SUCCESS)),
        cash_total      = Sum("amount", filter=Q(
            status=Payment.STATUS_SUCCESS,
            method=Payment.METHOD_CASH,
        )),
        online_total    = Sum("amount", filter=Q(
            status=Payment.STATUS_SUCCESS,
            method__in=[Payment.METHOD_ONLINE, Payment.METHOD_UPI, Payment.METHOD_CARD],
        )),
        success_count   = Count("id", filter=Q(status=Payment.STATUS_SUCCESS)),
        failed_count    = Count("id", filter=Q(status__in=[
            Payment.STATUS_FAILED, Payment.STATUS_PENDING,
        ])),
    )

    paginator = Paginator(qs, 50)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    return render(request, "finance/audit_log.html", {
        "page_obj":        page_obj,
        "total_collected": all_stats["total_collected"] or Decimal("0.00"),
        "cash_total":      all_stats["cash_total"]      or Decimal("0.00"),
        "online_total":    all_stats["online_total"]    or Decimal("0.00"),
        "success_count":   all_stats["success_count"],
        "failed_count":    all_stats["failed_count"],
    })