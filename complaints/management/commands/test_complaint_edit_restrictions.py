"""
أمر اختبار قيود تعديل الشكاوى
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from complaints.models import Complaint, ComplaintType
from customers.models import Customer

User = get_user_model()


class Command(BaseCommand):
    help = 'اختبار قيود تعديل الشكاوى حسب الحالة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='إنشاء بيانات اختبار'
        )
        parser.add_argument(
            '--test-restrictions',
            action='store_true',
            help='اختبار قيود التعديل'
        )

    def handle(self, *args, **options):
        if options['create_test_data']:
            self.create_test_data()
        
        if options['test_restrictions']:
            self.test_edit_restrictions()
        
        if not any(options.values()):
            self.create_test_data()
            self.test_edit_restrictions()

    def create_test_data(self):
        """إنشاء بيانات اختبار"""
        self.stdout.write("🔧 إنشاء بيانات اختبار...")
        
        # إنشاء مستخدم اختبار
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={
                'email': 'test@example.com',
                'first_name': 'مستخدم',
                'last_name': 'اختبار'
            }
        )
        
        # إنشاء عميل اختبار
        customer, created = Customer.objects.get_or_create(
            name='عميل اختبار',
            defaults={
                'phone': '123456789',
                'email': 'customer@test.com'
            }
        )
        
        # إنشاء نوع شكوى
        complaint_type, created = ComplaintType.objects.get_or_create(
            name='اختبار',
            defaults={
                'description': 'نوع شكوى للاختبار',
                'default_deadline_hours': 24
            }
        )
        
        # إنشاء شكاوى بحالات مختلفة
        statuses = ['new', 'in_progress', 'overdue', 'resolved', 'closed']
        
        for status in statuses:
            complaint, created = Complaint.objects.get_or_create(
                title=f'شكوى اختبار - {status}',
                defaults={
                    'customer': customer,
                    'complaint_type': complaint_type,
                    'description': f'وصف شكوى اختبار للحالة {status}',
                    'status': status,
                    'created_by': user,
                    'deadline': timezone.now() + timedelta(hours=24)
                }
            )
            
            if created:
                self.stdout.write(f"✅ تم إنشاء شكوى: {complaint.complaint_number} - {status}")

    def test_edit_restrictions(self):
        """اختبار قيود التعديل"""
        self.stdout.write("\n🧪 اختبار قيود التعديل...")
        
        complaints = Complaint.objects.filter(title__startswith='شكوى اختبار')
        
        for complaint in complaints:
            can_edit = complaint.status == 'new'
            status_color = "🟢" if can_edit else "🔴"
            
            self.stdout.write(
                f"{status_color} الشكوى {complaint.complaint_number} "
                f"(حالة: {complaint.get_status_display()}) - "
                f"يمكن التعديل: {'نعم' if can_edit else 'لا'}"
            )
            
            # اختبار الإجراءات المتاحة
            actions = []
            
            # تغيير الحالة متاح دائماً (ما عدا المغلقة والملغية)
            if complaint.status not in ['closed', 'cancelled']:
                actions.append("تغيير الحالة")
            
            # الإسناد متاح دائماً (ما عدا المغلقة والملغية)
            if complaint.status not in ['closed', 'cancelled']:
                actions.append("الإسناد")
            
            # التصعيد متاح للحالات النشطة
            if complaint.status in ['new', 'in_progress', 'overdue']:
                actions.append("التصعيد")
            
            # إضافة ملاحظات متاح دائماً (ما عدا المغلقة والملغية)
            if complaint.status not in ['closed', 'cancelled']:
                actions.append("إضافة ملاحظة")
            
            self.stdout.write(f"   الإجراءات المتاحة: {', '.join(actions) if actions else 'لا توجد'}")
        
        self.stdout.write("\n📋 ملخص القواعد:")
        self.stdout.write("✅ تعديل المحتوى: متاح فقط للشكاوى الجديدة")
        self.stdout.write("✅ تغيير الحالة: متاح لجميع الحالات (ما عدا المغلقة والملغية)")
        self.stdout.write("✅ الإسناد: متاح لجميع الحالات (ما عدا المغلقة والملغية)")
        self.stdout.write("✅ التصعيد: متاح للحالات النشطة")
        self.stdout.write("✅ إضافة ملاحظات: متاح لجميع الحالات (ما عدا المغلقة والملغية)")
