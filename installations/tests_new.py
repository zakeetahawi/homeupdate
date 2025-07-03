"""
اختبارات النظام الجديد للتركيبات
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta, date
import json

from .models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationTechnician,
    InstallationAlert,
    DailyInstallationReport
)
from .services.calendar_service import CalendarService
from .services.alert_system import AlertSystem
from .services.technician_analytics import TechnicianAnalyticsService
from .services.analytics_engine import AnalyticsEngine
from .services.order_completion import OrderCompletionService

User = get_user_model()


class InstallationModelTests(TestCase):
    """اختبارات نماذج التركيبات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.team = InstallationTeamNew.objects.create(
            name='فريق الاختبار',
            branch_name='الفرع الرئيسي',
            max_daily_installations=5
        )
        
        self.technician = InstallationTechnician.objects.create(
            user=self.user,
            employee_id='EMP001',
            experience_years=3,
            max_daily_windows=15
        )
        
        self.installation = InstallationNew.objects.create(
            customer_name='عميل الاختبار',
            customer_phone='0123456789',
            customer_address='عنوان الاختبار',
            salesperson_name='بائع الاختبار',
            branch_name='الفرع الرئيسي',
            windows_count=5,
            order_date=timezone.now().date(),
            scheduled_date=timezone.now().date() + timedelta(days=1),
            team=self.team,
            created_by=self.user
        )
    
    def test_installation_creation(self):
        """اختبار إنشاء التركيب"""
        self.assertEqual(self.installation.customer_name, 'عميل الاختبار')
        self.assertEqual(self.installation.windows_count, 5)
        self.assertEqual(self.installation.status, 'pending')
        self.assertEqual(self.installation.priority, 'normal')
    
    def test_installation_str_method(self):
        """اختبار طريقة __str__ للتركيب"""
        expected = f"تركيب #{self.installation.id} - عميل الاختبار"
        self.assertEqual(str(self.installation), expected)
    
    def test_team_can_schedule_installation(self):
        """اختبار إمكانية جدولة تركيب للفريق"""
        target_date = timezone.now().date() + timedelta(days=2)
        self.assertTrue(self.team.can_schedule_installation(target_date))
    
    def test_technician_daily_windows_count(self):
        """اختبار حساب شبابيك الفني اليومية"""
        target_date = timezone.now().date() + timedelta(days=1)
        count = self.technician.get_daily_windows_count(target_date)
        self.assertEqual(count, 0)  # لا توجد تركيبات مجدولة للفني بعد


class CalendarServiceTests(TestCase):
    """اختبارات خدمة التقويم"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # إنشاء تركيبات للاختبار
        today = timezone.now().date()
        for i in range(3):
            InstallationNew.objects.create(
                customer_name=f'عميل {i+1}',
                customer_phone=f'01234567{i}0',
                windows_count=2 + i,
                scheduled_date=today + timedelta(days=i),
                created_by=self.user
            )
    
    def test_get_daily_schedule(self):
        """اختبار الحصول على جدول يومي"""
        today = timezone.now().date()
        schedule = CalendarService.get_daily_schedule(today)
        
        self.assertIn('date', schedule)
        self.assertIn('installations_list', schedule)
        self.assertIn('statistics', schedule)
        self.assertEqual(len(schedule['installations_list']), 1)
    
    def test_get_month_calendar(self):
        """اختبار الحصول على تقويم شهري"""
        today = timezone.now().date()
        calendar_data = CalendarService.get_month_calendar(today.year, today.month)
        
        self.assertIn('year', calendar_data)
        self.assertIn('month', calendar_data)
        self.assertIn('days', calendar_data)
        self.assertIn('statistics', calendar_data)


class AlertSystemTests(TestCase):
    """اختبارات نظام الإنذارات"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # إنشاء 15 تركيب في نفس اليوم لاختبار إنذار السعة
        today = timezone.now().date()
        for i in range(15):
            InstallationNew.objects.create(
                customer_name=f'عميل {i+1}',
                customer_phone=f'01234567{i:02d}',
                windows_count=1,
                scheduled_date=today,
                created_by=self.user
            )
    
    def test_daily_capacity_alert(self):
        """اختبار إنذار السعة اليومية"""
        today = timezone.now().date()
        alerts = AlertSystem.check_daily_capacity_alerts(today)
        
        # يجب أن يكون هناك إنذار لتجاوز 13 تركيب
        self.assertTrue(len(alerts) > 0)
        self.assertEqual(alerts[0]['alert_type'], 'daily_capacity_exceeded')
        self.assertEqual(alerts[0]['severity'], 'critical')
    
    def test_check_all_alerts(self):
        """اختبار فحص جميع الإنذارات"""
        today = timezone.now().date()
        all_alerts = AlertSystem.check_all_alerts(today)
        
        self.assertIsInstance(all_alerts, list)
        # يجب أن يكون هناك على الأقل إنذار السعة
        self.assertTrue(len(all_alerts) > 0)


class TechnicianAnalyticsTests(TestCase):
    """اختبارات تحليل أداء الفنيين"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.technician = InstallationTechnician.objects.create(
            user=self.user,
            employee_id='EMP001',
            experience_years=3,
            max_daily_windows=15
        )
        
        # إنشاء تركيبات مكتملة للفني
        today = timezone.now().date()
        for i in range(5):
            InstallationNew.objects.create(
                customer_name=f'عميل {i+1}',
                customer_phone=f'01234567{i}0',
                windows_count=3,
                scheduled_date=today - timedelta(days=i),
                status='completed',
                actual_end_date=timezone.now() - timedelta(days=i),
                quality_rating=4 + (i % 2),  # تقييمات 4 و 5
                created_by=self.user
            )
    
    def test_get_summary_statistics(self):
        """اختبار الحصول على إحصائيات ملخصة"""
        summary = TechnicianAnalyticsService.get_summary_statistics()
        
        self.assertIn('total_technicians', summary)
        self.assertIn('total_windows', summary)
        self.assertIn('total_installations', summary)
        self.assertIn('avg_windows_per_technician', summary)
    
    def test_technician_monthly_stats(self):
        """اختبار إحصائيات الفني الشهرية"""
        today = timezone.now().date()
        stats = TechnicianAnalyticsService.get_technician_monthly_stats(
            self.technician.id, today.year, today.month
        )
        
        self.assertIn('technician', stats)
        self.assertIn('summary', stats)
        self.assertIn('period', stats)


class OrderCompletionTests(TestCase):
    """اختبارات خدمة إكمال الطلبات"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.installation = InstallationNew.objects.create(
            customer_name='عميل الاختبار',
            customer_phone='0123456789',
            windows_count=5,
            scheduled_date=timezone.now().date(),
            status='scheduled',
            created_by=self.user
        )
    
    def test_complete_installation(self):
        """اختبار إكمال التركيب"""
        completion_data = {
            'quality_rating': 5,
            'customer_satisfaction': 4,
            'completion_notes': 'تم الإكمال بنجاح'
        }
        
        result = OrderCompletionService.complete_installation(
            self.installation.id,
            self.user,
            completion_data
        )
        
        self.assertTrue(result['success'])
        
        # التحقق من تحديث التركيب
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.status, 'completed')
        self.assertEqual(self.installation.quality_rating, 5)
        self.assertIsNotNone(self.installation.actual_end_date)
    
    def test_cancel_installation(self):
        """اختبار إلغاء التركيب"""
        result = OrderCompletionService.cancel_installation(
            self.installation.id,
            self.user,
            'سبب الإلغاء'
        )
        
        self.assertTrue(result['success'])
        
        # التحقق من تحديث التركيب
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.status, 'cancelled')


class ViewsTests(TestCase):
    """اختبارات العروض"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.installation = InstallationNew.objects.create(
            customer_name='عميل الاختبار',
            customer_phone='0123456789',
            windows_count=5,
            scheduled_date=timezone.now().date(),
            created_by=self.user
        )
    
    def test_dashboard_view(self):
        """اختبار عرض لوحة التحكم"""
        response = self.client.get('/installations/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لوحة التحكم')
    
    def test_installations_list_view(self):
        """اختبار عرض قائمة التركيبات"""
        response = self.client.get('/installations/list/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'عميل الاختبار')
    
    def test_installation_detail_view(self):
        """اختبار عرض تفاصيل التركيب"""
        response = self.client.get(f'/installations/{self.installation.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'عميل الاختبار')
    
    def test_create_installation_view(self):
        """اختبار عرض إنشاء التركيب"""
        response = self.client.get('/installations/create/')
        self.assertEqual(response.status_code, 200)
        
        # اختبار إنشاء تركيب جديد
        data = {
            'customer_name': 'عميل جديد',
            'customer_phone': '0987654321',
            'customer_address': 'عنوان جديد',
            'salesperson_name': 'بائع جديد',
            'branch_name': 'فرع جديد',
            'windows_count': 3,
            'order_date': timezone.now().date(),
            'scheduled_date': timezone.now().date() + timedelta(days=1),
            'location_type': 'open',
            'priority': 'normal',
        }
        
        response = self.client.post('/installations/create/', data)
        self.assertEqual(response.status_code, 302)  # إعادة توجيه بعد الإنشاء
        
        # التحقق من إنشاء التركيب
        new_installation = InstallationNew.objects.filter(
            customer_name='عميل جديد'
        ).first()
        self.assertIsNotNone(new_installation)


class ManagementCommandTests(TestCase):
    """اختبارات أوامر الإدارة"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # إنشاء بيانات للاختبار
        today = timezone.now().date()
        for i in range(15):  # إنشاء 15 تركيب لاختبار الإنذارات
            InstallationNew.objects.create(
                customer_name=f'عميل {i+1}',
                customer_phone=f'01234567{i:02d}',
                windows_count=1,
                scheduled_date=today,
                created_by=self.user
            )
    
    def test_check_alerts_command(self):
        """اختبار أمر فحص الإنذارات"""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('check_alerts', stdout=out)
        
        output = out.getvalue()
        self.assertIn('بدء فحص الإنذارات', output)
        self.assertIn('إنذار حرج', output)  # يجب أن يكون هناك إنذار لتجاوز السعة
    
    def test_generate_daily_report_command(self):
        """اختبار أمر إنشاء التقرير اليومي"""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        yesterday = (timezone.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
        call_command('generate_daily_report', '--date', yesterday, stdout=out)
        
        output = out.getvalue()
        self.assertIn('بدء إنشاء التقرير اليومي', output)
        
        # التحقق من إنشاء التقرير
        report = DailyInstallationReport.objects.filter(
            report_date=timezone.now().date() - timedelta(days=1)
        ).first()
        self.assertIsNotNone(report)


class IntegrationTests(TestCase):
    """اختبارات التكامل"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.team = InstallationTeamNew.objects.create(
            name='فريق التكامل',
            branch_name='فرع التكامل',
            max_daily_installations=10
        )
        
        self.technician = InstallationTechnician.objects.create(
            user=self.user,
            employee_id='INT001',
            experience_years=5,
            max_daily_windows=20
        )
        
        # ربط الفني بالفريق
        self.team.technicians.add(self.technician)
    
    def test_full_installation_workflow(self):
        """اختبار سير العمل الكامل للتركيب"""
        
        # 1. إنشاء التركيب
        installation = InstallationNew.objects.create(
            customer_name='عميل التكامل',
            customer_phone='0123456789',
            customer_address='عنوان التكامل',
            salesperson_name='بائع التكامل',
            branch_name='فرع التكامل',
            windows_count=8,
            order_date=timezone.now().date(),
            scheduled_date=timezone.now().date() + timedelta(days=1),
            team=self.team,
            priority='high',
            created_by=self.user
        )
        
        self.assertEqual(installation.status, 'pending')
        
        # 2. جدولة التركيب
        installation.status = 'scheduled'
        installation.save()
        
        # 3. بدء التركيب
        installation.status = 'in_progress'
        installation.actual_start_date = timezone.now()
        installation.save()
        
        # 4. إكمال التركيب
        completion_result = OrderCompletionService.complete_installation(
            installation.id,
            self.user,
            {
                'quality_rating': 5,
                'customer_satisfaction': 5,
                'completion_notes': 'تم الإكمال بنجاح'
            }
        )
        
        self.assertTrue(completion_result['success'])
        
        # 5. التحقق من النتيجة النهائية
        installation.refresh_from_db()
        self.assertEqual(installation.status, 'completed')
        self.assertEqual(installation.quality_rating, 5)
        self.assertIsNotNone(installation.actual_end_date)
        
        # 6. التحقق من إنشاء سجل الإكمال
        completion_log = getattr(installation, 'completion_log', None)
        if completion_log:
            self.assertEqual(completion_log.quality_rating, 5)
            self.assertEqual(completion_log.completed_by, self.user)
