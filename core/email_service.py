import threading
import logging
import traceback

from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


# ==============================
# Shared HTML Email Base
# ==============================
def build_html_email(title, body_content):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{title}</title>
    <style>
        /* ── Reset & Base ── */
        *, *::before, *::after {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            background-color: #eef1f5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333333;
            padding: 48px 20px;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}

        /* ── Outer Wrapper ── */
        .email-wrapper {{
            max-width: 620px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 40px rgba(0, 0, 0, 0.10), 0 2px 8px rgba(0,0,0,0.06);
        }}

        /* ── Header ── */
        .email-header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2c3e50 40%, #4a6fa5 100%);
            padding: 44px 48px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .email-header::before {{
            content: '';
            position: absolute;
            top: -60px;
            right: -60px;
            width: 200px;
            height: 200px;
            background: rgba(255,255,255,0.04);
            border-radius: 50%;
        }}
        .email-header::after {{
            content: '';
            position: absolute;
            bottom: -80px;
            left: -40px;
            width: 240px;
            height: 240px;
            background: rgba(255,255,255,0.03);
            border-radius: 50%;
        }}
        .email-header h1 {{
            color: #ffffff;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 0.6px;
            text-shadow: 0 1px 4px rgba(0,0,0,0.2);
            position: relative;
            z-index: 1;
        }}
        .email-header p {{
            color: #a8c4e0;
            font-size: 11px;
            margin-top: 8px;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            font-weight: 500;
            position: relative;
            z-index: 1;
        }}
        .header-badge {{
            display: inline-block;
            margin-top: 14px;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            padding: 4px 14px;
            font-size: 11px;
            color: #c8ddf0;
            letter-spacing: 0.5px;
            position: relative;
            z-index: 1;
        }}

        /* ── Body ── */
        .email-body {{
            padding: 44px 48px;
        }}
        .email-body p {{
            font-size: 15px;
            line-height: 1.75;
            color: #4a4a4a;
            margin-bottom: 18px;
        }}
        .email-body p:last-child {{
            margin-bottom: 0;
        }}

        /* ── Greeting ── */
        .greeting {{
            font-size: 22px !important;
            font-weight: 700;
            color: #1e3a5f !important;
            margin-bottom: 10px !important;
            letter-spacing: -0.3px;
        }}

        /* ── Credential Box ── */
        .credential-box {{
            background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 100%);
            border-left: 5px solid #4a6fa5;
            border-radius: 10px;
            padding: 22px 26px;
            margin: 26px 0;
            box-shadow: 0 2px 12px rgba(74, 111, 165, 0.10);
        }}
        .credential-box p {{
            font-size: 14px;
            color: #2c3e50;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .credential-box p:last-child {{
            margin-bottom: 0;
        }}
        .credential-box strong {{
            color: #1e3a5f;
            font-weight: 700;
            min-width: 110px;
            display: inline-block;
        }}
        .credential-box span {{
            font-family: 'Courier New', 'Lucida Console', monospace;
            background-color: #ffffff;
            border: 1px solid #c5d5f0;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 14px;
            color: #1a3a5c;
            font-weight: 600;
            letter-spacing: 0.3px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.06);
            word-break: break-all;
        }}

        /* ── Warning / Info / Danger / Success Boxes ── */
        .warning-box {{
            background: linear-gradient(135deg, #fffbf0 0%, #fff8e1 100%);
            border-left: 5px solid #e5a000;
            border-radius: 10px;
            padding: 16px 22px;
            margin: 22px 0;
            font-size: 14px;
            color: #6b4f00;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(229, 160, 0, 0.10);
        }}
        .warning-box strong {{
            font-weight: 700;
            color: #5a4000;
        }}

        .danger-box {{
            background: linear-gradient(135deg, #fff5f5 0%, #fee8e8 100%);
            border-left: 5px solid #e53e3e;
            border-radius: 10px;
            padding: 16px 22px;
            margin: 22px 0;
            font-size: 14px;
            color: #742a2a;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(229, 62, 62, 0.10);
        }}
        .danger-box strong {{
            font-weight: 700;
            color: #63171b;
        }}

        .success-box {{
            background: linear-gradient(135deg, #f0faf5 0%, #e6f7ee 100%);
            border-left: 5px solid #38a169;
            border-radius: 10px;
            padding: 16px 22px;
            margin: 22px 0;
            font-size: 14px;
            color: #1d4731;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(56, 161, 105, 0.10);
        }}
        .success-box strong {{
            font-weight: 700;
            color: #1a3d2b;
        }}

        /* ── CTA Button ── */
        .btn-container {{
            text-align: center;
            margin: 36px 0 28px;
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #4a6fa5, #2c3e50);
            color: #ffffff !important;
            text-decoration: none;
            padding: 15px 42px;
            border-radius: 50px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
            box-shadow: 0 6px 20px rgba(44, 62, 80, 0.30), 0 2px 6px rgba(74, 111, 165, 0.25);
        }}
        .fallback-link {{
            font-size: 12px;
            color: #999;
            word-break: break-all;
            text-align: center;
            margin-top: 14px;
        }}
        .fallback-link a {{
            color: #4a6fa5;
            text-decoration: underline;
        }}

        /* ── Divider ── */
        .divider {{
            border: none;
            border-top: 1px solid #e8edf2;
            margin: 32px 0;
        }}

        /* ── Stats / Info Strip ── */
        .info-strip {{
            display: flex;
            gap: 12px;
            margin: 24px 0;
        }}
        .info-strip-item {{
            flex: 1;
            background: #f7f9fc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px 16px;
            text-align: center;
        }}
        .info-strip-item .info-label {{
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }}
        .info-strip-item .info-value {{
            font-size: 15px;
            font-weight: 700;
            color: #2c3e50;
        }}

        /* ── Footer ── */
        .email-footer {{
            background: linear-gradient(180deg, #f4f7fb 0%, #eef1f5 100%);
            padding: 28px 48px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}
        .email-footer p {{
            font-size: 12px;
            color: #9aa5b4;
            line-height: 1.8;
        }}
        .email-footer a {{
            color: #4a6fa5;
            text-decoration: none;
            font-weight: 500;
        }}
        .email-footer a:hover {{
            text-decoration: underline;
        }}
        .footer-logo {{
            font-size: 14px;
            font-weight: 700;
            color: #4a6fa5;
            margin-bottom: 8px;
            letter-spacing: 0.3px;
        }}

        /* ── Utilities ── */
        .highlight {{
            color: #4a6fa5;
            font-weight: 700;
        }}
        .muted {{
            color: #888;
            font-size: 13px;
        }}

        /* ── Responsive ── */
        @media only screen and (max-width: 640px) {{
            body {{
                padding: 20px 12px;
            }}
            .email-header {{
                padding: 32px 28px;
            }}
            .email-header h1 {{
                font-size: 22px;
            }}
            .email-body {{
                padding: 32px 28px;
            }}
            .email-footer {{
                padding: 22px 28px;
            }}
            .credential-box {{
                padding: 18px 18px;
            }}
            .credential-box p {{
                flex-direction: column;
                align-items: flex-start;
                gap: 4px;
            }}
            .btn {{
                padding: 14px 32px;
                font-size: 14px;
                display: block;
                width: 100%;
                text-align: center;
            }}
            .info-strip {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-header">
            <h1>📚 Dooars Granthika</h1>
            <p>Library Management System</p>
            <span class="header-badge">✦ Official Notification</span>
        </div>
        <div class="email-body">
            {body_content}
        </div>
        <div class="email-footer">
            <div class="footer-logo">Dooars Granthika</div>
            <p>
                &copy; 2025 Dooars Granthika. All rights reserved.<br/>
                This is an automated message — please do not reply directly.<br/>
                <a href="#">Unsubscribe</a> &nbsp;&middot;&nbsp; <a href="#">Privacy Policy</a> &nbsp;&middot;&nbsp; <a href="#">Support</a>
            </p>
        </div>
    </div>
</body>
</html>
"""


# ==============================
# Basic Email Sender Function
# ==============================
def _send_email_task(subject, plain_message, html_message, recipient):
    """Internal: runs in a background thread — never blocks the request."""

    # ── Debug: log config before attempting send ──────────────────────────
    logger.info("=== EMAIL DEBUG ===")
    logger.info("EMAIL_BACKEND    : %s", getattr(settings, "EMAIL_BACKEND", "NOT SET"))
    logger.info("EMAIL_HOST       : %s", getattr(settings, "EMAIL_HOST", "NOT SET"))
    logger.info("EMAIL_PORT       : %s", getattr(settings, "EMAIL_PORT", "NOT SET"))
    logger.info("EMAIL_USE_TLS    : %s", getattr(settings, "EMAIL_USE_TLS", "NOT SET"))
    logger.info("EMAIL_HOST_USER  : %s", getattr(settings, "EMAIL_HOST_USER", "NOT SET"))
    logger.info("EMAIL_HOST_PASS  : %s", "SET" if getattr(settings, "EMAIL_HOST_PASSWORD", "") else "NOT SET / EMPTY")
    logger.info("DEFAULT_FROM_EMAIL: %s", getattr(settings, "DEFAULT_FROM_EMAIL", "NOT SET"))
    logger.info("TO               : %s", recipient)
    logger.info("SUBJECT          : %s", subject)
    logger.info("===================")

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        logger.info("✅ Email sent successfully to %s", recipient)
    except Exception as e:
        logger.error("❌ Email sending failed to %s | Error: %s", recipient, e)
        logger.error(traceback.format_exc())


def send_basic_email(subject, plain_message, html_message, recipient):
    """Dispatch email in a background thread and return immediately."""
    logger.info("send_basic_email() called → recipient=%s subject=%s", recipient, subject)
    thread = threading.Thread(
        target=_send_email_task,
        args=(subject, plain_message, html_message, recipient),
        daemon=False,   # FIX: daemon=True caused threads to be killed on Render
    )
    thread.start()
    return True


# ==============================
# 1️⃣ Account Credentials Email
# ==============================
def send_account_credentials(email, password, Username):
    subject = "Your Library Account Credentials"

    plain_message = f"""
Welcome to Dooars Granthika!
Your account has been created successfully.
Login Username: {Username}
Password: {password}
Please login and change your password immediately.
"""

    body_content = f"""
        <p class="greeting">Welcome aboard! 🎉</p>
        <p>Your account at <span class="highlight">Dooars Granthika</span> has been created successfully. Here are your login credentials to get started:</p>

        <div class="credential-box">
            <p><strong>Login Username:</strong> <span>{Username}</span></p>
            <p><strong>Password:</strong> <span>{password}</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Action Required:</strong> Please log in and change your password immediately to secure your account.
        </div>

        <hr class="divider"/>

        <p>Once logged in, you'll have access to our full library catalogue, borrowing history, and member resources.</p>
        <p>Happy reading and enjoy exploring our collection! 📖</p>
    """

    html_message = build_html_email("Account Credentials", body_content)
    return send_basic_email(subject, plain_message, html_message, email)


# ==============================
# 2️⃣ Welcome Email
# ==============================
def send_welcome_email(user):
    subject = "Welcome to Dooars Granthika"

    plain_message = f"""
Hello {user.username},
Welcome to Dooars Granthika Library System.
We are happy to have you with us.
Happy Reading!
"""

    body_content = f"""
        <p class="greeting">Hello, {user.username}! 👋</p>
        <p>Welcome to the <span class="highlight">Dooars Granthika Library System</span>. We're thrilled to have you as a member!</p>

        <div class="success-box">
            ✅ Your membership is now <strong>active</strong>. You have full access to our library collection and services.
        </div>

        <hr class="divider"/>

        <p>You can now browse our growing catalogue of books and resources, manage your borrowing history, and take advantage of all member benefits.</p>

        <p>If you ever have questions or need assistance, our library team is always happy to help.</p>

        <p style="margin-top: 24px; font-size: 18px;">Happy Reading! 🌟</p>
    """

    html_message = build_html_email("Welcome", body_content)
    return send_basic_email(subject, plain_message, html_message, user.email)


# ==============================
# 3️⃣ Password Reset Email
# ==============================
def send_password_reset_email(user, new_password, lib_name, username):
    subject = "Your New Password - Dooars Granthika"

    plain_message = f"""
Hello {lib_name},

Your password has been reset successfully.

Your username is: {username}
Your new temporary password is: {new_password}

Please log in and change your password immediately.

If you did not request this, please contact support.
"""

    body_content = f"""
        <p class="greeting">Password Reset</p>
        <p>Hello <span class="highlight">{lib_name}</span>, your password has been reset successfully. Use the temporary password below to log in:</p>

        <div class="credential-box">
            <p><strong>Username:</strong> <span>{username}</span></p>
            <p><strong>New Password:</strong> <span>{new_password}</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Action Required:</strong> Please log in using this password and change it immediately for security reasons.
        </div>

        <div class="danger-box">
            🛡️ <strong>Didn't request this?</strong> If you did not initiate a password reset, please contact our support team immediately as your account may be at risk.
        </div>
    """

    html_message = build_html_email("Password Reset", body_content)
    return send_basic_email(subject, plain_message, html_message, user.email)


# ==============================
# 4️⃣ Member Registration Confirmation Email
# ==============================
def send_member_confirmation_email(member):
    subject = "Membership Confirmed – Your Member ID | Dooars Granthika"

    plain_message = f"""
Hello {member.full_name},

Congratulations! Your membership at Dooars Granthika has been confirmed.

Your Member ID: {member.member_id}
Registered On:  {member.created_at.strftime('%d %b %Y') if member.created_at else 'N/A'}

Please keep your Member ID safe — you will need it for borrowing books,
visiting the library, and any future correspondence.

Happy Reading!
Dooars Granthika
"""

    phone_row = (
        f'<p><strong>Phone:</strong> <span>{member.phone}</span></p>'
        if getattr(member, 'phone', None) else ''
    )

    body_content = f"""
        <p class="greeting">Membership Confirmed! 🎊</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, congratulations! Your membership at <span class="highlight">Dooars Granthika Library</span> has been officially confirmed.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            <p><strong>Registered On:</strong> <span>{member.created_at.strftime('%d %b %Y') if member.created_at else 'N/A'}</span></p>
            {phone_row}
        </div>

        <div class="success-box">
            ✅ Your membership is now <strong>active</strong>. Please keep your <strong>Member ID</strong> safe — you will need it for borrowing books, library visits, and all future correspondence.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Member ID</div>
                <div class="info-value">{member.member_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color: #38a169;">Active ✓</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Role</div>
                <div class="info-value" style="font-size:13px;">{member.get_role_display()}</div>
            </div>
        </div>

        <hr class="divider"/>

        <p>You can now borrow books from our catalogue, track your borrowing history, and access all member benefits. Simply quote your <span class="highlight">Member ID</span> at the library counter or when contacting us.</p>
        <p style="margin-top: 24px; font-size: 18px;">Welcome to the family — Happy Reading! 📚</p>
    """

    html_message = build_html_email("Membership Confirmation", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 5️⃣ Member Reactivation Email
# ==============================
def send_member_reactivation_email(member):
    subject = "Your Library Membership Has Been Reactivated | Dooars Granthika"

    plain_message = f"""
Hello {member.full_name},

Great news! Your membership at Dooars Granthika has been reactivated.

Member ID: {member.member_id}
Status: Active

You now have full access to borrow books and use all library services again.

Happy Reading!
Dooars Granthika
"""

    phone_row = (
        f'<p><strong>Phone:</strong> <span>{member.phone}</span></p>'
        if getattr(member, 'phone', None) else ''
    )

    body_content = f"""
        <p class="greeting">Welcome Back! 🎉</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, your membership at <span class="highlight">Dooars Granthika Library</span> has been successfully reactivated.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            {phone_row}
        </div>

        <div class="success-box">
            ✅ Your account is now <strong>active</strong> again. You have full access to borrow books and use all library services.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Member ID</div>
                <div class="info-value">{member.member_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color: #38a169;">Active ✓</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Role</div>
                <div class="info-value" style="font-size:13px;">{member.get_role_display()}</div>
            </div>
        </div>

        <hr class="divider"/>

        <p>If you did not expect this reactivation or have any concerns, please contact our library team immediately.</p>
        <p style="margin-top: 24px; font-size: 18px;">Happy Reading! 📖</p>
    """

    html_message = build_html_email("Membership Reactivated", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 6️⃣ Clearance Confirmed Email
# ==============================
def send_clearance_confirmation_email(member):
    subject = "Library Clearance Confirmed | Dooars Granthika"

    clearance_date_str = (
        member.clearance_date.strftime('%d %b %Y')
        if member.clearance_date else 'N/A'
    )
    cleared_by_name = 'Library Administration'
    if member.cleared_by:
        cleared_by_name = member.cleared_by.get_full_name() or member.cleared_by.username

    dept_name = member.department.name if member.department else 'N/A'

    plain_message = f"""
Hello {member.full_name},

Your library clearance has been confirmed at Dooars Granthika.

Member ID     : {member.member_id}
Department    : {dept_name}
Clearance Date: {clearance_date_str}
Cleared By    : {cleared_by_name}

You have no outstanding books or dues. You may collect your clearance
certificate from the library if required.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Clearance Confirmed! ✅</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, we are pleased to confirm that your library clearance at <span class="highlight">Dooars Granthika</span> has been completed successfully.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            <p><strong>Department:</strong> <span>{dept_name}</span></p>
            <p><strong>Clearance Date:</strong> <span>{clearance_date_str}</span></p>
            <p><strong>Cleared By:</strong> <span>{cleared_by_name}</span></p>
        </div>

        <div class="success-box">
            ✅ You have <strong>no outstanding books, fines, or dues</strong>. Your library record is fully clear.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Books Pending</div>
                <div class="info-value" style="color: #38a169;">0</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Fines Due</div>
                <div class="info-value" style="color: #38a169;">₹0</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Clearance</div>
                <div class="info-value" style="color: #38a169;">Cleared ✓</div>
            </div>
        </div>

        <hr class="divider"/>

        <p>You may visit the library to collect your official <strong>Clearance Certificate</strong> if required for institutional purposes.</p>
        <p>Thank you for being a valued member of Dooars Granthika Library. We wish you all the best!</p>
    """

    html_message = build_html_email("Library Clearance Confirmed", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 7️⃣ Overdue Reminder Email
# ==============================
def send_overdue_reminder_email(member, overdue_transactions):
    """
    Send an overdue reminder to a member.

    Args:
        member               – Member model instance
        overdue_transactions – QuerySet or list of Transaction objects
                               with .book.title, .issue_date, .due_date,
                               .fine_amount populated.
    """
    subject = "⚠️ Overdue Books Notice – Action Required | Dooars Granthika"

    overdue_list = list(overdue_transactions)
    total_fine   = sum(float(t.fine_amount or 0) for t in overdue_list)
    book_count   = len(overdue_list)

    # Plain-text book lines
    book_lines = "\n".join(
        f"  • {t.book.title} — Due: {t.due_date.strftime('%d %b %Y')} | Fine: ₹{t.fine_amount or 0}"
        for t in overdue_list
    )

    plain_message = f"""
Hello {member.full_name},

This is a reminder that you have {book_count} overdue book(s) at Dooars Granthika Library.

Member ID    : {member.member_id}
Overdue Books:
{book_lines}

Total Fine Accrued: ₹{total_fine:.2f}

Please return the books at the earliest to avoid additional fines.
Visit the library or contact us for any assistance.

Dooars Granthika
"""

    # Build HTML table rows for each overdue transaction
    book_rows = ""
    for t in overdue_list:
        due_date = t.due_date
        if hasattr(due_date, 'date'):
            days_overdue = (timezone.now().date() - due_date.date()).days
        else:
            days_overdue = 0

        book_rows += f"""
            <tr>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#2c3e50;">{t.book.title}</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#666; text-align:center;">{t.issue_date.strftime('%d %b %Y')}</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#e53e3e; text-align:center; font-weight:600;">{t.due_date.strftime('%d %b %Y')}</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#e53e3e; text-align:center;">{days_overdue}d</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; font-weight:700; color:#742a2a; text-align:right;">₹{t.fine_amount or 0}</td>
            </tr>
        """

    body_content = f"""
        <p class="greeting">Overdue Notice ⚠️</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, this is a friendly reminder that you have overdue books at <span class="highlight">Dooars Granthika Library</span>. Please return them as soon as possible to avoid further fines.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Overdue Books:</strong> <span>{book_count} book(s)</span></p>
            <p><strong>Total Fine:</strong> <span>₹{total_fine:.2f}</span></p>
        </div>

        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; margin:24px 0; border:1px solid #e8edf2; border-radius:10px; overflow:hidden;">
            <thead>
                <tr style="background:linear-gradient(135deg, #1e3a5f, #2c3e50);">
                    <th style="padding:12px 14px; text-align:left; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Book Title</th>
                    <th style="padding:12px 14px; text-align:center; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Issued</th>
                    <th style="padding:12px 14px; text-align:center; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Due Date</th>
                    <th style="padding:12px 14px; text-align:center; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Overdue</th>
                    <th style="padding:12px 14px; text-align:right; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Fine</th>
                </tr>
            </thead>
            <tbody>
                {book_rows}
                <tr style="background:#f7f9fc;">
                    <td colspan="4" style="padding:12px 14px; font-size:14px; font-weight:700; color:#1e3a5f; text-align:right;">Total Fine:</td>
                    <td style="padding:12px 14px; font-size:15px; font-weight:700; color:#742a2a; text-align:right;">₹{total_fine:.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="danger-box">
            ⏰ <strong>Please return all overdue books immediately.</strong> Fines continue to accrue daily until the books are returned. Failure to return books may result in membership suspension.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Books Overdue</div>
                <div class="info-value" style="color:#e53e3e;">{book_count}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Total Fine</div>
                <div class="info-value" style="color:#e53e3e;">₹{total_fine:.2f}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Action</div>
                <div class="info-value" style="font-size:12px; color:#e53e3e;">Return ASAP</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>If you have already returned the books, please ignore this notice or contact us so we can update your record. We're always here to help!</p>
    """

    html_message = build_html_email("Overdue Books Notice", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 8️⃣ Member Account Closed Email
# ==============================
def send_member_deletion_email(member_name, member_id, member_email):
    """
    Send a farewell / account-closed notice.

    Accepts raw values (not the model instance) because the member will
    already be deleted from the DB when this is called.
    IMPORTANT: Call this BEFORE member.delete() in the view.
    """
    subject = "Your Library Membership Has Been Closed | Dooars Granthika"

    plain_message = f"""
Hello {member_name},

Your membership at Dooars Granthika Library has been closed.

Member ID: {member_id}

All your borrowing records have been archived. If you believe this was
done in error, please contact our library team immediately.

Thank you for being a member of Dooars Granthika.
"""

    body_content = f"""
        <p class="greeting">Membership Closed</p>
        <p>Hello <span class="highlight">{member_name}</span>, we are writing to inform you that your membership at <span class="highlight">Dooars Granthika Library</span> has been closed.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member_name}</span></p>
            <p><strong>Status:</strong> <span>Closed</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Your membership is no longer active.</strong> All borrowing privileges have been revoked and your records have been archived.
        </div>

        <div class="danger-box">
            🛡️ <strong>Not expecting this?</strong> If you did not request account closure or believe this was done in error, please contact our library support team immediately.
        </div>

        <hr class="divider"/>
        <p>Thank you for being a valued member of Dooars Granthika Library. We hope to welcome you back in the future.</p>
        <p style="margin-top: 16px;">Goodbye and best wishes! 👋</p>
    """

    html_message = build_html_email("Membership Closed", body_content)
    return send_basic_email(subject, plain_message, html_message, member_email)


# ==============================
# 9️⃣ Book Issued Confirmation Email
# ==============================
def send_book_issued_email(member, transaction):
    """
    Send a book-issued confirmation to a member.

    Args:
        member      – Member model instance
        transaction – Transaction model instance with .book.title,
                      .issue_date, .due_date, .copy_id (optional),
                      .fine_rate_per_day populated.
    """
    subject = "📖 Book Issued Successfully | Dooars Granthika"

    issue_date_str = (
        transaction.issue_date.strftime('%d %b %Y')
        if transaction.issue_date else 'N/A'
    )
    due_date_str = (
        transaction.due_date.strftime('%d %b %Y')
        if transaction.due_date else 'N/A'
    )
    copy_id_str = getattr(transaction, 'copy_id', None) or getattr(transaction, 'book_copy_id', 'N/A')
    fine_rate   = getattr(transaction, 'fine_rate_per_day', 'N/A')

    plain_message = f"""
Hello {member.full_name},

A book has been successfully issued to you at Dooars Granthika Library.

Member ID  : {member.member_id}
Book Title : {transaction.book.title}
Issue Date : {issue_date_str}
Due Date   : {due_date_str}

Please return the book on or before the due date to avoid late fines.

Happy Reading!
Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Book Issued! 📖</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, a book has been successfully issued to you from <span class="highlight">Dooars Granthika Library</span>.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book Title:</strong> <span>{transaction.book.title}</span></p>
            <p><strong>Copy ID:</strong> <span>{copy_id_str}</span></p>
            <p><strong>Issue Date:</strong> <span>{issue_date_str}</span></p>
            <p><strong>Due Date:</strong> <span>{due_date_str}</span></p>
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Issued On</div>
                <div class="info-value">{issue_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Return By</div>
                <div class="info-value" style="color:#e5a000;">{due_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Fine / Day</div>
                <div class="info-value" style="font-size:13px;">₹{fine_rate}</div>
            </div>
        </div>

        <div class="warning-box">
            📅 <strong>Return Reminder:</strong> Please return <strong>{transaction.book.title}</strong> on or before <strong>{due_date_str}</strong> to avoid late fines of ₹{fine_rate} per day.
        </div>

        <hr class="divider"/>
        <p>You can track your borrowing history and due dates from your member portal. If you need an extension, please contact the library in advance.</p>
        <p style="margin-top: 24px; font-size: 18px;">Happy Reading! 🌟</p>
    """

    html_message = build_html_email("Book Issued", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 🔟 Book Returned Confirmation Email
# ==============================
def send_book_returned_email(member, transaction, total_fine=None):
    """
    Send a book-returned confirmation to a member.

    Args:
        member      – Member model instance
        transaction – Transaction model instance with .book.title,
                      .issue_date, .due_date, .return_date.
        total_fine  – Decimal or None; the combined overdue + damage fine
                      created at return time (passed from views.py).
                      Falls back to transaction.fine_amount if not supplied.
    """
    subject = "✅ Book Returned Successfully | Dooars Granthika"

    issue_date_str  = (
        transaction.issue_date.strftime('%d %b %Y')
        if transaction.issue_date else 'N/A'
    )
    due_date_str    = (
        transaction.due_date.strftime('%d %b %Y')
        if transaction.due_date else 'N/A'
    )
    return_date_str = (
        transaction.return_date.strftime('%d %b %Y')
        if getattr(transaction, 'return_date', None) else 'N/A'
    )

    # Use the caller-supplied total_fine; fall back to the model property
    if total_fine is None:
        total_fine = getattr(transaction, 'fine_amount', None) or 0
    fine_paid = float(total_fine) > 0

    fine_block = f"""
        <div class="danger-box">
            💳 <strong>Outstanding Fine:</strong> A fine of <strong>₹{total_fine}</strong> has been recorded on your account for this transaction. Please clear it at the library counter.
        </div>
    """ if fine_paid else f"""
        <div class="success-box">
            ✅ <strong>No fines accrued.</strong> This book was returned on time — great job!
        </div>
    """

    plain_message = f"""
Hello {member.full_name},

Your book has been successfully returned at Dooars Granthika Library.

Member ID   : {member.member_id}
Book Title  : {transaction.book.title}
Issue Date  : {issue_date_str}
Due Date    : {due_date_str}
Return Date : {return_date_str}
Fine Amount : ₹{total_fine}

Thank you for returning the book.
Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Book Returned! ✅</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, your book has been successfully returned to <span class="highlight">Dooars Granthika Library</span>. Thank you!</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book Title:</strong> <span>{transaction.book.title}</span></p>
            <p><strong>Issue Date:</strong> <span>{issue_date_str}</span></p>
            <p><strong>Due Date:</strong> <span>{due_date_str}</span></p>
            <p><strong>Returned On:</strong> <span>{return_date_str}</span></p>
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Issued On</div>
                <div class="info-value">{issue_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Returned On</div>
                <div class="info-value" style="color:#38a169;">{return_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Fine</div>
                <div class="info-value" style="color:{'#e53e3e' if fine_paid else '#38a169'};">₹{total_fine}</div>
            </div>
        </div>

        {fine_block}

        <hr class="divider"/>
        <p>Your borrowing record has been updated. You are now eligible to borrow another book from our collection.</p>
        <p style="margin-top: 24px; font-size: 18px;">Thank you and Happy Reading! 📚</p>
    """

    html_message = build_html_email("Book Returned", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣1️⃣ Fine Payment Confirmation Email
# ==============================
def send_fine_payment_confirmation_email(member, fine, payment_reference=None):
    """
    Send a fine payment confirmation to a member.

    Args:
        member            – Member model instance
        fine              – Fine model instance with .fine_type, .amount,
                            .transaction.book.title, .updated_at.
        payment_reference – Optional string reference / receipt number.
    """
    subject = "💳 Fine Payment Confirmed | Dooars Granthika"

    fine_type_display = fine.get_fine_type_display() if hasattr(fine, 'get_fine_type_display') else str(fine.fine_type)
    paid_on_str       = (
        fine.updated_at.strftime('%d %b %Y, %I:%M %p')
        if getattr(fine, 'updated_at', None) else 'N/A'
    )
    book_title        = 'N/A'
    try:
        book_title = fine.transaction.book.title
    except Exception:
        pass

    ref_row = (
        f'<p><strong>Receipt Ref:</strong> <span>{payment_reference}</span></p>'
        if payment_reference else ''
    )
    ref_plain = f"Receipt Ref : {payment_reference}\n" if payment_reference else ""

    plain_message = f"""
Hello {member.full_name},

Your fine payment has been confirmed at Dooars Granthika Library.

Member ID  : {member.member_id}
Book       : {book_title}
Fine Type  : {fine_type_display}
Amount Paid: ₹{fine.amount}
Paid On    : {paid_on_str}
{ref_plain}
Your account is now clear of this fine.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Payment Confirmed! 💳</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, your fine payment at <span class="highlight">Dooars Granthika Library</span> has been successfully processed.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book:</strong> <span>{book_title}</span></p>
            <p><strong>Fine Type:</strong> <span>{fine_type_display}</span></p>
            <p><strong>Amount Paid:</strong> <span>₹{fine.amount}</span></p>
            <p><strong>Paid On:</strong> <span>{paid_on_str}</span></p>
            {ref_row}
        </div>

        <div class="success-box">
            ✅ <strong>Payment received.</strong> This fine has been marked as <strong>Paid</strong> on your account. No further action is required.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Fine Type</div>
                <div class="info-value" style="font-size:13px;">{fine_type_display}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Amount Paid</div>
                <div class="info-value" style="color:#38a169;">₹{fine.amount}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color:#38a169;">Paid ✓</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>Please retain this email as your payment confirmation. If you have any queries regarding this transaction, please contact our library team with your Member ID and receipt reference.</p>
        <p style="margin-top: 24px;">Thank you for settling your dues promptly! 🙏</p>
    """

    html_message = build_html_email("Fine Payment Confirmed", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣2️⃣ Membership Renewal Reminder Email
# ==============================
def send_membership_renewal_reminder_email(member, expiry_date, days_remaining):
    """
    Send a membership renewal reminder to a member.

    Args:
        member         – Member model instance
        expiry_date    – date object representing membership expiry
        days_remaining – int, number of days until expiry
    """
    subject = "🔔 Membership Renewal Reminder | Dooars Granthika"

    expiry_date_str = (
        expiry_date.strftime('%d %b %Y')
        if hasattr(expiry_date, 'strftime') else str(expiry_date)
    )

    # Urgency styling based on days remaining
    if days_remaining <= 7:
        urgency_box = f"""
        <div class="danger-box">
            🚨 <strong>Urgent:</strong> Your membership expires in <strong>{days_remaining} day(s)</strong> on <strong>{expiry_date_str}</strong>. Renew immediately to avoid losing access.
        </div>
        """
        urgency_colour = "#e53e3e"
    elif days_remaining <= 30:
        urgency_box = f"""
        <div class="warning-box">
            ⚠️ <strong>Reminder:</strong> Your membership expires in <strong>{days_remaining} day(s)</strong> on <strong>{expiry_date_str}</strong>. Please renew soon to avoid any interruption.
        </div>
        """
        urgency_colour = "#e5a000"
    else:
        urgency_box = f"""
        <div class="success-box">
            📅 <strong>Heads up:</strong> Your membership will expire on <strong>{expiry_date_str}</strong> ({days_remaining} days remaining). Renew early to enjoy uninterrupted access.
        </div>
        """
        urgency_colour = "#38a169"

    plain_message = f"""
Hello {member.full_name},

This is a reminder that your library membership at Dooars Granthika
will expire soon.

Member ID      : {member.member_id}
Expiry Date    : {expiry_date_str}
Days Remaining : {days_remaining} day(s)

Please visit the library or contact us to renew your membership before
it expires to avoid any interruption to your borrowing privileges.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Renewal Reminder 🔔</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, this is a friendly reminder that your membership at <span class="highlight">Dooars Granthika Library</span> is approaching its expiry date.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            <p><strong>Expiry Date:</strong> <span>{expiry_date_str}</span></p>
            <p><strong>Days Remaining:</strong> <span style="color:{urgency_colour}; font-weight:700;">{days_remaining} day(s)</span></p>
        </div>

        {urgency_box}

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Member ID</div>
                <div class="info-value">{member.member_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Expires On</div>
                <div class="info-value" style="color:{urgency_colour}; font-size:13px;">{expiry_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Days Left</div>
                <div class="info-value" style="color:{urgency_colour};">{days_remaining}</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>To renew your membership, please visit the library in person or contact our team. Renewing on time ensures you continue to enjoy uninterrupted access to our full catalogue and member benefits.</p>
        <p style="margin-top: 24px;">We look forward to seeing you! 📚</p>
    """

    html_message = build_html_email("Membership Renewal Reminder", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣3️⃣ Book Renewed Email  ← NEW
# ==============================
def send_book_renewed_email(member, transaction, late_fine_amount=None):
    """
    Send a loan-renewal confirmation to a member.

    Args:
        member           – Member model instance
        transaction      – Transaction after renewal (.due_date is the NEW due date,
                           .renewal_count is the updated count,
                           .loan_duration_days for the period).
        late_fine_amount – Decimal or None; the overdue fine created at renewal time.
    """
    subject = "🔄 Book Loan Renewed | Dooars Granthika"

    new_due_date_str = (
        transaction.due_date.strftime('%d %b %Y')
        if transaction.due_date else 'N/A'
    )
    max_renewals = getattr(transaction, 'max_renewal_count', '—')

    fine_block = ""
    if late_fine_amount and float(late_fine_amount) > 0:
        fine_block = f"""
        <div class="warning-box">
            ⚠️ <strong>Late Renewal Fine:</strong> Because this loan was overdue at the time of renewal,
            a fine of <strong>₹{late_fine_amount}</strong> has been applied to your account.
            Please clear it at the library counter.
        </div>
        """
    else:
        fine_block = """
        <div class="success-box">
            ✅ <strong>No late fine.</strong> Your loan was renewed on time — no extra charges applied.
        </div>
        """

    plain_message = f"""
Hello {member.full_name},

Your book loan has been successfully renewed at Dooars Granthika Library.

Member ID     : {member.member_id}
Book Title    : {transaction.book.title}
New Due Date  : {new_due_date_str}
Renewal Count : {transaction.renewal_count}
Late Fine     : {'₹' + str(late_fine_amount) if late_fine_amount and float(late_fine_amount) > 0 else 'None'}

Please return the book on or before the new due date to avoid further fines.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Loan Renewed! 🔄</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, your book loan at <span class="highlight">Dooars Granthika Library</span> has been successfully renewed.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book Title:</strong> <span>{transaction.book.title}</span></p>
            <p><strong>New Due Date:</strong> <span>{new_due_date_str}</span></p>
            <p><strong>Renewal Count:</strong> <span>{transaction.renewal_count}</span></p>
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Renewal #</div>
                <div class="info-value">{transaction.renewal_count}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">New Due Date</div>
                <div class="info-value" style="color:#e5a000; font-size:13px;">{new_due_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Late Fine</div>
                <div class="info-value" style="color:{'#e53e3e' if late_fine_amount and float(late_fine_amount) > 0 else '#38a169'};">
                    {'₹' + str(late_fine_amount) if late_fine_amount and float(late_fine_amount) > 0 else '₹0'}
                </div>
            </div>
        </div>

        {fine_block}

        <div class="warning-box">
            📅 <strong>New Return Deadline:</strong> Please return <strong>{transaction.book.title}</strong>
            on or before <strong>{new_due_date_str}</strong> to avoid further late fines.
        </div>

        <hr class="divider"/>
        <p>If you need another extension, please contact the library before the new due date. Further renewals may be subject to library policy.</p>
        <p style="margin-top: 24px; font-size: 18px;">Happy Reading! 📚</p>
    """

    html_message = build_html_email("Book Loan Renewed", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣4️⃣ Book Lost Notification Email  ← NEW
# ==============================
def send_book_lost_email(member, transaction):
    """
    Notify a member that their borrowed book has been marked as lost
    (either manually via mark_lost or automatically by the overdue daemon).

    Args:
        member      – Member model instance
        transaction – Transaction instance (.book.title, .lost_date, .fine_amount).
    """
    subject = "📕 Book Marked as Lost | Dooars Granthika"

    lost_date_str = (
        transaction.lost_date.strftime('%d %b %Y')
        if getattr(transaction, 'lost_date', None) else 'N/A'
    )
    fine_amount = getattr(transaction, 'fine_amount', None) or 0

    plain_message = f"""
Hello {member.full_name},

The following book on your account has been marked as LOST at Dooars Granthika Library.

Member ID  : {member.member_id}
Book Title : {transaction.book.title}
Lost Date  : {lost_date_str}
Fine / Penalty : ₹{fine_amount}

Please visit the library at the earliest to discuss replacement or payment.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Book Marked as Lost 📕</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, the following book on your account has been marked as <strong>Lost</strong> at <span class="highlight">Dooars Granthika Library</span>.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book Title:</strong> <span>{transaction.book.title}</span></p>
            <p><strong>Marked Lost On:</strong> <span>{lost_date_str}</span></p>
            <p><strong>Fine / Penalty:</strong> <span>₹{fine_amount}</span></p>
        </div>

        <div class="danger-box">
            🚨 <strong>Action Required:</strong> A lost-book penalty of <strong>₹{fine_amount}</strong> has been
            applied to your account. Please visit the library to arrange replacement or payment at the earliest.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Book</div>
                <div class="info-value" style="font-size:12px;">{transaction.book.title[:20]}{'…' if len(transaction.book.title) > 20 else ''}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Lost On</div>
                <div class="info-value" style="font-size:13px;">{lost_date_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Penalty</div>
                <div class="info-value" style="color:#e53e3e;">₹{fine_amount}</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>If you believe this is an error or have already returned the book, please contact our library team immediately with your Member ID so we can investigate and update your record.</p>
    """

    html_message = build_html_email("Book Marked as Lost", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣5️⃣ Member Account Blocked Email  ← NEW
# ==============================
def send_member_blocked_email(member):
    """
    Notify a member that their account has been blocked due to overdue loans.

    Args:
        member – Member model instance (.full_name, .member_id, .email).
    """
    subject = "🚫 Your Library Account Has Been Blocked | Dooars Granthika"

    plain_message = f"""
Hello {member.full_name},

Your library account at Dooars Granthika has been blocked.

Member ID : {member.member_id}
Reason    : One or more overdue books have not been returned.

Your borrowing privileges are suspended until all overdue books are returned
and any outstanding fines are cleared.

Please visit the library as soon as possible.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Account Blocked 🚫</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, your library account at <span class="highlight">Dooars Granthika</span> has been <strong>blocked</strong>.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            <p><strong>Status:</strong> <span style="color:#e53e3e;">Blocked</span></p>
            <p><strong>Reason:</strong> <span>Overdue book(s) not returned</span></p>
        </div>

        <div class="danger-box">
            🚫 <strong>Account Suspended.</strong> You cannot borrow new books or renew existing loans
            until all overdue books are returned and outstanding fines are cleared.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Member ID</div>
                <div class="info-value">{member.member_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color:#e53e3e;">Blocked</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Action</div>
                <div class="info-value" style="font-size:11px; color:#e53e3e;">Return Books</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>To restore your account, please visit the library and return all overdue books. Once all loans are cleared, your account will be automatically reactivated.</p>
        <p>If you have any questions, our library team is happy to assist.</p>
    """

    html_message = build_html_email("Account Blocked", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣6️⃣ Fine Paid Receipt Email  ← NEW
# ==============================
def send_fine_paid_email(member, fine, transaction):
    """
    Send a fine-paid receipt to a member when a fine is marked paid
    via the mark_fine_paid view.

    Args:
        member      – Member model instance
        fine        – Fine model instance (.fine_type, .amount, .paid_date or .updated_at)
        transaction – Transaction instance (.book.title)
    """
    subject = "✅ Fine Payment Receipt | Dooars Granthika"

    fine_type_display = (
        fine.get_fine_type_display()
        if hasattr(fine, 'get_fine_type_display') else str(fine.fine_type)
    )
    paid_on_str = 'N/A'
    if getattr(fine, 'paid_date', None):
        paid_on_str = fine.paid_date.strftime('%d %b %Y')
    elif getattr(fine, 'updated_at', None):
        paid_on_str = fine.updated_at.strftime('%d %b %Y, %I:%M %p')

    book_title = 'N/A'
    try:
        book_title = transaction.book.title
    except Exception:
        pass

    plain_message = f"""
Hello {member.full_name},

Your fine payment has been received at Dooars Granthika Library.

Member ID  : {member.member_id}
Book       : {book_title}
Fine Type  : {fine_type_display}
Amount Paid: ₹{fine.amount}
Paid On    : {paid_on_str}

Thank you for clearing your dues.
Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Fine Receipt ✅</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, we confirm that your fine payment at
        <span class="highlight">Dooars Granthika Library</span> has been received and your account updated.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book:</strong> <span>{book_title}</span></p>
            <p><strong>Fine Type:</strong> <span>{fine_type_display}</span></p>
            <p><strong>Amount Paid:</strong> <span>₹{fine.amount}</span></p>
            <p><strong>Paid On:</strong> <span>{paid_on_str}</span></p>
        </div>

        <div class="success-box">
            ✅ <strong>Payment received.</strong> This fine is now marked as <strong>Paid</strong>.
            No further action is required for this charge.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Fine Type</div>
                <div class="info-value" style="font-size:12px;">{fine_type_display}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Amount</div>
                <div class="info-value" style="color:#38a169;">₹{fine.amount}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color:#38a169;">Paid ✓</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>Please retain this email as your receipt. For any queries, contact the library with your Member ID.</p>
        <p style="margin-top: 24px;">Thank you! 🙏</p>
    """

    html_message = build_html_email("Fine Payment Receipt", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣7️⃣ Fine Created / Applied Email  ← NEW
# ==============================
def send_fine_created_email(member, fine, transaction):
    """
    Notify a member when a new fine is applied to their account
    (e.g. lost-book penalty via add_penalty view).

    Args:
        member      – Member model instance
        fine        – Fine model instance (.fine_type, .amount)
        transaction – Transaction instance (.book.title)
    """
    subject = "⚠️ Fine Applied to Your Account | Dooars Granthika"

    fine_type_display = (
        fine.get_fine_type_display()
        if hasattr(fine, 'get_fine_type_display') else str(fine.fine_type)
    )
    created_on_str = (
        fine.created_at.strftime('%d %b %Y')
        if getattr(fine, 'created_at', None) else 'N/A'
    )

    book_title = 'N/A'
    try:
        book_title = transaction.book.title
    except Exception:
        pass

    plain_message = f"""
Hello {member.full_name},

A fine has been applied to your library account at Dooars Granthika.

Member ID  : {member.member_id}
Book       : {book_title}
Fine Type  : {fine_type_display}
Amount     : ₹{fine.amount}
Applied On : {created_on_str}

Please visit the library to clear this fine at your earliest convenience.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Fine Applied ⚠️</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, a new fine has been applied to your account
        at <span class="highlight">Dooars Granthika Library</span>.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book:</strong> <span>{book_title}</span></p>
            <p><strong>Fine Type:</strong> <span>{fine_type_display}</span></p>
            <p><strong>Amount Due:</strong> <span>₹{fine.amount}</span></p>
            <p><strong>Applied On:</strong> <span>{created_on_str}</span></p>
        </div>

        <div class="danger-box">
            💳 <strong>Payment Required:</strong> Please visit the library counter or contact us to
            clear this fine of <strong>₹{fine.amount}</strong> as soon as possible.
            Outstanding fines may restrict your borrowing privileges.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Fine Type</div>
                <div class="info-value" style="font-size:12px;">{fine_type_display}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Amount Due</div>
                <div class="info-value" style="color:#e53e3e;">₹{fine.amount}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color:#e53e3e;">Unpaid</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>If you believe this fine was applied in error, please visit the library with your Member ID so we can review the record.</p>
    """

    html_message = build_html_email("Fine Applied", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣8️⃣ Book Recovered Email  ← NEW
# ==============================
def send_book_recovered_email(member, missing):
    """
    Notify a member that a book previously marked as lost/missing has
    been recovered.

    Args:
        member  – Member model instance
        missing – MissingBook model instance (.book.title, .status,
                  .reported_date).
    """
    subject = "📗 Book Recovered | Dooars Granthika"

    book_title    = 'N/A'
    reported_date = 'N/A'
    try:
        book_title    = missing.book.title
        reported_date = missing.reported_date.strftime('%d %b %Y') if missing.reported_date else 'N/A'
    except Exception:
        pass

    recovered_on_str = timezone.now().strftime('%d %b %Y')

    plain_message = f"""
Hello {member.full_name},

Good news! A book previously reported as lost/missing on your account has been recovered.

Member ID    : {member.member_id}
Book Title   : {book_title}
Reported On  : {reported_date}
Recovered On : {recovered_on_str}

Please visit the library if you have any questions about fines or penalties
related to this book.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Book Recovered! 📗</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, we're pleased to let you know that a book
        previously reported as lost or missing on your account has been <strong>recovered</strong>.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Book Title:</strong> <span>{book_title}</span></p>
            <p><strong>Originally Reported:</strong> <span>{reported_date}</span></p>
            <p><strong>Recovered On:</strong> <span>{recovered_on_str}</span></p>
        </div>

        <div class="success-box">
            ✅ <strong>Book recovered.</strong> The library inventory has been updated to reflect this.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Book</div>
                <div class="info-value" style="font-size:12px;">{book_title[:20]}{'…' if len(book_title) > 20 else ''}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Recovered On</div>
                <div class="info-value" style="font-size:13px;">{recovered_on_str}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color:#38a169;">Recovered ✓</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>If any fines or penalties were applied in relation to this book, please visit the library counter
        and our team will review your account accordingly.</p>
        <p style="margin-top: 24px;">Thank you! 📚</p>
    """

    html_message = build_html_email("Book Recovered", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 1️⃣9️⃣ Daily Fine Reminder Email
# ==============================
def send_fine_daily_reminder(member, unpaid_fines, library_name="Dooars Granthika"):
    """
    Send a daily reminder to a member who has one or more unpaid fines.

    Called automatically by the fine_sync background daemon once per day
    (when FINE_DAILY_REMINDER is True in settings).

    Args:
        member        – Member model instance (.full_name, .member_id, .email)
        unpaid_fines  – QuerySet / list of unpaid Fine instances, each with:
                          .fine_type, .amount, .transaction.book.title
        library_name  – Display name of the library (default: Dooars Granthika)

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not unpaid_fines:
        return False

    subject = f"🔔 Outstanding Fine Reminder | {library_name}"

    # ── Aggregate totals ──────────────────────────────────────────────────
    total_amount = sum(f.amount for f in unpaid_fines)
    fine_count   = len(unpaid_fines)

    # ── Build plain-text fine rows ────────────────────────────────────────
    plain_rows = ""
    for idx, fine in enumerate(unpaid_fines, 1):
        fine_type_label = (
            fine.get_fine_type_display()
            if hasattr(fine, "get_fine_type_display") else str(fine.fine_type)
        )
        try:
            book_title = fine.transaction.book.title
        except Exception:
            book_title = "N/A"
        plain_rows += f"  {idx}. {book_title} — {fine_type_label}: ₹{fine.amount}\n"

    plain_message = f"""
Hello {member.full_name},

This is a friendly reminder that you have {fine_count} outstanding fine(s) on your
library account at {library_name}.

Member ID : {member.member_id}

Outstanding Fines:
{plain_rows}
Total Due : ₹{total_amount}

Please visit the library counter at your earliest convenience to clear your dues.
Unpaid fines may restrict your borrowing privileges.

{library_name}
"""

    # ── Build HTML fine rows ──────────────────────────────────────────────
    html_fine_rows = ""
    for fine in unpaid_fines:
        fine_type_label = (
            fine.get_fine_type_display()
            if hasattr(fine, "get_fine_type_display") else str(fine.fine_type)
        )
        try:
            book_title = fine.transaction.book.title
        except Exception:
            book_title = "N/A"
        html_fine_rows += f"""
            <p>
                <strong>{fine_type_label}:</strong>
                <span>{book_title}</span>
                &nbsp;—&nbsp;
                <span style="color:#e53e3e; font-weight:700;">₹{fine.amount}</span>
            </p>"""

    body_content = f"""
        <p class="greeting">Outstanding Fine Reminder 🔔</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, this is a daily reminder
        from <span class="highlight">{library_name}</span> that you have unpaid fine(s) on your account.
        Please clear your dues at the earliest to avoid any borrowing restrictions.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Total Fines:</strong> <span>{fine_count} unpaid</span></p>
            {html_fine_rows}
            <p style="margin-top:10px; border-top:1px solid #c5d5f0; padding-top:10px;">
                <strong>Total Due:</strong>
                <span style="color:#e53e3e; font-weight:700; font-size:15px;">₹{total_amount}</span>
            </p>
        </div>

        <div class="danger-box">
            ⚠️ <strong>Action Required:</strong> You have <strong>{fine_count} unpaid fine(s)</strong>
            totalling <strong>₹{total_amount}</strong>. Fines continue to accrue daily until cleared.
            Outstanding fines may restrict your borrowing privileges.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Fines Due</div>
                <div class="info-value" style="color:#e53e3e;">{fine_count}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Total Amount</div>
                <div class="info-value" style="color:#e53e3e;">₹{total_amount}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color:#e53e3e;">Unpaid</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>Please visit the library counter with your Member ID to settle these dues.
        If you have already paid, kindly disregard this reminder.</p>
        <p style="margin-top: 24px;">Thank you for being a valued member! 📚</p>
    """

    html_message = build_html_email("Outstanding Fine Reminder", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)

# ==============================
# 2️⃣0️⃣ Staff Credentials Email
# ==============================
def send_staff_credentials_email(staff_member, username, password, added_by_name=None):
    """
    Send login credentials to a newly created staff member.

    Called from superuser/views.py → staff_add() immediately after the
    Django User + StaffMember records are saved.

    Args:
        staff_member   – StaffMember model instance
                         (.full_name, .email, .employee_id,
                          .primary_role.name, .primary_role.level,
                          .primary_role.get_department_display())
        username       – The Django User username just created
        password       – The plain-text password (before hashing) — only
                         available at creation time, never stored
        added_by_name  – Display name of the person who created the account
                         (e.g. "Superuser" or the manager's full_name)

    Returns:
        True if the email was dispatched to the background thread,
        False if the staff member has no email address.
    """
    recipient = getattr(staff_member, 'email', None)
    if not recipient:
        logger.warning(
            "send_staff_credentials_email: staff member %s has no email — skipping.",
            staff_member.employee_id,
        )
        return False

    full_name    = staff_member.full_name
    employee_id  = staff_member.employee_id
    role_name    = staff_member.primary_role.name
    role_level   = staff_member.primary_role.level
    department   = staff_member.primary_role.get_department_display()
    added_by     = added_by_name or "Superuser"
    joined_date  = timezone.now().strftime('%d %b %Y')

    subject = f"🎉 Welcome to the Team — Your Login Credentials | Dooars Granthika"

    plain_message = f"""
Hello {full_name},

Welcome to the Dooars Granthika team! Your staff account has been created.

Your Login Credentials
──────────────────────
Username    : {username}
Password    : {password}
Employee ID : {employee_id}
Role        : {role_name} (Level {role_level})
Department  : {department}

⚠  Please log in and change your password immediately.
   Never share your credentials with anyone.

Added by    : {added_by}
Account created on : {joined_date}

Dooars Granthika — Internal Staff Portal
"""

    body_content = f"""
        <p class="greeting">Welcome to the Team! 🎉</p>
        <p>Hello <span class="highlight">{full_name}</span>, your staff account at
        <span class="highlight">Dooars Granthika</span> has been set up by
        <span class="highlight">{added_by}</span>.
        Use the credentials below to log in to the staff portal.</p>

        <div class="credential-box">
            <p><strong>Username:</strong>    <span>{username}</span></p>
            <p><strong>Password:</strong>    <span>{password}</span></p>
            <p><strong>Employee ID:</strong> <span>{employee_id}</span></p>
            <p><strong>Role:</strong>        <span>{role_name} — Level {role_level}</span></p>
            <p><strong>Department:</strong>  <span>{department}</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Action Required:</strong> Please log in immediately and change your
            password from the profile settings. Never share your credentials with anyone.
        </div>

        <div class="danger-box">
            🔒 <strong>Security Notice:</strong> This message contains sensitive login
            information. If you did not expect this email, contact the system administrator
            at once.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Employee ID</div>
                <div class="info-value">{employee_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Role Level</div>
                <div class="info-value">L{role_level}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Department</div>
                <div class="info-value" style="font-size:12px;">{department}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Joined</div>
                <div class="info-value" style="font-size:12px;">{joined_date}</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>If you have any questions about your role or access permissions, please reach out
        to your line manager or the platform administrator.</p>
        <p style="margin-top:24px;">Welcome aboard — let's build something great together! 🚀</p>
    """

    html_message = build_html_email("Staff Account Credentials", body_content)
    return send_basic_email(subject, plain_message, html_message, recipient)