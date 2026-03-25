import logging
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("core.whatsapp_service")


# ==============================
# Shared WhatsApp Business Sender
# ==============================
def send_whatsapp_message(to_number, message):
    """
    Send a WhatsApp message via the Meta WhatsApp Business Cloud API.

    Args:
        to_number – Recipient phone number in E.164 digits (e.g. "919876543210")
                    Do NOT include the "+" prefix — Meta expects digits only.
        message   – Plain-text message body

    Returns:
        True on success, False on failure.

    Required Django settings:
        WA_ACCESS_TOKEN    – Permanent System User access token from Meta Business Manager
                             (Permissions: whatsapp_business_messaging, whatsapp_business_management)
        WA_PHONE_NUMBER_ID – The numeric Phone Number ID from WhatsApp Manager
                             (NOT the display phone number — found in Meta Developer Console)

    Meta API docs:
        https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages
    """
    url = f"https://graph.facebook.com/v22.0/{settings.WA_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # Meta expects digits only — strip leading "+" if present
    to_number = str(to_number).lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message,
        },
    }

    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                return True
            logger.error(
                "WhatsApp API error %s (attempt %d): %s",
                response.status_code, attempt + 1, response.text,
            )
            logger.debug(
                "  -> to: %s | phone_number_id: %s",
                to_number, settings.WA_PHONE_NUMBER_ID,
            )
        except requests.RequestException as exc:
            logger.warning("WhatsApp request failed (attempt %d): %s", attempt + 1, exc)
        except Exception as exc:
            logger.exception("WhatsApp unexpected error: %s", exc)
            return False
    return False


# ==============================
# Helper: extract phone from model
# ==============================
def _get_phone(obj, label="object"):
    """
    Extract and normalise a phone number from a model instance.

    Checks .phone directly, then .profile.phone as a fallback.
    Normalisation applied to every number returned:
      - Strip leading "+", spaces, and dashes
      - Auto-prefix "91" for bare 10-digit Indian mobile numbers

    Returns:
        Normalised E.164 digit string (e.g. "919876543210"), or None if not found.
    """
    phone = getattr(obj, "phone", None) or getattr(
        getattr(obj, "profile", None), "phone", None
    )
    if not phone:
        logger.debug("WhatsApp skipped: no phone number found on %s.", label)
        return None

    # Normalise: strip "+", spaces, dashes
    phone = str(phone).replace("+", "").replace(" ", "").replace("-", "")

    # Auto-prefix country code for bare 10-digit Indian mobile numbers
    if len(phone) == 10 and phone.isdigit():
        phone = "91" + phone

    return phone


# ==============================
# 1️⃣ Account Credentials
# ==============================
def send_account_credentials_whatsapp(phone, password, username):
    """
    Notify a new staff/admin user of their login credentials.

    Args:
        phone    – Recipient phone number in E.164 digits (e.g. "919876543210")
        password – Plain-text temporary password
        username – Login username
    """
    message = (
        "📚 *Dooars Granthika – Account Created*\n\n"
        "Welcome! Your library account has been created successfully.\n\n"
        f"🔹 *Login Username:* {username}\n"
        f"🔹 *Password:* {password}\n\n"
        "⚠️ *Action Required:* Please log in and change your password immediately to secure your account.\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 2️⃣ Welcome Message
# ==============================
def send_welcome_whatsapp(user):
    """
    Send a welcome message to a newly registered user.

    Args:
        user – Django User instance (must have .phone or .profile.phone)
    """
    phone = _get_phone(user, f"user '{user.username}'")
    if not phone:
        return False

    message = (
        f"👋 *Hello, {user.username}!*\n\n"
        "Welcome to *Dooars Granthika Library System*! 🎉\n\n"
        "✅ Your membership is now *active*. You have full access to our library collection and services.\n\n"
        "Browse our catalogue, manage your borrowing history, and enjoy all member benefits.\n\n"
        "📖 *Happy Reading!*\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 3️⃣ Password Reset
# ==============================
def send_password_reset_whatsapp(user, new_password, lib_name, username):
    """
    Notify a user that their password has been reset.

    Args:
        user         – Django User instance (must have .phone or .profile.phone)
        new_password – New temporary password (plain-text)
        lib_name     – Display name of the person (e.g. librarian full name)
        username     – Login username
    """
    phone = _get_phone(user, f"user '{user.username}'")
    if not phone:
        return False

    message = (
        "🔐 *Dooars Granthika – Password Reset*\n\n"
        f"Hello *{lib_name}*, your password has been reset successfully.\n\n"
        f"🔹 *Username:* {username}\n"
        f"🔹 *New Password:* {new_password}\n\n"
        "⚠️ *Action Required:* Log in with this password and change it immediately.\n\n"
        "🛡️ *Didn't request this?* Contact our support team immediately — your account may be at risk.\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 4️⃣ Member Registration Confirmation
# ==============================
def send_member_confirmation_whatsapp(member):
    """
    Confirm a new library member's registration and share their Member ID.

    Args:
        member – Member model instance with .full_name, .member_id,
                 .created_at, .phone, .get_role_display()
    """
    phone = _get_phone(member, f"member '{member.member_id}'")
    if not phone:
        return False

    registered_on = (
        member.created_at.strftime("%d %b %Y") if member.created_at else "N/A"
    )

    message = (
        "🎊 *Dooars Granthika – Membership Confirmed!*\n\n"
        f"Hello *{member.full_name}*, congratulations! Your membership has been officially confirmed.\n\n"
        f"🔹 *Member ID:* {member.member_id}\n"
        f"🔹 *Registered On:* {registered_on}\n"
        f"🔹 *Role:* {member.get_role_display()}\n"
        f"🔹 *Status:* Active ✓\n\n"
        "✅ Please keep your *Member ID* safe — you will need it for borrowing books and all future correspondence.\n\n"
        "📚 *Welcome to the family — Happy Reading!*\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 5️⃣ Member Reactivation
# ==============================
def send_member_reactivation_whatsapp(member):
    """
    Notify a member that their library account has been reactivated.

    Args:
        member – Member model instance with .full_name, .member_id,
                 .phone, .get_role_display()
    """
    phone = _get_phone(member, f"member '{member.member_id}'")
    if not phone:
        return False

    message = (
        "🎉 *Dooars Granthika – Membership Reactivated!*\n\n"
        f"Hello *{member.full_name}*, welcome back!\n\n"
        "Your library membership has been successfully *reactivated*.\n\n"
        f"🔹 *Member ID:* {member.member_id}\n"
        f"🔹 *Role:* {member.get_role_display()}\n"
        f"🔹 *Status:* Active ✓\n\n"
        "✅ You now have full access to borrow books and use all library services again.\n\n"
        "⚠️ If you did not expect this reactivation, please contact our library team immediately.\n\n"
        "📖 *Happy Reading!*\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 6️⃣ Clearance Confirmed
# ==============================
def send_clearance_confirmation_whatsapp(member):
    """
    Notify a member that their library clearance has been confirmed.

    Args:
        member – Member model instance with .full_name, .member_id,
                 .clearance_date, .cleared_by, .department, .phone
    """
    phone = _get_phone(member, f"member '{member.member_id}'")
    if not phone:
        return False

    clearance_date_str = (
        member.clearance_date.strftime("%d %b %Y")
        if member.clearance_date
        else "N/A"
    )
    cleared_by_name = "Library Administration"
    if member.cleared_by:
        cleared_by_name = (
            member.cleared_by.get_full_name() or member.cleared_by.username
        )

    dept_name = member.department.name if member.department else "N/A"

    message = (
        "✅ *Dooars Granthika – Clearance Confirmed!*\n\n"
        f"Hello *{member.full_name}*, your library clearance has been completed successfully.\n\n"
        f"🔹 *Member ID:* {member.member_id}\n"
        f"🔹 *Department:* {dept_name}\n"
        f"🔹 *Clearance Date:* {clearance_date_str}\n"
        f"🔹 *Cleared By:* {cleared_by_name}\n\n"
        "✅ You have *no outstanding books, fines, or dues*. Your library record is fully clear.\n\n"
        "📋 You may visit the library to collect your official *Clearance Certificate* if required.\n\n"
        "Thank you for being a valued member of Dooars Granthika. All the best!\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 7️⃣ Overdue Reminder
# ==============================
def send_overdue_reminder_whatsapp(member, overdue_transactions):
    """
    Send an overdue books reminder to a member.

    Args:
        member               – Member model instance
        overdue_transactions – QuerySet or list of Transaction objects
                               with .book.title, .issue_date, .due_date,
                               .fine_amount populated.
    """
    phone = _get_phone(member, f"member '{member.member_id}'")
    if not phone:
        return False

    overdue_list = list(overdue_transactions)
    total_fine   = sum(float(t.fine_amount or 0) for t in overdue_list)
    book_count   = len(overdue_list)

    book_lines = ""
    for i, t in enumerate(overdue_list, start=1):
        due_date = t.due_date
        if hasattr(due_date, "date"):
            days_overdue = (timezone.now().date() - due_date.date()).days
        else:
            days_overdue = 0

        book_lines += (
            f"  {i}. {t.book.title}\n"
            f"     Due: {t.due_date.strftime('%d %b %Y')} | "
            f"Overdue: {days_overdue}d | Fine: ₹{t.fine_amount or 0}\n"
        )

    message = (
        "⚠️ *Dooars Granthika – Overdue Books Notice*\n\n"
        f"Hello *{member.full_name}*, this is a reminder that you have *{book_count} overdue book(s)*.\n\n"
        f"🔹 *Member ID:* {member.member_id}\n"
        f"🔹 *Total Fine:* ₹{total_fine:.2f}\n\n"
        f"📕 *Overdue Books:*\n{book_lines}\n"
        "⏰ Please return all overdue books *immediately* to avoid further fines.\n"
        "Continued non-return may result in membership suspension.\n\n"
        "If you have already returned the books, please contact us to update your record.\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)


# ==============================
# 8️⃣ Member Account Closed
# ==============================
def send_member_deletion_whatsapp(member_name, member_id, member_phone):
    """
    Notify a member that their library account has been closed.

    Accepts raw values (not the model instance) because the member will
    already be deleted from the DB when this is called.
    IMPORTANT: Call this BEFORE member.delete() in the view.

    Args:
        member_name  – Full name string
        member_id    – Member ID string
        member_phone – Phone number in E.164 digits (e.g. "919876543210")
    """
    if not member_phone:
        logger.debug("WhatsApp deletion notice skipped: no phone for member %s", member_id)
        return False

    message = (
        "📋 *Dooars Granthika – Membership Closed*\n\n"
        f"Hello *{member_name}*, your membership at Dooars Granthika Library has been closed.\n\n"
        f"🔹 *Member ID:* {member_id}\n"
        f"🔹 *Status:* Closed\n\n"
        "All your borrowing records have been archived and your borrowing privileges have been revoked.\n\n"
        "🛡️ *Not expecting this?* If you believe this was done in error, please contact our library team immediately.\n\n"
        "Thank you for being a valued member of Dooars Granthika. We hope to welcome you back in the future. 👋\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(member_phone, message)


# ==============================
# 9️⃣ Book Issued
# ==============================
def send_book_issued_whatsapp(transaction):
    """
    Notify a member that a book has been issued to them.

    Args:
        transaction – Transaction model instance with .member, .book,
                      .transaction_id, .issue_date, .due_date
    """
    member = transaction.member
    phone  = _get_phone(member, f"member '{member.member_id}'")
    if not phone:
        return False

    issue_date = transaction.issue_date.strftime("%d %b %Y")
    due_date   = transaction.due_date.strftime("%d %b %Y")

    message = (
        "📚 *Dooars Granthika – Book Issued*\n\n"
        f"Hello *{member.full_name}*, a book has been successfully issued to you.\n\n"
        f"🔹 *Transaction ID:* {transaction.transaction_id}\n"
        f"🔹 *Book:* {transaction.book.title}\n"
        f"🔹 *Member ID:* {member.member_id}\n"
        f"🔹 *Issue Date:* {issue_date}\n"
        f"🔹 *Due Date:* {due_date}\n\n"
        "⚠️ Please return the book *on or before the due date* to avoid late fines.\n\n"
        "📖 *Happy Reading!*\n\n"
        "_This is an automated message from Dooars Granthika Library._"
    )
    return send_whatsapp_message(phone, message)