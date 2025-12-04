#!/usr/bin/env python3
"""
🌐 أداة فحص الثغرات عبر HTTP
Web Vulnerability Scanner

⚠️ استخدم فقط على تطبيقاتك الخاصة!
"""

import requests
import sys
import json
import re
import time
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# تعطيل تحذيرات SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║  🌐 Web Vulnerability Scanner                                  ║
║  فحص الثغرات عبر HTTP                                         ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
""")

class WebVulnerabilityScanner:
    def __init__(self, base_url, session=None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.verify = False
        self.vulnerabilities = []
        self.timeout = 10
        
    def add_vulnerability(self, severity, title, url, details):
        self.vulnerabilities.append({
            'severity': severity,
            'title': title,
            'url': url,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        color = {'CRITICAL': Colors.RED, 'HIGH': Colors.RED, 
                 'MEDIUM': Colors.YELLOW, 'LOW': Colors.GREEN}.get(severity, Colors.BLUE)
        print(f"{color}[{severity}]{Colors.END} {title}")
        print(f"  └─ URL: {url}")
        print(f"  └─ {details}\n")
    
    def check_security_headers(self):
        """فحص Security Headers"""
        print(f"\n{Colors.BOLD}[1/8] فحص Security Headers...{Colors.END}")
        
        try:
            response = self.session.get(self.base_url, timeout=self.timeout)
            headers = response.headers
            
            security_headers = {
                'X-Frame-Options': ('MEDIUM', 'حماية Clickjacking'),
                'X-Content-Type-Options': ('LOW', 'منع MIME sniffing'),
                'X-XSS-Protection': ('LOW', 'فلتر XSS'),
                'Strict-Transport-Security': ('MEDIUM', 'فرض HTTPS'),
                'Content-Security-Policy': ('MEDIUM', 'سياسة المحتوى'),
                'Referrer-Policy': ('LOW', 'سياسة المرجع'),
            }
            
            for header, (severity, desc) in security_headers.items():
                if header not in headers:
                    self.add_vulnerability(
                        severity,
                        f'Header مفقود: {header}',
                        self.base_url,
                        desc
                    )
            
            # فحص Server header (يكشف معلومات)
            if 'Server' in headers:
                self.add_vulnerability(
                    'LOW',
                    'Server Header يكشف معلومات',
                    self.base_url,
                    f'Server: {headers["Server"]}'
                )
                
        except Exception as e:
            print(f"{Colors.RED}خطأ: {e}{Colors.END}")
    
    def check_ssl_tls(self):
        """فحص SSL/TLS"""
        print(f"\n{Colors.BOLD}[2/8] فحص SSL/TLS...{Colors.END}")
        
        if self.base_url.startswith('http://'):
            self.add_vulnerability(
                'HIGH',
                'الموقع لا يستخدم HTTPS',
                self.base_url,
                'البيانات تُنقل بدون تشفير'
            )
        
        # فحص إعادة التوجيه من HTTP إلى HTTPS
        if self.base_url.startswith('https://'):
            http_url = self.base_url.replace('https://', 'http://')
            try:
                response = self.session.get(http_url, timeout=self.timeout, allow_redirects=False)
                if response.status_code not in [301, 302, 307, 308]:
                    self.add_vulnerability(
                        'MEDIUM',
                        'HTTP لا يُعيد التوجيه إلى HTTPS',
                        http_url,
                        'يمكن الوصول عبر HTTP غير المشفر'
                    )
            except:
                pass
    
    def check_sensitive_files(self):
        """فحص الملفات الحساسة المكشوفة"""
        print(f"\n{Colors.BOLD}[3/8] فحص الملفات الحساسة...{Colors.END}")
        
        sensitive_paths = [
            ('/.env', 'ملف البيئة'),
            ('/.git/config', 'Git repository'),
            ('/settings.py', 'إعدادات Django'),
            ('/config.php', 'إعدادات PHP'),
            ('/wp-config.php', 'إعدادات WordPress'),
            ('/admin/', 'لوحة التحكم'),
            ('/phpmyadmin/', 'phpMyAdmin'),
            ('/.htaccess', 'Apache config'),
            ('/web.config', 'IIS config'),
            ('/robots.txt', 'Robots file'),
            ('/sitemap.xml', 'Sitemap'),
            ('/debug/', 'Debug endpoint'),
            ('/__debug__/', 'Django Debug Toolbar'),
            ('/static/admin/', 'Django Admin Static'),
            ('/media/', 'Media files'),
            ('/backup/', 'Backup files'),
            ('/db.sqlite3', 'SQLite Database'),
            ('/database.sql', 'SQL Dump'),
            ('/.DS_Store', 'macOS metadata'),
            ('/Thumbs.db', 'Windows metadata'),
        ]
        
        for path, desc in sensitive_paths:
            url = urljoin(self.base_url, path)
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    severity = 'HIGH' if any(x in path for x in ['.env', '.git', 'config', 'sql', 'backup']) else 'MEDIUM'
                    self.add_vulnerability(
                        severity,
                        f'ملف حساس مكشوف: {path}',
                        url,
                        desc
                    )
            except:
                pass
    
    def check_directory_listing(self):
        """فحص Directory Listing"""
        print(f"\n{Colors.BOLD}[4/8] فحص Directory Listing...{Colors.END}")
        
        dirs = ['/static/', '/media/', '/uploads/', '/files/', '/images/']
        
        for dir_path in dirs:
            url = urljoin(self.base_url, dir_path)
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    # البحث عن علامات Directory Listing
                    indicators = ['Index of', 'Directory listing', '<title>Index', 'Parent Directory']
                    if any(ind in response.text for ind in indicators):
                        self.add_vulnerability(
                            'MEDIUM',
                            f'Directory Listing مفعل',
                            url,
                            'يمكن تصفح محتويات المجلد'
                        )
            except:
                pass
    
    def check_sql_injection(self):
        """فحص SQL Injection الأساسي"""
        print(f"\n{Colors.BOLD}[5/8] فحص SQL Injection...{Colors.END}")
        
        # نقاط الاختبار الشائعة
        test_paths = [
            '/api/products/?id=1',
            '/search/?q=test',
            '/user/?id=1',
        ]
        
        sql_payloads = [
            ("'", "SQL syntax error"),
            ("1' OR '1'='1", "boolean-based blind"),
            ("1; DROP TABLE--", "stacked queries"),
            ("1 UNION SELECT NULL--", "union-based"),
        ]
        
        for path in test_paths:
            base_test_url = urljoin(self.base_url, path)
            
            for payload, technique in sql_payloads:
                test_url = base_test_url.replace('=1', f'={payload}').replace('=test', f'={payload}')
                try:
                    response = self.session.get(test_url, timeout=self.timeout)
                    
                    # البحث عن علامات SQL error
                    sql_errors = [
                        'SQL syntax', 'mysql_', 'sqlite3', 'PostgreSQL',
                        'ORA-', 'Microsoft SQL', 'ODBC', 'syntax error',
                        'unclosed quotation', 'quoted string not properly'
                    ]
                    
                    if any(err in response.text for err in sql_errors):
                        self.add_vulnerability(
                            'CRITICAL',
                            f'SQL Injection محتمل ({technique})',
                            test_url,
                            'الموقع قد يكون معرضاً لـ SQL Injection'
                        )
                        break
                except:
                    pass
    
    def check_xss(self):
        """فحص XSS الأساسي"""
        print(f"\n{Colors.BOLD}[6/8] فحص XSS...{Colors.END}")
        
        xss_payloads = [
            '<script>alert(1)</script>',
            '"><script>alert(1)</script>',
            "'-alert(1)-'",
            '<img src=x onerror=alert(1)>',
        ]
        
        test_paths = ['/search/?q=', '/?search=', '/api/?query=']
        
        for path in test_paths:
            for payload in xss_payloads:
                test_url = urljoin(self.base_url, path + payload)
                try:
                    response = self.session.get(test_url, timeout=self.timeout)
                    
                    # تحقق إذا انعكس الـ payload بدون encoding
                    if payload in response.text:
                        self.add_vulnerability(
                            'HIGH',
                            'XSS (Reflected) محتمل',
                            test_url,
                            'المدخل ينعكس بدون filtering'
                        )
                        break
                except:
                    pass
    
    def check_csrf(self):
        """فحص CSRF"""
        print(f"\n{Colors.BOLD}[7/8] فحص CSRF...{Colors.END}")
        
        form_pages = ['/login/', '/register/', '/contact/', '/admin/login/']
        
        for page in form_pages:
            url = urljoin(self.base_url, page)
            try:
                response = self.session.get(url, timeout=self.timeout)
                
                if '<form' in response.text.lower():
                    if 'csrfmiddlewaretoken' not in response.text and 'csrf_token' not in response.text:
                        self.add_vulnerability(
                            'MEDIUM',
                            'CSRF Token مفقود',
                            url,
                            'النموذج لا يحتوي على CSRF token'
                        )
            except:
                pass
    
    def check_admin_panel(self):
        """فحص لوحة التحكم"""
        print(f"\n{Colors.BOLD}[8/8] فحص لوحة التحكم...{Colors.END}")
        
        admin_paths = [
            '/admin/', '/admin/login/', '/administrator/',
            '/wp-admin/', '/login/', '/dashboard/',
            '/cpanel/', '/manager/', '/control/'
        ]
        
        for path in admin_paths:
            url = urljoin(self.base_url, path)
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    self.add_vulnerability(
                        'LOW',
                        f'لوحة تحكم مكشوفة: {path}',
                        url,
                        'يمكن الوصول لصفحة تسجيل الدخول'
                    )
            except:
                pass
    
    def brute_force_test(self, login_url, username_field='username', password_field='password'):
        """اختبار Brute Force (محدود)"""
        print(f"\n{Colors.BOLD}[Bonus] اختبار Brute Force...{Colors.END}")
        
        common_credentials = [
            ('admin', 'admin'),
            ('admin', 'password'),
            ('admin', '123456'),
            ('root', 'root'),
            ('test', 'test'),
        ]
        
        url = urljoin(self.base_url, login_url)
        
        # أولاً، نحصل على CSRF token
        try:
            response = self.session.get(url, timeout=self.timeout)
            csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', response.text)
            csrf_token = csrf_match.group(1) if csrf_match else ''
        except:
            csrf_token = ''
        
        failed_attempts = 0
        for username, password in common_credentials:
            try:
                data = {
                    username_field: username,
                    password_field: password,
                    'csrfmiddlewaretoken': csrf_token
                }
                
                response = self.session.post(url, data=data, timeout=self.timeout)
                failed_attempts += 1
                
                # تحقق من نجاح الدخول
                if 'logout' in response.text.lower() or 'dashboard' in response.text.lower():
                    self.add_vulnerability(
                        'CRITICAL',
                        'كلمة سر ضعيفة/افتراضية',
                        url,
                        f'تم الدخول بـ {username}:{password}'
                    )
                    break
                
                time.sleep(0.5)  # تأخير لتجنب الحظر
            except:
                pass
        
        # تحقق من Rate Limiting
        if failed_attempts >= 5:
            self.add_vulnerability(
                'MEDIUM',
                'لا يوجد Rate Limiting',
                url,
                f'تمت {failed_attempts} محاولات بدون حظر'
            )
    
    def run_full_scan(self):
        """تشغيل الفحص الكامل"""
        print(f"🎯 فحص: {self.base_url}\n")
        
        self.check_security_headers()
        self.check_ssl_tls()
        self.check_sensitive_files()
        self.check_directory_listing()
        self.check_sql_injection()
        self.check_xss()
        self.check_csrf()
        self.check_admin_panel()
        
        return self.vulnerabilities
    
    def generate_report(self, output_file='web_security_report.json'):
        """إنشاء التقرير"""
        from collections import defaultdict
        
        by_severity = defaultdict(list)
        for vuln in self.vulnerabilities:
            by_severity[vuln['severity']].append(vuln)
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}📊 ملخص الفحص{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        total = len(self.vulnerabilities)
        print(f"إجمالي الثغرات: {Colors.BOLD}{total}{Colors.END}\n")
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = len(by_severity[severity])
            color = {'CRITICAL': Colors.RED, 'HIGH': Colors.RED, 
                     'MEDIUM': Colors.YELLOW, 'LOW': Colors.GREEN}[severity]
            if count:
                print(f"  {color}● {severity}: {count}{Colors.END}")
        
        # حفظ التقرير
        report = {
            'target': self.base_url,
            'timestamp': datetime.now().isoformat(),
            'total': total,
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'vulnerabilities': self.vulnerabilities
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n{Colors.GREEN}✅ تم حفظ التقرير: {output_file}{Colors.END}")
        
        return report


def main():
    print_banner()
    
    if len(sys.argv) < 2:
        print(f"الاستخدام: python {sys.argv[0]} <URL>")
        print(f"مثال: python {sys.argv[0]} https://yourdomain.com")
        sys.exit(1)
    
    target_url = sys.argv[1]
    
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'https://' + target_url
    
    scanner = WebVulnerabilityScanner(target_url)
    scanner.run_full_scan()
    scanner.generate_report()


if __name__ == '__main__':
    main()
