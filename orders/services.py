"""
خدمات تطبيق الطلبات
توفر هذه الوحدة خدمات لإدارة الطلبات
"""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.query import QuerySet
from django.utils import timezone

from crm.services import BaseService

from .models import Order, OrderItem, Payment


class OrderService(BaseService[Order]):
    """
    خدمة إدارة الطلبات
    توفر هذه الخدمة وظائف لإدارة الطلبات
    """

    model_class = Order

    @classmethod
    def search_orders(cls, search_term: str = None, **filters) -> QuerySet[Order]:
        """
        البحث عن الطلبات

        Args:
            search_term: مصطلح البحث
            **filters: مرشحات إضافية

        Returns:
            مجموعة استعلام تحتوي على الطلبات المطابقة
        """
        queryset = cls.get_all(**filters)

        if search_term:
            queryset = queryset.filter(
                Q(order_number__icontains=search_term)
                | Q(customer__name__icontains=search_term)
                | Q(invoice_number__icontains=search_term)
                | Q(invoice_number_2__icontains=search_term)
                | Q(invoice_number_3__icontains=search_term)
                | Q(contract_number__icontains=search_term)
                | Q(contract_number_2__icontains=search_term)
                | Q(contract_number_3__icontains=search_term)
            )

        return queryset.select_related(
            "customer", "salesperson", "branch", "created_by"
        )

    @classmethod
    def get_order_statistics(
        cls, branch_id: int = None, start_date: Any = None, end_date: Any = None
    ) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الطلبات

        Args:
            branch_id: معرف الفرع (اختياري)
            start_date: تاريخ البداية (اختياري)
            end_date: تاريخ النهاية (اختياري)

        Returns:
            قاموس يحتوي على إحصائيات الطلبات
        """
        queryset = cls.get_all()

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        # إحصائيات عامة
        stats = queryset.aggregate(
            total_count=Count("id"),
            total_amount=Sum("final_price"),
            paid_amount=Sum("paid_amount"),
            pending_count=Count("id", filter=Q(tracking_status="pending")),
            processing_count=Count("id", filter=Q(tracking_status="processing")),
            delivered_count=Count("id", filter=Q(tracking_status="delivered")),
        )

        # إحصائيات حسب نوع الطلب
        order_types = queryset.values("order_type").annotate(
            count=Count("id"), amount=Sum("final_price")
        )

        # إحصائيات حسب الشهر (آخر 6 أشهر)
        from django.db.models.functions import ExtractMonth

        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = (
            queryset.filter(created_at__gte=six_months_ago)
            .annotate(month=ExtractMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"), amount=Sum("final_price"))
            .order_by("month")
        )

        return {
            "general": stats,
            "by_type": list(order_types),
            "monthly": list(monthly_stats),
        }

    @classmethod
    def get_order_with_related_data(cls, order_id: int) -> Optional[Order]:
        """
        الحصول على طلب مع البيانات المرتبطة

        Args:
            order_id: معرف الطلب

        Returns:
            الطلب مع البيانات المرتبطة إذا تم العثور عليه، وإلا None
        """
        try:
            return (
                Order.objects.select_related(
                    "customer", "salesperson", "branch", "created_by"
                )
                .prefetch_related("items", "payments")
                .get(id=order_id)
            )
        except Order.DoesNotExist:
            return None

    @classmethod
    def calculate_order_total(cls, order_id: int) -> float:
        """
        حساب إجمالي الطلب

        Args:
            order_id: معرف الطلب

        Returns:
            إجمالي الطلب
        """
        order = cls.get_by_id(order_id)

        if not order:
            return 0

        # استخدام استعلام مُحسّن لحساب إجمالي الطلب
        total = (
            order.items.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("quantity") * F("unit_price"), output_field=DecimalField()
                    )
                )
            )["total"]
            or 0
        )

        return float(total)

    @classmethod
    def add_payment(
        cls,
        order_id: int,
        amount: float,
        payment_method: str,
        reference_number: str = None,
        created_by_id: int = None,
    ) -> Optional[Payment]:
        """
        إضافة دفعة للطلب

        Args:
            order_id: معرف الطلب
            amount: المبلغ
            payment_method: طريقة الدفع
            reference_number: رقم المرجع (اختياري)
            created_by_id: معرف المستخدم الذي أنشأ الدفعة (اختياري)

        Returns:
            الدفعة التي تم إنشاؤها إذا نجحت العملية، وإلا None
        """
        order = cls.get_by_id(order_id)

        if not order:
            return None

        payment = Payment(
            order=order,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number or "",
            created_by_id=created_by_id,
        )

        payment.save()

        # تحديث المبلغ المدفوع في الطلب
        order.paid_amount = order.paid_amount + amount
        order.save(update_fields=["paid_amount"])

        return payment

    @classmethod
    def update_order_status(
        cls,
        order_id: int,
        new_status: str,
        changed_by_id: int = None,
        notes: str = None,
    ) -> bool:
        """
        تحديث حالة الطلب

        Args:
            order_id: معرف الطلب
            new_status: الحالة الجديدة
            changed_by_id: معرف المستخدم الذي قام بالتغيير (اختياري)
            notes: ملاحظات (اختياري)

        Returns:
            True إذا تم التحديث بنجاح، وإلا False
        """
        order = cls.get_by_id(order_id)

        if not order:
            return False

        old_status = order.tracking_status
        order.tracking_status = new_status
        order.save(update_fields=["tracking_status"])

        # إنشاء سجل لتغيير الحالة
        from .models import OrderStatusLog

        OrderStatusLog.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=changed_by_id,
            notes=notes or "",
        )

        # إرسال إشعار بتغيير الحالة
        order.notify_status_change(old_status, new_status, changed_by_id, notes)

        return True
