"""
transactions/forms.py

All forms used by the transactions app.

Key design note
───────────────
MarkFinePaidForm.fine_id is a CharField (not IntegerField) because it holds
the human-readable Fine.fine_id column value (e.g. "DGDOOFN032512345")
from the dooars_granthika_db.finance_fine table — NOT the integer primary key.

The view (mark_fine_paid) looks up the Fine with:
    Fine.objects.for_library(library).get(fine_id=cd["fine_id"])

and the template sets the field via:
    data-fine-id="{{ fine.fine_id }}"   ← string, e.g. DGDOOFN032512345
"""

from __future__ import annotations

from datetime import date

from django import forms


# ─────────────────────────────────────────────────────────────────────────────
# Issue Book Form
# ─────────────────────────────────────────────────────────────────────────────

class IssueBookForm(forms.Form):
    """
    Accepts the hidden member/book/copy PKs submitted by the issue_book
    page (populated by AJAX autocomplete widgets).
    """

    member    = forms.IntegerField(widget=forms.HiddenInput)
    book      = forms.IntegerField(widget=forms.HiddenInput)
    book_copy = forms.IntegerField(widget=forms.HiddenInput, required=False)
    issue_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )

    def __init__(self, *args, library=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.library = library

    def clean_member(self):
        pk = self.cleaned_data["member"]
        from members.models import Member
        try:
            return Member.objects.get(pk=pk, owner=self.library.user)
        except Member.DoesNotExist:
            raise forms.ValidationError("Member not found.")

    def clean_book(self):
        pk = self.cleaned_data["book"]
        from books.models import Book
        try:
            return Book.objects.get(pk=pk, owner=self.library.user)
        except Book.DoesNotExist:
            raise forms.ValidationError("Book not found.")

    def clean_book_copy(self):
        pk = self.cleaned_data.get("book_copy")
        if not pk:
            return None
        from books.models import BookCopy
        try:
            return BookCopy.objects.get(pk=pk)
        except BookCopy.DoesNotExist:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Return Book Form
# ─────────────────────────────────────────────────────────────────────────────

class ReturnBookForm(forms.Form):
    CONDITION_CHOICES = [
        ("good",    "Good"),
        ("fair",    "Fair"),
        ("damaged", "Damaged"),
        ("lost",    "Lost"),
    ]

    transaction_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    return_date    = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )
    condition = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        initial="good",
        required=False,
    )
    damage_charge = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
        initial=0,
    )
    return_notes  = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )
    fine_paid_now = forms.BooleanField(required=False)


# ─────────────────────────────────────────────────────────────────────────────
# Mark Fine Paid Form
# ─────────────────────────────────────────────────────────────────────────────

class MarkFinePaidForm(forms.Form):
    """
    IMPORTANT: fine_id is a CharField that holds the human-readable Fine.fine_id
    value (e.g. "DGDOOFN032512345") from the finance_fine table — NOT the
    integer primary key.  The template populates it from {{ fine.fine_id }}.
    """

    fine_id = forms.CharField(
        max_length=20,
        widget=forms.HiddenInput,
    )
    payment_method = forms.ChoiceField(
        choices=[
            ("cash",  "Cash"),
            ("upi",   "UPI"),
            ("card",  "Card"),
            ("other", "Other"),
        ],
        initial="cash",
    )
    payment_ref = forms.CharField(
        max_length=100,
        required=False,
    )

    def clean_fine_id(self):
        val = self.cleaned_data.get("fine_id", "").strip()
        if not val:
            raise forms.ValidationError("Fine ID is required.")
        return val


# ─────────────────────────────────────────────────────────────────────────────
# Mark Lost Form
# ─────────────────────────────────────────────────────────────────────────────

class MarkLostForm(forms.Form):
    REASON_CHOICES = [
        ("lost",     "Book Lost"),
        ("damaged",  "Severely Damaged"),
        ("missing",  "Missing - Not Returned"),
        ("other",    "Other"),
    ]

    transaction_id = forms.IntegerField(widget=forms.HiddenInput)
    reason         = forms.ChoiceField(choices=REASON_CHOICES, required=False)
    book_price     = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        label="Replacement / Penalty Amount (₹)",
        help_text="Pre-filled from book catalogue price. Adjust if needed.",
    )
    fine_paid_now  = forms.BooleanField(
        required=False,
        label="Mark penalty as collected now",
    )
    notes          = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Add Penalty Form
# ─────────────────────────────────────────────────────────────────────────────

class AddPenaltyForm(forms.Form):
    REASON_CHOICES = [
        ("lost",     "Book Lost"),
        ("damaged",  "Severely Damaged"),
        ("missing",  "Missing - Not Returned"),
        ("other",    "Other"),
    ]

    missing_id     = forms.IntegerField(widget=forms.HiddenInput)
    penalty_amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    penalty_reason = forms.ChoiceField(choices=REASON_CHOICES, required=False)
    notes          = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
    )