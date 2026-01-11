"""
خدمات تطبيق العملاء
توفر هذه الوحدة خدمات لإدارة العملاء
"""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.db.models import Count, F, Q, Sum
from django.db.models.query import QuerySet
from django.utils import timezone

from crm.services import BaseService

from .models import Customer, CustomerCategory, CustomerNote


class CustomerService(BaseService[Customer]):
    """
    خدمة إدارة العملاء
    توفر هذه الخدمة وظائف لإدارة العملاء
    """

    model_class = Customer

    @classmethod
    def search_customers(cls, search_term: str = None, **filters) -> QuerySet[Customer]:
        """
        البحث عن العملاء

        Args:
            search_term: مصطلح البحث
            **filters: مرشحات إضافية

        Returns:
            مجموعة استعلام تحتوي على العملاء المطابقين
        """
        queryset = cls.get_all(**filters)

        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term)
                | Q(code__icontains=search_term)
                | Q(phone__icontains=search_term)
                | Q(email__icontains=search_term)
            )

        return queryset.select_related("category", "branch", "created_by")

    @classmethod
    def get_customer_statistics(cls, branch_id: int = None) -> Dict[str, int]:
        """
        الحصول على إحصائيات العملاء

        Args:
            branch_id: معرف الفرع (اختياري)

        Returns:
            قاموس يحتوي على إحصائيات العملاء
        """
        queryset = cls.get_all()

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        stats = queryset.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status="active")),
            inactive=Count("id", filter=Q(status="inactive")),
            vip=Count("id", filter=Q(customer_type="vip")),
            regular=Count("id", filter=Q(customer_type="regular")),
            wholesale=Count("id", filter=Q(customer_type="wholesale")),
            new_this_month=Count(
                "id", filter=Q(created_at__gte=timezone.now() - timedelta(days=30))
            ),
        )

        return stats

    @classmethod
    def get_customer_with_related_data(cls, customer_id: int) -> Optional[Customer]:
        """
        الحصول على عميل مع البيانات المرتبطة

        Args:
            customer_id: معرف العميل

        Returns:
            العميل مع البيانات المرتبطة إذا تم العثور عليه، وإلا None
        """
        try:
            return (
                Customer.objects.select_related("category", "branch", "created_by")
                .prefetch_related("notes_history", "customer_orders", "inspections")
                .get(id=customer_id)
            )
        except Customer.DoesNotExist:
            return None

    @classmethod
    def add_customer_note(
        cls, customer_id: int, note_text: str, created_by_id: int
    ) -> Optional[CustomerNote]:
        """
        إضافة ملاحظة للعميل

        Args:
            customer_id: معرف العميل
            note_text: نص الملاحظة
            created_by_id: معرف المستخدم الذي أنشأ الملاحظة

        Returns:
            الملاحظة التي تم إنشاؤها إذا نجحت العملية، وإلا None
        """
        customer = cls.get_by_id(customer_id)

        if not customer:
            return None

        note = CustomerNote(
            customer=customer, note=note_text, created_by_id=created_by_id
        )

        note.save()
        return note

    @classmethod
    def get_customer_activity(cls, customer_id: int) -> Dict[str, Any]:
        """
        الحصول على نشاط العميل

        Args:
            customer_id: معرف العميل

        Returns:
            قاموس يحتوي على نشاط العميل
        """
        customer = cls.get_by_id(customer_id)

        if not customer:
            return {}

        # الحصول على عدد الطلبات
        orders_count = customer.customer_orders.count()

        # الحصول على إجمالي المبيعات
        total_sales = (
            customer.customer_orders.aggregate(total=Sum("final_price"))["total"] or 0
        )

        # الحصول على عدد المعاينات
        inspections_count = customer.inspections.count()

        # الحصول على آخر نشاط
        last_order = customer.customer_orders.order_by("-created_at").first()
        last_inspection = customer.inspections.order_by("-created_at").first()
        last_note = customer.notes_history.order_by("-created_at").first()

        # تحديد آخر نشاط
        last_activity = None
        last_activity_date = None

        if last_order:
            last_activity = "order"
            last_activity_date = last_order.created_at

        if last_inspection and (
            not last_activity_date or last_inspection.created_at > last_activity_date
        ):
            last_activity = "inspection"
            last_activity_date = last_inspection.created_at

        if last_note and (
            not last_activity_date or last_note.created_at > last_activity_date
        ):
            last_activity = "note"
            last_activity_date = last_note.created_at

        return {
            "orders_count": orders_count,
            "total_sales": total_sales,
            "inspections_count": inspections_count,
            "last_activity": last_activity,
            "last_activity_date": last_activity_date,
        }


class CustomerCategoryService(BaseService[CustomerCategory]):
    """
    خدمة إدارة تصنيفات العملاء
    توفر هذه الخدمة وظائف لإدارة تصنيفات العملاء
    """

    model_class = CustomerCategory

    @classmethod
    def get_categories_with_customer_count(cls) -> QuerySet[CustomerCategory]:
        """
        الحصول على تصنيفات العملاء مع عدد العملاء في كل تصنيف

        Returns:
            مجموعة استعلام تحتوي على تصنيفات العملاء مع عدد العملاء
        """
        return cls.get_all().annotate(customer_count=Count("customers"))
