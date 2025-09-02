"""
Management command لإنشاء بيانات تجريبية لنظام تتبع النشاط
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import random

from user_activity.models import UserActivityLog, UserSession, UserLoginHistory, OnlineUser

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية لنظام تتبع النشاط'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='عدد المستخدمين لإنشاء بيانات لهم (افتراضي: 5)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='عدد الأيام للبيانات التجريبية (افتراضي: 7)'
        )
        
        parser.add_argument(
            '--activities-per-day',
            type=int,
            default=20,
            help='عدد الأنشطة لكل يوم لكل مستخدم (افتراضي: 20)'
        )

    def handle(self, *args, **options):
        users_count = options['users']
        days = options['days']
        activities_per_day = options['activities_per_day']
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 بدء إنشاء بيانات تجريبية لـ {users_count} مستخدمين لمدة {days} أيام')
        )
        
        # الحصول على المستخدمين
        users = list(User.objects.all()[:users_count])
        if len(users) < users_count:
            self.stdout.write(
                self.style.WARNING(f'⚠️ يوجد فقط {len(users)} مستخدمين في النظام')
            )
        
        if not users:
            self.stdout.write(
                self.style.ERROR('❌ لا يوجد مستخدمون في النظام')
            )
            return
        
        # إنشاء البيانات
        total_activities = 0
        total_sessions = 0
        total_logins = 0
        
        for day in range(days):
            date = timezone.now() - timedelta(days=day)
            
            for user in users:
                # إنشاء جلسة تسجيل دخول
                login_time = date.replace(
                    hour=random.randint(8, 10),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                logout_time = login_time + timedelta(
                    hours=random.randint(4, 8),
                    minutes=random.randint(0, 59)
                )
                
                # إنشاء سجل تسجيل دخول
                login_history = UserLoginHistory.objects.create(
                    user=user,
                    login_time=login_time,
                    logout_time=logout_time,
                    ip_address=self.get_random_ip(),
                    user_agent=self.get_random_user_agent(),
                    session_key=f'session_{user.id}_{day}_{random.randint(1000, 9999)}',
                    browser=random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
                    operating_system=random.choice(['Windows 10', 'macOS', 'Ubuntu', 'iOS', 'Android']),
                    device_type=random.choice(['desktop', 'mobile', 'tablet']),
                    pages_visited=random.randint(10, 50),
                    actions_performed=random.randint(5, 25),
                    logout_reason='manual'
                )
                total_logins += 1
                
                # إنشاء جلسة
                session = UserSession.objects.create(
                    user=user,
                    session_key=login_history.session_key,
                    ip_address=login_history.ip_address,
                    user_agent=login_history.user_agent,
                    login_time=login_time,
                    last_activity=logout_time,
                    logout_time=logout_time,
                    is_active=False,
                    device_type=login_history.device_type,
                    browser=login_history.browser,
                    operating_system=login_history.operating_system
                )
                total_sessions += 1
                
                # إنشاء أنشطة للجلسة
                current_time = login_time
                for activity_num in range(random.randint(activities_per_day // 2, activities_per_day)):
                    current_time += timedelta(minutes=random.randint(5, 30))
                    if current_time > logout_time:
                        break
                    
                    activity_type = random.choice([
                        'page_view', 'dashboard_view', 'create', 'update', 'delete',
                        'search', 'export', 'read'
                    ])
                    
                    entity_type = random.choice([
                        'customer', 'order', 'product', 'inspection', 'manufacturing',
                        'installation', 'inventory', 'report', 'page'
                    ])
                    
                    UserActivityLog.objects.create(
                        user=user,
                        session=session,
                        action_type=activity_type,
                        entity_type=entity_type,
                        description=self.get_activity_description(activity_type, entity_type),
                        url_path=self.get_random_url_path(entity_type),
                        http_method=random.choice(['GET', 'POST', 'PUT', 'DELETE']),
                        ip_address=login_history.ip_address,
                        user_agent=login_history.user_agent,
                        timestamp=current_time,
                        success=random.choice([True, True, True, True, False]),  # 80% نجاح
                        extra_data={
                            'page_title': self.get_page_title(entity_type),
                            'status_code': random.choice([200, 201, 400, 404, 500]),
                        }
                    )
                    total_activities += 1
        
        # إنشاء بعض المستخدمين النشطين حالياً
        online_users_count = min(3, len(users))
        for i in range(online_users_count):
            user = users[i]
            OnlineUser.objects.update_or_create(
                user=user,
                defaults={
                    'last_seen': timezone.now() - timedelta(minutes=random.randint(0, 4)),
                    'current_page': '/dashboard/',
                    'current_page_title': 'لوحة التحكم',
                    'ip_address': self.get_random_ip(),
                    'session_key': f'current_session_{user.id}',
                    'device_info': {
                        'browser': 'Chrome 120.0',
                        'os': 'Windows 10',
                        'device': 'Desktop',
                        'is_mobile': False,
                        'is_tablet': False,
                        'is_pc': True,
                    },
                    'pages_visited': random.randint(5, 15),
                    'actions_performed': random.randint(2, 10),
                    'login_time': timezone.now() - timedelta(hours=random.randint(1, 4)),
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ تم إنشاء البيانات التجريبية بنجاح:\n'
                f'   📊 {total_activities} نشاط\n'
                f'   🔐 {total_logins} سجل دخول\n'
                f'   💻 {total_sessions} جلسة\n'
                f'   🟢 {online_users_count} مستخدم متصل حالياً'
            )
        )

    def get_random_ip(self):
        """إنشاء عنوان IP عشوائي"""
        return f"{random.randint(192, 203)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

    def get_random_user_agent(self):
        """إنشاء user agent عشوائي"""
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        ]
        return random.choice(agents)

    def get_activity_description(self, activity_type, entity_type):
        """إنشاء وصف للنشاط"""
        descriptions = {
            'page_view': f'عرض صفحة {entity_type}',
            'dashboard_view': 'عرض لوحة التحكم',
            'create': f'إنشاء {entity_type} جديد',
            'update': f'تحديث {entity_type}',
            'delete': f'حذف {entity_type}',
            'search': f'البحث في {entity_type}',
            'export': f'تصدير بيانات {entity_type}',
            'read': f'قراءة تفاصيل {entity_type}',
        }
        return descriptions.get(activity_type, f'{activity_type} {entity_type}')

    def get_random_url_path(self, entity_type):
        """إنشاء مسار URL عشوائي"""
        paths = {
            'customer': f'/customers/{random.randint(1, 100)}/',
            'order': f'/orders/{random.randint(1, 200)}/',
            'product': f'/products/{random.randint(1, 50)}/',
            'inspection': f'/inspections/{random.randint(1, 150)}/',
            'manufacturing': f'/manufacturing/{random.randint(1, 80)}/',
            'installation': f'/installations/{random.randint(1, 120)}/',
            'inventory': f'/inventory/{random.randint(1, 60)}/',
            'report': f'/reports/{random.choice(["daily", "monthly", "yearly"])}/',
            'page': random.choice(['/dashboard/', '/profile/', '/settings/']),
        }
        return paths.get(entity_type, f'/{entity_type}/')

    def get_page_title(self, entity_type):
        """إنشاء عنوان صفحة"""
        titles = {
            'customer': 'إدارة العملاء',
            'order': 'إدارة الطلبات',
            'product': 'إدارة المنتجات',
            'inspection': 'إدارة المعاينات',
            'manufacturing': 'إدارة التصنيع',
            'installation': 'إدارة التركيبات',
            'inventory': 'إدارة المخزون',
            'report': 'التقارير',
            'page': 'صفحة عامة',
        }
        return titles.get(entity_type, entity_type)
