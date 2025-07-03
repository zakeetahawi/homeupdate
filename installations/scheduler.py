#!/usr/bin/env python
"""
مجدول المهام للنظام الجديد للتركيبات (بديل Celery)
"""
import os
import sys
import django
import threading
import time
import schedule
from datetime import datetime, timedelta
import logging

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.core.management import call_command
from django.utils import timezone

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('installations.scheduler')


class InstallationScheduler:
    """مجدول مهام التركيبات"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """بدء المجدول"""
        if self.running:
            logger.warning("المجدول يعمل بالفعل")
            return
        
        logger.info("🚀 بدء مجدول مهام التركيبات...")
        
        # جدولة المهام
        self.schedule_tasks()
        
        # بدء خيط المجدول
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("✅ تم بدء المجدول بنجاح")
    
    def stop(self):
        """إيقاف المجدول"""
        if not self.running:
            return
        
        logger.info("⏹️ إيقاف مجدول المهام...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("✅ تم إيقاف المجدول")
    
    def schedule_tasks(self):
        """جدولة المهام"""
        
        # فحص الإنذارات كل ساعة
        schedule.every().hour.do(self.check_alerts_job)
        logger.info("📅 جدولة فحص الإنذارات: كل ساعة")
        
        # التقرير اليومي في الساعة 8 صباحاً
        schedule.every().day.at("08:00").do(self.daily_report_job)
        logger.info("📅 جدولة التقرير اليومي: 8:00 صباحاً")
        
        # تنظيف البيانات القديمة كل أسبوع (الجمعة 2 صباحاً)
        schedule.every().friday.at("02:00").do(self.cleanup_job)
        logger.info("📅 جدولة تنظيف البيانات: الجمعة 2:00 صباحاً")
        
        # الملخص الأسبوعي (السبت 9 صباحاً)
        schedule.every().saturday.at("09:00").do(self.weekly_summary_job)
        logger.info("📅 جدولة الملخص الأسبوعي: السبت 9:00 صباحاً")
        
        # فحص الأداء كل 30 دقيقة
        schedule.every(30).minutes.do(self.performance_check_job)
        logger.info("📅 جدولة فحص الأداء: كل 30 دقيقة")
        
        # تحديث الإحصائيات كل 15 دقيقة
        schedule.every(15).minutes.do(self.update_statistics_job)
        logger.info("📅 جدولة تحديث الإحصائيات: كل 15 دقيقة")
    
    def _run_scheduler(self):
        """تشغيل المجدول"""
        logger.info("🔄 بدء حلقة المجدول...")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # فحص كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في المجدول: {e}")
                time.sleep(60)
        
        logger.info("⏹️ انتهت حلقة المجدول")
    
    def check_alerts_job(self):
        """مهمة فحص الإنذارات"""
        try:
            logger.info("🚨 بدء فحص الإنذارات...")
            call_command('check_alerts', verbosity=0)
            logger.info("✅ انتهى فحص الإنذارات")
        except Exception as e:
            logger.error(f"❌ خطأ في فحص الإنذارات: {e}")
    
    def daily_report_job(self):
        """مهمة التقرير اليومي"""
        try:
            logger.info("📊 بدء إنشاء التقرير اليومي...")
            yesterday = (timezone.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
            call_command('generate_daily_report', '--date', yesterday, '--send-email', verbosity=0)
            logger.info("✅ انتهى إنشاء التقرير اليومي")
        except Exception as e:
            logger.error(f"❌ خطأ في التقرير اليومي: {e}")
    
    def cleanup_job(self):
        """مهمة تنظيف البيانات القديمة"""
        try:
            logger.info("🧹 بدء تنظيف البيانات القديمة...")
            call_command('cleanup_old_data', '--force', verbosity=0)
            logger.info("✅ انتهى تنظيف البيانات")
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف البيانات: {e}")
    
    def weekly_summary_job(self):
        """مهمة الملخص الأسبوعي"""
        try:
            logger.info("📈 بدء إنشاء الملخص الأسبوعي...")
            self.send_weekly_summary()
            logger.info("✅ انتهى إنشاء الملخص الأسبوعي")
        except Exception as e:
            logger.error(f"❌ خطأ في الملخص الأسبوعي: {e}")
    
    def performance_check_job(self):
        """مهمة فحص الأداء"""
        try:
            logger.debug("⚡ فحص الأداء...")
            self.check_system_performance()
        except Exception as e:
            logger.error(f"❌ خطأ في فحص الأداء: {e}")
    
    def update_statistics_job(self):
        """مهمة تحديث الإحصائيات"""
        try:
            logger.debug("📊 تحديث الإحصائيات...")
            self.update_cached_statistics()
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الإحصائيات: {e}")
    
    def send_weekly_summary(self):
        """إرسال الملخص الأسبوعي"""
        from django.core.mail import send_mail
        from django.conf import settings
        from accounts.models import User
        from installations.models_new import InstallationNew
        
        # حساب الأسبوع الماضي
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday() + 1)
        week_end = week_start + timedelta(days=6)
        
        # الحصول على إحصائيات الأسبوع
        weekly_installations = InstallationNew.objects.filter(
            scheduled_date__range=[week_start, week_end]
        )
        
        total_installations = weekly_installations.count()
        completed_installations = weekly_installations.filter(status='completed').count()
        total_windows = sum(inst.windows_count for inst in weekly_installations)
        
        # إنشاء محتوى البريد الإلكتروني
        subject = f"الملخص الأسبوعي للتركيبات - {week_start.strftime('%Y/%m/%d')} - {week_end.strftime('%Y/%m/%d')}"
        
        message = f"""
الملخص الأسبوعي لنظام التركيبات
الفترة: {week_start.strftime('%Y/%m/%d')} - {week_end.strftime('%Y/%m/%d')}

إحصائيات الأسبوع:
- إجمالي التركيبات: {total_installations}
- التركيبات المكتملة: {completed_installations}
- إجمالي الشبابيك: {total_windows}
- معدل الإكمال: {(completed_installations/total_installations*100):.1f}%

تم إنشاء هذا التقرير تلقائياً في {timezone.now().strftime('%Y-%m-%d %H:%M')}

مع تحيات،
نظام إدارة التركيبات
"""
        
        # إرسال للإدارة
        managers = User.objects.filter(
            is_staff=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if managers.exists():
            recipient_list = [user.email for user in managers]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=recipient_list,
                fail_silently=True
            )
            
            logger.info(f"📧 تم إرسال الملخص الأسبوعي إلى {len(recipient_list)} مدير")
    
    def check_system_performance(self):
        """فحص أداء النظام"""
        import psutil
        
        # فحص استخدام الذاكرة
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            logger.warning(f"⚠️ استخدام الذاكرة مرتفع: {memory.percent}%")
        
        # فحص استخدام القرص
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            logger.warning(f"⚠️ استخدام القرص مرتفع: {disk.percent}%")
        
        # فحص استخدام المعالج
        cpu = psutil.cpu_percent(interval=1)
        if cpu > 80:
            logger.warning(f"⚠️ استخدام المعالج مرتفع: {cpu}%")
    
    def update_cached_statistics(self):
        """تحديث الإحصائيات المخزنة مؤقتاً"""
        from django.core.cache import cache
        from installations.services.analytics_engine import AnalyticsEngine
        
        try:
            # تحديث إحصائيات لوحة التحكم
            dashboard_analytics = AnalyticsEngine.get_dashboard_analytics()
            cache.set('dashboard_analytics', dashboard_analytics, 900)  # 15 دقيقة
            
            # تحديث مقارنة الفروع
            branch_comparison = AnalyticsEngine.get_branch_comparison()
            cache.set('branch_comparison', branch_comparison, 1800)  # 30 دقيقة
            
            logger.debug("📊 تم تحديث الإحصائيات المخزنة مؤقتاً")
            
        except Exception as e:
            logger.error(f"خطأ في تحديث الإحصائيات: {e}")


def main():
    """الدالة الرئيسية"""
    
    # إنشاء مجلد السجلات إذا لم يكن موجوداً
    os.makedirs('logs', exist_ok=True)
    
    # إنشاء المجدول
    scheduler = InstallationScheduler()
    
    try:
        # بدء المجدول
        scheduler.start()
        
        print("🎯 مجدول مهام التركيبات يعمل...")
        print("📋 المهام المجدولة:")
        print("   - فحص الإنذارات: كل ساعة")
        print("   - التقرير اليومي: 8:00 صباحاً")
        print("   - تنظيف البيانات: الجمعة 2:00 صباحاً")
        print("   - الملخص الأسبوعي: السبت 9:00 صباحاً")
        print("   - فحص الأداء: كل 30 دقيقة")
        print("   - تحديث الإحصائيات: كل 15 دقيقة")
        print("\n⏹️ اضغط Ctrl+C للإيقاف")
        
        # انتظار إيقاف المستخدم
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 تم طلب الإيقاف...")
        scheduler.stop()
        print("✅ تم إيقاف المجدول بنجاح")
    
    except Exception as e:
        logger.error(f"خطأ في المجدول الرئيسي: {e}")
        scheduler.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
