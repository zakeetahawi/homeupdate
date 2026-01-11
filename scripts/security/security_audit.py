#!/usr/bin/env python
"""
🔒 Security Audit Script - فحص أمني شامل
يفحص النظام ويعطي تقرير عن الحالة الأمنية
"""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from colorama import Fore, Style, init
from django.conf import settings
from django.core.management import call_command

init(autoreset=True)


def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{text:^60}")
    print(f"{Fore.CYAN}{'='*60}\n")


def print_check(status, message):
    if status:
        print(f"{Fore.GREEN}✅ {message}")
    else:
        print(f"{Fore.RED}❌ {message}")
    return status


def check_secret_key():
    """فحص SECRET_KEY"""
    print_header("🔑 SECRET_KEY Check")

    key = settings.SECRET_KEY

    # فحص طول المفتاح
    if len(key) >= 50:
        print_check(True, f"SECRET_KEY length: {len(key)} chars (Good)")
    else:
        print_check(
            False, f"SECRET_KEY length: {len(key)} chars (Too short - should be 50+)"
        )

    # فحص إذا كان يحتوي على 'insecure'
    if "insecure" in key.lower():
        print_check(False, "SECRET_KEY contains 'insecure' - CHANGE IT!")
    else:
        print_check(True, "SECRET_KEY doesn't contain 'insecure'")

    # فحص التنوع
    unique_chars = len(set(key))
    if unique_chars < 20:
        print_check(
            False, f"SECRET_KEY has only {unique_chars} unique characters (Too simple)"
        )
    else:
        print_check(True, f"SECRET_KEY has {unique_chars} unique characters")


def check_debug():
    """فحص DEBUG"""
    print_header("🐛 DEBUG Check")

    if settings.DEBUG:
        print_check(False, "DEBUG = True (⚠️  Should be False in production)")

        if os.environ.get("DEVELOPMENT_MODE"):
            print(f"{Fore.YELLOW}   ℹ️  DEVELOPMENT_MODE is set - OK for development")
        else:
            print(
                f"{Fore.RED}   ⚠️  DEVELOPMENT_MODE not set - This might be production!"
            )
    else:
        print_check(True, "DEBUG = False (Safe for production)")


def check_allowed_hosts():
    """فحص ALLOWED_HOSTS"""
    print_header("🌐 ALLOWED_HOSTS Check")

    hosts = settings.ALLOWED_HOSTS

    if "*" in hosts:
        print_check(False, "ALLOWED_HOSTS contains '*' (Security Risk!)")
    else:
        print_check(True, "ALLOWED_HOSTS doesn't contain '*'")

    print(f"\n{Fore.CYAN}Configured hosts:")
    for host in hosts[:10]:  # أول 10
        print(f"  • {host}")

    if len(hosts) > 10:
        print(f"  ... and {len(hosts) - 10} more")


def check_https_settings():
    """فحص إعدادات HTTPS"""
    print_header("🔒 HTTPS/SSL Settings Check")

    checks = [
        ("SECURE_SSL_REDIRECT", getattr(settings, "SECURE_SSL_REDIRECT", False)),
        ("SECURE_HSTS_SECONDS", getattr(settings, "SECURE_HSTS_SECONDS", 0)),
        ("SESSION_COOKIE_SECURE", getattr(settings, "SESSION_COOKIE_SECURE", False)),
        ("CSRF_COOKIE_SECURE", getattr(settings, "CSRF_COOKIE_SECURE", False)),
        (
            "SECURE_BROWSER_XSS_FILTER",
            getattr(settings, "SECURE_BROWSER_XSS_FILTER", False),
        ),
        (
            "SECURE_CONTENT_TYPE_NOSNIFF",
            getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False),
        ),
    ]

    for name, value in checks:
        if isinstance(value, bool):
            print_check(value, f"{name} = {value}")
        else:
            print_check(value > 0, f"{name} = {value}")


def check_database():
    """فحص قاعدة البيانات"""
    print_header("💾 Database Check")

    db = settings.DATABASES["default"]

    print(f"{Fore.CYAN}Engine: {db.get('ENGINE', 'Not set')}")
    print(f"{Fore.CYAN}Name: {db.get('NAME', 'Not set')}")

    # التحقق من عدم وجود كلمات مرور في الكود
    if "PASSWORD" in db and db["PASSWORD"]:
        if db["PASSWORD"] == "postgres" or db["PASSWORD"] == "password":
            print_check(False, "Database password is weak or default!")
        else:
            print_check(True, "Database password is set")
    else:
        print(f"{Fore.YELLOW}⚠️  No database password configured")


def run_django_check():
    """تشغيل فحص Django الأمني"""
    print_header("🔍 Django Security Check")

    print(f"{Fore.YELLOW}Running: python manage.py check --deploy\n")

    try:
        call_command("check", deploy=True)
        print(f"\n{Fore.GREEN}✅ Django security check passed!")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Django security check found issues:")
        print(str(e))


def generate_secure_key():
    """توليد مفتاح آمن جديد"""
    import secrets

    key = secrets.token_hex(50)

    print_header("🔑 Generate New SECRET_KEY")
    print(f"{Fore.GREEN}New SECRET_KEY (copy to .env):\n")
    print(f"{Fore.YELLOW}SECRET_KEY={key}\n")


def main():
    """Main function"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("=" * 60)
    print(" 🔒 SECURITY AUDIT SCRIPT ".center(60))
    print("=" * 60)
    print(Style.RESET_ALL)

    # Run all checks
    check_secret_key()
    check_debug()
    check_allowed_hosts()
    check_https_settings()
    check_database()
    run_django_check()

    # Options
    print_header("📋 Actions")
    print("1. Generate new SECRET_KEY")
    print("2. Exit")

    choice = input(f"\n{Fore.CYAN}Choose an option (1-2): {Fore.RESET}")

    if choice == "1":
        generate_secure_key()

    print(f"\n{Fore.GREEN}✅ Security audit complete!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Audit interrupted by user")
        sys.exit(0)
