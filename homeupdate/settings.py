INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_apscheduler',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    # الأقسام الأساسية
    'accounts',  # Accounts
    'customers',  # إدارة العملاء
    'orders',  # الطلبات
    'inspections',  # المعاينات
    'manufacturing',  # Manufacturing
    'installations',  # قسم التركيبات
    'odoo_db_manager',  # إدارة قواعد البيانات
    'inventory',  # إدارة المخزون
    'reports',  # التقارير
    'backup_system',  # نظام النسخ الاحتياطي والاستعادة الجديد

]

import os
import dj_database_url

# إعدادات قاعدة البيانات
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:5525@localhost:5432/crm_system')

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL)
}
