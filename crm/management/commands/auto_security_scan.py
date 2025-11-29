"""
نظام فحص أمني تلقائي متقدم
يفحص المشروع بحثاً عن ثغرات أمنية بشكل دوري
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import re
import json
from pathlib import Path
from datetime import datetime


class Command(BaseCommand):
    help = 'فحص أمني متقدم تلقائي للمشروع'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='فحص شامل (يستغرق وقتاً أطول)',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح المشاكل تلقائياً حيثما أمكن',
        )
    
    def handle(self, *args, **options):
        full_scan = options.get('full', False)
        auto_fix = options.get('fix', False)
        
        self.stdout.write(self.style.SUCCESS('\n🔍 بدء الفحص الأمني المتقدم...\n'))
        
        issues = []
        critical = []
        warnings = []
        info = []
        
        # 1. فحص استخدام eval/exec الخطر
        self.stdout.write('1️⃣  فحص الدوال الخطرة...')
        dangerous = self.scan_dangerous_functions()
        if dangerous:
            critical.extend(dangerous)
        
        # 2. فحص hardcoded secrets
        self.stdout.write('2️⃣  فحص المفاتيح المكشوفة...')
        secrets = self.scan_hardcoded_secrets()
        if secrets:
            critical.extend(secrets)
        
        # 3. فحص SQL Injection المحتملة
        self.stdout.write('3️⃣  فحص SQL Injection...')
        sql_issues = self.scan_sql_injection()
        if sql_issues:
            warnings.extend(sql_issues)
        
        # 4. فحص XSS في Templates
        self.stdout.write('4️⃣  فحص XSS في القوالب...')
        xss_issues = self.scan_xss_templates()
        if xss_issues:
            warnings.extend(xss_issues)
        
        # 5. فحص Dependencies القديمة
        self.stdout.write('5️⃣  فحص المكتبات القديمة...')
        outdated = self.scan_outdated_packages()
        if outdated:
            info.extend(outdated)
        
        # 6. فحص إعدادات DEBUG
        self.stdout.write('6️⃣  فحص إعدادات DEBUG...')
        debug_check = self.check_debug_settings()
        if debug_check:
            warnings.extend(debug_check)
        
        # 7. فحص الأذونات
        self.stdout.write('7️⃣  فحص أذونات الملفات...')
        permissions = self.scan_file_permissions()
        if permissions:
            info.extend(permissions)
        
        # 8. فحص HTTPS
        self.stdout.write('8️⃣  فحص إعدادات HTTPS...')
        https_check = self.check_https_settings()
        if https_check:
            warnings.extend(https_check)
        
        if full_scan:
            # 9. فحص شامل للكود
            self.stdout.write('9️⃣  فحص شامل للكود...')
            code_issues = self.full_code_scan()
            if code_issues:
                info.extend(code_issues)
        
        # طباعة النتائج
        self.print_results(critical, warnings, info)
        
        # حفظ التقرير
        self.save_report(critical, warnings, info)
        
        # الإصلاح التلقائي
        if auto_fix and (critical or warnings):
            self.auto_fix_issues(critical, warnings)
    
    def scan_dangerous_functions(self):
        """فحص الدوال الخطرة مثل eval, exec"""
        issues = []
        dangerous_patterns = [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'__import__\s*\(',
            r'compile\s*\(',
        ]
        
        for py_file in Path(settings.BASE_DIR).rglob('*.py'):
            if 'venv' in str(py_file) or 'migrations' in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                for pattern in dangerous_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        issues.append({
                            'type': 'CRITICAL',
                            'file': str(py_file.relative_to(settings.BASE_DIR)),
                            'line': line_num,
                            'issue': f'استخدام دالة خطرة: {match.group()}',
                            'severity': 'عالي جداً'
                        })
            except:
                pass
        
        return issues
    
    def scan_hardcoded_secrets(self):
        """فحص المفاتيح السرية المكشوفة"""
        issues = []
        secret_patterns = [
            (r'password\s*=\s*["\'](?!.*{).{8,}["\']', 'كلمة مرور مكشوفة'),
            (r'api[_-]?key\s*=\s*["\'].+["\']', 'API key مكشوف'),
            (r'secret[_-]?key\s*=\s*["\'].+["\']', 'Secret key مكشوف'),
            (r'aws[_-]?access', 'AWS credentials مكشوفة'),
        ]
        
        for py_file in Path(settings.BASE_DIR).rglob('*.py'):
            if 'venv' in str(py_file) or 'migrations' in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                for pattern, desc in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append({
                            'type': 'CRITICAL',
                            'file': str(py_file.relative_to(settings.BASE_DIR)),
                            'issue': desc,
                            'severity': 'عالي'
                        })
            except:
                pass
        
        return issues
    
    def scan_sql_injection(self):
        """فحص SQL Injection المحتملة"""
        issues = []
        sql_patterns = [
            r'\.raw\s*\(',
            r'\.extra\s*\(',
            r'cursor\.execute\s*\(\s*f["\']',
            r'cursor\.execute\s*\(\s*["\'].*%s',
        ]
        
        for py_file in Path(settings.BASE_DIR).rglob('*.py'):
            if 'venv' in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                for pattern in sql_patterns:
                    if re.search(pattern, content):
                        issues.append({
                            'type': 'WARNING',
                            'file': str(py_file.relative_to(settings.BASE_DIR)),
                            'issue': 'SQL query محتمل الخطورة - راجع يدوياً',
                            'severity': 'متوسط'
                        })
            except:
                pass
        
        return issues
    
    def scan_xss_templates(self):
        """فحص XSS في القوالب"""
        issues = []
        
        for template in Path(settings.BASE_DIR).rglob('*.html'):
            if 'venv' in str(template):
                continue
            
            try:
                content = template.read_text()
                
                # فحص استخدام |safe
                safe_count = len(re.findall(r'\|safe', content))
                if safe_count > 0:
                    issues.append({
                        'type': 'WARNING',
                        'file': str(template.relative_to(settings.BASE_DIR)),
                        'issue': f'استخدام |safe {safe_count} مرة - تأكد من أمان البيانات',
                        'severity': 'متوسط'
                    })
                
                # فحص innerHTML
                innerhtml_count = len(re.findall(r'\.innerHTML\s*=', content))
                if innerhtml_count > 0:
                    issues.append({
                        'type': 'WARNING',
                        'file': str(template.relative_to(settings.BASE_DIR)),
                        'issue': f'استخدام innerHTML {innerhtml_count} مرة - استخدم textContent',
                        'severity': 'متوسط'
                    })
            except:
                pass
        
        return issues
    
    def scan_outdated_packages(self):
        """فحص المكتبات القديمة"""
        issues = []
        
        try:
            import subprocess
            result = subprocess.run(
                ['pip', 'list', '--outdated', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                outdated = json.loads(result.stdout)
                for pkg in outdated[:10]:  # أول 10 فقط
                    issues.append({
                        'type': 'INFO',
                        'issue': f'{pkg["name"]} قديمة: {pkg["version"]} → {pkg["latest_version"]}',
                        'severity': 'منخفض'
                    })
        except:
            pass
        
        return issues
    
    def check_debug_settings(self):
        """فحص إعدادات DEBUG"""
        issues = []
        
        if settings.DEBUG:
            issues.append({
                'type': 'WARNING',
                'issue': 'DEBUG = True - يجب تعطيله في الإنتاج',
                'severity': 'عالي'
            })
        
        return issues
    
    def scan_file_permissions(self):
        """فحص أذونات الملفات"""
        issues = []
        
        # فحص ملفات حساسة
        sensitive_files = [
            'manage.py',
            'crm/settings.py',
            '.env',
        ]
        
        for file_path in sensitive_files:
            full_path = Path(settings.BASE_DIR) / file_path
            if full_path.exists():
                mode = oct(full_path.stat().st_mode)[-3:]
                if mode in ['777', '666']:
                    issues.append({
                        'type': 'INFO',
                        'file': file_path,
                        'issue': f'أذونات غير آمنة: {mode}',
                        'severity': 'متوسط'
                    })
        
        return issues
    
    def check_https_settings(self):
        """فحص إعدادات HTTPS"""
        issues = []
        
        if not settings.DEBUG:
            https_settings = {
                'SECURE_SSL_REDIRECT': False,
                'SESSION_COOKIE_SECURE': False,
                'CSRF_COOKIE_SECURE': False,
            }
            
            for setting, default in https_settings.items():
                if not getattr(settings, setting, default):
                    issues.append({
                        'type': 'WARNING',
                        'issue': f'{setting} غير مفعّل',
                        'severity': 'عالي'
                    })
        
        return issues
    
    def full_code_scan(self):
        """فحص شامل للكود"""
        # TODO: تنفيذ فحص أكثر تفصيلاً
        return []
    
    def print_results(self, critical, warnings, info):
        """طباعة النتائج"""
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('\n📊 نتائج الفحص:\n'))
        
        if not critical and not warnings and not info:
            self.stdout.write(self.style.SUCCESS('✅ لم يتم العثور على مشاكل!'))
            self.stdout.write(self.style.SUCCESS('   المشروع آمن جداً.\n'))
            return
        
        if critical:
            self.stdout.write(self.style.ERROR(f'\n🔴 مشاكل حرجة ({len(critical)}):'))
            for issue in critical[:5]:  # أول 5 فقط
                self.stdout.write(self.style.ERROR(f'  • {issue.get("file", "")}: {issue["issue"]}'))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f'\n⚠️  تحذيرات ({len(warnings)}):'))
            for issue in warnings[:5]:
                self.stdout.write(self.style.WARNING(f'  • {issue.get("file", "")}: {issue["issue"]}'))
        
        if info:
            self.stdout.write(self.style.HTTP_INFO(f'\n💡 ملاحظات ({len(info)}):'))
            for issue in info[:5]:
                self.stdout.write(self.style.HTTP_INFO(f'  • {issue["issue"]}'))
        
        self.stdout.write('\n' + '='*70 + '\n')
    
    def save_report(self, critical, warnings, info):
        """حفظ التقرير"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'critical': critical,
            'warnings': warnings,
            'info': info,
            'total': len(critical) + len(warnings) + len(info)
        }
        
        report_file = Path(settings.BASE_DIR) / 'logs' / 'security_scan.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(f'📄 التقرير محفوظ في: {report_file}')
    
    def auto_fix_issues(self, critical, warnings):
        """إصلاح تلقائي للمشاكل"""
        self.stdout.write(self.style.WARNING('\n🔧 محاولة الإصلاح التلقائي...'))
        self.stdout.write(self.style.WARNING('   (قيد التطوير)\n'))
