"""
books/services.py
Dooars Granthika — Book Copy ID generation service.

ID Format:
    DG<LIB3>BK<MM><YY><SERIAL>

    Segment    Width   Example
    ─────────────────────────────────
    DG          2      DG          (system prefix)
    LIB3        3      DGR         (library code, uppercased)
    BK          2      BK          (module code)
    MM          2      03          (month, zero-padded)
    YY          2      26          (2-digit year)
    SERIAL      3      001         (resets to 001 every new month)
    ─────────────────────────────────
    Total      14      DGDGRBK0326001

Rules:
  • Library code is derived automatically from accounts_library.name:
      1. Take the first letter of each whitespace-separated word.
      2. If that gives ≥ 3 chars, use the first 3 (e.g. "Dooars Granthika Raj" → DGR).
      3. If < 3 chars, pad with the next characters of the first word
         (e.g. "Dooars Granthika" → DG + first char of "Dooars"[2:] → DGO  ...
          but if the library already has a `code` field, that is used directly).
  • Library code must be exactly 3 characters (uppercased automatically).
  • Serial is a 3-digit zero-padded integer starting at 001 each month.
  • Serial resets to 001 on the first ID generated in any new month.
  • The reset is month-AND-year scoped (MM+YY prefix), so Jan-2026 and
    Jan-2027 are independent sequences.
  • IDs are globally unique — enforced by the DB unique constraint on
    BookCopy.copy_id and by SELECT FOR UPDATE inside generate_book_copy_ids.
  • generate_book_copy_ids() is the primary public function.
  • create_book_copies() generates IDs and bulk-creates BookCopy rows,
    assigning copy_number sequentially within the parent book.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Union

from django.db import transaction
from django.db.models import Max

if TYPE_CHECKING:
    from .models import BookCopy


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

SYSTEM_PREFIX = "DG"
MODULE_CODE   = "BK"
SERIAL_DIGITS = 3
SERIAL_MAX    = 10 ** SERIAL_DIGITS - 1   # 999
# Total copy_id length: 2 + 3 + 2 + 2 + 2 + 3 = 14
COPY_ID_LEN   = 2 + 3 + 2 + 2 + 2 + SERIAL_DIGITS


# ─────────────────────────────────────────────────────────────
# Library code derivation
# ─────────────────────────────────────────────────────────────

def derive_library_code(library) -> str:
    """
    Read accounts_library.library_name and return its first 3 characters,
    uppercased.

    e.g.  library_name = "Dooars Granthika"  →  "DOO"
    """
    name = getattr(library, "library_name", None) or ""
    name = name.strip()
    if not name:
        raise ValueError(
            "accounts_library.library_name is empty. "
            "Please set a library name in Settings."
        )
    if len(name) < 3:
        raise ValueError(
            f"accounts_library.library_name {name!r} must be at least 3 characters."
        )
    return name[:3].upper()


def get_library_code(library_or_code: Union[str, object]) -> str:
    """
    Accept either a raw 3-char string or a Library instance.
    Returns a validated 3-character uppercase library code.
    """
    if isinstance(library_or_code, str):
        return _validate_library_code(library_or_code)
    return derive_library_code(library_or_code)


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _validate_library_code(library_code: str) -> str:
    """
    Normalise and validate the library code.
    Raises ValueError if the code is not exactly 3 non-whitespace characters.
    """
    code = library_code.strip().upper()
    if len(code) != 3:
        raise ValueError(
            f"Library code must be exactly 3 characters; "
            f"got {len(code)} character(s): {library_code!r}"
        )
    return code


def _build_prefix(library_code: str, month: int, year: int) -> str:
    """
    Compose the month-scoped prefix used for serial lookup and ID construction.

    Format: DG<LIB3>BK<MM><YY>
    Example: DGDGRBK0326   (library=DGR, March 2026)
    """
    mm = f"{month:02d}"
    yy = f"{year % 100:02d}"
    return f"{SYSTEM_PREFIX}{library_code}{MODULE_CODE}{mm}{yy}"


def _current_max_serial(prefix: str) -> int:
    """
    Return the highest serial currently stored for *prefix*, or 0 if none.
    Must be called inside a SELECT FOR UPDATE transaction block.
    """
    from .models import BookCopy

    prefix_len = len(prefix)

    copy_ids = (
        BookCopy.objects
        .filter(copy_id__startswith=prefix)
        .values_list("copy_id", flat=True)
    )

    max_serial = 0
    for cid in copy_ids:
        if len(cid) != COPY_ID_LEN:
            continue
        try:
            serial = int(cid[prefix_len: prefix_len + SERIAL_DIGITS])
        except ValueError:
            continue
        if serial > max_serial:
            max_serial = serial

    return max_serial


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def generate_book_copy_ids(
    library_or_code: Union[str, object],
    quantity: int,
) -> list[str]:
    """
    Generate *quantity* unique Book Copy IDs for the given library.

    Parameters
    ----------
    library_or_code : str | Library instance
        Either a validated 3-char string code, OR an accounts.Library
        instance — the code will be derived automatically from library.name.
    quantity : int
        Number of IDs to generate (must be ≥ 1).

    Returns
    -------
    list[str]
        Ordered list of unique Copy ID strings, each exactly 14 characters.

    Raises
    ------
    ValueError   – bad library code / quantity < 1
    OverflowError – serial would exceed 999 for the current month
    """
    code = get_library_code(library_or_code)

    if quantity < 1:
        raise ValueError(f"quantity must be ≥ 1; got {quantity!r}")

    today  = date.today()
    prefix = _build_prefix(code, today.month, today.year)

    with transaction.atomic():
        from .models import BookCopy

        BookCopy.objects.select_for_update().filter(
            copy_id__startswith=prefix
        ).values("id")

        max_serial   = _current_max_serial(prefix)
        start_serial = max_serial + 1
        end_serial   = start_serial + quantity - 1

        if end_serial > SERIAL_MAX:
            raise OverflowError(
                f"Serial overflow: {quantity} ID(s) requested starting at "
                f"{start_serial:0{SERIAL_DIGITS}d} would exceed the "
                f"{SERIAL_DIGITS}-digit cap ({SERIAL_MAX}) for prefix "
                f"'{prefix}'. Reduce quantity or wait until next month."
            )

        ids = [
            f"{prefix}{serial:0{SERIAL_DIGITS}d}"
            for serial in range(start_serial, end_serial + 1)
        ]

    return ids


def create_book_copies(
    book,
    library_or_code: Union[str, object],
    quantity: int,
) -> list["BookCopy"]:
    """
    Generate IDs and bulk-create *quantity* BookCopy records for *book*.

    Parameters
    ----------
    book : Book
        The parent Book instance (must already be saved).
    library_or_code : str | Library instance
        Either a 3-char string code, or a Library instance (code derived
        automatically from library.name via derive_library_code()).
    quantity : int
        Number of physical copies to create (must be ≥ 1).

    Returns
    -------
    list[BookCopy]
        The newly created BookCopy instances (in copy_id order).
    """
    from .models import BookCopy

    if quantity < 1:
        raise ValueError(f"quantity must be ≥ 1; got {quantity!r}")

    with transaction.atomic():
        existing_max = (
            BookCopy.objects
            .filter(book=book)
            .aggregate(max_num=Max("copy_number"))["max_num"]
        ) or 0

        ids = generate_book_copy_ids(library_or_code, quantity)

        copies = BookCopy.objects.bulk_create([
            BookCopy(
                book        = book,
                copy_id     = copy_id,
                copy_number = existing_max + offset + 1,
                status      = BookCopy.Status.AVAILABLE,
            )
            for offset, copy_id in enumerate(ids)
        ])

    return copies