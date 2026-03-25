"""
core/id_generator.py
════════════════════
Centralized, cryptographically-secure Compact Random ID Generator
for the Dooars Granthika Library SaaS platform.

ID Format
─────────
  DG  <LIB>  <MODULE>  <YY>  <NNNNNNNN>
  ├─── Brand prefix (always "DG")
  │     ├─── First 3 alphanumeric chars of library name, uppercase
  │     │     ├─── Module code  (BK / ST / TC / GM / TR / FN)
  │     │     │     ├─── Last 2 digits of current year
  │     │     │     │     └─── 8-digit cryptographically-secure random number
  │     │     │     │          (first digit is never 0)
  DG   DOO    BK    26   48392071
  ────────────────────────────────
  → DGDOOBK2648392071   (18 chars total)

Examples
────────
  Book:        DGDOOBK2648392071
  Student:     DGDOOST2692715482
  Teacher:     DGDOOTC2666392011
  Gen Member:  DGDOOGM2691928374
  Transaction: DGDOOTR2618273645
  Fine:        DGDOOFN2691928374

Design goals
────────────
  • No hyphens — barcode / Excel / API friendly.
  • No sequential counters — no counter tables, no race conditions.
  • Cryptographically secure — uses `secrets` module only.
  • Uniqueness guaranteed — retries until no collision (≤ MAX_RETRIES).
  • Reusable — single function handles every model/field combination.
  • PostgreSQL-optimised — single SELECT per attempt, no locking needed.
"""

import re
import secrets
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

BRAND_PREFIX = "DG"

# Supported module codes — extend here when adding new models.
MODULE_CODES = {
    "BK": "Book",
    "ST": "Student",
    "TC": "Teacher",
    "GM": "General Member",
    "TR": "Transaction",
    "FN": "Fine",
}

# Safety valve: abort after this many collision retries.
# With 8-digit random numbers the probability of a collision is astronomically
# low even at millions of records, so 10 retries is purely defensive.
MAX_RETRIES = 10

# Minimum length of the cleaned library name prefix.
MIN_LIB_PREFIX_LEN = 3


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clean_library_prefix(owner) -> str:
    """
    Derive the 3-character uppercase library prefix from the owner.

    Resolution order:
      1. owner.library.library_name   (Library model via OneToOneField)
      2. owner.get_full_name()
      3. owner.username

    Rules:
      • Strip all non-alphanumeric characters.
      • Take first 3 characters.
      • Convert to uppercase.
      • Raise ValidationError if fewer than 3 alphanumeric characters exist.

    Examples:
      "Dooars Library"   → "DOO"
      "St. Xavier's"     → "STX"
      "123 Public"       → "123"
    """
    # Try to access the related Library model (accounts app)
    raw_name = ""
    try:
        raw_name = owner.library.library_name or ""
    except Exception:
        pass

    if not raw_name:
        try:
            raw_name = owner.get_full_name() or ""
        except Exception:
            pass

    if not raw_name:
        raw_name = getattr(owner, "username", "") or ""

    # Keep only alphanumeric characters
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_name)

    if len(cleaned) < MIN_LIB_PREFIX_LEN:
        raise ValidationError(
            f"Library name '{raw_name}' must contain at least "
            f"{MIN_LIB_PREFIX_LEN} alphanumeric characters to generate an ID. "
            f"Please update the library name in settings."
        )

    return cleaned[:3].upper()


def _current_year_suffix() -> str:
    """Return the last 2 digits of the current year as a string, e.g. '26'."""
    return str(datetime.now().year)[-2:]


def _secure_random_8() -> str:
    """
    Generate a cryptographically-secure 8-digit numeric string.

    Guarantees:
      • Exactly 8 digits.
      • First digit is never 0 (i.e. value in range 10_000_000 – 99_999_999).
      • Uses secrets.randbelow exclusively — no `random` module.
    """
    # secrets.randbelow(N) returns int in [0, N)
    # Range: 10_000_000 to 99_999_999 inclusive → 90_000_000 possible values
    value = 10_000_000 + secrets.randbelow(90_000_000)
    return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_compact_id(
    owner,
    module_code: str,
    model_class,
    field_name: str = "id",
    random_length: int = 8,
) -> str:
    """
    Generate a unique Compact Random ID and return it as a string.

    Parameters
    ──────────
    owner
        The Django User instance who owns the record.  The library name is
        resolved from ``owner.library.library_name`` (falls back to username).

    module_code : str
        One of: "BK", "ST", "TC", "GM", "TR", "FN".
        Raises ``ValidationError`` for unrecognised codes.

    model_class : django.db.models.Model
        The model class to check for uniqueness
        (e.g. ``Book``, ``Member``, ``Transaction``).

    field_name : str
        The name of the field on ``model_class`` that stores the ID
        (e.g. ``"book_id"``, ``"member_id"``, ``"transaction_id"``).

    random_length : int
        Length of the random numeric suffix.  Default is 8 (per spec).
        Changing this does not affect the uniqueness guarantee.

    Returns
    ───────
    str
        A unique ID string such as ``"DGDOOBK2648392071"``.

    Raises
    ──────
    ValidationError
        If the module code is invalid or the library name is too short.
    RuntimeError
        If a unique ID cannot be generated after MAX_RETRIES attempts
        (effectively impossible in production).

    Notes
    ─────
    • This function is safe for concurrent use — each attempt independently
      generates a fresh random suffix and does a SELECT to verify uniqueness.
      No locking is required because collisions are statistically negligible.
    • Safe for bulk Excel import: call once per row, each call is independent.
    • The ``random_length`` parameter is intentionally fixed at 8 in the spec;
      it is exposed only for future extension / testing.
    """
    # ── 1. Validate module code ───────────────────────────────────────────────
    module_code = module_code.upper()
    if module_code not in MODULE_CODES:
        raise ValidationError(
            f"Invalid module code '{module_code}'. "
            f"Supported codes: {', '.join(MODULE_CODES.keys())}."
        )

    # ── 2. Build the fixed prefix once ───────────────────────────────────────
    lib_prefix  = _clean_library_prefix(owner)   # e.g. "DOO"
    year_suffix = _current_year_suffix()          # e.g. "26"

    # DG + LIB + MODULE + YY  →  e.g. "DGDOOBK26"
    fixed_prefix = f"{BRAND_PREFIX}{lib_prefix}{module_code}{year_suffix}"

    # ── 3. Generate + collision-check loop ───────────────────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        random_part = _secure_random_8()
        candidate   = f"{fixed_prefix}{random_part}"

        # Fast uniqueness check — single indexed lookup
        if not model_class.objects.filter(**{field_name: candidate}).exists():
            return candidate

        # Collision encountered (astronomically rare) — retry silently
        # Log at WARNING level if you have a logger configured:
        # import logging; logging.getLogger(__name__).warning(
        #     "ID collision on attempt %d: %s", attempt, candidate)

    raise RuntimeError(
        f"Could not generate a unique {module_code} ID after {MAX_RETRIES} attempts. "
        "This should never happen in production. Check your database for anomalies."
    )


def get_module_code_for_member(role: str) -> str:
    """
    Resolve the correct module code for a Member based on their role.

    Parameters
    ──────────
    role : str
        One of the Member.ROLE_CHOICES values: "student", "teacher", "general".

    Returns
    ───────
    str  —  "ST", "TC", or "GM"

    Raises
    ──────
    ValidationError for unrecognised roles.
    """
    mapping = {
        "student": "ST",
        "teacher": "TC",
        "general": "GM",
    }
    code = mapping.get(role)
    if code is None:
        raise ValidationError(
            f"Unknown member role '{role}'. "
            f"Expected one of: {', '.join(mapping.keys())}."
        )
    return code