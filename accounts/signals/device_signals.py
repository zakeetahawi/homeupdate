"""
Signals للأجهزة المصرح بها
- تحديث أجهزة المستخدم عند تغيير الفرع
- تعميم الجهاز الجديد على جميع مستخدمي الفرع
- إضافة أجهزة الفرع للمستخدم الجديد
"""
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from accounts.models import BranchDevice
import logging

User = get_user_model()
logger = logging.getLogger('django')


@receiver(pre_save, sender=User)
def track_branch_change(sender, instance, **kwargs):
    """
    تتبع تغيير الفرع للمستخدم
    """
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            # حفظ الفرع القديم في attribute مؤقت
            instance._old_branch = old_instance.branch
        except User.DoesNotExist:
            instance._old_branch = None
    else:
        instance._old_branch = None


@receiver(post_save, sender=User)
def update_user_devices_on_branch_change(sender, instance, created, **kwargs):
    """
    تحديث أجهزة المستخدم عند تغيير الفرع أو إنشاء مستخدم جديد
    """
    # تجنب المعالجة أثناء fixtures/migrations
    if kwargs.get('raw', False):
        return
    
    old_branch = getattr(instance, '_old_branch', None)
    new_branch = instance.branch
    
    # سيناريو 1: مستخدم جديد مع فرع
    if created and new_branch:
        branch_devices = BranchDevice.objects.filter(
            branch=new_branch,
            is_active=True
        )
        if branch_devices.exists():
            instance.authorized_devices.set(branch_devices)
            logger.info(
                f"✅ New user '{instance.username}' authorized for "
                f"{branch_devices.count()} devices from branch '{new_branch.name}'"
            )
        return
    
    # سيناريو 2: تغيير الفرع
    if not created and old_branch != new_branch:
        # حذف جميع الأجهزة القديمة
        instance.authorized_devices.clear()
        logger.info(f"🗑️ Cleared all devices for user '{instance.username}' due to branch change")
        
        # إضافة أجهزة الفرع الجديد
        if new_branch:
            branch_devices = BranchDevice.objects.filter(
                branch=new_branch,
                is_active=True
            )
            if branch_devices.exists():
                instance.authorized_devices.set(branch_devices)
                logger.info(
                    f"✅ User '{instance.username}' moved to branch '{new_branch.name}' - "
                    f"authorized for {branch_devices.count()} devices"
                )
        else:
            logger.info(f"ℹ️ User '{instance.username}' removed from branch - no devices authorized")


@receiver(post_save, sender=BranchDevice)
def authorize_device_for_branch_users(sender, instance, created, **kwargs):
    """
    تعميم الجهاز الجديد على جميع مستخدمي الفرع تلقائياً
    """
    # تجنب المعالجة أثناء fixtures/migrations
    if kwargs.get('raw', False):
        return
    
    # فقط عند إنشاء جهاز جديد أو تفعيل جهاز
    if created or instance.is_active:
        branch_users = User.objects.filter(
            branch=instance.branch,
            is_active=True
        )
        
        if branch_users.exists():
            for user in branch_users:
                # التحقق من الحد الأقصى (20 جهاز)
                current_devices_count = user.authorized_devices.count()
                if current_devices_count < 20:
                    user.authorized_devices.add(instance)
                else:
                    logger.warning(
                        f"⚠️ User '{user.username}' has reached the maximum limit "
                        f"of 20 devices - device '{instance.device_name}' not added"
                    )
            
            logger.info(
                f"✅ Device '{instance.device_name}' (Branch: {instance.branch.name}) "
                f"authorized for {branch_users.count()} users automatically"
            )
    
    # عند تعطيل الجهاز، إزالته من جميع المستخدمين
    elif not instance.is_active:
        instance.authorized_users.clear()
        logger.info(
            f"🗑️ Device '{instance.device_name}' deactivated - "
            f"removed from all users"
        )


@receiver(m2m_changed, sender=User.authorized_devices.through)
def validate_authorized_devices_limit(sender, instance, action, **kwargs):
    """
    التحقق من عدم تجاوز الحد الأقصى (20 جهاز) للمستخدم
    """
    if action == "pre_add":
        current_count = instance.authorized_devices.count()
        adding_count = len(kwargs.get('pk_set', []))
        
        if current_count + adding_count > 20:
            raise ValueError(
                f"لا يمكن إضافة {adding_count} جهاز. "
                f"المستخدم لديه {current_count} جهاز بالفعل "
                f"والحد الأقصى هو 20 جهاز."
            )
