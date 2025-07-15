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
    'factory',  # المصنع
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
} 