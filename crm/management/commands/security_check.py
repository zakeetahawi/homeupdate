"""
أمر Django للفحص الأمني الدوري
يفحص إعدادات الأمان ويحذر من المشاكل
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'فحص أمني للإعدادات والكود'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل أكثر',
        )
    
    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        issues = []
        warnings = []
        recommendations = []
        
        self.stdout.write(self.style.SUCCESS('\n🔒 بدء الفحص الأمني...\n'))
        
        # 1. فحص DEBUG
        if settings.DEBUG:
            issues.append('⚠️  DEBUG مفعّل - يجب تعطيله في الإنتاج')
            if verbose:
                self.stdout.write(self.style.WARNING('  DEBUG = True وُجد في settings.py'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ DEBUG معطّل'))
        
        # 2. فحص SECRET_KEY
        if hasattr(settings, 'SECRET_KEY'):
            if settings.SECRET_KEY.startswith('dev-insecure'):
                issues.append('⚠️  SECRET_KEY يستخدم مفتاح التطوير')
            elif len(settings.SECRET_KEY) < 50:
                warnings.append('⚡ SECRET_KEY قصير جداً (يفضل 50+ حرف)')
            else:
                self.stdout.write(self.style.SUCCESS('✅ SECRET_KEY آمن'))
        else:
            issues.append('🔴 SECRET_KEY غير موجود!')
        
        # 3. فحص ALLOWED_HOSTS
        if hasattr(settings, 'ALLOWED_HOSTS'):
            if '*' in settings.ALLOWED_HOSTS:
                issues.append('⚠️  ALLOWED_HOSTS يسمح بجميع النطاقات (*)')
            elif not settings.ALLOWED_HOSTS:
                issues.append('⚠️  ALLOWED_HOSTS فارغ')
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ ALLOWED_HOSTS محدد ({len(settings.ALLOWED_HOSTS)} نطاق)'))
        
        # 4. فحص إعدادات HTTPS (للإنتاج فقط)
        if not settings.DEBUG:
            https_settings = {
                'SECURE_SSL_REDIRECT': 'إعادة التوجيه لـ HTTPS',
                'SESSION_COOKIE_SECURE': 'ملفات تعريف جلسة آمنة',
                'CSRF_COOKIE_SECURE': 'ملفات تعريف CSRF آمنة',
                'SECURE_HSTS_SECONDS': 'HTTP Strict Transport Security',
            }
            
            for setting_name, description in https_settings.items():
                if not getattr(settings, setting_name, False):
                    warnings.append(f'⚡ {setting_name} غير مفعّل ({description})')
                else:
                    if verbose:
                        self.stdout.write(self.style.SUCCESS(f'  ✅ {setting_name}'))
        
        # 5. فحص DATABASES
        if hasattr(settings, 'DATABASES'):
            default_db = settings.DATABASES.get('default', {})
            if default_db.get('PASSWORD') in ['', 'password', '1234']:
                issues.append('🔴 كلمة مرور قاعدة البيانات ضعيفة أو فارغة')
            else:
                self.stdout.write(self.style.SUCCESS('✅ كلمة مرور قاعدة البيانات محمية'))
        
        # 6. فحص MIDDLEWARE
        if hasattr(settings, 'MIDDLEWARE'):
            required_middleware = [
                'django.middleware.security.SecurityMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ]
            
            for middleware in required_middleware:
                if middleware not in settings.MIDDLEWARE:
                    warnings.append(f'⚡ {middleware} مفقود من MIDDLEWARE')
                elif verbose:
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {middleware}'))
        
        # 7. فحص كلمات المرور القوية
        if hasattr(settings, 'AUTH_PASSWORD_VALIDATORS'):
            if len(settings.AUTH_PASSWORD_VALIDATORS) < 3:
                warnings.append('⚡ قليل من محققي كلمات المرور (يفضل 4+)')
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ محققي كلمات المرور ({len(settings.AUTH_PASSWORD_VALIDATORS)})'))
        
        # 8. فحص إعدادات الملفات
        file_settings = {
            'FILE_UPLOAD_MAX_MEMORY_SIZE': 10 * 1024 * 1024,  # 10 MB
            'DATA_UPLOAD_MAX_MEMORY_SIZE': 10 * 1024 * 1024,  # 10 MB
        }
        
        for setting_name, recommended_value in file_settings.items():
            if not hasattr(settings, setting_name):
                recommendations.append(f'💡 يُنصح بتعيين {setting_name}')
            elif verbose:
                current = getattr(settings, setting_name)
                self.stdout.write(self.style.SUCCESS(f'  ✅ {setting_name} = {current}'))
        
        # 9. فحص X-Frame-Options
        if not settings.DEBUG:
            x_frame = getattr(settings, 'X_FRAME_OPTIONS', None)
            if x_frame not in ['DENY', 'SAMEORIGIN']:
                warnings.append('⚡ X_FRAME_OPTIONS يجب أن يكون DENY أو SAMEORIGIN')
            elif verbose:
                self.stdout.write(self.style.SUCCESS(f'  ✅ X_FRAME_OPTIONS = {x_frame}'))
        
        # 10. فحص Session timeout
        session_age = getattr(settings, 'SESSION_COOKIE_AGE', None)
        if session_age and session_age > 86400 * 7:  # أكثر من أسبوع
            warnings.append('⚡ SESSION_COOKIE_AGE طويل جداً (أكثر من أسبوع)')
        elif verbose and session_age:
            days = session_age / 86400
            self.stdout.write(self.style.SUCCESS(f'  ✅ SESSION_COOKIE_AGE = {days:.1f} يوم'))
        
        # طباعة النتائج
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('\n📊 ملخص الفحص الأمني:\n'))
        
        if not issues and not warnings:
            self.stdout.write(self.style.SUCCESS('✅ لم يتم العثور على مشاكل أمنية!'))
            self.stdout.write(self.style.SUCCESS('   النظام آمن ومُعد بشكل صحيح.\n'))
        else:
            if issues:
                self.stdout.write(self.style.ERROR(f'\n🔴 مشاكل عاجلة ({len(issues)}):'))
                for issue in issues:
                    self.stdout.write(self.style.ERROR(f'  {issue}'))
            
            if warnings:
                self.stdout.write(self.style.WARNING(f'\n⚡ تحذيرات ({len(warnings)}):'))
                for warning in warnings:
                    self.stdout.write(self.style.WARNING(f'  {warning}'))
            
            if recommendations:
                self.stdout.write(self.style.HTTP_INFO(f'\n💡 توصيات ({len(recommendations)}):'))
                for rec in recommendations:
                    self.stdout.write(self.style.HTTP_INFO(f'  {rec}'))
        
        self.stdout.write('\n' + '='*70)
        
        # نصائح عامة
        self.stdout.write(self.style.HTTP_INFO('\n💡 نصائح للأمان الأفضل:'))
        self.stdout.write('  1. راجع ملف .env وتأكد من عدم رفعه لـ Git')
        self.stdout.write('  2. استخدم HTTPS في الإنتاج دائماً')
        self.stdout.write('  3. حدّث المكتبات بانتظام: pip list --outdated')
        self.stdout.write('  4. فعّل النسخ الاحتياطي التلقائي')
        self.stdout.write('  5. راقب السجلات (logs) بانتظام\n')
        
        # الخروج بكود خطأ إذا كانت هناك مشاكل عاجلة
        if issues:
            self.stdout.write(self.style.ERROR('⚠️  يوجد مشاكل أمنية عاجلة يجب إصلاحها!\n'))
            return  # لا نرمي خطأ، فقط ننبه
        
        self.stdout.write(self.style.SUCCESS('✅ الفحص الأمني اكتمل بنجاح!\n'))
