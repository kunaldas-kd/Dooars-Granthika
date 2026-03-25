# finance/models.py
# ─────────────────────────────────────────────────────────────────────────────
# Core financial models for the Dooars Granthika Library Management System.
#
# Models
# ──────
#   Fine            – A monetary penalty raised against a library transaction
#   Payment         – A payment record that settles one or more fines
#   Expense         – An operational expenditure recorded by staff
#   PaymentSettings – Per-library Razorpay gateway credentials
#
# Conventions
# ───────────
#   • All money fields use DecimalField(max_digits=10, decimal_places=2).
#   • Every model stores a `library` FK so data is always tenant-scoped.
#   • "Snapshot" fields (member_name, book_title, …) are denormalised copies
#     that survive even if the related objects are later deleted.
#   • BinaryField is *not* used here; the accounts `Library` model owns the
#     logo BinaryField.  Views read it from `request.user.library`.
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from datetime import date
from decimal import Decimal

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fernet():
    """Return a Fernet instance keyed from settings.FERNET_KEY (bytes or str)."""
    key = getattr(settings, "FERNET_KEY", None)
    if key is None:
        # Fallback: derive a stable 32-byte key from SECRET_KEY so the app
        # works without an explicit FERNET_KEY setting.
        import base64, hashlib
        raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw)
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def generate_receipt_number(library) -> str:
    """
    Generate a unique receipt number for the given library.
    Format:  RCT-DG-<LIB>-<XXXXXXXX>
      LIB      -- first 3 characters of the library name, uppercased
      XXXXXXXX -- 8 random digits
    """
    from django.utils.crypto import get_random_string

    lib_name = (
        getattr(library, "library_name", None)
        or getattr(library, "name", None)
        or ""
    ).strip()
    lib_prefix = lib_name[:3].upper() if len(lib_name) >= 3 else lib_name.upper().ljust(3, "X")
    lib_prefix = "".join(c for c in lib_prefix if c.isalnum()) or "LIB"

    for _ in range(20):
        digits    = get_random_string(8, "0123456789")
        candidate = f"RCT-DG-{lib_prefix}-{digits}"
        if not Payment.objects.filter(receipt_number=candidate).exists():
            return candidate
    # Extremely unlikely fallback
    return f"RCT-DG-{lib_prefix}-{uuid.uuid4().int % 100_000_000:08d}"


# ─────────────────────────────────────────────────────────────────────────────
# Custom QuerySet / Manager for tenant scoping
# ─────────────────────────────────────────────────────────────────────────────

class FineQuerySet(models.QuerySet):
    def for_library(self, library):
        return self.filter(library=library)

    def unpaid(self):
        return self.filter(status=Fine.STATUS_UNPAID)

    def paid(self):
        return self.filter(status=Fine.STATUS_PAID)


class FineManager(models.Manager):
    def get_queryset(self):
        return FineQuerySet(self.model, using=self._db)

    def for_library(self, library):
        return self.get_queryset().for_library(library)


# ─────────────────────────────────────────────────────────────────────────────
# Fine
# ─────────────────────────────────────────────────────────────────────────────

class Fine(models.Model):
    """
    A financial penalty attached to a library transaction (e.g. overdue,
    lost book, damage).

    The fine_id is a human-readable identifier shown to staff and members.
    Snapshot fields preserve member/book/transaction data for audit purposes
    even if those records are later altered or deleted.
    """

    # ── Status choices ────────────────────────────────────────────────────────
    STATUS_UNPAID = "unpaid"
    STATUS_PAID   = "paid"
    STATUS_WAIVED = "waived"

    STATUS_CHOICES = [
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PAID,   "Paid"),
        (STATUS_WAIVED, "Waived"),
    ]

    # ── Fine-type choices ─────────────────────────────────────────────────────
    FINE_TYPE_OVERDUE = "overdue"
    FINE_TYPE_LOST    = "lost"
    FINE_TYPE_DAMAGE  = "damage"
    FINE_TYPE_OTHER   = "other"

    FINE_TYPE_CHOICES = [
        (FINE_TYPE_OVERDUE, "Overdue"),
        (FINE_TYPE_LOST,    "Lost Book"),
        (FINE_TYPE_DAMAGE,  "Damage"),
        (FINE_TYPE_OTHER,   "Other"),
    ]

    # ── Short aliases — used by transactions/views.py and fine_sync.py ───────
    # Both naming styles resolve to the same string values:
    #   Fine.TYPE_OVERDUE  ==  Fine.FINE_TYPE_OVERDUE  ==  "overdue"
    TYPE_OVERDUE = FINE_TYPE_OVERDUE
    TYPE_LOST    = FINE_TYPE_LOST
    TYPE_DAMAGE  = FINE_TYPE_DAMAGE
    TYPE_OTHER   = FINE_TYPE_OTHER

    # ── Payment method choices (used when recording how a fine was settled) ──
    METHOD_CASH   = "cash"
    METHOD_ONLINE = "online"
    METHOD_WAIVER = "waiver"

    PAYMENT_METHOD_CHOICES = [
        (METHOD_CASH,   "Cash"),
        (METHOD_ONLINE, "Online / UPI"),
        (METHOD_WAIVER, "Waived"),
    ]

    # ── Core fields ──────────────────────────────────────────────────────────
    fine_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        db_index=True,
        help_text="Human-readable unique identifier, e.g. FINE-DG-ABCD-00001.",
    )

    library = models.ForeignKey(
        "accounts.Library",
        on_delete=models.CASCADE,
        related_name="fines",
    )

    # The issuing transaction — may be NULL if the transaction is later purged
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fines",
    )

    fine_type = models.CharField(
        max_length=20,
        choices=FINE_TYPE_CHOICES,
        default=FINE_TYPE_OVERDUE,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_UNPAID, db_index=True)
    paid_date  = models.DateField(null=True, blank=True)

    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_ref    = models.CharField(max_length=100, blank=True, help_text="Receipt number or gateway reference.")

    # ── Snapshot fields (denormalised for audit trail) ───────────────────────
    transaction_id_snapshot  = models.CharField(max_length=50,  blank=True)
    member_name              = models.CharField(max_length=200, blank=True)
    member_id_snapshot       = models.CharField(max_length=50,  blank=True)
    book_title               = models.CharField(max_length=300, blank=True)
    issue_date_snapshot      = models.DateField(null=True, blank=True)
    due_date_snapshot        = models.DateField(null=True, blank=True)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FineManager()

    class Meta:
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["library", "status"]),
            models.Index(fields=["library", "fine_type"]),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate fine_id on first save
        if not self.fine_id:
            self.fine_id = self._generate_fine_id()

        # Populate snapshot fields from the linked transaction (if present)
        if self.transaction_id and not self.transaction_id_snapshot:
            try:
                txn = self.transaction
                self.transaction_id_snapshot = getattr(txn, "transaction_id", "") or str(txn.pk)
                member = txn.member
                if member:
                    self.member_name        = f"{member.first_name} {member.last_name}".strip()
                    self.member_id_snapshot = getattr(member, "member_id", "") or str(member.pk)
                book = txn.book
                if book:
                    self.book_title = getattr(book, "title", "")
                self.issue_date_snapshot = getattr(txn, "issue_date", None)
                self.due_date_snapshot   = getattr(txn, "due_date",  None)
            except Exception:
                pass

        super().save(*args, **kwargs)

    def _generate_fine_id(self) -> str:
        """
        Format: DG<LIB3>FN<MM><YY><SERIAL>
        Mirrors the transaction ID scheme:  DG<LIB3>TR<MM><YY><SERIAL>

        e.g.  DGDOOFN032600001
              DG    — Dooars Granthika prefix
              DOO   — first 3 alpha chars of library name
              FN    — "fine" literal
              03    — month (zero-padded)
              26    — 2-digit year
              00001 — 5-digit serial for this library+month
        """
        today = date.today()

        lib_name    = getattr(self.library, "library_name", "") if self.library_id else ""
        alpha_chars = [c.upper() for c in lib_name if c.isalpha()]
        lib_prefix  = "".join(alpha_chars[:3]).ljust(3, "X")

        mm = today.strftime("%m")
        yy = today.strftime("%y")

        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1)

        existing = Fine.objects.filter(
            library=self.library,
            created_at__date__gte=month_start,
            created_at__date__lt=month_end,
        ).count()
        serial    = existing + 1
        candidate = f"DG{lib_prefix}FN{mm}{yy}{serial:05d}"

        while Fine.objects.filter(fine_id=candidate).exists():
            serial   += 1
            candidate = f"DG{lib_prefix}FN{mm}{yy}{serial:05d}"

        return candidate

    def __str__(self):
        return f"{self.fine_id} — {self.member_name or 'Unknown'} — ₹{self.amount} [{self.status}]"

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def is_unpaid(self) -> bool:
        return self.status == self.STATUS_UNPAID

    @property
    def is_paid(self) -> bool:
        return self.status == self.STATUS_PAID


# ─────────────────────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────────────────────

class Payment(models.Model):
    """
    Records the settlement of one fine (or a batch of fines grouped by the
    same receipt_number / gateway reference).

    Online (Razorpay) payments go through: PENDING → SUCCESS / FAILED.
    Cash payments are created directly with STATUS_SUCCESS.
    """

    # ── Status constants ──────────────────────────────────────────────────────
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED  = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED,  "Failed"),
    ]

    # ── Method constants ──────────────────────────────────────────────────────
    METHOD_CASH   = "cash"
    METHOD_ONLINE = "online"
    METHOD_UPI    = "upi"
    METHOD_CARD   = "card"
    METHOD_OTHER  = "other"

    METHOD_CHOICES = [
        (METHOD_CASH,   "Cash"),
        (METHOD_ONLINE, "Online"),
        (METHOD_UPI,    "UPI"),
        (METHOD_CARD,   "Card"),
        (METHOD_OTHER,  "Other"),
    ]

    # ── Relations ─────────────────────────────────────────────────────────────
    library = models.ForeignKey(
        "accounts.Library",
        on_delete=models.CASCADE,
        related_name="payments",
    )

    fine = models.ForeignKey(
        Fine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    # ── Core payment fields ───────────────────────────────────────────────────
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default=METHOD_CASH)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    transaction_date = models.DateTimeField(default=timezone.now)

    receipt_number = models.CharField(max_length=60, blank=True, db_index=True)
    collected_by   = models.CharField(max_length=150, blank=True)

    # ── Gateway fields (Razorpay) ─────────────────────────────────────────────
    gateway_order_id   = models.CharField(max_length=100, blank=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True)
    gateway_signature  = models.CharField(max_length=200, blank=True)

    # ── Snapshot fields ───────────────────────────────────────────────────────
    transaction_id_snapshot = models.CharField(max_length=50,  blank=True)
    member_name             = models.CharField(max_length=200, blank=True)
    member_id_snapshot      = models.CharField(max_length=50,  blank=True)
    book_title              = models.CharField(max_length=300, blank=True)
    fine_id_snapshot        = models.CharField(max_length=30,  blank=True)
    fine_type_snapshot      = models.CharField(max_length=20,  blank=True)
    fine_amount_snapshot    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    library_name            = models.CharField(max_length=255, blank=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date"]
        indexes  = [
            models.Index(fields=["library", "status"]),
            models.Index(fields=["library", "transaction_date"]),
            models.Index(fields=["receipt_number"]),
            models.Index(fields=["gateway_payment_id"]),
        ]

    def save(self, *args, **kwargs):
        # Auto-populate snapshot fields from the linked fine/transaction
        if self.fine_id and not self.fine_id_snapshot:
            try:
                fine = self.fine
                self.fine_id_snapshot     = fine.fine_id
                self.fine_type_snapshot   = fine.fine_type
                self.fine_amount_snapshot = fine.amount

                # Pull member/book/txn data from the fine's snapshots first
                self.member_name             = fine.member_name
                self.member_id_snapshot      = fine.member_id_snapshot
                self.book_title              = fine.book_title
                self.transaction_id_snapshot = fine.transaction_id_snapshot
            except Exception:
                pass

        if self.library_id and not self.library_name:
            try:
                self.library_name = self.library.library_name
            except Exception:
                pass

        super().save(*args, **kwargs)

    def mark_success(self, gateway_payment_id: str = "") -> None:
        """
        Atomically transition this payment to SUCCESS and mark the associated
        fine(s) as paid.  Safe to call multiple times (idempotent).
        """
        if self.status == self.STATUS_SUCCESS:
            return  # already done — idempotent

        if gateway_payment_id:
            self.gateway_payment_id = gateway_payment_id

        self.status = self.STATUS_SUCCESS
        self.save(update_fields=["status", "gateway_payment_id", "updated_at"])

        # Mark the fine paid
        if self.fine_id:
            Fine.objects.filter(pk=self.fine_id, status=Fine.STATUS_UNPAID).update(
                status         = Fine.STATUS_PAID,
                paid_date      = date.today(),
                payment_method = self.method,
                payment_ref    = self.receipt_number or self.gateway_payment_id,
            )
            # Also keep the transaction's fine_paid flag in sync
            try:
                txn = self.fine.transaction
                if txn:
                    txn.fine_paid      = True
                    txn.fine_paid_date = date.today()
                    txn.save(update_fields=["fine_paid", "fine_paid_date"])
            except Exception:
                pass

    def mark_failed(self) -> None:
        """Transition this payment to FAILED."""
        self.status = self.STATUS_FAILED
        self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"Payment #{self.pk} — {self.receipt_number or 'no-receipt'} — ₹{self.amount} [{self.status}]"


# ─────────────────────────────────────────────────────────────────────────────
# Expense
# ─────────────────────────────────────────────────────────────────────────────

class ExpenseQuerySet(models.QuerySet):
    def for_library(self, library):
        return self.filter(library=library)


class ExpenseManager(models.Manager):
    def get_queryset(self):
        return ExpenseQuerySet(self.model, using=self._db)

    def for_library(self, library):
        return self.get_queryset().for_library(library)


class Expense(models.Model):
    """
    Records an operational cost (stationery, maintenance, salaries, etc.).
    These are the *debit* entries in the Cash Book.
    """

    CATEGORY_STATIONERY  = "stationery"
    CATEGORY_MAINTENANCE = "maintenance"
    CATEGORY_SALARY      = "salary"
    CATEGORY_UTILITIES   = "utilities"
    CATEGORY_BOOKS       = "books"
    CATEGORY_EQUIPMENT   = "equipment"
    CATEGORY_OTHER       = "other"

    CATEGORY_CHOICES = [
        (CATEGORY_STATIONERY,  "Stationery"),
        (CATEGORY_MAINTENANCE, "Maintenance"),
        (CATEGORY_SALARY,      "Salary"),
        (CATEGORY_UTILITIES,   "Utilities"),
        (CATEGORY_BOOKS,       "Books & Periodicals"),
        (CATEGORY_EQUIPMENT,   "Equipment"),
        (CATEGORY_OTHER,       "Other"),
    ]

    library     = models.ForeignKey(
        "accounts.Library",
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    date        = models.DateField(default=date.today)
    description = models.CharField(max_length=500)
    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    amount      = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    notes       = models.TextField(blank=True)
    recorded_by = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExpenseManager()

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes  = [
            models.Index(fields=["library", "date"]),
            models.Index(fields=["library", "category"]),
        ]

    def __str__(self):
        return f"{self.date} — {self.description} — ₹{self.amount}"


# ─────────────────────────────────────────────────────────────────────────────
# PaymentSettings
# ─────────────────────────────────────────────────────────────────────────────

class PaymentSettings(models.Model):
    """
    Stores Razorpay API credentials for a library.  The key_secret is
    symmetrically encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256).

    Usage:
        ps = library.payment_settings
        if ps.is_configured():
            client = razorpay.Client(auth=(ps.key_id, ps.key_secret))
    """

    library = models.OneToOneField(
        "accounts.Library",
        on_delete=models.CASCADE,
        related_name="payment_settings",
    )

    is_active = models.BooleanField(default=False)

    # Public key stored in plain text — not sensitive
    key_id = models.CharField(max_length=100, blank=True)

    # Encrypted secret — never read directly; use the `key_secret` property
    _key_secret_enc = models.CharField(
        max_length=500,
        blank=True,
        db_column="key_secret_enc",
        help_text="Fernet-encrypted Razorpay key secret.",
    )

    webhook_secret = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Payment Settings"
        verbose_name_plural = "Payment Settings"

    # ── Encrypted key_secret property ─────────────────────────────────────────

    @property
    def key_secret(self) -> str:
        """Decrypt and return the Razorpay secret key."""
        if not self._key_secret_enc:
            return ""
        try:
            return _fernet().decrypt(self._key_secret_enc.encode()).decode()
        except (InvalidToken, Exception):
            return ""

    @key_secret.setter
    def key_secret(self, plaintext: str) -> None:
        """Encrypt and store the Razorpay secret key."""
        if plaintext:
            self._key_secret_enc = _fernet().encrypt(plaintext.encode()).decode()
        else:
            self._key_secret_enc = ""

    def is_configured(self) -> bool:
        """Return True only if the gateway is active AND credentials are set."""
        return bool(self.is_active and self.key_id and self._key_secret_enc)

    def __str__(self):
        configured = "✓ configured" if self.is_configured() else "✗ not configured"
        return f"PaymentSettings [{self.library}] — {configured}"