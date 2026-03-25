"""
superuser/models.py
====================
Superuser dashboard models for the Dooars Granthika SaaS platform.

The real Library tenant lives in accounts.models.Library.
The real subscription record lives in accounts.models.Subscription.

This app adds:
  Plan              — SaaS pricing tier definition (slug mirrors accounts.Subscription.plan)
  Invoice           — billing document per period, linked to accounts.Library
  BillingTransaction— payment event (distinct from transactions.Transaction = book loans)
  ActivityLog       — immutable superuser audit trail
"""

from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator


# ─────────────────────────────────────────────
#  Plan
# ─────────────────────────────────────────────

class Plan(models.Model):
    """
    SaaS pricing tier.  slug must match accounts.Subscription.PLAN_CHOICES values
    (basic | silver | gold | pro | enterprise) so the superuser can cross-reference
    which accounts.Subscription rows belong to which Plan definition.
    """

    BILLING_MONTHLY   = 'monthly'
    BILLING_QUARTERLY = 'quarterly'
    BILLING_ANNUAL    = 'annual'
    BILLING_CHOICES = [
        (BILLING_MONTHLY,   'Monthly'),
        (BILLING_QUARTERLY, 'Quarterly'),
        (BILLING_ANNUAL,    'Annual'),
    ]

    # Mirrors accounts.Subscription.PLAN_CHOICES
    SLUG_BASIC      = 'basic'
    SLUG_SILVER     = 'silver'
    SLUG_GOLD       = 'gold'
    SLUG_PRO        = 'pro'
    SLUG_ENTERPRISE = 'enterprise'

    name          = models.CharField(max_length=100, unique=True)
    slug          = models.SlugField(
                        max_length=20, unique=True,
                        help_text='Must match accounts.Subscription plan value '
                                  '(basic|silver|gold|pro|enterprise)')
    description   = models.TextField(blank=True)
    price         = models.DecimalField(
                        max_digits=10, decimal_places=2,
                        validators=[MinValueValidator(Decimal('0.00'))],
                        help_text='Monthly price in INR')
    billing_cycle = models.CharField(
                        max_length=20, choices=BILLING_CHOICES,
                        default=BILLING_MONTHLY)
    trial_days    = models.PositiveIntegerField(default=0)

    # Resource limits
    max_books     = models.PositiveIntegerField(
                        null=True, blank=True,
                        help_text='Max BookCopy records. Blank = unlimited')
    max_members   = models.PositiveIntegerField(
                        null=True, blank=True,
                        help_text='Max Member records. Blank = unlimited')
    storage_gb    = models.PositiveIntegerField(
                        null=True, blank=True,
                        help_text='Storage cap in GB. Blank = unlimited')

    features_text = models.TextField(blank=True, help_text='One feature per line')
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f'{self.name} (₹{self.price}/{self.billing_cycle})'

    # ── Template helpers ─────────────────────────────────────
    @property
    def features_list(self):
        return [f.strip() for f in self.features_text.splitlines() if f.strip()]

    # max_patrons is an alias used by templates inherited from the earlier build
    @property
    def max_patrons(self):
        return self.max_members

    # ── Live counts from accounts app ────────────────────────
    @property
    def active_subscription_count(self):
        try:
            from accounts.models import Subscription as AccSub
            return AccSub.objects.filter(plan=self.slug, is_active=True).count()
        except Exception:
            return 0

    @property
    def mrr(self):
        count = self.active_subscription_count
        if not count:
            return Decimal('0')
        if self.billing_cycle == self.BILLING_ANNUAL:
            return (self.price / 12) * count
        if self.billing_cycle == self.BILLING_QUARTERLY:
            return (self.price / 3) * count
        return self.price * count


# ─────────────────────────────────────────────
#  Invoice
# ─────────────────────────────────────────────

class Invoice(models.Model):
    """Billing document for one subscription period."""

    STATUS_PAID    = 'paid'
    STATUS_UNPAID  = 'unpaid'
    STATUS_OVERDUE = 'overdue'
    STATUS_VOID    = 'void'
    STATUS_CHOICES = [
        (STATUS_PAID,    'Paid'),
        (STATUS_UNPAID,  'Unpaid'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_VOID,    'Void'),
    ]

    # FKs to the real models in accounts
    library               = models.ForeignKey(
                                'accounts.Library',
                                on_delete=models.CASCADE,
                                related_name='billing_invoices')
    accounts_subscription = models.ForeignKey(
                                'accounts.Subscription',
                                on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='billing_invoices')

    # Snapshot fields (preserved even if plan changes)
    plan_name    = models.CharField(max_length=50, blank=True)
    library_name = models.CharField(max_length=200, blank=True)

    number       = models.CharField(max_length=30, unique=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                     default=STATUS_UNPAID)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    period_start = models.DateField()
    period_end   = models.DateField()
    issued_date  = models.DateField(default=timezone.now)
    due_date     = models.DateField()
    paid_date    = models.DateField(null=True, blank=True)

    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_date']
        verbose_name        = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f'{self.number} — {self.library_name or self.library.library_name}'

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self._generate_number()
        # Snapshot name fields on first save
        if not self.library_name and self.library_id:
            self.library_name = self.library.library_name
        if not self.plan_name and self.accounts_subscription_id:
            self.plan_name = self.accounts_subscription.plan
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        year = timezone.now().year
        last = Invoice.objects.filter(
            number__startswith=f'INV-{year}-'
        ).order_by('-number').first()
        seq = 1
        if last:
            try:
                seq = int(last.number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f'INV-{year}-{seq:04d}'

    @property
    def total(self):
        return self.amount + self.tax_amount

    def mark_overdue(self):
        if self.status == self.STATUS_UNPAID and self.due_date < timezone.now().date():
            self.status = self.STATUS_OVERDUE
            self.save(update_fields=['status', 'updated_at'])


# ─────────────────────────────────────────────
#  BillingTransaction
# ─────────────────────────────────────────────

class BillingTransaction(models.Model):
    """
    SaaS payment event.
    Named BillingTransaction to avoid collision with
    transactions.Transaction (= book-loan records).
    """

    STATUS_PAID     = 'paid'
    STATUS_PENDING  = 'pending'
    STATUS_FAILED   = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        (STATUS_PAID,     'Paid'),
        (STATUS_PENDING,  'Pending'),
        (STATUS_FAILED,   'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    TYPE_INITIAL  = 'initial'
    TYPE_RENEWAL  = 'renewal'
    TYPE_UPGRADE  = 'upgrade'
    TYPE_REFUND   = 'refund'
    TYPE_MANUAL   = 'manual'
    TYPE_CHOICES = [
        (TYPE_INITIAL, 'Initial'),
        (TYPE_RENEWAL, 'Renewal'),
        (TYPE_UPGRADE, 'Upgrade'),
        (TYPE_REFUND,  'Refund'),
        (TYPE_MANUAL,  'Manual'),
    ]

    library               = models.ForeignKey(
                                'accounts.Library',
                                on_delete=models.CASCADE,
                                related_name='billing_transactions')
    accounts_subscription = models.ForeignKey(
                                'accounts.Subscription',
                                on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='billing_transactions')
    invoice               = models.ForeignKey(
                                Invoice,
                                on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='billing_transactions')

    # Snapshot fields
    plan_name    = models.CharField(max_length=50, blank=True)
    library_name = models.CharField(max_length=200, blank=True)

    reference        = models.CharField(max_length=30, unique=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                         default=STATUS_PENDING)
    type             = models.CharField(max_length=20, choices=TYPE_CHOICES,
                                         default=TYPE_RENEWAL)
    amount           = models.DecimalField(max_digits=10, decimal_places=2)
    currency         = models.CharField(max_length=3, default='INR')
    gateway          = models.CharField(max_length=50, default='Razorpay',
                                         help_text='e.g. Razorpay, Stripe, Manual')
    gateway_reference = models.CharField(max_length=200, blank=True)
    payment_method   = models.CharField(max_length=100, blank=True)

    subtotal     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gateway_fee  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    period_start    = models.DateField(null=True, blank=True)
    period_end      = models.DateField(null=True, blank=True)
    failure_code    = models.CharField(max_length=100, blank=True)
    failure_message = models.TextField(blank=True)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)
    notes           = models.TextField(blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Billing Transaction'
        verbose_name_plural = 'Billing Transactions'
        indexes = [
            models.Index(fields=['library', 'status']),
            models.Index(fields=['library', 'created_at']),
        ]

    def __str__(self):
        return f'{self.reference} — ₹{self.amount} [{self.status}]'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        if not self.subtotal:
            self.subtotal = self.amount
        if not self.net_amount:
            self.net_amount = self.amount - self.gateway_fee
        if not self.library_name and self.library_id:
            self.library_name = self.library.library_name
        if not self.plan_name and self.accounts_subscription_id:
            self.plan_name = self.accounts_subscription.plan
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference():
        import uuid
        now = timezone.now()
        suffix = uuid.uuid4().hex[:6].upper()
        return f'TXN-{now.strftime("%Y%m")}-{suffix}'


# ─────────────────────────────────────────────
#  ActivityLog
# ─────────────────────────────────────────────

class ActivityLog(models.Model):
    """Immutable superuser audit trail — insert only, never update."""

    model_name = models.CharField(max_length=80)
    object_id  = models.PositiveIntegerField(default=0)
    action     = models.CharField(max_length=100)
    user       = models.ForeignKey(
                     settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name='superuser_activity_logs')
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Direct FKs for efficient filtering (may be null when logging Plan/Invoice actions)
    library               = models.ForeignKey(
                                'accounts.Library',
                                on_delete=models.CASCADE,
                                null=True, blank=True,
                                related_name='superuser_activity_logs')
    accounts_subscription = models.ForeignKey(
                                'accounts.Subscription',
                                on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='superuser_activity_logs')

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return (
            f'[{self.created_at:%Y-%m-%d %H:%M}] '
            f'{self.model_name}#{self.object_id} — {self.action}'
        )

    @classmethod
    def log(cls, *, action, user=None, notes='',
            library=None, subscription=None,
            model_name='', object_id=0):
        """
        Convenience factory.

        Examples
        --------
        ActivityLog.log(action='activated', library=lib, user=request.user)
        ActivityLog.log(action='plan_created', model_name='Plan', object_id=plan.pk, user=u)
        ActivityLog.log(action='suspended', subscription=sub, user=request.user, notes=reason)
        """
        if library is None and subscription is not None:
            library = getattr(subscription, 'library', None)

        if not model_name:
            ref_obj = library or subscription
            if ref_obj:
                model_name = type(ref_obj).__name__
                object_id  = ref_obj.pk

        cls.objects.create(
            model_name=model_name,
            object_id=object_id,
            action=action,
            user=user,
            notes=notes,
            library=library,
            accounts_subscription=subscription,
        )


# ─────────────────────────────────────────────
#  Staff Hierarchy
# ─────────────────────────────────────────────

class StaffRole(models.Model):
    """
    Defines a named role in the company hierarchy.
    level: lower number = higher authority (0 = Founder/CEO, 1 = CTO, etc.)
    Superuser can create/edit roles; only roles above yours can be assigned by you.
    """
    DEPT_CHOICES = [
        ('executive',  'Executive'),
        ('tech',       'Technology'),
        ('sales',      'Sales & Marketing'),
        ('support',    'Support'),
        ('operations', 'Operations'),
        ('qa',         'Quality Assurance'),
        ('design',     'Design'),
        ('finance',    'Finance'),
    ]

    name        = models.CharField(max_length=100, unique=True)
    slug        = models.SlugField(max_length=60, unique=True)
    department  = models.CharField(max_length=30, choices=DEPT_CHOICES, default='tech')
    level       = models.PositiveSmallIntegerField(
                      default=10,
                      help_text='Hierarchy level: 0=CEO, 1=CTO/VP, 2=Head, 3=Senior, 4=Junior')
    description = models.TextField(blank=True)
    permissions = models.JSONField(
                      default=dict, blank=True,
                      help_text='Dict of permission flags e.g. {"can_add_staff": true}')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['level', 'name']
        verbose_name        = 'Staff Role'
        verbose_name_plural = 'Staff Roles'

    def __str__(self):
        return f'{self.name} (L{self.level})'

    @property
    def can_add_staff(self):
        return self.permissions.get('can_add_staff', self.level <= 3)

    @property
    def can_view_billing(self):
        return self.permissions.get('can_view_billing', self.level <= 2)

    @property
    def can_manage_plans(self):
        return self.permissions.get('can_manage_plans', self.level <= 1)


class StaffMember(models.Model):
    """
    A company staff member linked to a Django User.
    One person can hold multiple StaffRoles (primary + secondary).
    added_by: the StaffMember (or None for superuser) who created this record.
    """
    STATUS_ACTIVE    = 'active'
    STATUS_INACTIVE  = 'inactive'
    STATUS_ON_LEAVE  = 'on_leave'
    STATUS_CHOICES = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_ON_LEAVE, 'On Leave'),
    ]

    user          = models.OneToOneField(
                        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                        related_name='staff_profile')
    primary_role  = models.ForeignKey(
                        StaffRole, on_delete=models.PROTECT,
                        related_name='primary_staff')
    secondary_roles = models.ManyToManyField(
                        StaffRole, blank=True,
                        related_name='secondary_staff')
    added_by      = models.ForeignKey(
                        'self', on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='added_staff',
                        help_text='Who created this staff member')

    employee_id   = models.CharField(max_length=20, unique=True, blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    avatar_color  = models.CharField(max_length=7, default='#3d6bff',
                                      help_text='Hex color for avatar placeholder')
    bio           = models.TextField(blank=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                      default=STATUS_ACTIVE)
    joined_date   = models.DateField(default=timezone.now)
    notes         = models.TextField(blank=True,
                                      help_text='Private notes visible only to superuser')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['primary_role__level', 'user__first_name']
        verbose_name        = 'Staff Member'
        verbose_name_plural = 'Staff Members'

    def __str__(self):
        return f'{self.full_name} — {self.primary_role.name}'

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self._generate_employee_id()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_employee_id():
        import uuid
        return 'EMP-' + uuid.uuid4().hex[:6].upper()

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def hierarchy_level(self):
        return self.primary_role.level

    def can_add_staff_at_level(self, target_level):
        """
        A staff member can only add staff whose level is strictly greater
        (lower authority) than their own primary role level.
        Superuser can add anyone.
        """
        return self.primary_role.can_add_staff and self.hierarchy_level < target_level

    def get_all_roles(self):
        roles = [self.primary_role]
        roles += list(self.secondary_roles.all())
        return roles

    def get_manageable_roles(self):
        """Roles this staff member is allowed to assign to new staff."""
        return StaffRole.objects.filter(
            level__gt=self.hierarchy_level,
            is_active=True
        )


class StaffTask(models.Model):
    """
    Task assigned within the company hierarchy.
    Assignor must have lower or equal hierarchy level than assignee.
    """
    PRIORITY_LOW    = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH   = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW,    'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH,   'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    STATUS_TODO       = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_REVIEW     = 'review'
    STATUS_DONE       = 'done'
    STATUS_BLOCKED    = 'blocked'
    STATUS_CHOICES = [
        (STATUS_TODO,        'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_REVIEW,      'In Review'),
        (STATUS_DONE,        'Done'),
        (STATUS_BLOCKED,     'Blocked'),
    ]

    CATEGORY_CHOICES = [
        ('dev',      'Development'),
        ('sales',    'Sales'),
        ('support',  'Support'),
        ('qa',       'QA / Testing'),
        ('design',   'Design'),
        ('ops',      'Operations'),
        ('admin',    'Admin'),
        ('other',    'Other'),
    ]

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES,
                                    default=PRIORITY_MEDIUM)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                    default=STATUS_TODO)

    assigned_to = models.ForeignKey(
                      StaffMember, on_delete=models.CASCADE,
                      related_name='assigned_tasks')
    assigned_by = models.ForeignKey(
                      settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='created_tasks')

    due_date    = models.DateField(null=True, blank=True)
    started_at  = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Staff Task'
        verbose_name_plural = 'Staff Tasks'
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['assigned_to', 'due_date']),
        ]

    def __str__(self):
        return f'[{self.get_priority_display()}] {self.title} → {self.assigned_to}'

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        if self.status == self.STATUS_DONE and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.due_date and self.status not in (self.STATUS_DONE,):
            return self.due_date < timezone.now().date()
        return False

    @property
    def days_until_due(self):
        if not self.due_date:
            return None
        return (self.due_date - timezone.now().date()).days