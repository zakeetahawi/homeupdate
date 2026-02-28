"""
خدمة أساسية للنظام
توفر هذه الوحدة فئة أساسية للخدمات في النظام
تستخدم هذه الفئة كأساس لجميع الخدمات في النظام
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query import QuerySet

T = TypeVar("T", bound=models.Model)


class StatusSyncService:
    """خدمة مزامنة الحالات بين الطلبات والتصنيع"""

    # تطابق الحالات بين الطلبات والتصنيع
    ORDER_TO_MANUFACTURING_STATUS = {
        "pending_approval": "pending_approval",
        "pending": "pending",
        "in_progress": "in_progress",
        "ready_install": "ready_install",
        "completed": "completed",
        "delivered": "delivered",
        "rejected": "rejected",
        "cancelled": "cancelled",
    }

    MANUFACTURING_TO_ORDER_STATUS = {
        "pending_approval": "pending_approval",
        "pending": "pending",
        "in_progress": "in_progress",
        "ready_install": "ready_install",
        "completed": "completed",
        "delivered": "delivered",
        "rejected": "rejected",
        "cancelled": "cancelled",
    }

    @classmethod
    def sync_order_to_manufacturing(cls, order, manufacturing_order):
        """مزامنة حالة الطلب مع التصنيع"""
        new_manufacturing_status = cls.ORDER_TO_MANUFACTURING_STATUS.get(
            order.order_status, "pending"
        )

        if manufacturing_order.status != new_manufacturing_status:
            manufacturing_order.status = new_manufacturing_status
            manufacturing_order.save(update_fields=["status"])

    @classmethod
    def sync_manufacturing_to_order(cls, manufacturing_order, order):
        """مزامنة حالة التصنيع مع الطلب"""
        new_order_status = cls.MANUFACTURING_TO_ORDER_STATUS.get(
            manufacturing_order.status, "pending"
        )

        if order.order_status != new_order_status:
            order.order_status = new_order_status
            order.save(update_fields=["order_status"])

    @classmethod
    def validate_status_consistency(cls, order, manufacturing_order):
        """التحقق من تطابق الحالات"""
        expected_manufacturing_status = cls.ORDER_TO_MANUFACTURING_STATUS.get(
            order.order_status
        )
        expected_order_status = cls.MANUFACTURING_TO_ORDER_STATUS.get(
            manufacturing_order.status
        )

        return {
            "order_status_matches": order.order_status == expected_order_status,
            "manufacturing_status_matches": manufacturing_order.status
            == expected_manufacturing_status,
        }


class BaseService(Generic[T]):
    """
    فئة أساسية للخدمات في النظام
    توفر هذه الفئة وظائف أساسية مشتركة بين جميع الخدمات
    """

    model_class: Type[T] = None

    @classmethod
    def get_by_id(cls, id: int) -> Optional[T]:
        """
        الحصول على كائن بواسطة المعرف

        Args:
            id: معرف الكائن

        Returns:
            الكائن إذا تم العثور عليه، وإلا None
        """
        try:
            return cls.model_class.objects.get(id=id)
        except cls.model_class.DoesNotExist:
            return None

    @classmethod
    def get_all(cls, **filters) -> QuerySet[T]:
        """
        الحصول على جميع الكائنات التي تطابق المرشحات

        Args:
            **filters: مرشحات للبحث

        Returns:
            مجموعة استعلام تحتوي على الكائنات المطابقة
        """
        return cls.model_class.objects.filter(**filters)

    @classmethod
    def create(cls, **data) -> T:
        """
        إنشاء كائن جديد

        Args:
            **data: بيانات الكائن

        Returns:
            الكائن الذي تم إنشاؤه

        Raises:
            ValidationError: إذا كانت البيانات غير صالحة
        """
        instance = cls.model_class(**data)
        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    def update(cls, instance: T, **data) -> T:
        """
        تحديث كائن موجود

        Args:
            instance: الكائن المراد تحديثه
            **data: البيانات الجديدة

        Returns:
            الكائن بعد التحديث

        Raises:
            ValidationError: إذا كانت البيانات غير صالحة
        """
        for key, value in data.items():
            setattr(instance, key, value)

        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    def delete(cls, instance: T) -> bool:
        """
        حذف كائن

        Args:
            instance: الكائن المراد حذفه

        Returns:
            True إذا تم الحذف بنجاح، وإلا False
        """
        try:
            instance.delete()
            return True
        except Exception:
            return False

    @classmethod
    def bulk_create(cls, data_list: List[Dict[str, Any]]) -> List[T]:
        """
        إنشاء عدة كائنات دفعة واحدة

        Args:
            data_list: قائمة بيانات الكائنات

        Returns:
            قائمة الكائنات التي تم إنشاؤها
        """
        instances = [cls.model_class(**data) for data in data_list]
        return cls.model_class.objects.bulk_create(instances)

    @classmethod
    def bulk_update(cls, instances: List[T], fields: List[str]) -> int:
        """
        تحديث عدة كائنات دفعة واحدة

        Args:
            instances: قائمة الكائنات المراد تحديثها
            fields: قائمة الحقول المراد تحديثها

        Returns:
            عدد الكائنات التي تم تحديثها
        """
        return cls.model_class.objects.bulk_update(instances, fields)
