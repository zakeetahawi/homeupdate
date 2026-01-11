"""
إشارات النظام المحاسبي - التكامل التلقائي
Accounting Signals - Auto Integration
"""

from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

# ============================================
# إشارات المدفوعات
# Payment Signals
# ============================================


def create_payment_transaction(payment):
    """
    إنشاء قيد محاسبي للدفعة
    """
    from .models import Account, AccountingSettings, Transaction, TransactionLine

    try:
        settings = AccountingSettings.objects.first()
        if not settings:
            return None

        # الحصول على الحسابات
        cash_account = settings.default_cash_account
        receivables_account = settings.default_receivables_account

        if not cash_account or not receivables_account:
            return None

        # البحث عن حساب العميل إن وجد
        customer_account = None
        if payment.order and payment.order.customer:
            customer_account = Account.objects.filter(
                customer=payment.order.customer, is_customer_account=True
            ).first()

        # استخدام حساب العميل أو حساب المدينين العام
        debit_from = customer_account or receivables_account

        with db_transaction.atomic():
            # إنشاء القيد
            txn = Transaction.objects.create(
                transaction_date=(
                    payment.payment_date
                    if hasattr(payment, "payment_date")
                    else timezone.now().date()
                ),
                transaction_type="receipt",
                description=f"استلام دفعة للطلب {payment.order.order_number}",
                notes=(
                    f"رقم إيصال: {payment.receipt_number}"
                    if hasattr(payment, "receipt_number")
                    else ""
                ),
                order=payment.order,
                customer=payment.order.customer if payment.order else None,
                is_auto_generated=True,
                status="posted" if settings.auto_post_transactions else "draft",
            )

            # مدين - الصندوق/البنك
            TransactionLine.objects.create(
                transaction=txn,
                account=cash_account,
                debit_amount=payment.amount,
                credit_amount=Decimal("0"),
                description=f'استلام نقدي من {payment.order.customer.name if payment.order and payment.order.customer else "عميل"}',
            )

            # دائن - المدينين/حساب العميل
            TransactionLine.objects.create(
                transaction=txn,
                account=debit_from,
                debit_amount=Decimal("0"),
                credit_amount=payment.amount,
                description=f"تسديد مديونية للطلب {payment.order.order_number}",
            )

            txn.check_balance()
            txn.save()

            return txn
    except Exception as e:
        print(f"Error creating payment transaction: {e}")
        return None


def create_order_transaction(order):
    """
    إنشاء قيد محاسبي للطلب الجديد
    """
    from .models import Account, AccountingSettings, Transaction, TransactionLine

    try:
        settings = AccountingSettings.objects.first()
        if not settings:
            return None

        receivables_account = settings.default_receivables_account
        revenue_account = settings.default_revenue_account

        if not receivables_account or not revenue_account:
            return None

        # البحث عن حساب العميل
        customer_account = None
        if order.customer:
            customer_account = Account.objects.filter(
                customer=order.customer, is_customer_account=True
            ).first()

        # استخدام حساب العميل أو حساب المدينين العام
        debit_to = customer_account or receivables_account

        # حساب المبلغ الإجمالي - استخدم السعر النهائي بعد الخصم
        total_amount = (
            order.final_price_after_discount
            if hasattr(order, "final_price_after_discount")
            else Decimal("0")
        )
        if total_amount <= 0:
            return None

        with db_transaction.atomic():
            txn = Transaction.objects.create(
                transaction_date=(
                    order.order_date
                    if hasattr(order, "order_date")
                    else timezone.now().date()
                ),
                transaction_type="sales",
                description=f"إيراد مبيعات - طلب {order.order_number}",
                order=order,
                customer=order.customer,
                is_auto_generated=True,
                status="posted" if settings.auto_post_transactions else "draft",
            )

            # مدين - المدينين/حساب العميل
            TransactionLine.objects.create(
                transaction=txn,
                account=debit_to,
                debit_amount=total_amount,
                credit_amount=Decimal("0"),
                description=f"مديونية طلب {order.order_number}",
            )

            # دائن - الإيرادات
            TransactionLine.objects.create(
                transaction=txn,
                account=revenue_account,
                debit_amount=Decimal("0"),
                credit_amount=total_amount,
                description=f"إيراد طلب {order.order_number}",
            )

            txn.check_balance()
            txn.save()

            return txn
    except Exception as e:
        print(f"Error creating order transaction: {e}")
        return None


# ============================================
# إشارات العربونات
# Deposit Signals
# ============================================


def create_advance_transaction(advance):
    """
    إنشاء قيد محاسبي لعربون العميل
    """
    from .models import Account, AccountingSettings, Transaction, TransactionLine

    try:
        settings = AccountingSettings.objects.first()
        if not settings:
            return None

        cash_account = settings.default_cash_account
        advances_account = settings.default_advances_account

        if not cash_account or not advances_account:
            return None

        with db_transaction.atomic():
            txn = Transaction.objects.create(
                transaction_date=(
                    advance.created_at.date()
                    if advance.created_at
                    else timezone.now().date()
                ),
                transaction_type="receipt",
                description=f"استلام عربون من {advance.customer.name}",
                notes=f"حالة العربون: {advance.get_status_display()}",
                customer=advance.customer,
                customer_advance=advance,
                is_auto_generated=True,
                status="posted" if settings.auto_post_transactions else "draft",
            )

            # مدين - الصندوق
            TransactionLine.objects.create(
                transaction=txn,
                account=cash_account,
                debit_amount=advance.amount,
                credit_amount=Decimal("0"),
                description=f"استلام عربون نقدي",
            )

            # دائن - عربونات العملاء (التزام)
            TransactionLine.objects.create(
                transaction=txn,
                account=advances_account,
                debit_amount=Decimal("0"),
                credit_amount=advance.amount,
                description=f"عربون {advance.customer.name}",
            )

            txn.check_balance()
            txn.save()

            # ربط القيد بالسلفة
            advance.transaction = txn
            advance.save(update_fields=["transaction"])

            return txn
    except Exception as e:
        print(f"Error creating advance transaction: {e}")
        return None


# ============================================
# إشارات تحديث الملخص المالي
# Financial Summary Update Signals
# ============================================


def update_customer_financial_summary(customer):
    """
    تحديث الملخص المالي للعميل
    """
    from .models import CustomerFinancialSummary

    try:
        summary, created = CustomerFinancialSummary.objects.get_or_create(
            customer=customer
        )
        summary.refresh()
    except Exception as e:
        print(f"Error updating customer financial summary: {e}")


# ============================================
# تسجيل الإشارات
# Signal Registration
# ============================================


def register_order_signals():
    """
    تسجيل إشارات الطلبات
    """
    try:
        from orders.models import Order, Payment

        @receiver(post_save, sender=Payment)
        def payment_saved(sender, instance, created, **kwargs):
            if created:
                create_payment_transaction(instance)
                # تحديث الملخص المالي
                if instance.order and instance.order.customer:
                    update_customer_financial_summary(instance.order.customer)

        @receiver(post_save, sender=Order)
        def order_saved(sender, instance, created, **kwargs):
            if created:
                # إنشاء قيد المبيعات
                create_order_transaction(instance)
            # تحديث الملخص المالي
            if instance.customer:
                update_customer_financial_summary(instance.customer)

        print("Accounting signals registered for orders app")
    except ImportError:
        print("Orders app not found, skipping order signals")


def register_accounting_signals():
    """
    تسجيل إشارات النظام المحاسبي
    """
    from .models import CustomerAdvance, Transaction

    @receiver(post_save, sender=CustomerAdvance)
    def advance_saved(sender, instance, created, **kwargs):
        if created and not instance.transaction:
            create_advance_transaction(instance)
        # تحديث الملخص المالي
        update_customer_financial_summary(instance.customer)

    @receiver(post_save, sender=Transaction)
    def transaction_posted(sender, instance, **kwargs):
        # تحديث الملخص المالي عند ترحيل القيد
        if instance.status == "posted" and instance.customer:
            update_customer_financial_summary(instance.customer)


# ============================================
# إنشاء حساب للعميل الجديد
# Create Account for New Customer
# ============================================


def register_customer_signals():
    """
    تسجيل إشارات العملاء
    """
    try:
        from customers.models import Customer

        from .models import Account, AccountType

        @receiver(post_save, sender=Customer)
        def customer_saved(sender, instance, created, **kwargs):
            if created:
                # إنشاء حساب للعميل الجديد
                try:
                    # البحث عن نوع حساب المدينين
                    receivables_type = AccountType.objects.filter(
                        code_prefix="1200"
                    ).first()

                    if receivables_type:
                        # البحث عن الحساب الأب (المدينين)
                        parent_account = Account.objects.filter(
                            code_prefix="1210"  # ذمم العملاء
                        ).first()

                        # إنشاء حساب للعميل
                        customer_code = f"1210{instance.id:04d}"
                        Account.objects.get_or_create(
                            code=customer_code,
                            defaults={
                                "name": f"حساب العميل - {instance.name}",
                                "name_en": f"Customer Account - {instance.name}",
                                "account_type": receivables_type,
                                "parent": parent_account,
                                "customer": instance,
                                "is_customer_account": True,
                                "is_active": True,
                            },
                        )
                except Exception as e:
                    print(f"Error creating customer account: {e}")

        print("Accounting signals registered for customers app")
    except ImportError:
        print("Customers app not found, skipping customer signals")
