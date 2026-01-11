"""
Admin configurations for the public app
"""

from django.contrib import admin

# استيراد إعدادات admin الخاصة بتصميم QR
from .admin_qr_design import QRDesignSettingsAdmin

# تم تسجيل النماذج في admin_qr_design.py باستخدام @admin.register
# هذا الاستيراد يضمن تحميلها عند تحميل النظام
