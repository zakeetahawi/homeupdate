"""
اختبارات نماذج النظام المحاسبي
Accounting Models Tests
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounting.models import (
    Account,
    AccountType,
    Transaction,
    TransactionLine,
)

User = get_user_model()


class AccountTypeTestCase(TestCase):
    """اختبارات نوع الحساب"""

    def test_create_account_type(self):
        at = AccountType.objects.create(
            name="أصول اختبار",
            category="asset",
            code_prefix="99",
            normal_balance="debit",
        )
        self.assertEqual(str(at), "99 - أصول اختبار")
        self.assertTrue(at.is_active)


class AccountTestCase(TestCase):
    """اختبارات الحسابات"""

    def setUp(self):
        self.account_type = AccountType.objects.create(
            name="أصول",
            category="asset",
            code_prefix="1",
            normal_balance="debit",
        )
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_create_account(self):
        account = Account.objects.create(
            code="1001",
            name="حساب اختبار",
            account_type=self.account_type,
        )
        self.assertEqual(str(account), "1001 - حساب اختبار")
        self.assertTrue(account.is_active)
        self.assertEqual(account.current_balance, Decimal("0.00"))

    def test_account_level_no_parent(self):
        account = Account.objects.create(
            code="1000", name="جذر", account_type=self.account_type
        )
        self.assertEqual(account.level, 0)

    def test_account_level_with_parent(self):
        parent = Account.objects.create(
            code="1000", name="أب", account_type=self.account_type
        )
        child = Account.objects.create(
            code="1001", name="ابن", account_type=self.account_type, parent=parent
        )
        grandchild = Account.objects.create(
            code="1002", name="حفيد", account_type=self.account_type, parent=child
        )
        self.assertEqual(parent.level, 0)
        self.assertEqual(child.level, 1)
        self.assertEqual(grandchild.level, 2)

    def test_account_full_path(self):
        parent = Account.objects.create(
            code="1000", name="الأصول", account_type=self.account_type
        )
        child = Account.objects.create(
            code="1001", name="النقد", account_type=self.account_type, parent=parent
        )
        self.assertEqual(child.full_path, "الأصول > النقد")

    def test_account_clean_self_parent(self):
        account = Account.objects.create(
            code="1000", name="حساب", account_type=self.account_type
        )
        account.parent = account
        with self.assertRaises(ValidationError) as cm:
            account.clean()
        self.assertIn("parent", cm.exception.message_dict)

    def test_account_clean_circular_reference(self):
        a = Account.objects.create(
            code="1000", name="أ", account_type=self.account_type
        )
        b = Account.objects.create(
            code="1001", name="ب", account_type=self.account_type, parent=a
        )
        c = Account.objects.create(
            code="1002", name="ج", account_type=self.account_type, parent=b
        )
        # محاولة جعل a ابن c (حلقة دائرية)
        a.parent = c
        with self.assertRaises(ValidationError) as cm:
            a.clean()
        self.assertIn("parent", cm.exception.message_dict)

    def test_has_children(self):
        parent = Account.objects.create(
            code="1000", name="أب", account_type=self.account_type
        )
        self.assertFalse(parent.has_children)
        Account.objects.create(
            code="1001", name="ابن", account_type=self.account_type, parent=parent
        )
        self.assertTrue(parent.has_children)

    def test_get_balance_debit_account(self):
        account = Account.objects.create(
            code="1001",
            name="نقد",
            account_type=self.account_type,
            opening_balance=Decimal("1000.00"),
        )
        # لا قيود بعد
        self.assertEqual(account.get_balance(), Decimal("1000.00"))

    def test_update_balance(self):
        account = Account.objects.create(
            code="1001",
            name="نقد",
            account_type=self.account_type,
            opening_balance=Decimal("500.00"),
        )
        account.update_balance()
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("500.00"))


class TransactionTestCase(TestCase):
    """اختبارات القيود المحاسبية"""

    def setUp(self):
        self.asset_type = AccountType.objects.create(
            name="أصول", category="asset", code_prefix="1", normal_balance="debit"
        )
        self.revenue_type = AccountType.objects.create(
            name="إيرادات", category="revenue", code_prefix="4", normal_balance="credit"
        )
        self.cash = Account.objects.create(
            code="1001", name="نقد", account_type=self.asset_type
        )
        self.revenue = Account.objects.create(
            code="4001", name="إيرادات مبيعات", account_type=self.revenue_type
        )
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def _create_balanced_txn(self, amount=Decimal("100.00"), status="draft"):
        txn = Transaction.objects.create(
            transaction_type="payment",
            description="قيد اختبار",
            created_by=self.user,
            status=status,
        )
        TransactionLine.objects.create(
            transaction=txn, account=self.cash, debit=amount, credit=Decimal("0")
        )
        TransactionLine.objects.create(
            transaction=txn, account=self.revenue, debit=Decimal("0"), credit=amount
        )
        txn.calculate_totals()
        return txn

    def test_generate_transaction_number(self):
        txn = self._create_balanced_txn()
        self.assertTrue(txn.transaction_number.startswith("TXN-"))

    def test_is_balanced(self):
        txn = self._create_balanced_txn()
        self.assertTrue(txn.is_balanced)

    def test_calculate_totals(self):
        txn = self._create_balanced_txn(Decimal("250.00"))
        self.assertEqual(txn.total_debit, Decimal("250.00"))
        self.assertEqual(txn.total_credit, Decimal("250.00"))

    def test_post_balanced(self):
        txn = self._create_balanced_txn()
        txn.post(self.user)
        txn.refresh_from_db()
        self.assertEqual(txn.status, "posted")
        self.assertIsNotNone(txn.posted_at)
        self.assertEqual(txn.posted_by, self.user)

    def test_post_updates_balances(self):
        txn = self._create_balanced_txn(Decimal("100.00"))
        txn.post(self.user)
        self.cash.refresh_from_db()
        self.revenue.refresh_from_db()
        # النقد (مدين طبيعي): opening(0) + debit(100) - credit(0) = 100
        self.assertEqual(self.cash.current_balance, Decimal("100.00"))
        # الإيرادات (دائن طبيعي): opening(0) + credit(100) - debit(0) = 100
        self.assertEqual(self.revenue.current_balance, Decimal("100.00"))

    def test_post_unbalanced_raises(self):
        txn = Transaction.objects.create(
            transaction_type="payment",
            description="غير متوازن",
            created_by=self.user,
        )
        TransactionLine.objects.create(
            transaction=txn, account=self.cash, debit=Decimal("100"), credit=Decimal("0")
        )
        TransactionLine.objects.create(
            transaction=txn, account=self.revenue, debit=Decimal("0"), credit=Decimal("50")
        )
        txn.calculate_totals()
        with self.assertRaises(ValueError, msg="القيد غير متوازن"):
            txn.post(self.user)

    def test_post_already_posted_raises(self):
        txn = self._create_balanced_txn()
        txn.post(self.user)
        with self.assertRaises(ValueError, msg="مرحّل مسبقاً"):
            txn.post(self.user)

    def test_post_cancelled_raises(self):
        txn = self._create_balanced_txn()
        txn.status = "cancelled"
        txn.save(update_fields=["status"])
        with self.assertRaises(ValueError, msg="ملغي"):
            txn.post(self.user)

    def test_post_less_than_2_lines_raises(self):
        txn = Transaction.objects.create(
            transaction_type="payment",
            description="سطر واحد",
            created_by=self.user,
        )
        TransactionLine.objects.create(
            transaction=txn, account=self.cash, debit=Decimal("0"), credit=Decimal("0")
        )
        txn.calculate_totals()
        with self.assertRaises(ValueError, msg="سطرين"):
            txn.post(self.user)

    def test_post_inactive_account_raises(self):
        self.cash.is_active = False
        self.cash.save(update_fields=["is_active"])
        txn = self._create_balanced_txn()
        with self.assertRaises(ValueError, msg="غير نشط"):
            txn.post(self.user)

    def test_post_account_no_transactions_raises(self):
        self.cash.allow_transactions = False
        self.cash.save(update_fields=["allow_transactions"])
        txn = self._create_balanced_txn()
        with self.assertRaises(ValueError, msg="لا يسمح بالقيود"):
            txn.post(self.user)

    def test_cancel_posted(self):
        txn = self._create_balanced_txn()
        txn.post(self.user)
        txn.cancel(self.user)
        txn.refresh_from_db()
        self.assertEqual(txn.status, "cancelled")

    def test_cancel_already_cancelled_raises(self):
        txn = self._create_balanced_txn()
        txn.cancel(self.user)
        with self.assertRaises(ValueError, msg="ملغي مسبقاً"):
            txn.cancel(self.user)

    def test_create_reversal(self):
        txn = self._create_balanced_txn(Decimal("200.00"))
        txn.post(self.user)
        reversal = txn.create_reversal(self.user)
        self.assertEqual(reversal.status, "draft")
        self.assertEqual(reversal.lines.count(), 2)
        # التحقق من عكس المبالغ
        rev_cash_line = reversal.lines.get(account=self.cash)
        self.assertEqual(rev_cash_line.debit, Decimal("0.00"))
        self.assertEqual(rev_cash_line.credit, Decimal("200.00"))

    def test_create_reversal_non_posted_raises(self):
        txn = self._create_balanced_txn()
        with self.assertRaises(ValueError, msg="مرحّلة فقط"):
            txn.create_reversal(self.user)


class TransactionLineTestCase(TestCase):
    """اختبارات بنود القيد"""

    def setUp(self):
        self.account_type = AccountType.objects.create(
            name="أصول", category="asset", code_prefix="1", normal_balance="debit"
        )
        self.account = Account.objects.create(
            code="1001", name="نقد", account_type=self.account_type
        )
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.txn = Transaction.objects.create(
            transaction_type="payment",
            description="اختبار",
            created_by=self.user,
        )

    def test_create_line(self):
        line = TransactionLine.objects.create(
            transaction=self.txn,
            account=self.account,
            debit=Decimal("100.00"),
            credit=Decimal("0.00"),
            description="بند اختبار",
        )
        self.assertIn("1001", str(line))
        self.assertIn("100", str(line))

    def test_line_clean_both_positive_raises(self):
        line = TransactionLine(
            transaction=self.txn,
            account=self.account,
            debit=Decimal("100.00"),
            credit=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError):
            line.clean()

    def test_line_clean_both_zero_raises(self):
        line = TransactionLine(
            transaction=self.txn,
            account=self.account,
            debit=Decimal("0.00"),
            credit=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            line.clean()
