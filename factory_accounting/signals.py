"""
Signals for Factory Accounting
إشارات حسابات المصنع - تسجيل تغييرات الحالات تلقائياً
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from manufacturing.models import ManufacturingOrder

from .models import FactoryCard, ProductionStatusLog


@receiver(post_save, sender=ManufacturingOrder)
def log_status_change(sender, instance, created, **kwargs):
    """
    Log status changes for manufacturing orders
    تسجيل تغييرات حالة أوامر التصنيع
    """
    # Log initial status only if it's a production-ready status
    # فقط: جاهز للتركيب أو مكتمل
    if created:
        if instance.status in ["ready_install", "completed"]:
            ProductionStatusLog.objects.create(
                manufacturing_order=instance,
                status=instance.status,
                changed_by=getattr(instance, "_changed_by", None),
            )
    else:
        # Check if status changed using tracker
        if instance.tracker.has_changed("status"):
            ProductionStatusLog.objects.create(
                manufacturing_order=instance,
                status=instance.status,
                changed_by=getattr(instance, "_changed_by", None),
            )

            # Update factory card production date if exists
            if hasattr(instance, "factory_card"):
                instance.factory_card.update_production_date()


@receiver(post_save, sender=ManufacturingOrder)
def create_factory_card_on_completion(sender, instance, created, **kwargs):
    """
    Auto-create factory card when order reaches ready_install or completed
    إنشاء بطاقة المصنع تلقائياً عند الوصول لحالة جاهز أو مكتمل
    """
    if not created and instance.status in ["ready_install", "completed"]:
        # Update or create card
        card = getattr(instance, "factory_card", None)

        if not card:
            card = FactoryCard.objects.create(
                manufacturing_order=instance,
                created_by=getattr(instance, "_changed_by", None),
            )

        # Calculate total meters and cutter costs automatically
        card.calculate_total_meters()

        # Sync dates
        card.update_production_date()

        # Sync status: If order is completed or ready for install, card should be completed (unless paid)
        if instance.status in ["completed", "ready_install"] and card.status not in [
            "completed",
            "paid",
        ]:
            card.status = "completed"
            card.save(update_fields=["status", "updated_at"])
