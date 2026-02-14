"""
إشعارات الشكاوى - pre_save فقط لتخزين الحالة السابقة
جميع الإشعارات الفعلية تمر عبر notifications/signals.py (النظام الرئيسي الموحد)
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Complaint


@receiver(pre_save, sender=Complaint)
def track_complaint_changes(sender, instance, **kwargs):
    """
    تتبع تغييرات الشكوى قبل الحفظ (pre_save)
    يخزن الحالة القديمة والمسؤول القديم كسمات مؤقتة على الكائن
    ليتم قراءتها وتنظيفها في notifications/signals.py
    """
    if instance.pk:
        try:
            old_instance = Complaint.objects.get(pk=instance.pk)

            # تتبع تغيير الحالة
            if old_instance.status != instance.status:
                instance._old_status = old_instance.status
                instance._status_changed = True

            # تتبع تغيير المسؤول
            if old_instance.assigned_to != instance.assigned_to:
                instance._old_assignee = old_instance.assigned_to
                instance._assignee_changed = True

        except Complaint.DoesNotExist:
            pass
