# core/views.py

from django.shortcuts import render
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings


# ─────────────────────────────────────────────────────────────────────────────
# Contact form fields and their validation rules
# ─────────────────────────────────────────────────────────────────────────────

SUBJECT_CHOICES = {
    "general", "sales", "support", "feature", "bug", "partnership"
}

def _validate_contact_form(data: dict) -> dict:
    """
    Validate all contact form fields.
    Returns a dict of field -> error message for any invalid fields.
    """
    errors = {}

    name = data.get("name", "").strip()
    if not name:
        errors["name"] = "Full name is required."
    elif len(name) < 2:
        errors["name"] = "Name must be at least 2 characters."

    email = data.get("email", "").strip()
    if not email:
        errors["email"] = "Email address is required."
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "Enter a valid email address."

    phone = data.get("phone", "").strip()
    if phone and not all(c in "+0123456789 -(). " for c in phone):
        errors["phone"] = "Enter a valid phone number."

    subject = data.get("subject", "").strip()
    if not subject:
        errors["subject"] = "Please select a subject."
    elif subject not in SUBJECT_CHOICES:
        errors["subject"] = "Invalid subject selected."

    message = data.get("message", "").strip()
    if not message:
        errors["message"] = "Message cannot be empty."
    elif len(message) < 10:
        errors["message"] = "Message must be at least 10 characters."

    return errors


def _send_contact_emails(data: dict) -> bool:
    """
    Send two emails on a successful contact form submission:
      1. Notification to the site admin (dooarsprajukti@gmail.com)
      2. Auto-reply confirmation to the sender

    Uses the existing email_service infrastructure.
    Returns True on success, False if sending failed.
    """
    try:
        from core.email_service import build_html_email, send_basic_email

        name         = data["name"]
        email        = data["email"]
        phone        = data.get("phone") or "Not provided"
        organization = data.get("organization") or "Not provided"
        subject_val  = data["subject"].replace("_", " ").title()
        message      = data["message"]

        # ── 1. Admin notification email ───────────────────────────────────
        admin_body = f"""
            <p class="greeting">New Contact Form Submission 📬</p>
            <p>A new message has been received via the Dooars Granthika contact form.</p>

            <div class="credential-box">
                <p><strong>Name:</strong>         <span>{name}</span></p>
                <p><strong>Email:</strong>         <span>{email}</span></p>
                <p><strong>Phone:</strong>         <span>{phone}</span></p>
                <p><strong>Organization:</strong>  <span>{organization}</span></p>
                <p><strong>Subject:</strong>       <span>{subject_val}</span></p>
            </div>

            <div class="info-strip">
                <div class="info-strip-item">
                    <div class="info-label">From</div>
                    <div class="info-value" style="font-size:12px;">{name}</div>
                </div>
                <div class="info-strip-item">
                    <div class="info-label">Subject</div>
                    <div class="info-value" style="font-size:12px;">{subject_val}</div>
                </div>
            </div>

            <div class="credential-box" style="margin-top:1.5rem;">
                <p><strong>Message:</strong></p>
                <p style="white-space:pre-wrap; margin-top:0.5rem;">{message}</p>
            </div>

            <div class="success-box">
                📩 Reply directly to <strong>{email}</strong> to respond to this enquiry.
            </div>
        """

        admin_html  = build_html_email("New Contact Form Message", admin_body)
        admin_plain = (
            f"New contact form message from {name}\n\n"
            f"Email:        {email}\n"
            f"Phone:        {phone}\n"
            f"Organization: {organization}\n"
            f"Subject:      {subject_val}\n\n"
            f"Message:\n{message}"
        )
        send_basic_email(
            subject       = f"[Contact Form] {subject_val} — {name}",
            plain_message = admin_plain,
            html_message  = admin_html,
            recipient     = "dooarsprajukti@gmail.com",
        )

        # ── 2. Auto-reply to the sender ───────────────────────────────────
        reply_body = f"""
            <p class="greeting">Thank you, {name}! 🙏</p>
            <p>We have received your message at <span class="highlight">Dooars Granthika</span>
            and will get back to you as soon as possible.</p>

            <div class="credential-box">
                <p><strong>Subject:</strong> <span>{subject_val}</span></p>
                <p><strong>Received:</strong> <span>Your message has been logged.</span></p>
            </div>

            <div class="success-box">
                ✅ We typically respond within <strong>1–2 business days</strong>.
                For urgent queries, email us directly at
                <strong>dooarsprajukti@gmail.com</strong>.
            </div>

            <hr class="divider"/>
            <p>Here is a copy of your message for your records:</p>
            <div class="credential-box" style="margin-top:1rem;">
                <p style="white-space:pre-wrap;">{message}</p>
            </div>
            <p style="margin-top:24px;">We look forward to speaking with you! 📚</p>
        """

        reply_html  = build_html_email("We received your message", reply_body)
        reply_plain = (
            f"Hi {name},\n\n"
            f"Thank you for contacting Dooars Granthika.\n"
            f"We have received your message and will respond within 1–2 business days.\n\n"
            f"Your message:\n{message}\n\n"
            f"Dooars Granthika"
        )
        send_basic_email(
            subject       = "We received your message — Dooars Granthika",
            plain_message = reply_plain,
            html_message  = reply_html,
            recipient     = email,
        )

        return True

    except Exception as e:
        import logging
        logging.getLogger("core.views").error("Contact form email error: %s", e)
        return False


def _save_contact_submission(data: dict) -> None:
    """
    Persist the contact form submission to the DB if the ContactMessage
    model exists.  Silently skips if the model/table is not yet available.
    """
    try:
        from core.models import ContactMessage
        ContactMessage.objects.create(
            name         = data["name"].strip(),
            email        = data["email"].strip(),
            phone        = data.get("phone", "").strip(),
            organization = data.get("organization", "").strip(),
            subject      = data.get("subject", "").strip(),
            message      = data["message"].strip(),
        )
    except Exception:
        pass  # Model not yet created — emails still sent



def _get_home_stats() -> dict:
    """
    Query live counts from the database for the home page stats section.

    Returns a dict with:
        total_books      – total BookCopy records (physical copies) across all libraries
        total_libraries  – total registered Library instances
        total_members    – total Member records across all libraries

    Each value is formatted with commas (e.g. "10,000+") and falls back
    gracefully to "—" if the app/model is not yet installed.
    """
    stats = {
        "total_books":     "—",
        "total_libraries": "—",
        "total_members":   "—",
    }

    # ── Book count — physical copies (books_bookcopy table) ──────────
    # BookCopy has one row per physical copy (available/borrowed/lost/damaged)
    # This gives the true "books managed" count, not just unique titles.
    try:
        from books.models import BookCopy
        count = BookCopy.objects.count()
        stats["total_books"] = f"{count:,}+"
    except Exception:
        pass

    # ── Library count (accounts.Library) ─────────────────────────────
    try:
        from accounts.models import Library
        count = Library.objects.count()
        stats["total_libraries"] = f"{count:,}+"
    except Exception:
        pass

    # ── Member count — all roles (student + teacher + general) ───────
    # Member.ROLE_CHOICES = "student", "teacher", "general"
    try:
        from members.models import Member
        count = Member.objects.count()  # all roles combined
        stats["total_members"] = f"{count:,}+"
    except Exception:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            count = User.objects.filter(library__isnull=False).count()
            stats["total_members"] = f"{count:,}+"
        except Exception:
            pass

    return stats

def _get_active_plan():
    try:
        from subscriptions.models import Plan
        print(Plan.objects.filter(is_active=True).order_by("display_order", "price"))
        return Plan.objects.filter(is_active=True).order_by("display_order", "price")
    except Exception:
        print("no")
        return[]
def home(request):
    stats = _get_home_stats()
    return render(request, 'core/home.html', {"stats": stats})


def about(request):
    return render(request, 'core/about.html')


def pricing(request):
    plans = _get_active_plan()
    return render(request, 'core/pricing.html',{"plans":plans})


def contact(request):
    if request.method == "POST":
        data = {
            "name":         request.POST.get("name", ""),
            "email":        request.POST.get("email", ""),
            "phone":        request.POST.get("phone", ""),
            "organization": request.POST.get("organization", ""),
            "subject":      request.POST.get("subject", ""),
            "message":      request.POST.get("message", ""),
        }

        errors = _validate_contact_form(data)

        if errors:
            # Re-render form with errors and pre-filled values
            return render(request, "core/contact.html", {
                "errors":    errors,
                "form_data": data,
            })

        # Save to DB (no-op if model not created yet)
        _save_contact_submission(data)

        # Send emails
        email_sent = _send_contact_emails(data)

        if email_sent:
            messages.success(
                request,
                "Your message has been sent! We'll get back to you within 1–2 business days."
            )
        else:
            messages.warning(
                request,
                "Your message was received but we couldn't send a confirmation email. "
                "We'll still be in touch soon."
            )

        return render(request, "core/contact.html", {"form_submitted": True})

    # GET — render blank form
    return render(request, "core/contact.html")


def privacy(request):
    return render(request, 'core/privacy.html')


def terms(request):
    return render(request, 'core/terms.html')