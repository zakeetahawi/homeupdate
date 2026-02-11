"""
إشارات النظام المحاسبي - التكامل التلقائي
Accounting Signals - Auto Integration
"""

import logging
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger('accounting')

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

        # تحديد العميل والطلب
        customer = None
        order = None
        if payment.order:
            order = payment.order
            customer = order.customer
        elif hasattr(payment, 'customer') and payment.customer:
            customer = payment.customer

        # البحث عن حساب العميل إن وجد
        customer_account = None
        if customer:
            customer_account = Account.objects.filter(
                customer=customer, is_customer_account=True
            ).first()

        # استخدام حساب العميل أو حساب المدينين العام
        debit_from = customer_account or receivables_account

        # وصف مختلف حسب نوع الدفعة
        if order:
            description = f"استلام دفعة للطلب {order.order_number}"
            line_desc = f"تسديد مديونية للطلب {order.order_number}"
            customer_name = customer.name if customer else "عميل"
            cash_desc = f"استلام نقدي من {customer_name}"
        else:
            customer_name = customer.name if customer else "عميل"
            description = f"استلام دفعة عامة من {customer_name}"
            line_desc = f"دفعة عامة من {customer_name}"
            cash_desc = f"استلام نقدي من {customer_name}"

        with db_transaction.atomic():
            # إنشاء القيد
            txn = Transaction.objects.create(
                date=(
                    payment.payment_date
                    if hasattr(payment, "payment_date")
                    else timezone.now().date()
                ),
                transaction_type="payment",
                description=description,
                reference=(
                    f"إيصال: {payment.reference_number}"
                    if hasattr(payment, "reference_number") and payment.reference_number
                    else ""
                ),
                order=order,
                payment=payment,
                customer=customer,
                status="posted" if settings.auto_post_transactions else "draft",
            )

            # مدين - الصندوق/البنك
            TransactionLine.objects.create(
                transaction=txn,
                account=cash_account,
                debit=payment.amount,
                credit=Decimal("0"),
                description=cash_desc,
            )

            # دائن - المدينين/حساب العميل
            TransactionLine.objects.create(
                transaction=txn,
                account=debit_from,
                debit=Decimal("0"),
                credit=payment.amount,
                description=line_desc,
            )

            txn.save()

            return txn
    except Exception as e:
        import logging
        logger = logging.getLogger('accounting')
        logger.error(f"Error creating payment transaction: {e}", exc_info=True)
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
                date=(
                    order.order_date
                    if hasattr(order, "order_date")
                    else timezone.now().date()
                ),
                transaction_type="invoice",
                description=f"إيراد مبيعات - طلب {order.order_number}",
                order=order,
                customer=order.customer,
                status="posted" if settings.auto_post_transactions else "draft",
            )

            # مدين - المدينين/حساب العميل
            TransactionLine.objects.create(
                transaction=txn,
                account=debit_to,
                debit=total_amount,
                credit=Decimal("0"),
                description=f"مديونية طلب {order.order_number}",
            )

            # دائن - الإيرادات
            TransactionLine.objects.create(
                transaction=txn,
                account=revenue_account,
                debit=Decimal("0"),
                credit=total_amount,
                description=f"إيراد طلب {order.order_number}",
            )

            txn.save()

            return txn
    except Exception as e:
        logger.error(f"Error creating order transaction: {e}", exc_info=True)
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
        receivables_account = settings.default_receivables_account

        if not cash_account:
            return None

        # البحث عن حساب العربونات (التزام) أو استخدام حساب المدينين
        advances_account = Account.objects.filter(
            account_type__code_prefix__startswith='2',
            name__icontains='عربون'
        ).first()
        if not advances_account:
            # إذا لم يوجد حساب عربونات، نستخدم حساب العميل أو المدينين
            if advance.customer:
                advances_account = Account.objects.filter(
                    customer=advance.customer, is_customer_account=True
                ).first()
            if not advances_account:
                advances_account = receivables_account
        if not advances_account:
            return None

        with db_transaction.atomic():
            txn = Transaction.objects.create(
                date=(
                    advance.created_at.date()
                    if advance.created_at
                    else timezone.now().date()
                ),
                transaction_type="advance",
                description=f"استلام عربون من {advance.customer.name}",
                reference=f"عربون #{advance.id} - {advance.get_status_display()}",
                customer=advance.customer,
                status="posted" if settings.auto_post_transactions else "draft",
            )

            # مدين - الصندوق
            TransactionLine.objects.create(
                transaction=txn,
                account=cash_account,
                debit=advance.amount,
                credit=Decimal("0"),
                description="استلام عربون نقدي",
            )

            # دائن - عربونات العملاء (التزام)
            TransactionLine.objects.create(
                transaction=txn,
                account=advances_account,
                debit=Decimal("0"),
                credit=advance.amount,
                description=f"عربون {advance.customer.name}",
            )

            txn.save()

            # ربط القيد بالسلفة
            advance.transaction = txn
            advance.save(update_fields=["transaction"])

            return txn
    except Exception as e:
        logger.error(f"Error creating advance transaction: {e}", exc_info=True)
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
        logger.error(f"Error updating customer financial summary: {e}", exc_info=True)


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
                elif hasattr(instance, 'customer') and instance.customer:
                    update_customer_financial_summary(instance.customer)

        @receiver(post_delete, sender=Payment)
        def payment_deleted(sender, instance, **kwargs):
            """عكس القيد المحاسبي عند حذف دفعة"""
            try:
                from .models import Transaction
                # البحث عن القيد المرتبط بالدفعة وإلغائه
                related_txns = Transaction.objects.filter(payment=instance, status='posted')
                for txn in related_txns:
                    txn.create_reversal(
                        description=f"عكس تلقائي - حذف الدفعة #{instance.id}"
                    )
                # تحديث الملخص المالي
                customer = None
                if instance.order and instance.order.customer:
                    customer = instance.order.customer
                elif hasattr(instance, 'customer') and instance.customer:
                    customer = instance.customer
                if customer:
                    update_customer_financial_summary(customer)
            except Exception as e:
                logger.error(f"Error reversing payment transaction on delete: {e}", exc_info=True)

        @receiver(post_save, sender=Order)
        def order_saved(sender, instance, created, **kwargs):
            if created:
                # إنشاء قيد المبيعات
                create_order_transaction(instance)
            else:
                # عكس القيد عند إلغاء الطلب
                if hasattr(instance, 'status') and instance.status == 'cancelled':
                    try:
                        from .models import Transaction
                        related_txns = Transaction.objects.filter(
                            order=instance, status='posted'
                        ).exclude(transaction_type='reversal')
                        for txn in related_txns:
                            # تجنب العكس المتكرر
                            if not Transaction.objects.filter(
                                order=instance, transaction_type='reversal',
                                description__icontains=str(txn.id)
                            ).exists():
                                txn.create_reversal(
                                    description=f"عكس تلقائي - إلغاء الطلب {instance.order_number} (قيد #{txn.id})"
                                )
                        logger.info(f"Reversed transactions for cancelled order {instance.order_number}")
                    except Exception as e:
                        logger.error(f"Error reversing order transactions on cancel: {e}", exc_info=True)
            # تحديث الملخص المالي
            if instance.customer:
                update_customer_financial_summary(instance.customer)

        logger.info("Accounting signals registered for orders app")
    except ImportError:
        logger.warning("Orders app not found, skipping order signals")


def register_accounting_signals():
    """
    تسجيل إشارات النظام المحاسبي
    """
    from .models import Transaction

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
                        code_prefix="1100"
                    ).first()

                    if receivables_type:
                        # البحث عن الحساب الأب (العملاء تحت الذمم المدينة) أو إنشاؤه
                        parent_account = Account.objects.filter(
                            code="1121",
                            account_type=receivables_type
                        ).first()
                        
                        if not parent_account:
                            # إنشاء حساب العملاء الرئيسي
                            parent_account = Account.objects.create(
                                code="1121",
                                name="العملاء",
                                name_en="Customers",
                                account_type=receivables_type,
                                is_active=True,
                                allow_transactions=False,  # حساب أب
                            )

                        # إنشاء حساب للعميل تحت العملاء
                        customer_code = f"1121{instance.id:05d}"
                        Account.objects.get_or_create(
                            code=customer_code,
                            defaults={
                                "name": f"{instance.name}",
                                "name_en": f"{instance.name}",
                                "account_type": receivables_type,
                                "parent": parent_account,
                                "customer": instance,
                                "is_customer_account": True,
                                "is_active": True,
                            },
                        )
                except Exception as e:
                    logger.error(f"Error creating customer account: {e}", exc_info=True)

        logger.info("Accounting signals registered for customers app")
    except ImportError:
        logger.warning("Customers app not found, skipping customer signals")


# ============================================
# إشارات تحديث أرصدة الحسابات
# Account Balance Update Signals
# ============================================


@receiver(post_save, sender='accounting.TransactionLine')
def update_account_balance_on_line_save(sender, instance, created, **kwargs):
    """
    تحديث رصيد الحساب تلقائياً عند حفظ سطر قيد
    """
    try:
        if instance.account:
            instance.account.update_balance()
    except Exception as e:
        logger.error(f"Error updating account balance on line save: {e}", exc_info=True)


@receiver(post_delete, sender='accounting.TransactionLine')
def update_account_balance_on_line_delete(sender, instance, **kwargs):
    """
    تحديث رصيد الحساب تلقائياً عند حذف سطر قيد
    """
    try:
        if instance.account:
            instance.account.update_balance()
    except Exception as e:
        logger.error(f"Error updating account balance on line delete: {e}", exc_info=True)


# ============================================
# إشارات مدفوعات التركيبات
# Installation Payment Signals
# ============================================


@receiver(post_save, sender='installations.InstallationPayment')
def create_installation_payment_transaction(sender, instance, created, **kwargs):
    """
    إنشاء قيد محاسبي عند تسجيل دفعة تركيب
    مدين: النقدية / دائن: حساب العميل
    """
    if not created:
        return

    from .models import Account, AccountingSettings, Transaction, TransactionLine

    try:
        settings_obj = AccountingSettings.objects.first()
        if not settings_obj or not settings_obj.cash_account:
            logger.warning("Installation payment: no AccountingSettings or cash_account configured")
            return

        # الحصول على العميل من التركيب
        installation = instance.installation
        if not installation or not hasattr(installation, 'order') or not installation.order:
            logger.warning(f"Installation payment {instance.pk}: no order linked")
            return

        customer = installation.order.customer
        if not customer:
            logger.warning(f"Installation payment {instance.pk}: no customer on order")
            return

        # الحصول على حساب العميل
        customer_account = Account.objects.filter(customer=customer, is_active=True).first()
        if not customer_account:
            logger.warning(f"Installation payment {instance.pk}: no accounting account for customer {customer.pk}")
            return

        amount = Decimal(str(instance.amount))
        if amount <= 0:
            return

        with db_transaction.atomic():
            txn = Transaction.objects.create(
                transaction_type="payment",
                date=timezone.now().date(),
                description=f"دفعة تركيب للعميل {customer.name} - {instance.get_payment_type_display()}",
                reference=instance.receipt_number or f"INST-PAY-{instance.pk}",
                customer=customer,
                created_by=instance.created_by,
                status="draft",
            )

            # مدين النقدية
            TransactionLine.objects.create(
                transaction=txn,
                account=settings_obj.cash_account,
                debit=amount,
                credit=Decimal("0.00"),
                description=f"استلام دفعة تركيب - {customer.name}",
            )

            # دائن حساب العميل
            TransactionLine.objects.create(
                transaction=txn,
                account=customer_account,
                debit=Decimal("0.00"),
                credit=amount,
                description=f"سداد دفعة تركيب - {instance.get_payment_type_display()}",
            )

            txn.calculate_totals()
            txn.post(instance.created_by)

            logger.info(
                f"Installation payment transaction created: {txn.transaction_number} "
                f"for customer {customer.name}, amount {amount}"
            )

    except Exception as e:
        logger.error(f"Error creating installation payment transaction: {e}", exc_info=True)


# ============================================
# إشارات بطاقات المصنع
# Factory Card Signals
# ============================================


@receiver(post_save, sender='factory_accounting.FactoryCard')
def create_factory_card_payment_transaction(sender, instance, **kwargs):
    """
    إنشاء قيد محاسبي عند دفع بطاقة المصنع (الحالة → مدفوع)
    مدين: مصروفات التصنيع / دائن: النقدية
    """
    # فقط عند تغيير الحالة إلى مدفوع
    if instance.status != 'paid':
        return

    from .models import Account, AccountingSettings, Transaction, TransactionLine

    # التحقق من عدم وجود قيد سابق لهذه البطاقة
    existing = Transaction.objects.filter(
        reference=f"FACTORY-{instance.pk}",
        status__in=["draft", "posted"],
    ).exists()
    if existing:
        return

    try:
        settings_obj = AccountingSettings.objects.first()
        if not settings_obj or not settings_obj.cash_account:
            logger.warning("Factory card payment: no AccountingSettings or cash_account configured")
            return

        # الحصول على حساب مصروفات التصنيع
        manufacturing_expense = Account.objects.filter(
            code__startswith="5",
            name__icontains="تصنيع",
            is_active=True,
        ).first()

        if not manufacturing_expense:
            # محاولة بحث بديل
            manufacturing_expense = Account.objects.filter(
                account_type__category="expense",
                is_active=True,
                allow_transactions=True,
            ).first()

        if not manufacturing_expense:
            logger.warning(f"Factory card {instance.pk}: no manufacturing expense account found")
            return

        amount = instance.total_cutter_cost or Decimal("0.00")
        if amount <= 0:
            return

        with db_transaction.atomic():
            txn = Transaction.objects.create(
                transaction_type="expense",
                date=timezone.now().date(),
                description=f"دفع بطاقة مصنع رقم {instance.pk} - تكلفة القص",
                reference=f"FACTORY-{instance.pk}",
                created_by=instance.created_by,
                status="draft",
            )

            # مدين مصروفات التصنيع
            TransactionLine.objects.create(
                transaction=txn,
                account=manufacturing_expense,
                debit=amount,
                credit=Decimal("0.00"),
                description=f"تكلفة قص - بطاقة مصنع {instance.pk}",
            )

            # دائن النقدية
            TransactionLine.objects.create(
                transaction=txn,
                account=settings_obj.cash_account,
                debit=Decimal("0.00"),
                credit=amount,
                description=f"دفع من النقدية - بطاقة مصنع {instance.pk}",
            )

            txn.calculate_totals()
            txn.post(instance.created_by)

            logger.info(
                f"Factory card payment transaction created: {txn.transaction_number} "
                f"for card {instance.pk}, amount {amount}"
            )

    except Exception as e:
        logger.error(f"Error creating factory card payment transaction: {e}", exc_info=True)
