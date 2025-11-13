"""
مهام خلفية لتطبيق الطلبات
"""

import logging
from celery import shared_task
from django.utils import timezone
from .models import Order

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def upload_contract_to_drive_async(self, order_id):
    """
    مهمة خلفية لرفع ملف العقد إلى Google Drive
    """
    try:
        # الحصول على الطلب
        order = Order.objects.get(pk=order_id)
        
        # التحقق من وجود ملف العقد
        if not order.contract_file:
            logger.warning(f"لا يوجد ملف عقد للطلب {order.order_number}")
            return {'success': False, 'message': 'لا يوجد ملف عقد'}
        
        # التحقق من أن الملف لم يتم رفعه مسبقاً
        if order.is_contract_uploaded_to_drive:
            logger.info(f"ملف العقد للطلب {order.order_number} تم رفعه مسبقاً")
            return {'success': True, 'message': 'تم رفع الملف مسبقاً'}
        
        # رفع الملف
        success, message = order.upload_contract_to_google_drive()
        
        if success:
            logger.info(f"تم رفع ملف العقد للطلب {order.order_number} بنجاح")
            return {'success': True, 'message': 'تم رفع الملف بنجاح'}
        else:
            logger.error(f"فشل في رفع ملف العقد للطلب {order.order_number}: {message}")
            # إعادة المحاولة في حالة الفشل
            raise self.retry(countdown=60, exc=Exception(message))
            
    except Order.DoesNotExist:
        logger.error(f"الطلب {order_id} غير موجود")
        return {'success': False, 'message': 'الطلب غير موجود'}
        
    except Exception as e:
        logger.error(f"خطأ في رفع ملف العقد للطلب {order_id}: {str(e)}")
        
        # إعادة المحاولة في حالة الخطأ
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        else:
            # في حالة فشل جميع المحاولات، نسجل الخطأ
            logger.error(f"فشل نهائي في رفع ملف العقد للطلب {order_id} بعد {self.max_retries} محاولات")
            return {'success': False, 'message': f'فشل نهائي: {str(e)}'}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue='file_uploads')
def upload_inspection_to_drive_async(self, inspection_id):
    """
    مهمة خلفية لرفع ملف المعاينة إلى Google Drive
    """
    try:
        from inspections.models import Inspection
        
        # الحصول على المعاينة
        inspection = Inspection.objects.get(pk=inspection_id)
        
        # التحقق من وجود ملف المعاينة
        if not inspection.inspection_file:
            logger.warning(f"لا يوجد ملف معاينة للمعاينة {inspection.id}")
            return {'success': False, 'message': 'لا يوجد ملف معاينة'}
        
        # التحقق من أن الملف لم يتم رفعه مسبقاً
        if inspection.is_uploaded_to_drive:
            logger.info(f"ملف المعاينة {inspection.id} تم رفعه مسبقاً")
            return {'success': True, 'message': 'تم رفع الملف مسبقاً'}
        
        # رفع الملف
        success = inspection.upload_to_google_drive_async()
        
        if success:
            logger.info(f"تم رفع ملف المعاينة {inspection.id} بنجاح")
            return {'success': True, 'message': 'تم رفع الملف بنجاح'}
        else:
            logger.error(f"فشل في رفع ملف المعاينة {inspection.id}")
            # إعادة المحاولة في حالة الفشل
            raise self.retry(countdown=60, exc=Exception("فشل في رفع الملف"))
            
    except Exception as e:
        logger.error(f"خطأ في رفع ملف المعاينة {inspection_id}: {str(e)}")
        
        # إعادة المحاولة في حالة الخطأ
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        else:
            # في حالة فشل جميع المحاولات، نسجل الخطأ
            logger.error(f"فشل نهائي في رفع ملف المعاينة {inspection_id} بعد {self.max_retries} محاولات")
            return {'success': False, 'message': f'فشل نهائي: {str(e)}'}


@shared_task
def cleanup_failed_uploads():
    """
    مهمة دورية لتنظيف الملفات التي فشل رفعها
    """
    try:
        from datetime import timedelta
        
        # البحث عن الطلبات التي لديها ملفات عقود ولم يتم رفعها منذ أكثر من ساعة
        one_hour_ago = timezone.now() - timedelta(hours=1)
        failed_orders = Order.objects.filter(
            contract_file__isnull=False,
            is_contract_uploaded_to_drive=False,
            created_at__lt=one_hour_ago
        )
        
        retry_count = 0
        for order in failed_orders:
            try:
                # إعادة محاولة رفع الملف
                upload_contract_to_drive_async.delay(order.pk)
                retry_count += 1
            except Exception as e:
                logger.error(f"خطأ في إعادة جدولة رفع ملف العقد للطلب {order.pk}: {str(e)}")
        
        logger.info(f"تم إعادة جدولة {retry_count} ملف عقد للرفع")
        
        # نفس الشيء للمعاينات
        from inspections.models import Inspection
        failed_inspections = Inspection.objects.filter(
            inspection_file__isnull=False,
            is_uploaded_to_drive=False,
            created_at__lt=one_hour_ago
        )
        
        inspection_retry_count = 0
        for inspection in failed_inspections:
            try:
                # إرسال المهمة إلى queue المناسب
                upload_inspection_to_drive_async.apply_async(
                    args=[inspection.pk],
                    queue='file_uploads'  # تأكد من استخدام القائمة الصحيحة
                )
                inspection_retry_count += 1
            except Exception as e:
                logger.error(f"خطأ في إعادة جدولة رفع ملف المعاينة {inspection.pk}: {str(e)}")
        
        logger.info(f"تم إعادة جدولة {inspection_retry_count} ملف معاينة للرفع")
        
        return {
            'success': True,
            'orders_retried': retry_count,
            'inspections_retried': inspection_retry_count
        }
        
    except Exception as e:
        logger.error(f"خطأ في مهمة تنظيف الملفات الفاشلة: {str(e)}")
        return {'success': False, 'message': str(e)}


@shared_task
def update_order_status_async(order_id, old_status, new_status, changed_by_id=None, notes=''):
    """
    مهمة خلفية لتحديث حالة الطلب وإرسال الإشعارات
    """
    try:
        order = Order.objects.get(pk=order_id)
        
        # تحديث الحالة
        order.tracking_status = new_status
        order.save(update_fields=['tracking_status'])
        
        # إنشاء سجل تغيير الحالة
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        changed_by = None
        if changed_by_id:
            try:
                changed_by = User.objects.get(pk=changed_by_id)
            except User.DoesNotExist:
                pass
        
        order.notify_status_change(old_status, new_status, changed_by, notes)
        
        logger.info(f"تم تحديث حالة الطلب {order.order_number} من {old_status} إلى {new_status}")
        
        return {'success': True, 'message': 'تم تحديث الحالة بنجاح'}
        
    except Order.DoesNotExist:
        logger.error(f"الطلب {order_id} غير موجود")
        return {'success': False, 'message': 'الطلب غير موجود'}
        
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة الطلب {order_id}: {str(e)}")
        return {'success': False, 'message': str(e)}


@shared_task
def calculate_order_totals_async(order_id):
    """
    مهمة خلفية لحساب إجماليات الطلب
    """
    try:
        order = Order.objects.get(pk=order_id)
        
        # حساب السعر النهائي
        final_price = order.calculate_final_price()
        
        # تحديث المبلغ الإجمالي
        order.total_amount = final_price
        order.save(update_fields=['final_price', 'total_amount'])
        
        logger.info(f"تم حساب إجماليات الطلب {order.order_number}: {final_price}")
        
        return {'success': True, 'final_price': float(final_price)}
        
    except Order.DoesNotExist:
        logger.error(f"الطلب {order_id} غير موجود")
        return {'success': False, 'message': 'الطلب غير موجود'}
        
    except Exception as e:
        logger.error(f"خطأ في حساب إجماليات الطلب {order_id}: {str(e)}")
        return {'success': False, 'message': str(e)}


@shared_task
def clear_expired_cache():
    """
    مهمة دورية لتنظيف التخزين المؤقت المنتهي الصلاحية
    """
    try:
        from .cache import OrderCache

        # تنظيف التخزين المؤقت القديم
        OrderCache.clear_all_cache()

        logger.info("تم تنظيف التخزين المؤقت المنتهي الصلاحية")

        return {'success': True, 'message': 'تم تنظيف التخزين المؤقت بنجاح'}

    except Exception as e:
        logger.error(f"خطأ في تنظيف التخزين المؤقت: {str(e)}")
        return {'success': False, 'message': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_contract_async(self, order_id, template_id=None, user_id=None):
    """
    مهمة خلفية لتوليد العقد تلقائياً بعد حفظ الطلب

    Args:
        order_id: معرف الطلب
        template_id: معرف قالب العقد (اختياري)
        user_id: معرف المستخدم الذي أنشأ الطلب
    """
    try:
        from .services.contract_generation_service import ContractGenerationService
        from .contract_models import ContractTemplate
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # الحصول على الطلب
        order = Order.objects.get(pk=order_id)

        # الحصول على المستخدم
        user = None
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                pass

        # الحصول على القالب
        template = None
        if template_id:
            try:
                template = ContractTemplate.objects.get(pk=template_id)
            except ContractTemplate.DoesNotExist:
                logger.warning(f"القالب {template_id} غير موجود، سيتم استخدام القالب الافتراضي")

        # توليد العقد
        service = ContractGenerationService(order, template)
        success = service.save_contract_to_order(user)

        if success:
            logger.info(f"تم توليد العقد للطلب {order.order_number} بنجاح")

            # رفع العقد إلى Google Drive تلقائياً
            if order.contract_file:
                upload_contract_to_drive_async.delay(order_id)

            return {'success': True, 'message': 'تم توليد العقد بنجاح'}
        else:
            logger.error(f"فشل في توليد العقد للطلب {order.order_number}")
            raise self.retry(countdown=60, exc=Exception('فشل في توليد العقد'))

    except Order.DoesNotExist:
        logger.error(f"الطلب {order_id} غير موجود")
        return {'success': False, 'message': 'الطلب غير موجود'}

    except Exception as e:
        logger.error(f"خطأ في توليد العقد للطلب {order_id}: {str(e)}")

        # إعادة المحاولة في حالة الخطأ
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)

        return {'success': False, 'message': str(e)}
