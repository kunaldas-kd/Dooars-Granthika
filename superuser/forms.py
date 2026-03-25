"""
superuser/forms.py
==================
Forms for the Dooars Granthika SaaS Superuser Dashboard.
All forms align with the REAL accounts.Library / accounts.Subscription models.
"""

from django import forms
from django.utils.text import slugify
from .models import Plan, Invoice, BillingTransaction


# ─────────────────────────────────────────────
#  Plan Forms
# ─────────────────────────────────────────────

PLAN_SLUG_CHOICES = [
    ('basic',      'Basic'),
    ('silver',     'Silver'),
    ('gold',       'Gold'),
    ('pro',        'Pro'),
    ('enterprise', 'Enterprise'),
]


class PlanForm(forms.ModelForm):
    """Create or edit a Plan definition."""

    class Meta:
        model  = Plan
        fields = [
            'name', 'slug', 'description', 'price', 'billing_cycle',
            'trial_days', 'max_books', 'max_members', 'storage_gb',
            'features_text', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Pro, Enterprise…',
            }),
            'slug': forms.Select(
                choices=PLAN_SLUG_CHOICES,
                attrs={'class': 'form-control'},
            ),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Describe what this plan offers…',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': '0.00',
                'step': '0.01', 'min': '0',
            }),
            'billing_cycle': forms.Select(attrs={'class': 'form-control'}),
            'trial_days': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0',
            }),
            'max_books': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for unlimited',
            }),
            'max_members': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for unlimited',
            }),
            'storage_gb': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 50',
            }),
            'features_text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Unlimited patrons\nAdvanced analytics\nPriority support',
            }),
            'is_active': forms.CheckboxInput(attrs={'id': 'is_active'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price


class PlanDeleteForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label='I understand this action cannot be undone.',
        error_messages={'required': 'You must confirm the deletion.'},
    )


# ─────────────────────────────────────────────
#  Library Filter
# ─────────────────────────────────────────────

class LibraryFilterForm(forms.Form):
    PLAN_CHOICES = [('', 'All Plans')] + PLAN_SLUG_CHOICES

    STATUS_CHOICES = [
        ('',        'All'),
        ('active',  'Active'),
        ('expired', 'Expired'),
    ]

    plan   = forms.ChoiceField(
                choices=PLAN_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    status = forms.ChoiceField(
                choices=STATUS_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    q      = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'filter-search-input',
                    'placeholder': 'Search name, code or email…',
                }))


class LibrarySuspendForm(forms.Form):
    """Reason when suspending a library or subscription."""
    reason = forms.CharField(
        required=False,
        label='Reason (optional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'e.g. Outstanding payment, policy violation…',
        }),
    )


# ─────────────────────────────────────────────
#  Subscription Filter / Actions
# ─────────────────────────────────────────────

class SubscriptionFilterForm(forms.Form):
    PLAN_CHOICES = [('', 'All Plans')] + PLAN_SLUG_CHOICES
    STATUS_CHOICES = [
        ('',        'All'),
        ('active',  'Active'),
        ('expired', 'Expired'),
    ]

    plan   = forms.ChoiceField(
                choices=PLAN_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    status = forms.ChoiceField(
                choices=STATUS_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    q      = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'filter-search-input',
                    'placeholder': 'Search library name or code…',
                }))


class SubscriptionActivateForm(forms.Form):
    """No extra fields needed — POST is enough for activate."""
    pass


class CancelSubscriptionForm(forms.Form):
    REASON_CHOICES = [
        ('',                '— Select reason —'),
        ('non_payment',     'Non-payment'),
        ('library_request', 'Library request'),
        ('policy_violation','Policy violation'),
        ('plan_downgrade',  'Plan downgrade'),
        ('other',           'Other'),
    ]
    reason = forms.ChoiceField(
        choices=REASON_CHOICES, required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    notes  = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2,
            'placeholder': 'Additional notes…',
        }),
    )


# ─────────────────────────────────────────────
#  Billing Transaction Filter
# ─────────────────────────────────────────────

class BillingTransactionFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All')] + list(BillingTransaction.STATUS_CHOICES)
    TYPE_CHOICES   = [('', 'All Types')] + list(BillingTransaction.TYPE_CHOICES)

    status = forms.ChoiceField(
                choices=STATUS_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    type   = forms.ChoiceField(
                choices=TYPE_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    q      = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'filter-search-input',
                    'placeholder': 'Search ref or library…',
                }))


# ─────────────────────────────────────────────
#  Invoice Filter
# ─────────────────────────────────────────────

class InvoiceFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All')] + list(Invoice.STATUS_CHOICES)

    status = forms.ChoiceField(
                choices=STATUS_CHOICES, required=False,
                widget=forms.Select(attrs={'class': 'filter-select'}))
    q      = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'filter-search-input',
                    'placeholder': 'Invoice # or library…',
                }))
