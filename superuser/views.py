"""
superuser/views.py
==================
All views for the Dooars Granthika SaaS Superuser Dashboard.

Queries the REAL models:
  accounts.Library          — tenant record (library_name, library_code, status …)
  accounts.Subscription     — plan + expiry for each library
  accounts.LibraryRuleSettings — late_fine, borrowing_period …
  books.BookCopy            — physical copy count per library
  members.Member            — member count per library
  superuser.Plan            — plan definitions (price, features …)
  superuser.Invoice         — billing invoices
  superuser.BillingTransaction — payment events
  superuser.ActivityLog     — audit trail
"""

from decimal import Decimal
from calendar import month_abbr

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache

from .models import Plan, Invoice, BillingTransaction, ActivityLog, StaffRole, StaffMember, StaffTask
from .forms import (
    PlanForm, PlanDeleteForm,
    LibraryFilterForm, LibrarySuspendForm,
    SubscriptionFilterForm, SubscriptionActivateForm,
    BillingTransactionFilterForm, InvoiceFilterForm,
)

# ── Email + credential helpers ───────────────────────────────
try:
    from core.email_service import (
        send_staff_credentials_email,
        send_password_reset_email as _send_pw_reset,
    )
    _EMAIL_AVAILABLE = True
except ImportError:
    _EMAIL_AVAILABLE = False

try:
    from accounts.utils import generate_random_password, generate_username, is_valid_email
    _UTILS_AVAILABLE = True
except ImportError:
    import secrets, string as _string
    def generate_random_password(length=12):
        alphabet = _string.ascii_letters + _string.digits
        while True:
            pw = ''.join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.isupper() for c in pw) and
                    any(c.islower() for c in pw) and
                    any(c.isdigit() for c in pw)):
                return pw
    def generate_username(prefix="DG", digits=8):
        number_part = ''.join(secrets.choice(_string.digits) for _ in range(digits))
        return f"{prefix}{number_part}"
    def is_valid_email(email):
        import re
        return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email.strip()))
    _UTILS_AVAILABLE = False


# ── Lazy imports for cross-app models ───────────────────────

def _get_library_model():
    from accounts.models import Library
    return Library

def _get_acc_subscription_model():
    from accounts.models import Subscription
    return Subscription

def _get_book_copy_model():
    try:
        from books.models import BookCopy
        return BookCopy
    except ImportError:
        return None

def _get_member_model():
    try:
        from members.models import Member
        return Member
    except ImportError:
        return None


# ─────────────────────────────────────────────
#  Access control
# ─────────────────────────────────────────────

def _is_superuser_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


_superuser_check = user_passes_test(
    _is_superuser_or_staff,
    login_url='accounts:signin',
)


def superuser_view(fn):
    """Decorator: login required + must be staff or superuser."""
    return login_required(login_url='accounts:signin')(_superuser_check(fn))


def superuser_only(fn):
    """Decorator: login required + must be a true superuser (not just staff)."""
    return login_required(login_url='accounts:signin')(
        user_passes_test(
            lambda u: u.is_authenticated and u.is_superuser,
            login_url='accounts:signin',
        )(fn)
    )


# ─────────────────────────────────────────────
#  Staff helper utilities (used by dashboard + staff views)
# ─────────────────────────────────────────────

def _get_requesting_staff(request):
    """Return StaffMember for request.user, or None (means superuser with full access)."""
    if request.user.is_superuser:
        return None
    try:
        return request.user.staff_profile
    except Exception:
        return None


def _assert_can_manage_staff(request, target_level=None):
    """
    Raise PermissionError if current user cannot manage staff.
    Superuser always can. Staff can only add/edit staff at strictly lower level.
    """
    staff = _get_requesting_staff(request)
    if staff is None:
        return  # superuser — full access
    if not staff.primary_role.can_add_staff:
        raise PermissionError("Your role does not have staff management permissions.")
    if target_level is not None and not staff.can_add_staff_at_level(target_level):
        raise PermissionError(
            f"You can only manage staff at a level higher than yours ({staff.hierarchy_level})."
        )


# ─────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────

@superuser_view
def dashboard(request):
    Library     = _get_library_model()
    AccSub      = _get_acc_subscription_model()
    BookCopy    = _get_book_copy_model()
    Member      = _get_member_model()
    now         = timezone.now()

    # ── Determine who is viewing ──────────────────────────────
    requesting_staff = _get_requesting_staff(request)

    # ── Personal task stats (for any staff member) ────────────
    my_task_stats   = None
    my_recent_tasks = None
    if requesting_staff:
        my_qs = StaffTask.objects.filter(assigned_to=requesting_staff)
        my_task_stats = {
            'todo':        my_qs.filter(status=StaffTask.STATUS_TODO).count(),
            'in_progress': my_qs.filter(status=StaffTask.STATUS_IN_PROGRESS).count(),
            'done':        my_qs.filter(status=StaffTask.STATUS_DONE).count(),
            'overdue':     sum(1 for t in my_qs if t.is_overdue),
        }
        my_recent_tasks = my_qs.select_related('assigned_by').order_by('-created_at')[:5]

    # ── Manager KPIs (staff who can add/manage other staff) ───
    managed_staff_count = None
    managed_task_stats  = None
    if requesting_staff and getattr(requesting_staff.primary_role, 'can_add_staff', False):
        managed_qs = StaffMember.objects.filter(
            primary_role__level__gt=requesting_staff.hierarchy_level
        )
        managed_staff_count = managed_qs.count()
        mgd_tasks = StaffTask.objects.filter(
            assigned_to__primary_role__level__gt=requesting_staff.hierarchy_level
        )
        managed_task_stats = {
            'todo':        mgd_tasks.filter(status=StaffTask.STATUS_TODO).count(),
            'in_progress': mgd_tasks.filter(status=StaffTask.STATUS_IN_PROGRESS).count(),
            'done':        mgd_tasks.filter(status=StaffTask.STATUS_DONE).count(),
            'overdue':     sum(1 for t in mgd_tasks if t.is_overdue),
        }

    # ── Superuser-only KPIs ───────────────────────────────────
    total_libraries = active_subs = expired_subs = None
    total_books = total_members = mrr = None
    plan_dist = expiring_soon = recent_libraries = recent_transactions = None

    if request.user.is_superuser:
        total_libraries = Library.objects.count()
        active_subs     = AccSub.objects.filter(is_active=True).count()
        expired_subs    = AccSub.objects.filter(is_active=False).count()
        _books          = BookCopy.objects.count() if BookCopy else 0
        _members        = Member.objects.count() if Member else 0
        total_books     = f'{_books:,}'
        total_members   = f'{_members:,}'

        mrr_val = Decimal('0')
        for plan in Plan.objects.filter(is_active=True):
            mrr_val += plan.mrr
        mrr = f'{mrr_val:,.2f}'

        plan_dist = (
            AccSub.objects.filter(is_active=True)
            .values('plan').annotate(count=Count('id')).order_by('-count')
        )
        expiring_soon = (
            AccSub.objects.filter(
                is_active=True,
                expiry_date__range=[now.date(), now.date() + timezone.timedelta(days=7)]
            ).select_related('library').order_by('expiry_date')[:5]
        )
        recent_libraries = (
            Library.objects.select_related('subscription').order_by('-created_at')[:5]
        )
        recent_transactions = (
            BillingTransaction.objects.select_related('library').order_by('-created_at')[:5]
        )

    context = {
        'requesting_staff':    requesting_staff,
        # superuser
        'total_libraries':     total_libraries,
        'active_subs':         active_subs,
        'expired_subs':        expired_subs,
        'total_books':         total_books,
        'total_members':       total_members,
        'mrr':                 mrr,
        'plan_dist':           plan_dist,
        'expiring_soon':       expiring_soon,
        'recent_libraries':    recent_libraries,
        'recent_transactions': recent_transactions,
        # personal tasks
        'my_task_stats':       my_task_stats,
        'my_recent_tasks':     my_recent_tasks,
        # manager
        'managed_staff_count': managed_staff_count,
        'managed_task_stats':  managed_task_stats,
    }
    return render(request, 'superuser/dashboard/dashboard.html', context)



# ─────────────────────────────────────────────
#  Libraries
# ─────────────────────────────────────────────

@superuser_view
def libraries_list(request):
    Library = _get_library_model()
    AccSub  = _get_acc_subscription_model()

    qs   = Library.objects.select_related('subscription', 'user').order_by('-created_at')
    form = LibraryFilterForm(request.GET)

    if form.is_valid():
        cd = form.cleaned_data
        if cd.get('plan'):
            qs = qs.filter(subscription__plan=cd['plan'])
        if cd.get('status'):
            # accounts.Library has no status field; we derive it from subscription
            if cd['status'] == 'active':
                qs = qs.filter(subscription__is_active=True)
            elif cd['status'] == 'expired':
                qs = qs.filter(subscription__is_active=False)
        if cd.get('q'):
            q = cd['q']
            qs = qs.filter(
                Q(library_name__icontains=q) |
                Q(institute_email__icontains=q) |
                Q(library_code__icontains=q)
            )

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'superuser/libraries/libraries_list.html', {
        'libraries': page,
        'form':      form,
        'plans':     Plan.objects.filter(is_active=True),
    })


@superuser_view
def library_detail(request, pk):
    Library  = _get_library_model()
    BookCopy = _get_book_copy_model()
    Member   = _get_member_model()

    library = get_object_or_404(
        Library.objects.select_related(
            'user', 'subscription', 'rules', 'member_settings',
            'security', 'notifications', 'appearance'
        ),
        pk=pk
    )

    # Usage stats
    book_count   = BookCopy.objects.filter(book__owner=library.user).count() if BookCopy else 0
    member_count = Member.objects.filter(owner=library.user).count() if Member else 0

    # Activity logs for this library
    activity_logs = (
        ActivityLog.objects
        .filter(library=library)
        .order_by('-created_at')[:15]
    )

    # Recent billing transactions
    recent_billing = (
        BillingTransaction.objects
        .filter(library=library)
        .order_by('-created_at')[:5]
    )

    context = {
        'library':         library,
        'book_count':      book_count,
        'member_count':    member_count,
        'activity_logs':   activity_logs,
        'recent_billing':  recent_billing,
    }
    return render(request, 'superuser/libraries/library_detail.html', context)


@superuser_view
def library_suspend(request, pk):
    Library = _get_library_model()
    library = get_object_or_404(Library, pk=pk)
    form    = LibrarySuspendForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        reason = form.cleaned_data.get('reason', '')
        # Deactivate the subscription
        try:
            sub = library.subscription
            sub.is_active = False
            sub.save(update_fields=['is_active'])
        except Exception:
            pass

        ActivityLog.log(
            action='suspended',
            library=library,
            user=request.user,
            notes=reason or 'Library suspended by superuser',
        )
        messages.warning(
            request,
            f'Library "{library.library_name}" ({library.library_code}) has been suspended.'
        )
        return redirect('superuser:library_detail', pk=pk)

    return render(request, 'superuser/libraries/library_suspend.html',
                  {'library': library, 'form': form})


@superuser_view
def library_activate(request, pk):
    Library = _get_library_model()
    library = get_object_or_404(Library, pk=pk)

    if request.method == 'POST':
        try:
            sub = library.subscription
            sub.is_active = True
            # Extend expiry by 30 days from today if already expired
            if sub.expiry_date < timezone.now().date():
                sub.expiry_date = timezone.now().date() + timezone.timedelta(days=30)
            sub.save(update_fields=['is_active', 'expiry_date'])
        except Exception:
            pass

        ActivityLog.log(
            action='activated',
            library=library,
            user=request.user,
            notes='Library reactivated by superuser',
        )
        messages.success(
            request,
            f'Library "{library.library_name}" has been activated.'
        )
        return redirect('superuser:library_detail', pk=pk)

    return render(request, 'superuser/libraries/library_activate.html', {'library': library})


# ─────────────────────────────────────────────
#  Subscriptions  (accounts.Subscription rows)
# ─────────────────────────────────────────────

@superuser_view
def subscriptions_list(request):
    AccSub = _get_acc_subscription_model()

    qs = (
        AccSub.objects
        .select_related('library', 'library__user')
        .order_by('-start_date')
    )
    form = SubscriptionFilterForm(request.GET)

    if form.is_valid():
        cd = form.cleaned_data
        if cd.get('plan'):
            qs = qs.filter(plan=cd['plan'])
        if cd.get('status') == 'active':
            qs = qs.filter(is_active=True)
        elif cd.get('status') == 'expired':
            qs = qs.filter(is_active=False)
        if cd.get('q'):
            q = cd['q']
            qs = qs.filter(
                Q(library__library_name__icontains=q) |
                Q(library__library_code__icontains=q) |
                Q(library__institute_email__icontains=q)
            )

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get('page', 1))

    context = {
        'subscriptions': page,
        'form':          form,
        'plans':         Plan.objects.filter(is_active=True),
        'today':         timezone.now().date(),
    }
    return render(request, 'superuser/subscriptions/subscriptions_list.html', context)


@superuser_view
def subscription_detail(request, pk):
    AccSub  = _get_acc_subscription_model()
    sub     = get_object_or_404(
        AccSub.objects.select_related('library', 'library__user'),
        pk=pk
    )
    invoices      = Invoice.objects.filter(accounts_subscription=sub).order_by('-issued_date')[:10]
    billing_tx    = BillingTransaction.objects.filter(accounts_subscription=sub).order_by('-created_at')[:10]
    activity_logs = ActivityLog.objects.filter(accounts_subscription=sub).order_by('-created_at')[:10]
    plan_def      = Plan.objects.filter(slug=sub.plan).first()

    context = {
        'subscription':  sub,
        'plan_def':      plan_def,
        'invoices':      invoices,
        'transactions':  billing_tx,
        'activity_logs': activity_logs,
    }
    return render(request, 'superuser/subscriptions/subscription_detail.html', context)


@superuser_view
def activate_subscription(request, pk):
    AccSub = _get_acc_subscription_model()
    sub    = get_object_or_404(AccSub.objects.select_related('library'), pk=pk)

    if request.method == 'POST':
        sub.is_active = True
        if sub.expiry_date < timezone.now().date():
            sub.expiry_date = timezone.now().date() + timezone.timedelta(days=30)
        sub.save(update_fields=['is_active', 'expiry_date'])

        ActivityLog.log(
            action='subscription_activated',
            subscription=sub,
            library=sub.library,
            user=request.user,
            notes=f'Subscription #{pk} activated by superuser',
        )
        messages.success(
            request,
            f'Subscription for "{sub.library.library_name}" has been activated.'
        )
        return redirect('superuser:subscription_detail', pk=pk)

    return render(request, 'superuser/subscriptions/activate_subscription.html', {'subscription': sub})


@superuser_view
def suspend_subscription(request, pk):
    AccSub = _get_acc_subscription_model()
    sub    = get_object_or_404(AccSub.objects.select_related('library'), pk=pk)
    form   = LibrarySuspendForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        reason = form.cleaned_data.get('reason', '')
        sub.is_active = False
        sub.save(update_fields=['is_active'])

        ActivityLog.log(
            action='subscription_suspended',
            subscription=sub,
            library=sub.library,
            user=request.user,
            notes=reason or 'Suspended by superuser',
        )
        messages.warning(
            request,
            f'Subscription for "{sub.library.library_name}" has been suspended.'
        )
        return redirect('superuser:subscription_detail', pk=pk)

    return render(request, 'superuser/subscriptions/suspend_subscription.html',
                  {'subscription': sub, 'form': form})


@superuser_view
def cancel_subscription(request, pk):
    """Cancel = deactivate + set expiry to today."""
    AccSub = _get_acc_subscription_model()
    sub    = get_object_or_404(AccSub.objects.select_related('library'), pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        notes  = request.POST.get('notes', '')
        sub.is_active   = False
        sub.expiry_date = timezone.now().date()
        sub.save(update_fields=['is_active', 'expiry_date'])

        ActivityLog.log(
            action='subscription_cancelled',
            subscription=sub,
            library=sub.library,
            user=request.user,
            notes=f'{reason} — {notes}'.strip(' —'),
        )
        messages.error(
            request,
            f'Subscription for "{sub.library.library_name}" has been cancelled.'
        )
        return redirect('superuser:subscription_detail', pk=pk)

    return render(request, 'superuser/subscriptions/cancel_subscription.html', {'subscription': sub})


# ─────────────────────────────────────────────
#  Plans
# ─────────────────────────────────────────────

@superuser_only
def plans_list(request):
    plans = Plan.objects.order_by('price')
    # Annotate each with live count from accounts.Subscription
    for plan in plans:
        plan.live_count = plan.active_subscription_count
        plan.live_mrr   = plan.mrr

    return render(request, 'superuser/subscriptions/plans_list.html', {'plans': plans})


@superuser_only
def plan_create(request):
    form = PlanForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plan = form.save(commit=False)
        if not plan.slug:
            plan.slug = slugify(plan.name)
        plan.save()
        ActivityLog.log(
            action='plan_created',
            model_name='Plan',
            object_id=plan.pk,
            user=request.user,
            notes=f'Plan "{plan.name}" created at ₹{plan.price}/mo',
        )
        messages.success(request, f'Plan "{plan.name}" created successfully.')
        return redirect('superuser:plans_list')

    return render(request, 'superuser/subscriptions/plan_create.html', {'form': form})


@superuser_only
def plan_edit(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    form = PlanForm(request.POST or None, instance=plan)

    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.log(
            action='plan_updated',
            model_name='Plan',
            object_id=plan.pk,
            user=request.user,
            notes=f'Plan "{plan.name}" updated',
        )
        messages.success(request, f'Plan "{plan.name}" updated.')
        return redirect('superuser:plans_list')

    return render(request, 'superuser/subscriptions/plan_edit.html', {'plan': plan, 'form': form})


@superuser_only
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    form = PlanDeleteForm(request.POST or None)

    if request.method == 'POST':
        live_count = plan.active_subscription_count
        if live_count > 0:
            messages.error(
                request,
                f'Cannot delete "{plan.name}" — '
                f'{live_count} active subscription(s) exist.'
            )
            return redirect('superuser:plan_delete', pk=pk)
        if form.is_valid():
            name = plan.name
            plan.delete()
            messages.success(request, f'Plan "{name}" deleted.')
            return redirect('superuser:plans_list')

    return render(request, 'superuser/subscriptions/plan_delete.html', {'plan': plan, 'form': form})


# ─────────────────────────────────────────────
#  Billing Transactions
# ─────────────────────────────────────────────

@superuser_view
def transactions_list(request):
    qs   = BillingTransaction.objects.select_related('library').order_by('-created_at')
    form = BillingTransactionFilterForm(request.GET)

    if form.is_valid():
        cd = form.cleaned_data
        if cd.get('status'):
            qs = qs.filter(status=cd['status'])
        if cd.get('type'):
            qs = qs.filter(type=cd['type'])
        if cd.get('q'):
            q = cd['q']
            qs = qs.filter(
                Q(reference__icontains=q) |
                Q(library__library_name__icontains=q) |
                Q(library__library_code__icontains=q)
            )

    now = timezone.now()
    month_qs = BillingTransaction.objects.filter(
        created_at__year=now.year, created_at__month=now.month
    )
    paid_this_month = (
        month_qs.filter(status=BillingTransaction.STATUS_PAID)
                .aggregate(t=Sum('amount'))['t'] or Decimal('0')
    )

    paginator = Paginator(qs, 30)
    page      = paginator.get_page(request.GET.get('page', 1))

    context = {
        'transactions':    page,
        'form':            form,
        'paid_this_month': f'{paid_this_month:,.2f}',
        'pending_count':   month_qs.filter(status=BillingTransaction.STATUS_PENDING).count(),
        'failed_count':    month_qs.filter(status=BillingTransaction.STATUS_FAILED).count(),
        'refunded_count':  month_qs.filter(status=BillingTransaction.STATUS_REFUNDED).count(),
    }
    return render(request, 'superuser/billing/transactions_list.html', context)


@superuser_view
def transaction_detail(request, pk):
    tx = get_object_or_404(
        BillingTransaction.objects.select_related('library', 'invoice', 'accounts_subscription'),
        pk=pk
    )
    related = (
        BillingTransaction.objects
        .filter(library=tx.library)
        .exclude(pk=pk)
        .order_by('-created_at')[:5]
    )
    return render(request, 'superuser/billing/transaction_detail.html', {
        'transaction':          tx,
        'related_transactions': related,
    })


@superuser_view
@require_POST
def transaction_retry(request, pk):
    tx = get_object_or_404(BillingTransaction, pk=pk)
    if tx.status != BillingTransaction.STATUS_FAILED:
        messages.error(request, 'Only failed transactions can be retried.')
        return redirect('superuser:transaction_detail', pk=pk)
    tx.status = BillingTransaction.STATUS_PENDING
    tx.save(update_fields=['status', 'updated_at'])
    messages.info(request, f'Transaction {tx.reference} queued for retry.')
    return redirect('superuser:transaction_detail', pk=pk)


# ─────────────────────────────────────────────
#  Invoices
# ─────────────────────────────────────────────

@superuser_view
def invoices(request):
    qs   = Invoice.objects.select_related('library').order_by('-issued_date')
    form = InvoiceFilterForm(request.GET)

    if form.is_valid():
        cd = form.cleaned_data
        if cd.get('status'):
            qs = qs.filter(status=cd['status'])
        if cd.get('q'):
            q = cd['q']
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(library__library_name__icontains=q) |
                Q(library__library_code__icontains=q)
            )

    paginator = Paginator(qs, 30)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'superuser/billing/invoices.html', {
        'invoices': page,
        'form':     form,
    })


@superuser_view
@require_POST
def invoice_remind(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    # TODO: send actual email via celery / send_mail
    messages.success(
        request,
        f'Payment reminder sent for invoice {invoice.number}.'
    )
    return redirect('superuser:invoices')


# ─────────────────────────────────────────────
#  Revenue Report
# ─────────────────────────────────────────────

@superuser_only
def revenue_report(request):
    now  = timezone.now()
    year = int(request.GET.get('year', now.year))

    monthly_data = []
    cumulative   = Decimal('0')

    for month in range(1, 13):
        gross = (
            BillingTransaction.objects
            .filter(created_at__year=year, created_at__month=month,
                    status=BillingTransaction.STATUS_PAID)
            .aggregate(t=Sum('amount'))['t'] or Decimal('0')
        )
        refunds = (
            BillingTransaction.objects
            .filter(created_at__year=year, created_at__month=month,
                    status=BillingTransaction.STATUS_REFUNDED)
            .aggregate(t=Sum('amount'))['t'] or Decimal('0')
        )
        net = gross - refunds
        cumulative += net

        AccSub = _get_acc_subscription_model()
        new_subs = AccSub.objects.filter(
            start_date__year=year, start_date__month=month
        ).count()

        prev_net = monthly_data[-1]['net_raw'] if monthly_data else Decimal('0')
        growth   = round(float((net - prev_net) / prev_net * 100), 1) if prev_net else 0

        monthly_data.append({
            'month':         f'{month_abbr[month]} {year}',
            'new_subs':      new_subs,
            'gross':         f'{gross:,.2f}',
            'refunds':       f'{refunds:,.2f}',
            'net':           f'{net:,.2f}',
            'net_raw':       net,
            'cumulative':    f'{cumulative:,.2f}',
            'growth':        growth,
        })

    # Plan breakdown
    plans = Plan.objects.filter(is_active=True).order_by('price')
    total_mrr_val = sum(p.mrr for p in plans)
    total_mrr_div = total_mrr_val or Decimal('1')  # safe divisor — avoids ZeroDivisionError
    plan_revenue = []
    for p in plans:
        mrr  = p.mrr
        ytd  = (
            BillingTransaction.objects
            .filter(plan_name=p.slug,
                    status=BillingTransaction.STATUS_PAID,
                    created_at__year=year)
            .aggregate(t=Sum('amount'))['t'] or Decimal('0')
        )
        plan_revenue.append({
            'name':        p.name,
            'active_subs': p.active_subscription_count,
            'price':       f'{p.price:,.2f}',
            'mrr':         f'{mrr:,.2f}',
            'percent':     round(float(mrr / total_mrr_div * 100), 1),
            'ytd':         f'{ytd:,.2f}',
        })

    AccSub        = _get_acc_subscription_model()
    total_active  = AccSub.objects.filter(is_active=True).count()
    avg_revenue   = round(float(total_mrr_val) / total_active, 2) if total_active else 0

    context = {
        'mrr':          f'{total_mrr_val:,.0f}',
        'arr':          f'{total_mrr_val * 12:,.0f}',
        'avg_revenue':  f'{avg_revenue:,.2f}',
        'churn_rate':   '—',
        'monthly_data': monthly_data,
        'plan_revenue': plan_revenue,
        'year':         year,
        'years':        list(range(now.year, now.year - 4, -1)),
    }
    return render(request, 'superuser/analytics/revenue_report.html', context)


# ─────────────────────────────────────────────
#  Usage Overview
# ─────────────────────────────────────────────

@superuser_only
def usage_overview(request):
    Library  = _get_library_model()
    AccSub   = _get_acc_subscription_model()
    BookCopy = _get_book_copy_model()
    Member   = _get_member_model()

    libraries       = Library.objects.select_related('subscription').all()
    total_libraries = libraries.count()
    total_patrons   = Member.objects.count() if Member else 0
    total_books     = BookCopy.objects.count() if BookCopy else 0

    # Top 5 libraries by member count
    top_libraries = []
    if Member:
        top_lib_ids = (
            Member.objects
            .values('owner')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')[:5]
        )
        for row in top_lib_ids:
            try:
                lib = Library.objects.select_related('subscription').get(user_id=row['owner'])
                top_libraries.append({
                    'pk':           lib.pk,
                    'name':         lib.library_name,
                    'code':         lib.library_code,
                    'patron_count': row['cnt'],
                    'plan':         lib.subscription.plan if hasattr(lib, 'subscription') else '—',
                })
            except Exception:
                pass

    # Subscriptions expiring soon
    expiring = (
        AccSub.objects
        .filter(
            is_active=True,
            expiry_date__gte=timezone.now().date(),
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=14)
        )
        .select_related('library')
        .order_by('expiry_date')[:10]
    )

    context = {
        'total_libraries': total_libraries,
        'total_patrons':   f'{total_patrons:,}',
        'total_books':     f'{total_books:,}',
        'top_libraries':   top_libraries,
        'expiring':        expiring,
        'today':           timezone.now().date(),
    }
    return render(request, 'superuser/analytics/usage_overview.html', context)

# ─────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────

_SETTINGS_KEY = 'superuser_platform_settings'

def _load_settings():
    return cache.get(_SETTINGS_KEY) or {}

def _save_settings(data):
    existing = _load_settings()
    existing.update(data)
    cache.set(_SETTINGS_KEY, existing, timeout=None)
    return existing


@superuser_only
def settings_view(request):
    return render(request, 'superuser/dashboard/settings.html', {
        'settings': _load_settings(),
    })


@superuser_only
@require_POST
def settings_save(request, section):
    """Handle POST for any settings section."""
    if section == 'purge_logs':
        count, _ = ActivityLog.objects.all().delete()
        messages.success(request, f'Purged {count} activity log entries.')
        return redirect('superuser:settings')

    if section == 'mark_overdue':
        updated = 0
        for inv in Invoice.objects.filter(status=Invoice.STATUS_UNPAID):
            if inv.due_date < timezone.now().date():
                inv.status = Invoice.STATUS_OVERDUE
                inv.save(update_fields=['status', 'updated_at'])
                updated += 1
        messages.success(request, f'Marked {updated} invoice(s) as overdue.')
        return redirect('superuser:settings')

    # For all other sections, collect POST data and persist
    data = {}
    bool_fields = [
        'allow_registrations', 'allow_trials', 'maintenance_mode',
        'auto_invoice_email', 'auto_payment_reminder',
        'notify_new_library', 'notify_expiry_7d',
        'notify_failed_payment', 'notify_weekly_digest',
        'auto_activate_on_payment', 'require_staff',
    ]
    for key, value in request.POST.items():
        if key == 'csrfmiddlewaretoken':
            continue
        data[key] = value

    # Checkboxes not submitted = False
    for field in bool_fields:
        if field not in request.POST:
            data[field] = False
        else:
            data[field] = True

    _save_settings(data)
    messages.success(request, f'{section.replace("_", " ").title()} settings saved.')
    ActivityLog.log(
        action=f'settings_updated_{section}',
        user=request.user,
        model_name='Settings',
        notes=f'Section "{section}" updated',
    )
    return redirect('superuser:settings')


# ─────────────────────────────────────────────
#  Staff Hierarchy Views
# ─────────────────────────────────────────────


# ── Staff List ────────────────────────────────────────────

@superuser_view
def staff_list(request):
    requesting_staff = _get_requesting_staff(request)

    qs = StaffMember.objects.select_related(
        'user', 'primary_role', 'added_by', 'added_by__user'
    ).prefetch_related('secondary_roles').order_by('primary_role__level', 'user__first_name')

    # Non-superuser staff: only see staff they added or at lower levels
    if requesting_staff:
        qs = qs.filter(primary_role__level__gt=requesting_staff.hierarchy_level)

    # Filters
    dept   = request.GET.get('dept', '')
    status = request.GET.get('status', '')
    q      = request.GET.get('q', '')

    if dept:
        qs = qs.filter(primary_role__department=dept)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q)  |
            Q(user__email__icontains=q)      |
            Q(employee_id__icontains=q)      |
            Q(primary_role__name__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page      = paginator.get_page(request.GET.get('page', 1))

    # Roles this user can assign
    if requesting_staff:
        assignable_roles = requesting_staff.get_manageable_roles()
    else:
        assignable_roles = StaffRole.objects.filter(is_active=True)

    # Stats
    total      = StaffMember.objects.count()
    active     = StaffMember.objects.filter(status=StaffMember.STATUS_ACTIVE).count()
    by_dept    = (StaffMember.objects
                  .values('primary_role__department')
                  .annotate(cnt=Count('id'))
                  .order_by('-cnt'))

    return render(request, 'superuser/staff/staff_list.html', {
        'staff_members':    page,
        'assignable_roles': assignable_roles,
        'roles':            StaffRole.objects.filter(is_active=True),
        'total_staff':      total,
        'active_staff':     active,
        'by_dept':          by_dept,
        'requesting_staff': requesting_staff,
        'dept_filter':      dept,
        'status_filter':    status,
        'q':                q,
        'dept_choices':     StaffRole.DEPT_CHOICES,
        'status_choices':   StaffMember.STATUS_CHOICES,
    })


# ── Staff Detail ──────────────────────────────────────────

@superuser_view
def staff_detail(request, pk):
    requesting_staff = _get_requesting_staff(request)
    member = get_object_or_404(
        StaffMember.objects.select_related('user', 'primary_role', 'added_by__user')
                           .prefetch_related('secondary_roles'),
        pk=pk
    )

    # Non-superuser can only view staff at lower levels
    if requesting_staff and member.hierarchy_level <= requesting_staff.hierarchy_level:
        messages.error(request, "You do not have permission to view this profile.")
        return redirect('superuser:staff_list')

    tasks     = StaffTask.objects.filter(assigned_to=member).order_by('-created_at')[:20]
    added_staff = StaffMember.objects.filter(added_by=member).select_related('user', 'primary_role')

    task_stats = {
        'total':       tasks.count(),
        'todo':        StaffTask.objects.filter(assigned_to=member, status=StaffTask.STATUS_TODO).count(),
        'in_progress': StaffTask.objects.filter(assigned_to=member, status=StaffTask.STATUS_IN_PROGRESS).count(),
        'done':        StaffTask.objects.filter(assigned_to=member, status=StaffTask.STATUS_DONE).count(),
        'overdue':     sum(1 for t in StaffTask.objects.filter(assigned_to=member) if t.is_overdue),
    }

    return render(request, 'superuser/staff/staff_detail.html', {
        'member':           member,
        'tasks':            tasks,
        'added_staff':      added_staff,
        'task_stats':       task_stats,
        'requesting_staff': requesting_staff,
        'roles':            StaffRole.objects.filter(is_active=True),
    })


# ── Add Staff ─────────────────────────────────────────────

@superuser_view
def staff_add(request):
    requesting_staff = _get_requesting_staff(request)

    if requesting_staff:
        assignable_roles = requesting_staff.get_manageable_roles()
    else:
        assignable_roles = StaffRole.objects.filter(is_active=True)

    if request.method == 'POST':
        # Validate target role level
        role_id = request.POST.get('primary_role')
        try:
            role = StaffRole.objects.get(pk=role_id)
            _assert_can_manage_staff(request, target_level=role.level)
        except StaffRole.DoesNotExist:
            messages.error(request, 'Invalid role selected.')
            return redirect('superuser:staff_add')
        except PermissionError as e:
            messages.error(request, str(e))
            return redirect('superuser:staff_add')

        # ── Collect form fields ───────────────────────────────────
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        password   = request.POST.get('password', '').strip()

        # ── Auto-generate username if left blank ─────────────────
        User = get_user_model()
        if not username:
            for _ in range(10):  # up to 10 attempts to find a unique one
                candidate = generate_username(prefix='DG')
                if not User.objects.filter(username=candidate).exists():
                    username = candidate
                    break
            else:
                messages.error(request, 'Could not generate a unique username. Please enter one manually.')
                return render(request, 'superuser/staff/staff_add.html', {
                    'assignable_roles': assignable_roles,
                    'requesting_staff': requesting_staff,
                    'post': request.POST,
                })

        # ── Auto-generate password if left blank ─────────────────
        auto_password = not bool(password)
        if auto_password:
            password = generate_random_password(length=12)

        # ── Basic validation ──────────────────────────────────────
        if not email:
            messages.error(request, 'Email address is required.')
            return render(request, 'superuser/staff/staff_add.html', {
                'assignable_roles': assignable_roles,
                'requesting_staff': requesting_staff,
                'post': request.POST,
            })

        if not is_valid_email(email):
            messages.error(request, f'"{email}" is not a valid email address.')
            return render(request, 'superuser/staff/staff_add.html', {
                'assignable_roles': assignable_roles,
                'requesting_staff': requesting_staff,
                'post': request.POST,
            })

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken.')
            return render(request, 'superuser/staff/staff_add.html', {
                'assignable_roles': assignable_roles,
                'requesting_staff': requesting_staff,
                'post': request.POST,
            })

        if User.objects.filter(email=email).exists():
            messages.error(request, f'A user with email "{email}" already exists.')
            return render(request, 'superuser/staff/staff_add.html', {
                'assignable_roles': assignable_roles,
                'requesting_staff': requesting_staff,
                'post': request.POST,
            })

        user = User.objects.create_user(
            username=username, email=email,
            password=password,
            first_name=first_name, last_name=last_name,
            is_staff=(role.level <= 2),
        )

        secondary_ids = request.POST.getlist('secondary_roles')
        member = StaffMember.objects.create(
            user=user,
            primary_role=role,
            added_by=requesting_staff,
            phone=request.POST.get('phone', ''),
            bio=request.POST.get('bio', ''),
            notes=request.POST.get('notes', ''),
            joined_date=request.POST.get('joined_date') or timezone.now().date(),
        )
        if secondary_ids:
            sec_roles = StaffRole.objects.filter(pk__in=secondary_ids)
            member.secondary_roles.set(sec_roles)

        ActivityLog.log(
            action='staff_added',
            user=request.user,
            model_name='StaffMember',
            object_id=member.pk,
            notes=f'Added {member.full_name} as {role.name}',
        )

        # ── Send credentials email ────────────────────────────────
        if _EMAIL_AVAILABLE:
            added_by_name = (
                requesting_staff.full_name if requesting_staff else 'Superuser'
            )
            email_sent = send_staff_credentials_email(
                staff_member=member,
                username=username,
                password=password,
                added_by_name=added_by_name,
            )
            if email_sent:
                messages.success(
                    request,
                    f'Staff member "{member.full_name}" added and credentials '
                    f'emailed to {member.email}.'
                )
            else:
                messages.warning(
                    request,
                    f'Staff member "{member.full_name}" added, but credentials '
                    f'email could not be sent (no email address on record).'
                )
        else:
            messages.success(request, f'Staff member "{member.full_name}" added successfully.')

        return redirect('superuser:staff_detail', pk=member.pk)

    return render(request, 'superuser/staff/staff_add.html', {
        'assignable_roles': assignable_roles,
        'requesting_staff': requesting_staff,
        'post': {},
    })


# ── Edit Staff ────────────────────────────────────────────

@superuser_view
def staff_edit(request, pk):
    requesting_staff = _get_requesting_staff(request)
    member = get_object_or_404(StaffMember.objects.select_related('user', 'primary_role'), pk=pk)

    try:
        _assert_can_manage_staff(request, target_level=member.hierarchy_level)
    except PermissionError as e:
        messages.error(request, str(e))
        return redirect('superuser:staff_list')

    if requesting_staff:
        assignable_roles = requesting_staff.get_manageable_roles()
    else:
        assignable_roles = StaffRole.objects.filter(is_active=True)

    if request.method == 'POST':
        role_id = request.POST.get('primary_role')
        try:
            role = StaffRole.objects.get(pk=role_id)
            _assert_can_manage_staff(request, target_level=role.level)
        except (StaffRole.DoesNotExist, PermissionError) as e:
            messages.error(request, str(e))
            return redirect('superuser:staff_edit', pk=pk)

        u = member.user
        u.first_name = request.POST.get('first_name', u.first_name)
        u.last_name  = request.POST.get('last_name', u.last_name)
        u.email      = request.POST.get('email', u.email)
        new_pass = request.POST.get('password', '').strip()
        if new_pass:
            u.set_password(new_pass)
        u.is_staff = (role.level <= 2)
        u.save()

        member.primary_role = role
        member.phone        = request.POST.get('phone', member.phone)
        member.bio          = request.POST.get('bio', member.bio)
        member.notes        = request.POST.get('notes', member.notes)
        member.status       = request.POST.get('status', member.status)
        joined = request.POST.get('joined_date', '')
        if joined:
            member.joined_date = joined
        member.save()

        secondary_ids = request.POST.getlist('secondary_roles')
        member.secondary_roles.set(StaffRole.objects.filter(pk__in=secondary_ids))

        ActivityLog.log(
            action='staff_updated',
            user=request.user,
            model_name='StaffMember',
            object_id=member.pk,
            notes=f'Updated {member.full_name}',
        )

        # ── Send password-reset email if password was changed ─────
        if new_pass and _EMAIL_AVAILABLE:
            try:
                _send_pw_reset(
                    user=member.user,
                    new_password=new_pass,
                    lib_name=member.full_name,
                    username=member.user.username,
                )
            except Exception:
                pass  # email failure must never block the save

        messages.success(request, f'"{member.full_name}" updated.')
        return redirect('superuser:staff_detail', pk=pk)

    return render(request, 'superuser/staff/staff_edit.html', {
        'member':           member,
        'assignable_roles': assignable_roles,
        'requesting_staff': requesting_staff,
        'status_choices':   StaffMember.STATUS_CHOICES,
    })


# ── Deactivate / Remove Staff ─────────────────────────────

@superuser_view
@require_POST
def staff_deactivate(request, pk):
    requesting_staff = _get_requesting_staff(request)
    member = get_object_or_404(StaffMember, pk=pk)

    try:
        _assert_can_manage_staff(request, target_level=member.hierarchy_level)
    except PermissionError as e:
        messages.error(request, str(e))
        return redirect('superuser:staff_detail', pk=pk)

    member.status = StaffMember.STATUS_INACTIVE
    member.user.is_active = False
    member.user.save(update_fields=['is_active'])
    member.save(update_fields=['status', 'updated_at'])

    ActivityLog.log(
        action='staff_deactivated',
        user=request.user,
        model_name='StaffMember',
        object_id=member.pk,
        notes=f'Deactivated {member.full_name}',
    )
    messages.warning(request, f'"{member.full_name}" has been deactivated.')
    return redirect('superuser:staff_list')


# ── Roles CRUD ────────────────────────────────────────────

@superuser_only
def roles_list(request):
    """Only true superuser manages roles."""
    roles = StaffRole.objects.annotate(
        primary_count=Count('primary_staff', distinct=True),
        secondary_count=Count('secondary_staff', distinct=True),
    ).order_by('level')
    return render(request, 'superuser/staff/roles_list.html', {
        'roles': roles,
        'dept_choices': StaffRole.DEPT_CHOICES,
    })


@superuser_only
@require_POST
def role_save(request, pk=None):
    """Create or update a role. Superuser only."""
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can manage roles.')
        return redirect('superuser:roles_list')

    if pk:
        role = get_object_or_404(StaffRole, pk=pk)
    else:
        role = StaffRole()

    role.name       = request.POST.get('name', '').strip()
    role.department = request.POST.get('department', 'tech')
    role.level      = int(request.POST.get('level', 10))
    role.description = request.POST.get('description', '')
    role.is_active  = request.POST.get('is_active') == 'on'

    import json
    perms_raw = request.POST.get('permissions', '{}')
    try:
        role.permissions = json.loads(perms_raw)
    except Exception:
        role.permissions = {}

    from django.utils.text import slugify as dj_slugify
    if not pk:
        role.slug = dj_slugify(role.name)

    role.save()
    messages.success(request, f'Role "{role.name}" saved.')
    return redirect('superuser:roles_list')


@superuser_only
@require_POST
def role_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete roles.')
        return redirect('superuser:roles_list')
    role = get_object_or_404(StaffRole, pk=pk)
    if role.primary_staff.exists():
        messages.error(request, f'Cannot delete "{role.name}" — staff members still hold this as primary role.')
        return redirect('superuser:roles_list')
    role.delete()
    messages.success(request, f'Role "{role.name}" deleted.')
    return redirect('superuser:roles_list')


# ── Task Management ───────────────────────────────────────

@superuser_view
def tasks_list(request):
    requesting_staff = _get_requesting_staff(request)

    qs = StaffTask.objects.select_related(
        'assigned_to__user', 'assigned_to__primary_role', 'assigned_by'
    ).order_by('-created_at')

    # Non-superuser: see only tasks assigned to staff they manage + their own
    if requesting_staff:
        manageable_ids = StaffMember.objects.filter(
            primary_role__level__gt=requesting_staff.hierarchy_level
        ).values_list('id', flat=True)
        qs = qs.filter(
            Q(assigned_to__in=manageable_ids) | Q(assigned_to=requesting_staff)
        )

    status_f   = request.GET.get('status', '')
    priority_f = request.GET.get('priority', '')
    assignee_f = request.GET.get('assignee', '')
    q          = request.GET.get('q', '')

    if status_f:
        qs = qs.filter(status=status_f)
    if priority_f:
        qs = qs.filter(priority=priority_f)
    if assignee_f:
        qs = qs.filter(assigned_to_id=assignee_f)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get('page', 1))

    if requesting_staff:
        assignable_staff = StaffMember.objects.filter(
            primary_role__level__gt=requesting_staff.hierarchy_level
        ).select_related('user', 'primary_role')
    else:
        assignable_staff = StaffMember.objects.filter(
            status=StaffMember.STATUS_ACTIVE
        ).select_related('user', 'primary_role')

    # Quick stats
    all_tasks = StaffTask.objects.all() if not requesting_staff else \
                StaffTask.objects.filter(assigned_to__primary_role__level__gt=requesting_staff.hierarchy_level)

    stats = {
        'todo':        all_tasks.filter(status=StaffTask.STATUS_TODO).count(),
        'in_progress': all_tasks.filter(status=StaffTask.STATUS_IN_PROGRESS).count(),
        'review':      all_tasks.filter(status=StaffTask.STATUS_REVIEW).count(),
        'done':        all_tasks.filter(status=StaffTask.STATUS_DONE).count(),
        'overdue':     sum(1 for t in all_tasks if t.is_overdue),
    }

    return render(request, 'superuser/staff/tasks_list.html', {
        'tasks':           page,
        'stats':           stats,
        'assignable_staff': assignable_staff,
        'status_choices':  StaffTask.STATUS_CHOICES,
        'priority_choices': StaffTask.PRIORITY_CHOICES,
        'category_choices': StaffTask.CATEGORY_CHOICES,
        'status_f':        status_f,
        'priority_f':      priority_f,
        'assignee_f':      assignee_f,
        'q':               q,
        'requesting_staff': requesting_staff,
    })


@superuser_view
@require_POST
def task_save(request, pk=None):
    requesting_staff = _get_requesting_staff(request)

    if pk:
        task = get_object_or_404(StaffTask, pk=pk)
    else:
        task = StaffTask()

    assignee_id = request.POST.get('assigned_to')
    try:
        assignee = StaffMember.objects.get(pk=assignee_id)
    except StaffMember.DoesNotExist:
        messages.error(request, 'Invalid assignee.')
        return redirect('superuser:tasks_list')

    # Verify permission
    if requesting_staff and not requesting_staff.can_add_staff_at_level(assignee.hierarchy_level):
        messages.error(request, 'You cannot assign tasks to this staff member.')
        return redirect('superuser:tasks_list')

    task.title       = request.POST.get('title', '').strip()
    task.description = request.POST.get('description', '')
    task.category    = request.POST.get('category', 'other')
    task.priority    = request.POST.get('priority', StaffTask.PRIORITY_MEDIUM)
    task.status      = request.POST.get('status', StaffTask.STATUS_TODO)
    task.assigned_to = assignee
    task.assigned_by = request.user
    task.notes       = request.POST.get('notes', '')
    due = request.POST.get('due_date', '')
    task.due_date    = due or None
    task.save()

    messages.success(request, f'Task "{task.title}" saved.')
    return redirect('superuser:tasks_list')


@superuser_view
@require_POST
def task_status_update(request, pk):
    """Quick AJAX-friendly status update."""
    task = get_object_or_404(StaffTask, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(StaffTask.STATUS_CHOICES):
        task.status = new_status
        task.save(update_fields=['status', 'updated_at', 'started_at', 'completed_at'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'status': task.get_status_display()})
    return redirect('superuser:tasks_list')


@superuser_view
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(StaffTask, pk=pk)
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('superuser:tasks_list')