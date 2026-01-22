"""
Order Service Layer - Business Logic
فصل منطق الأعمال عن العروض (Views)
"""

from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from customers.models import Customer
from installations.models import InstallationSchedule
from manufacturing.models import ManufacturingOrder
from orders.contract_models import ContractCurtain
from orders.models import Order, OrderItem

User = get_user_model()


class OrderService:
    """
    خدمة إدارة الطلبات
    تحتوي على جميع منطق الأعمال المتعلق بالطلبات
    """

    @staticmethod
    @transaction.atomic
    def create_order(
        customer_id: int,
        items_data: List[Dict[str, Any]],
        created_by: User,
        **order_data,
    ) -> Order:
        """
        إنشاء طلب جديد مع جميع العمليات المرتبطة

        Args:
            customer_id: معرف العميل
            items_data: قائمة ببيانات عناصر الطلب
            created_by: المستخدم الذي أنشأ الطلب
            **order_data: بيانات إضافية للطلب

        Returns:
            Order: كائن الطلب المنشأ

        Raises:
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        # التحقق من العميل
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise ValidationError(f"العميل {customer_id} غير موجود")

        # إنشاء الطلب
        order = Order.objects.create(
            customer=customer, created_by=created_by, status="pending", **order_data
        )

        # إنشاء عناصر الطلب
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)

        # إنشاء أمر تصنيع تلقائياً
        ManufacturingOrder.objects.create(
            order=order, status="pending", created_by=created_by
        )

        # إنشاء جدول تركيب إذا كان مطلوباً
        if order_data.get("installation_required", True):
            InstallationSchedule.objects.create(order=order, status="pending")

        return order

    @staticmethod
    def calculate_order_total(order: Order) -> float:
        """
        حساب إجمالي الطلب

        Args:
            order: كائن الطلب

        Returns:
            float: إجمالي المبلغ
        """
        items = order.items.all()
        total = sum(item.total_price for item in items if item.total_price)
        return float(total)

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order, reason: str, cancelled_by: User) -> None:
        """
        إلغاء طلب

        Args:
            order: كائن الطلب
            reason: سبب الإلغاء
            cancelled_by: المستخدم الذي ألغى الطلب
        """
        # تحديث حالة الطلب
        order.status = "cancelled"
        order.cancellation_reason = reason
        order.cancelled_by = cancelled_by
        order.cancelled_at = timezone.now()
        order.save()

        # إلغاء أمر التصنيع
        if hasattr(order, "manufacturing_order"):
            mfg_order = order.manufacturing_order
            mfg_order.status = "cancelled"
            mfg_order.save()

        # إلغاء جدول التركيب
        if hasattr(order, "installation_schedule"):
            install = order.installation_schedule
            install.status = "cancelled"
            install.save()

    @staticmethod
    def get_order_progress(order: Order) -> Dict[str, Any]:
        """
        الحصول على تقدم الطلب

        Args:
            order: كائن الطلب

        Returns:
            dict: معلومات التقدم
        """
        progress = {
            "order_status": order.status,
            "manufacturing_status": None,
            "installation_status": None,
            "overall_progress": 0,
        }

        # حالة التصنيع
        if hasattr(order, "manufacturing_order"):
            progress["manufacturing_status"] = order.manufacturing_order.status

        # حالة التركيب
        if hasattr(order, "installation_schedule"):
            progress["installation_status"] = order.installation_schedule.status

        # حساب التقدم الإجمالي
        statuses = [
            order.status,
            progress["manufacturing_status"],
            progress["installation_status"],
        ]

        completed = sum(1 for s in statuses if s == "completed")
        total = len([s for s in statuses if s is not None])

        if total > 0:
            progress["overall_progress"] = int((completed / total) * 100)

        return progress

    @staticmethod
    def validate_order_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        التحقق من صحة بيانات الطلب

        Args:
            data: بيانات الطلب

        Returns:
            tuple: (صحيح/خطأ, رسالة الخطأ)
        """
        # التحقق من وجود العميل
        if "customer_id" not in data:
            return False, "معرف العميل مطلوب"

        # التحقق من وجود عناصر
        if "items" not in data or not data["items"]:
            return False, "يجب إضافة عنصر واحد على الأقل"

        # التحقق من تاريخ التسليم
        if "delivery_date" in data:
            delivery_date = data["delivery_date"]
            if delivery_date < timezone.now().date():
                return False, "تاريخ التسليم يجب أن يكون في المستقبل"

        return True, None


class ContractService:
    """
    خدمة إدارة العقود
    """

    @staticmethod
    @transaction.atomic
    def create_contract_curtain(
        order: Order, curtain_data: Dict[str, Any]
    ) -> ContractCurtain:
        """
        إنشاء ستارة عقد جديدة

        Args:
            order: الطلب المرتبط
            curtain_data: بيانات الستارة

        Returns:
            ContractCurtain: كائن الستارة المنشأ
        """
        curtain = ContractCurtain.objects.create(order=order, **curtain_data)
        return curtain

    @staticmethod
    def calculate_curtain_cost(curtain: ContractCurtain) -> float:
        """
        حساب تكلفة الستارة

        Args:
            curtain: كائن الستارة

        Returns:
            float: التكلفة الإجمالية
        """
        # حساب تكلفة الأقمشة
        fabric_cost = sum(
            fabric.total_price for fabric in curtain.fabrics.all() if fabric.total_price
        )

        # حساب تكلفة الإكسسوارات
        accessory_cost = sum(
            acc.total_price for acc in curtain.accessories.all() if acc.total_price
        )

        return float(fabric_cost + accessory_cost)
