"""
transactions/models.py

Fine logic lives in finance/models.py.
This file contains Transaction and MissingBook.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import models

from accounts.models import Library

import random
from django.db import IntegrityError, transaction as db_transaction
# ─────────────────────────────────────────────────────────────────────────────
# Transaction ID generator
# ─────────────────────────────────────────────────────────────────────────────
def _generate_transaction_id(library, issue_date: date) -> str:
    lib_name    = getattr(library, "library_name", "") or ""
    alpha_chars = [c.upper() for c in lib_name if c.isalpha()]
    lib_prefix  = "".join(alpha_chars[:3]).ljust(3, "X")

    serial = random.randint(100000, 999999)
    return f"DG{lib_prefix}TR{serial}"

# ─────────────────────────────────────────────────────────────────────────────
# Tenant isolation helpers
# ─────────────────────────────────────────────────────────────────────────────

class TenantQuerySet(models.QuerySet):
    def for_library(self, library):
        return self.filter(library=library)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_library(self, library):
        return self.get_queryset().for_library(library)


class TenantModelMixin(models.Model):
    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True


# ─────────────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(TenantModelMixin):
    """
    One row per borrowing event, scoped to a Library tenant.
    Fine maths live entirely in @property — no stored column can drift.
    fine_rate_per_day is snapshotted from LibraryRuleSettings.late_fine at
    issue time so historic records are unaffected by rule changes.
    """

    STATUS_ISSUED          = "issued"
    STATUS_RETURNED        = "returned"
    STATUS_OVERDUE         = "overdue"
    STATUS_OVERDUE_SETTLED = "overdue_settled"
    STATUS_LOST            = "lost"

    STATUS_CHOICES = [
        (STATUS_ISSUED,          "Issued"),
        (STATUS_RETURNED,        "Returned"),
        (STATUS_OVERDUE,         "Overdue"),
        (STATUS_OVERDUE_SETTLED, "Overdue – Settled"),
        (STATUS_LOST,            "Lost"),
    ]

    CONDITION_GOOD    = "good"
    CONDITION_FAIR    = "fair"
    CONDITION_DAMAGED = "damaged"

    CONDITION_CHOICES = [
        (CONDITION_GOOD,    "Good"),
        (CONDITION_FAIR,    "Fair"),
        (CONDITION_DAMAGED, "Damaged"),
    ]

    # ── Human-readable transaction ID ─────────────────────────────────────
    transaction_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        db_index=True,
        help_text=(
            "Auto-generated: DG<LIB3>TR<MM><YY><SERIAL>  "
            "e.g. DGDOOTR032600003"
        ),
    )

    # ── Relations ─────────────────────────────────────────────────────────
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="issue_transactions",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    book_copy = models.ForeignKey(
        "books.BookCopy",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        help_text="The specific copy that was issued.",
    )

    # ── Dates ─────────────────────────────────────────────────────────────
    issue_date  = models.DateField()
    due_date    = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    lost_date   = models.DateField(null=True, blank=True)

    # ── Loan settings — snapshotted at issue time ──────────────────────────
    loan_duration_days = models.PositiveIntegerField(default=14)
    fine_rate_per_day  = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("2.00"),
        help_text="Copied from LibraryRuleSettings.late_fine at issue time.",
    )

    # ── Status & condition ────────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_ISSUED, db_index=True,
    )
    return_condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, blank=True,
    )

    # ── Staff audit ───────────────────────────────────────────────────────
    issued_by   = models.CharField(max_length=150, blank=True)
    returned_to = models.CharField(max_length=150, blank=True)

    # ── Renewal ───────────────────────────────────────────────────────────
    renewal_count = models.PositiveIntegerField(default=0)

    # ── Fine / payment ────────────────────────────────────────────────────
    damage_charge  = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"),
    )
    fine_paid      = models.BooleanField(default=False)
    fine_paid_date = models.DateField(null=True, blank=True)

    # ── Notes ─────────────────────────────────────────────────────────────
    notes        = models.TextField(blank=True)
    return_notes = models.TextField(blank=True)

    # ── Audit ─────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=["library", "status"]),
            models.Index(fields=["library", "due_date"]),
            models.Index(fields=["library", "member"]),
            models.Index(fields=["book"]),
        ]

    def __str__(self):
        tid = self.transaction_id or f"#{self.pk}"
        return f"Txn {tid} — {self.member} / {self.book}"

    # ── Auto-generate transaction_id on first save ────────────────────────

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = _generate_transaction_id(
                self.library, self.issue_date or date.today()
            )
        max_retries = 5
        for attempt in range(max_retries):
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError as e:
                if "transaction_id" in str(e) and attempt < max_retries - 1:
                    self.transaction_id = _generate_transaction_id(
                        self.library, self.issue_date or date.today()
                    )
                else:
                    raise

    # ── Fine computation ──────────────────────────────────────────────────

    @property
    def is_overdue(self) -> bool:
        if self.status in (self.STATUS_RETURNED, self.STATUS_LOST, self.STATUS_OVERDUE_SETTLED):
            return False
        return date.today() > self.due_date

    @property
    def overdue_days(self) -> int:
        if self.status == self.STATUS_RETURNED and self.return_date:
            return max(0, (self.return_date - self.due_date).days)
        if not self.is_overdue:
            return 0
        return max(0, (date.today() - self.due_date).days)

    def _live_fine_rate(self) -> Decimal:
        try:
            rate = self.library.rules.late_fine
            if rate is not None:
                return Decimal(rate)
        except Exception:
            pass
        return self.fine_rate_per_day

    @property
    def overdue_fine(self) -> Decimal:
        return Decimal(self.overdue_days) * self._live_fine_rate()

    @property
    def fine_amount(self) -> Decimal:
        return self.overdue_fine + self.damage_charge

    @property
    def days_borrowed(self) -> int:
        end = self.return_date or date.today()
        return max(0, (end - self.issue_date).days)

    @property
    def overdue_severity(self) -> str:
        d = self.overdue_days
        if d <= 7:
            return "mild"
        if d <= 30:
            return "moderate"
        return "severe"

    @classmethod
    def sync_overdue_for_library(cls, library) -> None:
        """
        Bulk-flip issued → overdue for all past-due transactions,
        and refresh fine_rate_per_day from the live rule.
        """
        today = date.today()

        cls.objects.for_library(library).filter(
            status=cls.STATUS_ISSUED,
            due_date__lt=today,
        ).update(status=cls.STATUS_OVERDUE)

        try:
            live_rate = library.rules.late_fine
        except Exception:
            live_rate = None

        if live_rate is not None:
            (
                cls.objects
                .for_library(library)
                .filter(status__in=(cls.STATUS_ISSUED, cls.STATUS_OVERDUE))
                .exclude(fine_rate_per_day=Decimal(live_rate))
                .update(fine_rate_per_day=Decimal(live_rate))
            )


# ─────────────────────────────────────────────────────────────────────────────
# MissingBook
# ─────────────────────────────────────────────────────────────────────────────

class MissingBook(TenantModelMixin):
    """
    Lifecycle tracker for books reported missing / lost / recovered.
    OneToOne with Transaction — one record per borrowing event.
    """

    STATUS_MISSING   = "missing"
    STATUS_LOST      = "lost"
    STATUS_RECOVERED = "recovered"

    STATUS_CHOICES = [
        (STATUS_MISSING,   "Missing"),
        (STATUS_LOST,      "Lost"),
        (STATUS_RECOVERED, "Recovered"),
    ]

    REASON_CHOICES = [
        ("lost",     "Book Lost"),
        ("damaged",  "Severely Damaged"),
        ("missing",  "Missing - Not Returned"),
        ("other",    "Other"),
    ]

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="missing_record",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="missing_book_records",
    )

    status        = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_MISSING,
    )
    reported_date = models.DateField(default=date.today)
    reason        = models.CharField(
        max_length=20, choices=REASON_CHOICES, blank=True
    )
    notes         = models.TextField(blank=True)

    penalty_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
    )
    penalty_paid   = models.BooleanField(default=False)
    penalty_reason = models.CharField(
        max_length=20, choices=REASON_CHOICES, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Missing Book"
        verbose_name_plural = "Missing Books"
        indexes = [
            models.Index(fields=["library", "status"]),
        ]

    def __str__(self):
        return f"Missing: {self.book.title} ({self.status})"