"""
finance/tests.py
────────────────
Test suite for the finance app.

Run with:
    python manage.py test finance

Coverage
─────────
  Models:  Expense CRUD, Payment.mark_success, PaymentSettings.is_configured
  Views:   All admin views — GET rendering, POST logic, CSV export, edge cases
  URLs:    All named URL patterns resolve correctly
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — create shared test fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_library(user):
    """Return a Library object associated with the given user.
    Adjust the import/creation path to match your accounts app."""
    from accounts.models import Library
    lib, _ = Library.objects.get_or_create(user=user, defaults={"name": "Test Library"})
    # Attach library to user via the expected attribute
    user.library = lib
    return lib


def _make_member(library):
    from members.models import Member
    return Member.objects.create(
        library=library,
        first_name="Arjun",
        last_name="Sen",
        email="arjun@test.com",
        phone="9000000001",
    )


def _make_book(library):
    from books.models import Book
    return Book.objects.create(
        library=library,
        title="Wings of Fire",
        author="A.P.J. Abdul Kalam",
        total_copies=3,
        available_copies=2,
    )


def _make_transaction(library, member, book):
    from transactions.models import Transaction
    return Transaction.objects.create(
        library=library,
        member=member,
        book=book,
        issue_date=date.today() - timedelta(days=20),
        due_date=date.today() - timedelta(days=6),
        status="overdue",
    )


def _make_fine(transaction, amount=Decimal("30.00")):
    from transactions.models import Fine
    return Fine.objects.create(
        transaction=transaction,
        fine_type="overdue",
        amount=amount,
        status=Fine.STATUS_UNPAID,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Base test case with shared setUp
# ─────────────────────────────────────────────────────────────────────────────

class FinanceTestBase(TestCase):
    def setUp(self):
        self.client   = Client()
        self.user     = User.objects.create_user(
            username="librarian", password="pass1234", email="lib@test.com"
        )
        self.library  = _make_library(self.user)
        self.member   = _make_member(self.library)
        self.book     = _make_book(self.library)
        self.txn      = _make_transaction(self.library, self.member, self.book)
        self.fine     = _make_fine(self.txn)
        self.client.login(username="librarian", password="pass1234")


# ─────────────────────────────────────────────────────────────────────────────
# Model tests
# ─────────────────────────────────────────────────────────────────────────────

class PaymentSettingsModelTest(FinanceTestBase):
    def test_is_configured_false_when_inactive(self):
        from finance.models import PaymentSettings
        ps, _ = PaymentSettings.objects.get_or_create(library=self.library)
        ps.is_active = False
        ps.save()
        self.assertFalse(ps.is_configured())

    def test_is_configured_false_when_no_key(self):
        from finance.models import PaymentSettings
        ps, _ = PaymentSettings.objects.get_or_create(library=self.library)
        ps.is_active = True
        ps.key_id = ""
        ps.save()
        self.assertFalse(ps.is_configured())

    def test_is_configured_true(self):
        from finance.models import PaymentSettings
        ps, _ = PaymentSettings.objects.get_or_create(library=self.library)
        ps.is_active  = True
        ps.key_id     = "rzp_test_abc"
        ps.key_secret = "secret_xyz"
        ps.save()
        self.assertTrue(ps.is_configured())

    def test_key_secret_encrypt_decrypt_roundtrip(self):
        from finance.models import PaymentSettings
        ps, _ = PaymentSettings.objects.get_or_create(library=self.library)
        ps.key_secret = "my_secret_key"
        ps.save()
        ps.refresh_from_db()
        self.assertEqual(ps.key_secret, "my_secret_key")
        # Raw DB column should NOT equal the plain text
        self.assertNotEqual(ps._key_secret_enc, "my_secret_key")


class PaymentMarkSuccessTest(FinanceTestBase):
    def test_mark_success_sets_fine_paid(self):
        from django.db import transaction as dbt
        from finance.models import Payment
        from transactions.models import Fine

        payment = Payment.objects.create(
            library=self.library,
            fine=self.fine,
            method=Payment.METHOD_CASH,
            status=Payment.STATUS_PENDING,
            amount=self.fine.amount,
        )
        with dbt.atomic():
            payment.mark_success()

        payment.refresh_from_db()
        self.fine.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(self.fine.status, Fine.STATUS_PAID)

    def test_mark_success_is_idempotent(self):
        from django.db import transaction as dbt
        from finance.models import Payment

        payment = Payment.objects.create(
            library=self.library,
            fine=self.fine,
            method=Payment.METHOD_CASH,
            status=Payment.STATUS_PENDING,
            amount=self.fine.amount,
        )
        with dbt.atomic():
            payment.mark_success()
        original_updated = payment.updated_at
        with dbt.atomic():
            payment.mark_success()  # second call — should be no-op
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)

    def test_mark_failed(self):
        from finance.models import Payment
        payment = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=Payment.METHOD_ONLINE, status=Payment.STATUS_PENDING,
            amount=self.fine.amount,
        )
        payment.mark_failed()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_FAILED)


class ExpenseModelTest(FinanceTestBase):
    def test_create_expense(self):
        from finance.models import Expense
        exp = Expense.objects.create(
            library=self.library,
            date=date.today(),
            description="Bought new shelves",
            amount=Decimal("1500.00"),
            category="Maintenance",
            recorded_by="Librarian",
        )
        self.assertEqual(str(exp.amount), "1500.00")
        self.assertEqual(exp.category, "Maintenance")

    def test_for_library_scope(self):
        from finance.models import Expense
        other_user = User.objects.create_user(username="other", password="pass")
        other_lib  = _make_library(other_user)
        Expense.objects.create(library=other_lib, description="Other", amount=100, date=date.today())
        Expense.objects.create(library=self.library, description="Mine",  amount=200, date=date.today())
        self.assertEqual(Expense.objects.for_library(self.library).count(), 1)


# ─────────────────────────────────────────────────────────────────────────────
# View tests
# ─────────────────────────────────────────────────────────────────────────────

class ProcessPaymentViewTest(FinanceTestBase):
    def test_get_with_valid_fine(self):
        url = reverse("finance:process_payment") + f"?fine_id={self.fine.pk}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.member.first_name)
        self.assertContains(resp, str(self.fine.amount))

    def test_get_without_fine_id(self):
        resp = self.client.get(reverse("finance:process_payment"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["fine"])

    def test_get_with_wrong_library_fine(self):
        other_user = User.objects.create_user(username="other2", password="pass")
        other_lib  = _make_library(other_user)
        other_m    = _make_member(other_lib)
        other_b    = _make_book(other_lib)
        other_t    = _make_transaction(other_lib, other_m, other_b)
        other_f    = _make_fine(other_t)
        url  = reverse("finance:process_payment") + f"?fine_id={other_f.pk}"
        resp = self.client.get(url)
        # Should render with fine=None (not leaked to wrong library)
        self.assertIsNone(resp.context["fine"])


class CashPaymentViewTest(FinanceTestBase):
    def _post(self, extra=None):
        data = {
            "fine_id":        self.fine.pk,
            "receipt_number": "RCP-001",
            "collected_by":   "Test Staff",
            "next":           "/",
        }
        if extra:
            data.update(extra)
        return self.client.post(reverse("finance:cash_payment"), data)

    def test_successful_cash_payment(self):
        from finance.models import Payment
        from transactions.models import Fine
        resp = self._post()
        self.assertRedirects(resp, "/", fetch_redirect_response=False)
        self.fine.refresh_from_db()
        self.assertEqual(self.fine.status, Fine.STATUS_PAID)
        self.assertTrue(
            Payment.objects.filter(fine=self.fine, method=Payment.METHOD_CASH).exists()
        )

    def test_double_payment_rejected(self):
        from transactions.models import Fine
        self._post()
        self.fine.refresh_from_db()
        self.assertEqual(self.fine.status, Fine.STATUS_PAID)
        # Second attempt should redirect with a warning, not create another payment
        resp2 = self._post()
        self.assertEqual(resp2.status_code, 302)

    def test_post_only(self):
        resp = self.client.get(reverse("finance:cash_payment"))
        self.assertEqual(resp.status_code, 405)


class ConfirmRecoveryViewTest(FinanceTestBase):
    def test_get_renders(self):
        url  = reverse("finance:confirm_recovery") + f"?fine_id={self.fine.pk}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, str(self.fine.amount))

    def test_get_wrong_fine_404(self):
        url  = reverse("finance:confirm_recovery") + "?fine_id=99999"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


class PaymentReceiptViewTest(FinanceTestBase):
    def _create_payment(self):
        from django.db import transaction as dbt
        from finance.models import Payment
        p = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=Payment.METHOD_CASH, status=Payment.STATUS_PENDING,
            amount=self.fine.amount, receipt_number="RCP-999",
        )
        with dbt.atomic():
            p.mark_success()
        return p

    def test_receipt_renders(self):
        payment = self._create_payment()
        url     = reverse("finance:payment_receipt", args=[payment.pk])
        resp    = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "RCP-999")

    def test_receipt_wrong_library_404(self):
        other_user = User.objects.create_user(username="other3", password="pass")
        other_lib  = _make_library(other_user)
        from finance.models import Payment
        p = Payment.objects.create(
            library=other_lib, fine=self.fine,
            method=Payment.METHOD_CASH, status=Payment.STATUS_SUCCESS,
            amount=self.fine.amount,
        )
        url  = reverse("finance:payment_receipt", args=[p.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


class IncomeListViewTest(FinanceTestBase):
    def _create_payment(self, amount=Decimal("50.00"), method="cash"):
        from django.db import transaction as dbt
        from finance.models import Payment
        p = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=method, status=Payment.STATUS_PENDING, amount=amount,
        )
        with dbt.atomic():
            p.mark_success()
        return p

    def test_list_renders(self):
        self._create_payment()
        resp = self.client.get(reverse("finance:income_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("payments", resp.context)

    def test_stats_correct(self):
        self._create_payment(amount=Decimal("40.00"), method="cash")
        resp = self.client.get(reverse("finance:income_list"))
        self.assertEqual(resp.context["total_income"], Decimal("40.00"))
        self.assertEqual(resp.context["cash_income"],  Decimal("40.00"))

    def test_csv_export(self):
        self._create_payment()
        resp = self.client.get(reverse("finance:income_list") + "?export=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])

    def test_method_filter(self):
        self._create_payment(method="cash")
        resp = self.client.get(reverse("finance:income_list") + "?method=online")
        self.assertEqual(resp.context["total_count"], 0)


class ExpenseViewTest(FinanceTestBase):
    def test_add_get(self):
        resp = self.client.get(reverse("finance:add_expense"))
        self.assertEqual(resp.status_code, 200)

    def test_add_post_creates_expense(self):
        from finance.models import Expense
        resp = self.client.post(reverse("finance:add_expense"), {
            "date":        date.today().isoformat(),
            "description": "Bought pens",
            "amount":      "250.00",
            "category":    "Stationery",
            "recorded_by": "Staff",
        })
        self.assertRedirects(resp, reverse("finance:expense_list"), fetch_redirect_response=False)
        self.assertTrue(Expense.objects.filter(description="Bought pens").exists())

    def test_add_post_missing_required(self):
        resp = self.client.post(reverse("finance:add_expense"), {"amount": "100"})
        # Should stay on the form with an error message
        self.assertEqual(resp.status_code, 200)

    def test_edit_expense(self):
        from finance.models import Expense
        exp = Expense.objects.create(
            library=self.library, date=date.today(),
            description="Old desc", amount=Decimal("100.00"),
        )
        resp = self.client.post(
            reverse("finance:edit_expense", args=[exp.pk]),
            {
                "date": date.today().isoformat(), "description": "New desc",
                "amount": "200.00", "category": "Books",
            },
        )
        self.assertRedirects(resp, reverse("finance:expense_list"), fetch_redirect_response=False)
        exp.refresh_from_db()
        self.assertEqual(exp.description, "New desc")

    def test_delete_expense(self):
        from finance.models import Expense
        exp = Expense.objects.create(
            library=self.library, date=date.today(),
            description="To delete", amount=Decimal("50.00"),
        )
        resp = self.client.post(reverse("finance:delete_expense", args=[exp.pk]))
        self.assertRedirects(resp, reverse("finance:expense_list"), fetch_redirect_response=False)
        self.assertFalse(Expense.objects.filter(pk=exp.pk).exists())

    def test_expense_list_renders(self):
        resp = self.client.get(reverse("finance:expense_list"))
        self.assertEqual(resp.status_code, 200)

    def test_expense_csv(self):
        resp = self.client.get(reverse("finance:expense_list") + "?export=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])


class CashBookViewTest(FinanceTestBase):
    def test_renders_empty(self):
        resp = self.client.get(reverse("finance:cash_book"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("entries", resp.context)

    def test_credit_entries_from_payments(self):
        from django.db import transaction as dbt
        from finance.models import Payment
        p = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=Payment.METHOD_CASH, status=Payment.STATUS_PENDING,
            amount=Decimal("60.00"),
        )
        with dbt.atomic():
            p.mark_success()

        resp    = self.client.get(reverse("finance:cash_book"))
        entries = resp.context["entries"]
        credits = [e for e in entries if e["entry_type"] == "credit"]
        self.assertEqual(len(credits), 1)
        self.assertEqual(resp.context["total_credits"], Decimal("60.00"))

    def test_debit_entries_from_expenses(self):
        from finance.models import Expense
        Expense.objects.create(
            library=self.library, date=date.today(),
            description="Paper", amount=Decimal("80.00"),
        )
        resp    = self.client.get(reverse("finance:cash_book"))
        entries = resp.context["entries"]
        debits  = [e for e in entries if e["entry_type"] == "debit"]
        self.assertEqual(len(debits), 1)
        self.assertEqual(resp.context["total_debits"], Decimal("80.00"))

    def test_running_balance(self):
        from django.db import transaction as dbt
        from finance.models import Expense, Payment
        p = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=Payment.METHOD_CASH, status=Payment.STATUS_PENDING,
            amount=Decimal("100.00"),
        )
        with dbt.atomic():
            p.mark_success()
        Expense.objects.create(
            library=self.library, date=date.today(),
            description="Ink", amount=Decimal("30.00"),
        )
        resp    = self.client.get(reverse("finance:cash_book"))
        self.assertEqual(resp.context["closing_balance"], Decimal("70.00"))

    def test_csv_export(self):
        resp = self.client.get(reverse("finance:cash_book") + "?export=csv")
        self.assertIn("text/csv", resp["Content-Type"])


class DailyCollectionViewTest(FinanceTestBase):
    def test_renders_today(self):
        resp = self.client.get(reverse("finance:daily_collection"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["selected_date"], date.today())

    def test_renders_specific_date(self):
        d    = (date.today() - timedelta(days=3)).isoformat()
        resp = self.client.get(reverse("finance:daily_collection") + f"?date={d}")
        self.assertEqual(resp.status_code, 200)

    def test_totals(self):
        from django.db import transaction as dbt
        from finance.models import Payment
        p = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=Payment.METHOD_CASH, status=Payment.STATUS_PENDING,
            amount=Decimal("45.00"),
        )
        with dbt.atomic():
            p.mark_success()

        resp = self.client.get(reverse("finance:daily_collection"))
        self.assertEqual(resp.context["cash_total"], Decimal("45.00"))
        self.assertEqual(resp.context["day_total"],  Decimal("45.00"))


class FinanceReportsViewTest(FinanceTestBase):
    def test_renders(self):
        resp = self.client.get(reverse("finance:overview"))
        self.assertEqual(resp.status_code, 200)

    def test_all_periods(self):
        for period in ("this_month", "last_month", "this_year"):
            resp = self.client.get(reverse("finance:overview") + f"?period={period}")
            self.assertEqual(resp.status_code, 200)

    def test_context_keys_present(self):
        resp = self.client.get(reverse("finance:overview"))
        for key in ("total_income", "total_expenses", "net_surplus",
                    "pending_fines", "monthly_labels", "monthly_data"):
            self.assertIn(key, resp.context)

    def test_monthly_labels_valid_json(self):
        resp    = self.client.get(reverse("finance:overview"))
        labels  = json.loads(resp.context["monthly_labels"])
        self.assertEqual(len(labels), 12)

    def test_csv_export(self):
        resp = self.client.get(reverse("finance:overview") + "?export=csv")
        self.assertIn("text/csv", resp["Content-Type"])


class ProfitLossViewTest(FinanceTestBase):
    def test_renders(self):
        resp = self.client.get(reverse("finance:profit_loss"))
        self.assertEqual(resp.status_code, 200)

    def test_net_surplus_calculation(self):
        from django.db import transaction as dbt
        from finance.models import Expense, Payment
        p = Payment.objects.create(
            library=self.library, fine=self.fine,
            method=Payment.METHOD_CASH, status=Payment.STATUS_PENDING,
            amount=Decimal("200.00"),
        )
        with dbt.atomic():
            p.mark_success()
        Expense.objects.create(
            library=self.library, date=date.today(),
            description="Maintenance", amount=Decimal("50.00"), category="Maintenance",
        )
        resp = self.client.get(reverse("finance:profit_loss"))
        self.assertEqual(resp.context["net_surplus"], Decimal("150.00"))

    def test_income_breakdown_only_nonzero(self):
        resp = self.client.get(reverse("finance:profit_loss"))
        for item in resp.context["income_breakdown"]:
            self.assertGreater(item["amount"], 0)

    def test_chart_data_is_valid_json(self):
        resp = self.client.get(reverse("finance:profit_loss"))
        self.assertEqual(len(json.loads(resp.context["chart_labels"])), 12)
        self.assertEqual(len(json.loads(resp.context["chart_income"])), 12)
        self.assertEqual(len(json.loads(resp.context["chart_expenses"])), 12)


# ─────────────────────────────────────────────────────────────────────────────
# URL resolution tests
# ─────────────────────────────────────────────────────────────────────────────

class URLResolutionTest(TestCase):
    """Ensure every named URL resolves to the expected path."""

    URL_CASES = [
        ("finance:process_payment",  "/finance/process/"),
        ("finance:cash_payment",     "/finance/cash/"),
        ("finance:confirm_recovery", "/finance/confirm/"),
        ("finance:income_list",      "/finance/income/"),
        ("finance:expense_list",     "/finance/expenses/"),
        ("finance:add_expense",      "/finance/expenses/add/"),
        ("finance:cash_book",        "/finance/cash-book/"),
        ("finance:daily_collection", "/finance/daily/"),
        ("finance:overview",         "/finance/reports/"),
        ("finance:profit_loss",      "/finance/profit-loss/"),
        ("finance:member_fine_summary", "/finance/my-fines/"),
        ("finance:create_online_order", "/finance/order/"),
        ("finance:payment_success",  "/finance/success/"),
    ]

    def test_urls_resolve(self):
        for name, expected_path in self.URL_CASES:
            with self.subTest(name=name):
                self.assertEqual(reverse(name), expected_path)

    def test_parametric_urls(self):
        self.assertEqual(reverse("finance:payment_receipt",  args=[1]),   "/finance/receipt/1/")
        self.assertEqual(reverse("finance:edit_expense",     args=[42]),  "/finance/expenses/42/edit/")
        self.assertEqual(reverse("finance:delete_expense",   args=[42]),  "/finance/expenses/42/delete/")
        self.assertEqual(reverse("finance:razorpay_webhook", args=[5]),   "/finance/webhook/razorpay/5/")


# ─────────────────────────────────────────────────────────────────────────────
# Authentication tests
# ─────────────────────────────────────────────────────────────────────────────

class AuthRedirectTest(TestCase):
    """Unauthenticated requests to @login_required views must redirect."""

    PROTECTED_URLS = [
        "/finance/process/",
        "/finance/income/",
        "/finance/expenses/",
        "/finance/expenses/add/",
        "/finance/cash-book/",
        "/finance/daily/",
        "/finance/reports/",
        "/finance/profit-loss/",
        "/finance/my-fines/",
        "/finance/success/",
    ]

    def test_redirect_when_not_logged_in(self):
        c = Client()
        for url in self.PROTECTED_URLS:
            with self.subTest(url=url):
                resp = c.get(url)
                self.assertIn(resp.status_code, (302, 301), msg=f"{url} should redirect")
