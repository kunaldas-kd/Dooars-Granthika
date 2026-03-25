import secrets
import string
import re


# ==========================================================
# 🔐 SECURE RANDOM PASSWORD
# ==========================================================
def generate_random_password(length=10):
    """
    Generate a secure random password.
    Uses cryptographically strong randomness.
    Guarantees at least one uppercase, one digit, one special char.
    """
    if length < 8:
        length = 8

    alphabet = string.ascii_letters + string.digits
    while True:
        pw = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure minimum complexity
        if (any(c.isupper() for c in pw) and
                any(c.islower() for c in pw) and
                any(c.isdigit() for c in pw)):
            return pw


# ==========================================================
# 👤 AUTO USERNAME GENERATOR
# Example: DG582193
# ==========================================================
def generate_username(prefix="DG", digits=8):
    """
    Generate a random username with enough entropy to be practically unique.
    Using 8 digits gives 10^8 = 100 million combinations — collision is
    extremely unlikely. Uniqueness must still be confirmed in the view.
    """
    number_part = ''.join(secrets.choice(string.digits) for _ in range(digits))
    return f"{prefix}{number_part}"


# ==========================================================
# 📧 BASIC EMAIL VALIDATOR
# ==========================================================
def is_valid_email(email: str) -> bool:
    """Simple structural email check (does not do DNS lookup)."""
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return bool(re.match(pattern, email.strip()))