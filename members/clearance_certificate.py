"""
members/clearance_certificate.py
─────────────────────────────────
ReportLab-based library clearance certificate generator.

Ported from the standalone LibNexa desktop script (Library_clearence.py) to
work directly with the Django Member model and the multi-tenant Library model.

Usage (from views.py):
    from .clearance_certificate import build_clearance_pdf

    buf, filename = build_clearance_pdf(member, library)
    response = HttpResponse(buf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

Dependencies:
    pip install reportlab

If ReportLab is not installed the function raises ImportError — the calling
view should catch this and fall back gracefully.
"""

import io
import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, Table, TableStyle,
)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _resource_path(relative_path: str) -> str:
    """Resolve path to a bundled resource (works with PyInstaller too)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def _add_footer(canvas, doc):
    """
    Draw the 'LibNexa' logo + text in the bottom-right corner of every page.
    Mirrors the original add_footer() exactly.
    """
    page_width, _ = A4
    logo_width    = 40
    footer_y      = 0.2 * inch
    right_margin  = 0.4 * inch
    spacing       = 4
    text          = "Dooars Granthika"

    canvas.saveState()
    try:
        logo_path  = _resource_path("IMG/logo2.png")
        canvas.setFont("Helvetica-Bold", 10)
        text_width = canvas.stringWidth(text, "Helvetica-Bold", 10)
        logo_x     = page_width - logo_width - spacing - text_width - right_margin
        text_x     = logo_x + logo_width + spacing
        text_y     = footer_y + logo_width / 2.5

        if os.path.exists(logo_path):
            canvas.drawImage(
                logo_path, logo_x, footer_y,
                width=logo_width, height=logo_width,
                mask="auto", preserveAspectRatio=True,
            )

        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(text_x, text_y, text)

    except Exception as exc:
        # Never let a footer error crash the PDF build
        print(f"[clearance_certificate] footer warning: {exc}")
    finally:
        canvas.restoreState()


def _cert_number(member_id: str, institution_name: str, role: str) -> str:
    """
    Generate a certificate number in the same format as the original:
        <INST_SHORT>/<PREFIX>/<YEAR>/<SERIAL>

    Uses the member_id's trailing 4 characters as the serial component so
    each certificate is deterministic (no DB sequence needed).
    """
    short   = institution_name[:3].upper() if institution_name else "LIB"
    prefix  = "LIBT" if role == "teacher" else "LIB"
    year    = datetime.now().year
    serial  = (member_id or "0001")[-4:].upper()
    return f"{short}/{prefix}/{year}/{serial}"


def _student_body(
    member_name: str,
    member_id: str,
    department: str,
    institution_name: str,
    purpose: str,
    show_dues_line: bool = True,
) -> str:
    """
    Certificate body paragraph for Student / General members.
    `show_dues_line` mirrors the original `Payment Functionality` toggle.
    """
    dues_line = (
        "As per the library records, there are no dues pending against his/her name.<br/><br/>"
        if show_dues_line else ""
    )
    return (
        f"This is to certify that Mr./Ms. <b>{member_name}</b>, "
        f"Registration No.: <b>{member_id}</b>, a member of <b>{department}</b> "
        f"at <b>{institution_name}</b>, has returned all the books and other library "
        f"materials borrowed from the {institution_name} Library.<br/><br/>"
        f"{dues_line}"
        f"This certificate is issued upon request for the purpose of <b>{purpose}</b>.<br/><br/>"
        f"We wish him/her success in future endeavors."
    )


def _teacher_body(
    member_name: str,
    member_id: str,
    department: str,
    designation: str,
    institution_name: str,
    purpose: str,
) -> str:
    """
    Certificate body paragraph for Teacher / Faculty members.
    Mirrors TeacherBodytext() in the original.
    """
    return (
        f"This is to certify that Mr./Ms. <b>{member_name}</b>, "
        f"Employee ID: <b>{member_id}</b>, working as <b>{designation}</b> "
        f"in the <b>{department}</b> department of <b>{institution_name}</b>, "
        f"has returned all the books and other library materials borrowed from "
        f"the {institution_name} Library.<br/><br/>"
        f"As per the library records, there are no dues pending against his/her name.<br/><br/>"
        f"This certificate is issued upon request for the purpose of <b>{purpose}</b>.<br/><br/>"
        f"We wish him/her success in future endeavors."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def build_clearance_pdf(member, library=None) -> tuple[bytes, str]:
    """
    Generate a library clearance certificate PDF for *member* and return
    ``(pdf_bytes, suggested_filename)``.

    Parameters
    ----------
    member  : members.models.Member
        Must have clearance_status == 'cleared'.
    library : optional Library model instance
        If provided, used for institution name, address, email, etc.
        Falls back to sensible defaults when None.

    Returns
    -------
    pdf_bytes : bytes
    filename  : str   e.g. "clearance_STU-1-20240101120000.pdf"

    Raises
    ------
    ImportError   if ReportLab is not installed.
    ValueError    if the member has not been cleared.
    """

    if member.clearance_status != "cleared":
        raise ValueError(
            f"Member {member.member_id} has not been cleared yet."
        )

    # ── Resolve institution details ───────────────────────────────────────────
    if library is not None:
        institution_name  = getattr(library, "name", "Library")
        institution_email = getattr(library, "email", "")
        address           = getattr(library, "address", "")
        district          = getattr(library, "district", "")
        state             = getattr(library, "state", "")
        country           = getattr(library, "country", "India")
    else:
        institution_name  = "Library"
        institution_email = ""
        address = district = state = ""
        country = "India"

    # Build single-line address, skipping empty parts
    addr_parts = [p.title() for p in [address, district, state, country] if p.strip()]
    institution_address = ", ".join(addr_parts) if addr_parts else "India"

    # ── Member details ────────────────────────────────────────────────────────
    dept_name   = member.department.name if member.department else "N/A"
    designation = member.specialization or "Faculty"   # TeacherMemberForm stores designation here
    role        = member.role                           # 'student' | 'teacher' | 'general'

    purpose_map = {
        "student": "Final Semester Clearance",
        "teacher": "Faculty Resignation / Transfer",
        "general": "Library Membership Clearance",
    }
    purpose = purpose_map.get(role, "Library Clearance")

    cert_no    = _cert_number(member.member_id, institution_name, role)
    date_today = datetime.today().strftime("%d/%m/%Y")
    filename   = f"clearance_{member.member_id}.pdf"

    # ── Body text (role-aware) ─────────────────────────────────────────────────
    if role == "teacher":
        body_html = _teacher_body(
            member.full_name, member.member_id, dept_name,
            designation, institution_name, purpose,
        )
    else:
        body_html = _student_body(
            member.full_name, member.member_id, dept_name,
            institution_name, purpose, show_dues_line=True,
        )

    # ── Styles ────────────────────────────────────────────────────────────────
    base_styles  = getSampleStyleSheet()
    center_style = ParagraphStyle(
        "Center", parent=base_styles["Normal"], alignment=TA_CENTER,
    )
    bold_center  = ParagraphStyle(
        "BoldCenter", parent=center_style,
        fontName="Helvetica-Bold", fontSize=14,
    )
    normal_center = ParagraphStyle(
        "NormalCenter", parent=center_style, fontSize=11,
    )
    justify = ParagraphStyle(
        "JustifiedIndented", parent=base_styles["Normal"],
        alignment=TA_JUSTIFY, firstLineIndent=20, fontSize=11, leading=16,
    )
    right_style = ParagraphStyle(
        "RightAligned", parent=base_styles["Normal"],
        alignment=TA_RIGHT, fontSize=11,
    )
    title_style = ParagraphStyle(
        "CertTitle", parent=base_styles["Normal"],
        fontName="Helvetica-Bold", fontSize=13,
        alignment=TA_CENTER, spaceAfter=12,
    )
    small_gray = ParagraphStyle(
        "SmallGray", parent=base_styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#6b7280"),
        alignment=TA_CENTER,
    )

    # ── Build elements list (mirrors original generate_library_clearance_certificate) ──
    elements = [
        # Institution header
        Paragraph(institution_name.upper(), bold_center),
        Spacer(1, 0.06 * inch),
        Paragraph(institution_address, normal_center),
    ]

    if institution_email:
        elements.append(Paragraph(f"Email: {institution_email.lower()}", normal_center))

    elements += [
        Spacer(1, 0.1 * inch),
        HRFlowable(width="100%", thickness=1, color=colors.black),
        Spacer(1, 0.3 * inch),
    ]

    # Cert number + date row (mirrors cert_table in original)
    cert_table = Table(
        [[f"Certificate No.: {cert_no}", f"Date: {date_today}"]],
        colWidths=[3.5 * inch, 3.5 * inch],
    )
    cert_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (0, 0), "LEFT"),
        ("ALIGN",         (1, 0), (1, 0), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE",      (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(cert_table)
    elements.append(Spacer(1, 1.5 * inch))

    # Certificate title + body
    elements.append(Paragraph("Library Clearance Certificate", title_style))
    elements.append(Paragraph(body_html.strip(), justify))
    elements.append(Spacer(1, 1.3 * inch))

    # Librarian signature block (right-aligned, mirrors original)
    elements += [
        Paragraph("Librarian<br/>(Signature &amp; Seal)", right_style),
        Spacer(1, 0.2 * inch),
        Paragraph("Name: ____________________", right_style),
        Spacer(1, 0.06 * inch),
        Paragraph("Designation: _______________", right_style),
        Spacer(1, 0.06 * inch),
        Paragraph(f"Date: {date_today}", right_style),
    ]

    # Optional: cleared-by note at bottom
    if member.cleared_by:
        cleared_by_name = (
            member.cleared_by.get_full_name()
            or member.cleared_by.username
        )
        elements += [
            Spacer(1, 0.4 * inch),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")),
            Spacer(1, 0.1 * inch),
            Paragraph(
                f"Digitally recorded — cleared by: {cleared_by_name} "
                f"on {member.clearance_date.strftime('%d %B %Y') if member.clearance_date else date_today}",
                small_gray,
            ),
        ]

    # ── Render to an in-memory buffer ─────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=inch, rightMargin=inch,
        topMargin=inch, bottomMargin=inch,
    )
    doc.build(elements, onFirstPage=_add_footer, onLaterPages=_add_footer)
    buf.seek(0)

    return buf.read(), filename