from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.checks import Error, Warning
from django.core.checks.security.base import SECRET_KEY_MIN_LENGTH
import requests
import socket
import ssl

class Command(BaseCommand):
    help = 'Check security settings and SSL configuration'

    def handle(self, *args, **options):
        self.stdout.write('Checking security configuration...\n')
        
        # Check SSL/TLS settings
        self.stdout.write('\nSSL/TLS Configuration:')
        if settings.SECURE_SSL_REDIRECT:
            self.stdout.write(self.style.SUCCESS('✓ SECURE_SSL_REDIRECT is enabled'))
        else:
            self.stdout.write(self.style.WARNING('✗ SECURE_SSL_REDIRECT is not enabled'))
            
        if hasattr(settings, 'SECURE_PROXY_SSL_HEADER') and settings.SECURE_PROXY_SSL_HEADER:
            self.stdout.write(self.style.SUCCESS('✓ SECURE_PROXY_SSL_HEADER is configured'))
        else:
            self.stdout.write(self.style.WARNING('✗ SECURE_PROXY_SSL_HEADER is not configured'))

        # Check HSTS settings
        self.stdout.write('\nHSTS Configuration:')
        if settings.SECURE_HSTS_SECONDS:
            self.stdout.write(self.style.SUCCESS(f'✓ HSTS is enabled ({settings.SECURE_HSTS_SECONDS} seconds)'))
            if settings.SECURE_HSTS_INCLUDE_SUBDOMAINS:
                self.stdout.write(self.style.SUCCESS('✓ HSTS includes subdomains'))
            if settings.SECURE_HSTS_PRELOAD:
                self.stdout.write(self.style.SUCCESS('✓ HSTS preload is enabled'))
        else:
            self.stdout.write(self.style.WARNING('✗ HSTS is not enabled'))

        # Check cookie settings
        self.stdout.write('\nCookie Security:')
        if settings.SESSION_COOKIE_SECURE:
            self.stdout.write(self.style.SUCCESS('✓ Secure session cookies enabled'))
        else:
            self.stdout.write(self.style.WARNING('✗ Secure session cookies not enabled'))
            
        if settings.CSRF_COOKIE_SECURE:
            self.stdout.write(self.style.SUCCESS('✓ Secure CSRF cookies enabled'))
        else:
            self.stdout.write(self.style.WARNING('✗ Secure CSRF cookies not enabled'))

        # Check content security
        self.stdout.write('\nContent Security:')
        if settings.SECURE_CONTENT_TYPE_NOSNIFF:
            self.stdout.write(self.style.SUCCESS('✓ Content type nosniff enabled'))
        else:
            self.stdout.write(self.style.WARNING('✗ Content type nosniff not enabled'))

        if settings.SECURE_REFERRER_POLICY:
            self.stdout.write(self.style.SUCCESS(f'✓ Referrer Policy is set to: {settings.SECURE_REFERRER_POLICY}'))
        else:
            self.stdout.write(self.style.WARNING('✗ Referrer Policy not set'))

        # Check ALLOWED_HOSTS
        self.stdout.write('\nServer Configuration:')
        if settings.ALLOWED_HOSTS:
            self.stdout.write(self.style.SUCCESS(f'✓ ALLOWED_HOSTS is configured: {", ".join(settings.ALLOWED_HOSTS)}'))
        else:
            self.stdout.write(self.style.ERROR('✗ ALLOWED_HOSTS is empty'))

        # Check CSRF settings
        if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE:
            self.stdout.write(self.style.SUCCESS('✓ CSRF protection enabled'))
        else:
            self.stdout.write(self.style.ERROR('✗ CSRF protection not enabled'))

        # Check DEBUG setting
        if settings.DEBUG:
            self.stdout.write(self.style.ERROR('✗ DEBUG is enabled - disable this in production'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ DEBUG is disabled'))