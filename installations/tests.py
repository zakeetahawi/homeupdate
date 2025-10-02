from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Customer, Order

from .models import (
    Driver,
    InstallationArchive,
    InstallationPayment,
    InstallationSchedule,
    InstallationTeam,
    ModificationReport,
    ReceiptMemo,
    Technician,
)


class InstallationsTestCase(TestCase):
    """اختبارات قسم التركيبات"""

    def setUp(self):
        """إعداد البيانات الأولية للاختبارات"""
        # إنشاء مستخدم
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

        # إنشاء عميل
        self.customer = Customer.objects.create(
            name="عميل تجريبي", phone="0123456789", address="عنوان تجريبي"
        )

        # إنشاء طلب
        self.order = Order.objects.create(
            order_number="TEST-001",
            customer=self.customer,
            total_amount=1000,
            paid_amount=500,
        )

        # إنشاء فني
        self.technician = Technician.objects.create(
            name="فني تجريبي", phone="0123456788", specialization="تركيب عام"
        )

        # إنشاء سائق
        self.driver = Driver.objects.create(
            name="سائق تجريبي",
            phone="0123456787",
            license_number="123456",
            vehicle_number="ABC-123",
        )

        # إنشاء فريق
        self.team = InstallationTeam.objects.create(name="فريق تجريبي")
        self.team.technicians.add(self.technician)
        self.team.driver = self.driver
        self.team.save()

        # إنشاء جدولة تركيب
        self.installation = InstallationSchedule.objects.create(
            order=self.order,
            team=self.team,
            scheduled_date=timezone.now().date() + timedelta(days=1),
            scheduled_time=datetime.strptime("09:00", "%H:%M").time(),
            status="scheduled",
        )

        # إنشاء عميل للاختبارات
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_dashboard_view(self):
        """اختبار عرض لوحة التحكم"""
        response = self.client.get(reverse("installations:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/dashboard.html")

    def test_installation_list_view(self):
        """اختبار عرض قائمة التركيبات"""
        response = self.client.get(reverse("installations:installation_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/installation_list.html")

    def test_installation_detail_view(self):
        """اختبار عرض تفاصيل التركيب"""
        response = self.client.get(
            reverse("installations:installation_detail", args=[self.installation.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/installation_detail.html")

    def test_schedule_installation_view(self):
        """اختبار جدولة التركيب"""
        response = self.client.get(
            reverse("installations:schedule_installation", args=[self.installation.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/schedule_installation.html")

    def test_update_status_view(self):
        """اختبار تحديث حالة التركيب"""
        response = self.client.post(
            reverse("installations:update_status", args=[self.installation.id]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 200)

        # التحقق من تحديث الحالة
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.status, "in_progress")

    def test_daily_schedule_view(self):
        """اختبار عرض الجدول اليومي"""
        response = self.client.get(reverse("installations:daily_schedule"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/daily_schedule.html")

    def test_team_management_view(self):
        """اختبار إدارة الفرق"""
        response = self.client.get(reverse("installations:team_management"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/team_management.html")

    def test_add_payment_view(self):
        """اختبار إضافة دفعة"""
        response = self.client.get(
            reverse("installations:add_payment", args=[self.installation.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/add_payment.html")

    def test_add_modification_report_view(self):
        """اختبار إضافة تقرير تعديل"""
        response = self.client.get(
            reverse(
                "installations:add_modification_report", args=[self.installation.id]
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/add_modification_report.html")

    def test_add_receipt_memo_view(self):
        """اختبار إضافة مذكرة استلام"""
        response = self.client.get(
            reverse("installations:add_receipt_memo", args=[self.installation.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/add_receipt_memo.html")

    def test_archive_list_view(self):
        """اختبار عرض الأرشيف"""
        response = self.client.get(reverse("installations:archive_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "installations/archive_list.html")

    def test_installation_stats_api(self):
        """اختبار API الإحصائيات"""
        response = self.client.get(reverse("installations:installation_stats_api"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("total", response.json())
        self.assertIn("pending", response.json())
        self.assertIn("scheduled", response.json())
        self.assertIn("completed", response.json())

    def test_complete_installation_view(self):
        """اختبار إكمال التركيب"""
        # تغيير الحالة إلى قيد التنفيذ أولاً
        self.installation.status = "in_progress"
        self.installation.save()

        response = self.client.post(
            reverse("installations:complete_installation", args=[self.installation.id])
        )
        self.assertEqual(response.status_code, 200)

        # التحقق من تحديث الحالة
        self.installation.refresh_from_db()
        self.assertEqual(self.installation.status, "completed")

    def test_technician_model(self):
        """اختبار نموذج الفني"""
        technician = Technician.objects.create(
            name="فني جديد", phone="0123456786", specialization="تركيب متخصص"
        )
        self.assertEqual(technician.name, "فني جديد")
        self.assertEqual(technician.specialization, "تركيب متخصص")
        self.assertTrue(technician.is_active)

    def test_driver_model(self):
        """اختبار نموذج السائق"""
        driver = Driver.objects.create(
            name="سائق جديد",
            phone="0123456785",
            license_number="654321",
            vehicle_number="XYZ-789",
        )
        self.assertEqual(driver.name, "سائق جديد")
        self.assertEqual(driver.license_number, "654321")
        self.assertEqual(driver.vehicle_number, "XYZ-789")

    def test_installation_team_model(self):
        """اختبار نموذج فريق التركيب"""
        team = InstallationTeam.objects.create(name="فريق جديد")
        team.technicians.add(self.technician)
        team.driver = self.driver
        team.save()

        self.assertEqual(team.name, "فريق جديد")
        self.assertIn(self.technician, team.technicians.all())
        self.assertEqual(team.driver, self.driver)

    def test_installation_schedule_model(self):
        """اختبار نموذج جدولة التركيب"""
        installation = InstallationSchedule.objects.create(
            order=self.order,
            team=self.team,
            scheduled_date=timezone.now().date() + timedelta(days=2),
            scheduled_time=datetime.strptime("10:00", "%H:%M").time(),
            status="pending",
            notes="ملاحظات تجريبية",
        )

        self.assertEqual(installation.order, self.order)
        self.assertEqual(installation.team, self.team)
        self.assertEqual(installation.status, "pending")
        self.assertEqual(installation.notes, "ملاحظات تجريبية")

    def test_installation_payment_model(self):
        """اختبار نموذج دفعة التركيب"""
        payment = InstallationPayment.objects.create(
            installation=self.installation,
            payment_type="remaining",
            amount=500,
            payment_method="cash",
            receipt_number="REC-001",
            notes="دفعة تجريبية",
        )

        self.assertEqual(payment.installation, self.installation)
        self.assertEqual(payment.payment_type, "remaining")
        self.assertEqual(payment.amount, 500)
        self.assertEqual(payment.payment_method, "cash")

    def test_modification_report_model(self):
        """اختبار نموذج تقرير التعديل"""
        report = ModificationReport.objects.create(
            installation=self.installation, description="تقرير تعديل تجريبي"
        )

        self.assertEqual(report.installation, self.installation)
        self.assertEqual(report.description, "تقرير تعديل تجريبي")

    def test_receipt_memo_model(self):
        """اختبار نموذج مذكرة الاستلام"""
        memo = ReceiptMemo.objects.create(
            installation=self.installation,
            customer_signature=True,
            amount_received=500,
            notes="مذكرة استلام تجريبية",
        )

        self.assertEqual(memo.installation, self.installation)
        self.assertTrue(memo.customer_signature)
        self.assertEqual(memo.amount_received, 500)

    def test_installation_archive_model(self):
        """اختبار نموذج أرشيف التركيب"""
        # إكمال التركيب أولاً
        self.installation.status = "completed"
        self.installation.save()

        archive = InstallationArchive.objects.create(
            installation=self.installation,
            archived_by=self.user,
            archive_notes="أرشفة تجريبية",
        )

        self.assertEqual(archive.installation, self.installation)
        self.assertEqual(archive.archived_by, self.user)
        self.assertEqual(archive.archive_notes, "أرشفة تجريبية")

    def test_installation_service(self):
        """اختبار خدمة التركيبات"""
        from .services.installation_service import InstallationService

        # اختبار الإحصائيات
        stats = InstallationService.get_dashboard_stats()
        self.assertIn("total", stats)
        self.assertIn("pending", stats)
        self.assertIn("scheduled", stats)
        self.assertIn("completed", stats)

        # اختبار التركيبات اليوم
        today_installations = InstallationService.get_today_installations()
        self.assertIsInstance(today_installations, list)

        # اختبار البحث
        search_results = InstallationService.search_installations("TEST")
        self.assertIsInstance(search_results, list)

    def test_forms(self):
        """اختبار النماذج"""
        from .forms import (
            InstallationPaymentForm,
            InstallationScheduleForm,
            ModificationReportForm,
            ReceiptMemoForm,
        )

        # اختبار نموذج جدولة التركيب
        schedule_data = {
            "team": self.team.id,
            "scheduled_date": timezone.now().date() + timedelta(days=3),
            "scheduled_time": "11:00",
            "notes": "جدولة تجريبية",
        }
        schedule_form = InstallationScheduleForm(data=schedule_data)
        self.assertTrue(schedule_form.is_valid())

        # اختبار نموذج الدفعة
        payment_data = {
            "payment_type": "remaining",
            "amount": 500,
            "payment_method": "cash",
            "receipt_number": "REC-002",
            "notes": "دفعة تجريبية",
        }
        payment_form = InstallationPaymentForm(data=payment_data)
        self.assertTrue(payment_form.is_valid())

    def test_permissions(self):
        """اختبار الصلاحيات"""
        # اختبار الوصول بدون تسجيل دخول
        self.client.logout()
        response = self.client.get(reverse("installations:dashboard"))
        self.assertEqual(response.status_code, 302)  # إعادة توجيه للدخول

    def test_file_upload_validation(self):
        """اختبار التحقق من الملفات المرفوعة"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # اختبار ملف صالح
        valid_file = SimpleUploadedFile(
            "test.pdf", b"file_content", content_type="application/pdf"
        )

        # اختبار ملف غير صالح
        invalid_file = SimpleUploadedFile(
            "test.exe", b"file_content", content_type="application/x-msdownload"
        )

        # يمكن إضافة المزيد من اختبارات التحقق من الملفات هنا

    def tearDown(self):
        """تنظيف البيانات بعد الاختبارات"""
        # حذف جميع البيانات التجريبية
        InstallationArchive.objects.all().delete()
        ReceiptMemo.objects.all().delete()
        ModificationReport.objects.all().delete()
        InstallationPayment.objects.all().delete()
        InstallationSchedule.objects.all().delete()
        InstallationTeam.objects.all().delete()
        Driver.objects.all().delete()
        Technician.objects.all().delete()
        Order.objects.all().delete()
        Customer.objects.all().delete()
        User.objects.all().delete()
