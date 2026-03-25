"""
transactions/fine_sync.py
─────────────────────────
Background daemon that runs every SYNC_INTERVAL_SECONDS (default 60 s).

Each cycle does two things:
  1. Flip issued → overdue for all past-due transactions
     (Transaction.sync_overdue_for_library — existing behaviour).
  2. Create or update a Fine row for every active overdue transaction
     so the amount is always persisted in the DB and stays current.

Fine row upsert rules
─────────────────────
  • One Fine row per transaction per fine_type.
  • Only unpaid fines are updated — paid/waived rows are never touched.
  • Amount = overdue_days × fine_rate_per_day  (live rate from rules).
  • If the transaction is no longer overdue the fine row is left as-is
    (amount frozen at the day it was returned / cleared).

Daily reminder window:
  • Emails are only sent between 11:00 AM and 11:00 PM (local server time).
  • Once per calendar day per library (first cycle inside that window wins).

Override the sync interval in settings.py:
    FINE_SYNC_INTERVAL = 300   # every 5 minutes (default: 60)
"""

import logging
import os
import threading
import time
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger("transactions.fine_sync")

# ── Module-level guard — only one thread per process ─────────────────────────
_sync_thread: threading.Thread | None = None
_started = False
_lock    = threading.Lock()

SYNC_INTERVAL_SECONDS: int = int(getattr(settings, "FINE_SYNC_INTERVAL", 60))

# ── Daily reminder: track the last date reminders were sent per library ───────
# Key: library.pk  →  Value: date on which the last reminder batch was sent
_last_reminder_date: dict = {}
_reminder_lock = threading.Lock()

# ── Daily reminder window (inclusive, 24-hour clock) ─────────────────────────
REMINDER_START_HOUR: int = 11   # 11:00 AM
REMINDER_END_HOUR:   int = 23   # 11:00 PM  (hour < 23 means up to 22:59:59)


def _is_within_reminder_window() -> bool:
    """Return True if the current local time is between 11:00 AM and 11:00 PM."""
    now_hour = datetime.now().hour          # 0–23, local server time
    return REMINDER_START_HOUR <= now_hour < REMINDER_END_HOUR


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — flip issued → overdue  (existing logic, unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def _sync_overdue_status(library, Transaction) -> None:
    """Bulk-flip issued → overdue and keep fine_rate_per_day in sync."""
    Transaction.sync_overdue_for_library(library)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — persist Fine rows for every overdue transaction
# ─────────────────────────────────────────────────────────────────────────────

def _sync_fine_amounts(library, Transaction, Fine) -> int:
    """
    For every active (issued/overdue) transaction that has accrued a fine,
    create or update an unpaid Fine row so the amount is always in the DB.

    Rule 7: Fine rows are only created/updated if auto_fine is ON for the library.
    Rule 6: After syncing, block any active members who have overdue loans.

    Returns the number of Fine rows created or updated.
    """
    from django.db import transaction as db_tx

    # Rule 7: honour auto_fine setting
    auto_fine = True
    try:
        auto_fine = bool(library.rules.auto_fine)
    except Exception:
        pass

    if not auto_fine:
        # Auto-fine is OFF — still auto-block overdue members (Rule 6) but
        # do NOT create or update any Fine rows.
        _auto_block_overdue_members_sync(library, Transaction)
        return 0

    # Read grace period from library rules
    grace_period_days = 0
    try:
        grace_period_days = int(library.rules.grace_period or 0)
    except Exception:
        pass

    # All active loans — include BOTH issued and overdue so newly-flipped
    # overdue transactions (like txn #9) are picked up in the same cycle.
    active_txns = (
        Transaction.objects
        .for_library(library)
        .filter(status__in=(Transaction.STATUS_OVERDUE, Transaction.STATUS_ISSUED))
    )

    touched = 0

    for txn in active_txns:
        # Apply grace period: reduce overdue_days by grace_period before computing fine
        raw_overdue_days = txn.overdue_days
        effective_overdue_days = max(0, raw_overdue_days - grace_period_days)
        try:
            rate = library.rules.late_fine
            fine_rate = Decimal(rate) if rate is not None else txn.fine_rate_per_day
        except Exception:
            fine_rate = txn.fine_rate_per_day
        overdue_fine  = Decimal(effective_overdue_days) * fine_rate    # grace-adjusted
        damage_charge = txn.damage_charge   # stored field

        # ── Overdue fine row ──────────────────────────────────────────────
        if overdue_fine > Decimal("0.00"):
            try:
                with db_tx.atomic():
                    fine_obj, created = Fine.objects.get_or_create(
                        library     = library,
                        transaction = txn,
                        fine_type   = Fine.TYPE_OVERDUE,
                        defaults={
                            "amount": overdue_fine,
                            "status": Fine.STATUS_UNPAID,
                        },
                    )
                    if not created and fine_obj.status == Fine.STATUS_UNPAID:
                        if fine_obj.amount != overdue_fine:
                            fine_obj.amount = overdue_fine
                            fine_obj.save(update_fields=["amount", "updated_at"])
                    touched += 1
            except Exception as exc:
                logger.warning(
                    "fine_sync: could not upsert overdue fine for txn %s: %s",
                    txn.pk, exc,
                )

        # ── Damage charge row (only if not already created at return) ─────
        if damage_charge > Decimal("0.00"):
            try:
                with db_tx.atomic():
                    fine_obj, created = Fine.objects.get_or_create(
                        library     = library,
                        transaction = txn,
                        fine_type   = Fine.TYPE_DAMAGE,
                        defaults={
                            "amount": damage_charge,
                            "status": Fine.STATUS_UNPAID,
                        },
                    )
                    if not created and fine_obj.status == Fine.STATUS_UNPAID:
                        if fine_obj.amount != damage_charge:
                            fine_obj.amount = damage_charge
                            fine_obj.save(update_fields=["amount", "updated_at"])
                    touched += 1
            except Exception as exc:
                logger.warning(
                    "fine_sync: could not upsert damage fine for txn %s: %s",
                    txn.pk, exc,
                )

    # Rule 6: auto-block members who still have overdue loans
    _auto_block_overdue_members_sync(library, Transaction)

    # Rule: auto-mark severely overdue books as lost (if toggle ON)
    _auto_mark_lost_sync(library, Transaction, Fine)

    return touched


def _auto_mark_lost_sync(library, Transaction, Fine) -> None:
    """
    Background-thread version of auto_mark_lost:
    If rules.auto_mark_lost is ON, flip severely overdue (>60 days) transactions
    to STATUS_LOST and create a Fine(TYPE_LOST) row if auto_fine is also ON.
    """
    try:
        auto_mark_lost = bool(library.rules.auto_mark_lost)
    except Exception:
        auto_mark_lost = False

    if not auto_mark_lost:
        return

    AUTO_LOST_THRESHOLD_DAYS = 60
    from datetime import date as _date
    cutoff = _date.today() - __import__("datetime").timedelta(days=AUTO_LOST_THRESHOLD_DAYS)

    try:
        from members.models import Member
        from books.models import Book
        from transactions.models import MissingBook
    except Exception:
        return

    overdue_qs = (
        Transaction.objects
        .for_library(library)
        .filter(status=Transaction.STATUS_OVERDUE, due_date__lt=cutoff)
        .select_related("book")
    )

    auto_fine = True
    try:
        auto_fine = bool(library.rules.auto_fine)
    except Exception:
        pass

    for txn in overdue_qs:
        try:
            from django.db import transaction as _dbt
            with _dbt.atomic():
                txn.status    = Transaction.STATUS_LOST
                txn.lost_date = _date.today()
                txn.notes     = (txn.notes or "") + " [Auto-marked lost: overdue > 60 days]"
                txn.save(update_fields=["status", "lost_date", "notes", "updated_at"])
                book = txn.book
                book.total_copies     = max(0, book.total_copies - 1)
                book.available_copies = min(book.available_copies, book.total_copies)
                book.save(update_fields=["total_copies", "available_copies"])
                MissingBook.objects.update_or_create(
                    transaction=txn,
                    defaults={
                        "library":       library,
                        "book":          book,
                        "status":        MissingBook.STATUS_LOST,
                        "reported_date": _date.today(),
                        "notes":         "Auto-marked lost: overdue > 60 days",
                    },
                )
                if auto_fine:
                    Fine.objects.get_or_create(
                        library=library,
                        transaction=txn,
                        fine_type=Fine.TYPE_LOST,
                        defaults={
                            "amount": Decimal(txn.overdue_days) * txn.fine_rate_per_day,
                            "status": Fine.STATUS_UNPAID,
                        },
                    )
        except Exception as exc:
            logger.warning("fine_sync: auto_mark_lost failed for txn %s: %s", txn.pk, exc)


def _auto_block_overdue_members_sync(library, Transaction) -> None:
    """
    Rule 6 (background thread version): block any active members who have
    at least one STATUS_OVERDUE transaction for this library.
    """
    try:
        from members.models import Member
        overdue_member_ids = set(
            Transaction.objects.for_library(library)
            .filter(status=Transaction.STATUS_OVERDUE)
            .values_list("member_id", flat=True)
            .distinct()
        )
        if overdue_member_ids:
            Member.objects.filter(
                pk__in=overdue_member_ids,
                status="active",
            ).update(status="blocked")
    except Exception as exc:
        logger.warning("fine_sync: auto-block failed for library %s: %s", library.pk, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — send daily fine reminder emails (once per calendar day, 11 AM–11 PM)
# ─────────────────────────────────────────────────────────────────────────────

def _send_daily_fine_reminders(library, Fine) -> int:
    """
    Once per calendar day (and only between 11:00 AM – 11:00 PM local time),
    email every member who has at least one unpaid fine for this library.

    Controlled by settings.FINE_DAILY_REMINDER (default: True).

    Returns the number of reminder emails sent.
    """
    # Honour opt-out setting
    if not getattr(settings, "FINE_DAILY_REMINDER", True):
        return 0

    # ── Time-window guard: only send between 11:00 AM and 11:00 PM ───────────
    if not _is_within_reminder_window():
        logger.debug(
            "fine_sync: reminder skipped for library %s — outside 11 AM–11 PM window "
            "(current hour: %d).",
            library.pk, datetime.now().hour,
        )
        return 0

    today = date.today()

    with _reminder_lock:
        if _last_reminder_date.get(library.pk) == today:
            return 0  # already sent today for this library
        # Mark as sent *before* sending to avoid a second thread racing in
        _last_reminder_date[library.pk] = today

    try:
        from core.email_service import send_fine_daily_reminder
        from members.models import Member
    except Exception as exc:
        logger.warning(
            "fine_sync: daily reminder — could not import dependencies: %s", exc
        )
        # Roll back the date guard so the next cycle retries
        with _reminder_lock:
            _last_reminder_date.pop(library.pk, None)
        return 0

    library_name = getattr(library, "name", "Dooars Granthika")

    # Fetch all unpaid fines for this library, grouped by member
    try:
        unpaid_fines = (
            Fine.objects
            .filter(library=library, status=Fine.STATUS_UNPAID)
            .select_related("transaction__member", "transaction__book")
        )
    except Exception as exc:
        logger.warning(
            "fine_sync: daily reminder — could not query fines for library %s: %s",
            library.pk, exc,
        )
        # Roll back the date guard so the next cycle retries
        with _reminder_lock:
            _last_reminder_date.pop(library.pk, None)
        return 0

    # Group fines by member
    member_fines: dict = {}
    for fine in unpaid_fines:
        try:
            member = fine.transaction.member
            if member and member.email:
                member_fines.setdefault(member, []).append(fine)
        except Exception:
            continue

    sent = 0
    for member, fines in member_fines.items():
        try:
            success = send_fine_daily_reminder(
                member=member,
                unpaid_fines=fines,
                library_name=library_name,
            )
            if success:
                sent += 1
                logger.debug(
                    "fine_sync: reminder sent to member %s (%s fine(s)).",
                    getattr(member, "member_id", member.pk),
                    len(fines),
                )
            else:
                logger.warning(
                    "fine_sync: reminder email failed for member %s.",
                    getattr(member, "member_id", member.pk),
                )
        except Exception as exc:
            logger.warning(
                "fine_sync: daily reminder error for member %s: %s",
                getattr(member, "member_id", member.pk), exc,
            )

    if sent:
        logger.info(
            "fine_sync: daily reminders sent for library '%s' — %d email(s) at %s.",
            library_name, sent, datetime.now().strftime("%H:%M"),
        )
    return sent


# ─────────────────────────────────────────────────────────────────────────────
# Combined sync — called every cycle
# ─────────────────────────────────────────────────────────────────────────────

def _run_sync_once() -> int:
    """
    Full sync pass: overdue status flip + Fine row upserts for all libraries.
    Returns the number of libraries processed.
    """
    from accounts.models import Library
    from finance.models import Fine
    from .models import Transaction

    libraries = list(Library.objects.all())
    synced = 0

    for library in libraries:
        try:
            _sync_overdue_status(library, Transaction)
            touched = _sync_fine_amounts(library, Transaction, Fine)
            reminded = _send_daily_fine_reminders(library, Fine)
            logger.debug(
                "fine_sync: library %s — %d fine row(s) created/updated, %d reminder(s) sent.",
                getattr(library, "name", library.pk),
                touched,
                reminded,
            )
            synced += 1
        except Exception as exc:
            logger.warning(
                "fine_sync: error syncing library %s (pk=%s): %s",
                getattr(library, "name", "?"),
                library.pk,
                exc,
            )

    return synced


# ─────────────────────────────────────────────────────────────────────────────
# Background thread
# ─────────────────────────────────────────────────────────────────────────────

def _sync_loop() -> None:
    logger.info(
        "fine_sync: background thread started (PID %s, interval %ss, "
        "reminder window %02d:00–%02d:00).",
        os.getpid(),
        SYNC_INTERVAL_SECONDS,
        REMINDER_START_HOUR,
        REMINDER_END_HOUR,
    )
    while True:
        time.sleep(SYNC_INTERVAL_SECONDS)
        try:
            count = _run_sync_once()
            logger.debug(
                "fine_sync: synced %d librar%s.",
                count,
                "y" if count == 1 else "ies",
            )
        except Exception as exc:
            logger.exception("fine_sync: unexpected error in sync loop: %s", exc)


def start_auto_sync() -> None:
    """
    Start the background sync thread (safe to call multiple times).
    Call this from TransactionsConfig.ready().
    """
    global _sync_thread, _started

    with _lock:
        if _started:
            return
        _started = True

    _sync_thread = threading.Thread(
        target=_sync_loop,
        name="fine-auto-sync",
        daemon=True,
    )
    _sync_thread.start()
    logger.info(
        "fine_sync: daemon thread '%s' launched (interval=%ss).",
        _sync_thread.name,
        SYNC_INTERVAL_SECONDS,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Manual trigger
# ─────────────────────────────────────────────────────────────────────────────

def run_sync_now() -> int:
    """
    Run the full sync immediately (blocking).
    Useful from the shell or management commands:
        from transactions.fine_sync import run_sync_now
        run_sync_now()
    """
    count = _run_sync_once()
    logger.info(
        "fine_sync: manual run — synced %d librar%s.",
        count, "y" if count == 1 else "ies",
    )
    return count