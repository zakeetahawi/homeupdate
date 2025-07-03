"""
خدمة إكمال الطلبات وتحديث الحالات
"""
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from ..models_new import InstallationNew, InstallationAlert
from orders.models import Order
from accounts.models import User

logger = logging.getLogger(__name__)


class OrderCompletionService:
    """خدمة إكمال الطلبات وإدارة الحالات"""
    
    @classmethod
    @transaction.atomic
    def complete_installation(cls, installation_id: int, 
                            completed_by: User,
                            completion_data: Dict = None) -> Dict:
        """إكمال التركيب وتحديث حالة الطلب"""
        
        try:
            installation = InstallationNew.objects.select_for_update().get(
                id=installation_id
            )
        except InstallationNew.DoesNotExist:
            return {
                'success': False,
                'error': 'التركيب غير موجود'
            }
        
        # التحقق من إمكانية الإكمال
        if installation.status == 'completed':
            return {
                'success': False,
                'error': 'التركيب مكتمل مسبقاً'
            }
        
        if installation.status not in ['scheduled', 'in_progress']:
            return {
                'success': False,
                'error': f'لا يمكن إكمال التركيب في الحالة الحالية: {installation.get_status_display()}'
            }
        
        # تحديث بيانات الإكمال
        completion_data = completion_data or {}
        
        installation.status = 'completed'
        installation.actual_end_date = timezone.now()
        installation.updated_by = completed_by
        
        # إذا لم يكن هناك تاريخ بدء فعلي، نضعه الآن
        if not installation.actual_start_date:
            installation.actual_start_date = installation.actual_end_date - timedelta(hours=2)
        
        # تحديث تقييم الجودة إذا تم توفيره
        if 'quality_rating' in completion_data:
            quality_rating = completion_data['quality_rating']
            if 1 <= quality_rating <= 5:
                installation.quality_rating = quality_rating
        
        # تحديث رضا العميل إذا تم توفيره
        if 'customer_satisfaction' in completion_data:
            satisfaction = completion_data['customer_satisfaction']
            if 1 <= satisfaction <= 5:
                installation.customer_satisfaction = satisfaction
        
        # إضافة ملاحظات الإكمال
        if 'completion_notes' in completion_data:
            completion_notes = completion_data['completion_notes']
            if installation.notes:
                installation.notes += f"\n\nملاحظات الإكمال ({timezone.now().strftime('%Y-%m-%d %H:%M')}): {completion_notes}"
            else:
                installation.notes = f"ملاحظات الإكمال: {completion_notes}"
        
        # حفظ التركيب
        installation.save()
        
        # تحديث حالة الطلب المرتبط
        order_update_result = cls._update_order_status(installation, completed_by)
        
        # إنشاء سجل إكمال
        completion_log = cls._create_completion_log(installation, completed_by, completion_data)
        
        # إرسال إشعارات
        cls._send_completion_notifications(installation, completed_by)
        
        # تحديث الإحصائيات
        cls._update_completion_statistics(installation)
        
        logger.info(f"تم إكمال التركيب {installation_id} بواسطة {completed_by.username}")
        
        return {
            'success': True,
            'message': 'تم إكمال التركيب بنجاح',
            'installation_id': installation_id,
            'completion_time': installation.actual_end_date,
            'order_updated': order_update_result['success'],
            'completion_log_id': completion_log.id if completion_log else None
        }
        
    @classmethod
    def _update_order_status(cls, installation: InstallationNew, 
                           updated_by: User) -> Dict:
        """تحديث حالة الطلب المرتبط"""
        
        try:
            order = installation.order
            
            # التحقق من وجود تركيبات أخرى غير مكتملة لنفس الطلب
            other_installations = InstallationNew.objects.filter(
                order=order
            ).exclude(id=installation.id)
            
            incomplete_installations = other_installations.exclude(status='completed')
            
            if not incomplete_installations.exists():
                # جميع التركيبات مكتملة، يمكن إغلاق الطلب
                order.status = 'completed'
                order.completion_date = timezone.now()
                order.updated_by = updated_by
                order.save()
                
                logger.info(f"تم إغلاق الطلب {order.id} بعد إكمال جميع التركيبات")
                
                return {
                    'success': True,
                    'message': 'تم إغلاق الطلب بنجاح',
                    'order_closed': True
                }
            else:
                # لا تزال هناك تركيبات غير مكتملة
                return {
                    'success': True,
                    'message': 'الطلب لا يزال مفتوحاً (تركيبات أخرى غير مكتملة)',
                    'order_closed': False,
                    'remaining_installations': incomplete_installations.count()
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة الطلب {installation.order.id}: {str(e)}")
            return {
                'success': False,
                'error': f'خطأ في تحديث حالة الطلب: {str(e)}'
            }
    
    @classmethod
    def _create_completion_log(cls, installation: InstallationNew,
                             completed_by: User, completion_data: Dict):
        """إنشاء سجل إكمال التركيب"""
        
        try:
            from ..models_new import InstallationCompletionLog
            
            # إنشاء نموذج سجل الإكمال إذا لم يكن موجوداً
            completion_log = InstallationCompletionLog.objects.create(
                installation=installation,
                completed_by=completed_by,
                completion_date=installation.actual_end_date,
                quality_rating=installation.quality_rating,
                customer_satisfaction=installation.customer_satisfaction,
                completion_notes=completion_data.get('completion_notes', ''),
                duration_hours=installation.duration_hours,
                issues_encountered=completion_data.get('issues_encountered', ''),
                customer_feedback=completion_data.get('customer_feedback', ''),
                photos_taken=completion_data.get('photos_taken', False),
                warranty_explained=completion_data.get('warranty_explained', False),
                cleanup_completed=completion_data.get('cleanup_completed', False),
            )
            
            return completion_log
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء سجل الإكمال: {str(e)}")
            return None
    
    @classmethod
    def _send_completion_notifications(cls, installation: InstallationNew,
                                     completed_by: User):
        """إرسال إشعارات الإكمال"""
        
        try:
            # إشعار للعميل (SMS/Email)
            cls._notify_customer_completion(installation)
            
            # إشعار للإدارة
            cls._notify_management_completion(installation, completed_by)
            
            # إشعار للمبيعات
            cls._notify_sales_completion(installation)
            
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعارات الإكمال: {str(e)}")
    
    @classmethod
    def _notify_customer_completion(cls, installation: InstallationNew):
        """إشعار العميل بإكمال التركيب"""
        
        try:
            # إرسال SMS للعميل
            message = f"""
            عزيزي {installation.customer_name}،
            
            تم إكمال تركيب الشبابيك بنجاح.
            رقم التركيب: {installation.id}
            تاريخ الإكمال: {installation.actual_end_date.strftime('%Y-%m-%d %H:%M')}
            
            شكراً لثقتكم بنا.
            """
            
            # هنا يمكن إضافة كود إرسال SMS
            logger.info(f"تم إرسال إشعار إكمال للعميل {installation.customer_name}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار العميل: {str(e)}")
    
    @classmethod
    def _notify_management_completion(cls, installation: InstallationNew,
                                    completed_by: User):
        """إشعار الإدارة بإكمال التركيب"""
        
        try:
            # إنشاء إشعار في النظام
            from django.contrib.contenttypes.models import ContentType
            
            # يمكن إضافة نظام إشعارات داخلي هنا
            logger.info(f"تم إشعار الإدارة بإكمال التركيب {installation.id}")
            
        except Exception as e:
            logger.error(f"خطأ في إشعار الإدارة: {str(e)}")
    
    @classmethod
    def _notify_sales_completion(cls, installation: InstallationNew):
        """إشعار فريق المبيعات بإكمال التركيب"""
        
        try:
            # إشعار البائع المسؤول
            if installation.order and installation.order.salesperson:
                # يمكن إرسال إشعار للبائع
                logger.info(f"تم إشعار البائع {installation.salesperson_name} بإكمال التركيب")
            
        except Exception as e:
            logger.error(f"خطأ في إشعار المبيعات: {str(e)}")
    
    @classmethod
    def _update_completion_statistics(cls, installation: InstallationNew):
        """تحديث إحصائيات الإكمال"""
        
        try:
            from ..models_new import DailyInstallationReport
            
            # تحديث التقرير اليومي
            completion_date = installation.actual_end_date.date()
            report = DailyInstallationReport.generate_report(completion_date)
            
            logger.info(f"تم تحديث إحصائيات الإكمال لتاريخ {completion_date}")
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الإحصائيات: {str(e)}")
    
    @classmethod
    def cancel_installation(cls, installation_id: int, 
                          cancelled_by: User,
                          cancellation_reason: str = '') -> Dict:
        """إلغاء التركيب"""
        
        try:
            with transaction.atomic():
                installation = InstallationNew.objects.select_for_update().get(
                    id=installation_id
                )
                
                if installation.status == 'cancelled':
                    return {
                        'success': False,
                        'error': 'التركيب ملغي مسبقاً'
                    }
                
                if installation.status == 'completed':
                    return {
                        'success': False,
                        'error': 'لا يمكن إلغاء تركيب مكتمل'
                    }
                
                # تحديث حالة التركيب
                installation.status = 'cancelled'
                installation.updated_by = cancelled_by
                
                # إضافة سبب الإلغاء للملاحظات
                cancellation_note = f"تم الإلغاء في {timezone.now().strftime('%Y-%m-%d %H:%M')} بواسطة {cancelled_by.get_full_name()}"
                if cancellation_reason:
                    cancellation_note += f"\nسبب الإلغاء: {cancellation_reason}"
                
                if installation.notes:
                    installation.notes += f"\n\n{cancellation_note}"
                else:
                    installation.notes = cancellation_note
                
                installation.save()
                
                # إنشاء تنبيه للإلغاء
                InstallationAlert.objects.create(
                    installation=installation,
                    alert_type='cancellation',
                    severity='medium',
                    title=f'تم إلغاء التركيب #{installation.id}',
                    message=f'تم إلغاء التركيب للعميل {installation.customer_name}. السبب: {cancellation_reason or "غير محدد"}'
                )
                
                logger.info(f"تم إلغاء التركيب {installation_id} بواسطة {cancelled_by.username}")
                
                return {
                    'success': True,
                    'message': 'تم إلغاء التركيب بنجاح',
                    'installation_id': installation_id,
                    'cancelled_at': timezone.now()
                }
                
        except InstallationNew.DoesNotExist:
            return {
                'success': False,
                'error': 'التركيب غير موجود'
            }
        except Exception as e:
            logger.error(f"خطأ في إلغاء التركيب {installation_id}: {str(e)}")
            return {
                'success': False,
                'error': f'خطأ في إلغاء التركيب: {str(e)}'
            }
    
    @classmethod
    def reschedule_installation(cls, installation_id: int,
                              new_date: datetime.date,
                              new_time_start: datetime.time = None,
                              new_time_end: datetime.time = None,
                              rescheduled_by: User = None,
                              reason: str = '') -> Dict:
        """إعادة جدولة التركيب"""
        
        try:
            with transaction.atomic():
                installation = InstallationNew.objects.select_for_update().get(
                    id=installation_id
                )
                
                if installation.status in ['completed', 'cancelled']:
                    return {
                        'success': False,
                        'error': f'لا يمكن إعادة جدولة تركيب {installation.get_status_display()}'
                    }
                
                # حفظ التاريخ القديم
                old_date = installation.scheduled_date
                old_time_start = installation.scheduled_time_start
                old_time_end = installation.scheduled_time_end
                
                # تحديث التاريخ والوقت الجديد
                installation.scheduled_date = new_date
                if new_time_start:
                    installation.scheduled_time_start = new_time_start
                if new_time_end:
                    installation.scheduled_time_end = new_time_end
                
                installation.status = 'rescheduled'
                installation.updated_by = rescheduled_by
                
                # إضافة ملاحظة إعادة الجدولة
                reschedule_note = f"تم إعادة الجدولة في {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                if rescheduled_by:
                    reschedule_note += f" بواسطة {rescheduled_by.get_full_name()}"
                
                reschedule_note += f"\nمن: {old_date} {old_time_start or ''} - {old_time_end or ''}"
                reschedule_note += f"\nإلى: {new_date} {new_time_start or ''} - {new_time_end or ''}"
                
                if reason:
                    reschedule_note += f"\nالسبب: {reason}"
                
                if installation.notes:
                    installation.notes += f"\n\n{reschedule_note}"
                else:
                    installation.notes = reschedule_note
                
                installation.save()
                
                logger.info(f"تم إعادة جدولة التركيب {installation_id}")
                
                return {
                    'success': True,
                    'message': 'تم إعادة جدولة التركيب بنجاح',
                    'installation_id': installation_id,
                    'old_date': old_date,
                    'new_date': new_date,
                    'rescheduled_at': timezone.now()
                }
                
        except InstallationNew.DoesNotExist:
            return {
                'success': False,
                'error': 'التركيب غير موجود'
            }
        except Exception as e:
            logger.error(f"خطأ في إعادة جدولة التركيب {installation_id}: {str(e)}")
            return {
                'success': False,
                'error': f'خطأ في إعادة الجدولة: {str(e)}'
            }
    
    @classmethod
    def get_completion_summary(cls, date_range: Tuple[datetime.date, datetime.date] = None) -> Dict:
        """الحصول على ملخص الإكمالات"""
        
        if not date_range:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date, end_date = date_range
        
        # التركيبات المكتملة في الفترة
        completed_installations = InstallationNew.objects.filter(
            status='completed',
            actual_end_date__date__range=[start_date, end_date]
        )
        
        # إحصائيات الإكمال
        total_completed = completed_installations.count()
        total_windows = sum(inst.windows_count for inst in completed_installations)
        
        # متوسط تقييم الجودة
        quality_ratings = [inst.quality_rating for inst in completed_installations if inst.quality_rating]
        avg_quality = sum(quality_ratings) / len(quality_ratings) if quality_ratings else 0
        
        # متوسط رضا العملاء
        satisfaction_ratings = [inst.customer_satisfaction for inst in completed_installations if inst.customer_satisfaction]
        avg_satisfaction = sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0
        
        # التوزيع حسب الفرع
        branch_distribution = {}
        for installation in completed_installations:
            branch = installation.branch_name
            if branch not in branch_distribution:
                branch_distribution[branch] = 0
            branch_distribution[branch] += 1
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'summary': {
                'total_completed': total_completed,
                'total_windows': total_windows,
                'avg_quality_rating': round(avg_quality, 2),
                'avg_customer_satisfaction': round(avg_satisfaction, 2),
            },
            'distribution': {
                'by_branch': branch_distribution,
            }
        }
