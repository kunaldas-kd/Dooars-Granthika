"""subscriptions/forms.py"""

from django import forms
from .models import Plan


class PlanForm(forms.ModelForm):
    class Meta:
        model  = Plan
        fields = [
            "name", "slug", "tier", "tagline", "description",
            "price", "billing_cycle", "duration_days", "is_free",
            "max_members", "max_books", "max_book_copies", "max_staff",
            "allow_reports", "allow_export", "allow_sms",
            "allow_email_reminders", "allow_api_access",
            "allow_custom_branding", "allow_advance_booking",
            "priority_support",
            "is_popular", "is_active", "display_order",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "tagline":     forms.TextInput(attrs={"placeholder": "One-line pitch for this plan"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_free") and cleaned.get("price", 0) > 0:
            raise forms.ValidationError("A free plan must have a price of ₹0.")
        return cleaned