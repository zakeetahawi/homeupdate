#!/bin/bash
# تنظيف سجلات النشاط القديمة تلقائياً
# يُشغل يومياً في الساعة 2 صباحاً

cd /home/zakee/homeupdate
source venv/bin/activate

python << 'EOF'
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from user_activity.models import UserActivityLog
from django.utils import timezone
from datetime import timedelta

# حذف السجلات الأقدم من 30 يوم
cutoff_date = timezone.now() - timedelta(days=30)
old_logs = UserActivityLog.objects.filter(timestamp__lt=cutoff_date)
count = old_logs.count()

if count > 0:
    deleted = old_logs.delete()
    print(f"✅ تم حذف {deleted[0]:,} سجل نشاط قديم")
else:
    print("✅ لا توجد سجلات قديمة للحذف")
EOF

# VACUUM قاعدة البيانات
python manage.py shell << 'EOF'
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("VACUUM ANALYZE user_activity_useractivitylog;")
print("✅ تم تحسين جدول سجلات النشاط")
EOF

echo "✅ اكتمل التنظيف التلقائي"
