"""
books/models.py
Dooars Granthika — Books module models.

Models
------
Category   — taxonomy for books (owner-scoped)
Book       — bibliographic record (one per title/edition)
BookCopy   — one row per physical copy; carries the unique Copy ID
             and borrow status.

Design notes
------------
• Book stores only bibliographic information — no auto-generated IDs.
  Stock is derived at runtime from BookCopy querysets.

• BookCopy.copy_id uses the format:
      DG + LIB3 + BK + MM + YY + SERIAL(3)
  e.g. DGDGRBK0326001

• Status choices live on BookCopy.Status so views/admin can reference them
  without hard-coding strings.
"""

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

# Validates a BookCopy.copy_id at the model level.
# Pattern: DG + LIB3(uppercase alphanum) + BK + MM(01-12) + YY(00-99) + SERIAL(001-999)
_COPY_ID_RE = re.compile(
    r"^DG[A-Z0-9]{3}BK"
    r"(0[1-9]|1[0-2])"
    r"\d{2}"
    r"(00[1-9]|0[1-9]\d|[1-9]\d{2})$"
)


# ─────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────

class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)

    class Meta:
        verbose_name        = "Category"
        verbose_name_plural = "Categories"
        ordering            = ["name"]
        unique_together     = [("owner", "name")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────
# Book  (bibliographic record — one per title / edition)
# ─────────────────────────────────────────────────────────────

class Book(models.Model):
    LANGUAGE_CHOICES = [
        ("English",  "English"),
        ("Bengali",  "Bengali"),
        ("Hindi",    "Hindi"),
        ("Sanskrit", "Sanskrit"),
        ("Nepali",   "Nepali"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="books",
    )

    # ── Bibliographic fields ──────────────────────────────────────────
    title            = models.CharField(max_length=255)
    author           = models.CharField(max_length=255)
    isbn             = models.CharField(max_length=20, verbose_name="ISBN")
    category         = models.ForeignKey(
                           Category,
                           on_delete=models.SET_NULL,
                           null=True, blank=True,
                           related_name="books",
                       )
    publisher        = models.CharField(max_length=255, blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    language         = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, blank=True)
    edition          = models.CharField(max_length=50, blank=True)
    shelf_location   = models.CharField(max_length=50, blank=True)

    # ── Legacy aggregate columns — kept nullable for backward-compat ──
    # These will be REMOVED after the BookCopy back-fill migration runs.
    # Views and templates should use the derived properties below instead.
    total_copies = models.PositiveIntegerField(
        default=0,
        help_text="[Deprecated] Use BookCopy records instead. "
                  "Kept for migration compatibility.",
    )
    available_copies = models.PositiveIntegerField(
        default=0,
        help_text="[Deprecated] Use BookCopy records instead. "
                  "Kept for migration compatibility.",
    )

    # ── Cover image stored as binary blob ─────────────────────────────
    cover_image     = models.BinaryField(null=True, blank=True, editable=True)
    cover_mime_type = models.CharField(
        max_length=50, blank=True, default="image/jpeg",
        help_text="MIME type of the stored cover image.",
    )

    description = models.TextField(blank=True)
    price       = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Purchase / replacement price of the book (₹).",
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = "Book"
        verbose_name_plural = "Books"
        unique_together     = [("owner", "isbn")]

    def __str__(self):
        return f"{self.title} — {self.author}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    # ── Cover helper ──────────────────────────────────────────────────

    @property
    def cover_image_b64(self):
        """Data-URI string for use in <img src="…">."""
        if self.cover_image:
            import base64
            data = base64.b64encode(bytes(self.cover_image)).decode("ascii")
            mime = self.cover_mime_type or "image/jpeg"
            return f"data:{mime};base64,{data}"
        return ""

    # ── Derived stock properties (read from BookCopy) ──────────────────

    @property
    def copy_count(self) -> int:
        """Total number of registered physical copies."""
        return self.copies.count()

    @property
    def available_copy_count(self) -> int:
        """Number of copies currently available for borrowing."""
        return self.copies.filter(status=BookCopy.Status.AVAILABLE).count()

    @property
    def borrowed_copy_count(self) -> int:
        """Number of copies currently borrowed."""
        return self.copies.filter(status=BookCopy.Status.BORROWED).count()

    @property
    def issued_copies(self) -> int:
        """Alias kept for template backward-compat."""
        return self.borrowed_copy_count

    @property
    def stock_status(self) -> str:
        """String tag used by template badge logic."""
        avail = self.available_copy_count
        if avail == 0:
            return "out-stock"
        if avail <= 3:
            return "low-stock"
        return "available"


# ─────────────────────────────────────────────────────────────
# BookCopy  (one row per physical book copy)
# ─────────────────────────────────────────────────────────────

class BookCopy(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        BORROWED  = "borrowed",  "Borrowed"
        LOST      = "lost",      "Lost"
        DAMAGED   = "damaged",   "Damaged"

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="copies",
        verbose_name="Book",
    )

    # ── Physical copy ID — format: DG<LIB3>BK<MM><YY><SERIAL> ──────────
    # Total: 2+3+2+2+2+3 = 14 chars, e.g. DGDGRBK0326001
    copy_id = models.CharField(
        max_length=14,
        unique=True,
        db_index=True,
        verbose_name="Copy ID",
        help_text=(
            "Unique physical-copy identifier. "
            "Format: DG<LIB3>BK<MM><YY><SERIAL> (14 chars). "
            "Example: DGDGRBK0326001. "
            "Auto-generated; do not edit manually."
        ),
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )

    # ── Optional: track when this copy was borrowed / returned ────────
    # A full transaction model is out of scope for this sprint, but
    # these two lightweight fields let us record the last event without
    # a separate Loan model.
    borrowed_at  = models.DateTimeField(null=True, blank=True)
    returned_at  = models.DateTimeField(null=True, blank=True)

    copy_number = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Sequential copy number within the parent book (1, 2, 3 …).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ["copy_id"]
        verbose_name        = "Book Copy"
        verbose_name_plural = "Book Copies"
        indexes             = [
            models.Index(fields=["book", "status"]),
        ]

    def __str__(self):
        return f"{self.copy_id} [{self.get_status_display()}]"

    # ── DB-column sync ────────────────────────────────────────────────

    def _sync_book_copy_counts(self) -> None:
        """
        Re-count available copies for the parent Book and write the value
        to both Book.total_copies and Book.available_copies in a single
        UPDATE query.

        "Total Copies" in the book list represents total *available* copies —
        i.e. copies whose status is AVAILABLE.  Both columns are kept in sync
        with the available count so that any template or report reading either
        field gets the correct available figure.

        Called after every status change (save / delete / borrow / return).
        """
        qs          = BookCopy.objects.filter(book_id=self.book_id)
        avail_count = qs.filter(status=BookCopy.Status.AVAILABLE).count()
        Book.objects.filter(pk=self.book_id).update(
            total_copies=avail_count,
            available_copies=avail_count,
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_book_copy_counts()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._sync_book_copy_counts()

    # ── Validation ────────────────────────────────────────────────────

    def clean(self):
        """
        Validate copy_id format: DG<LIB3>BK<MM><YY><SERIAL>

        Called automatically by Django's full_clean() (admin, forms).
        The service layer always produces valid IDs, but this guard
        prevents hand-crafted or migrated data from breaking the format.
        """
        if self.copy_id and not _COPY_ID_RE.match(self.copy_id):
            raise ValidationError(
                {
                    "copy_id": (
                        "Copy ID must follow the format DG<LIB3>BK<MM><YY><SERIAL>. "
                        f"Expected 14 characters like 'DGDGRBK0326001'; "
                        f"got {self.copy_id!r}."
                    )
                }
            )

    # ── Borrow / Return helpers ───────────────────────────────────────

    def borrow(self) -> None:
        """
        Mark this copy as borrowed.
        Raises ValueError if the copy is not currently available.
        """
        if self.status != self.Status.AVAILABLE:
            raise ValueError(
                f"Copy {self.copy_id} cannot be borrowed — "
                f"current status: {self.get_status_display()}"
            )
        from django.utils import timezone
        self.status      = self.Status.BORROWED
        self.borrowed_at = timezone.now()
        self.returned_at = None
        self.save(update_fields=["status", "borrowed_at", "returned_at", "updated_at"])
        self._sync_book_copy_counts()

    def return_copy(self) -> None:
        """
        Mark this copy as returned (available).
        Raises ValueError if the copy is not currently borrowed.
        """
        if self.status != self.Status.BORROWED:
            raise ValueError(
                f"Copy {self.copy_id} cannot be returned — "
                f"current status: {self.get_status_display()}"
            )
        from django.utils import timezone
        self.status      = self.Status.AVAILABLE
        self.returned_at = timezone.now()
        self.save(update_fields=["status", "returned_at", "updated_at"])
        self._sync_book_copy_counts()