#!/usr/bin/env python
"""
فحص تفصيلي للمهام العالقة
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import BulkUploadLog
import redis

# فحص السجلات العالقة
stuck = BulkUploadLog.objects.filter(status='processing').values('id', 'task_id', 'file_name', 'created_at')
print(f'📊 عدد السجلات العالقة: {len(stuck)}')
print('='*80)

for log in stuck:
    print(f"\n🔍 سجل ID: {log['id']}")
    print(f"   الملف: {log['file_name']}")
    print(f"   Task ID: {log['task_id']}")
    print(f"   وقت الإنشاء: {log['created_at']}")
    
# فحص اتصال Redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    ping = r.ping()
    print(f'\n✅ Redis يعمل: {ping}')
    
    # فحص حالة المهام في Redis
    if len(stuck) > 0:
        print('\n🔎 فحص حالة المهام في Redis:')
        for log in stuck:
            if log['task_id']:
                task_meta = r.get(f"celery-task-meta-{log['task_id']}")
                if task_meta:
                    print(f"   ✅ مهمة {log['id']}: موجودة في Redis")
                    print(f"      البيانات: {task_meta.decode('utf-8')[:200]}...")
                else:
                    print(f"   ⚠️  مهمة {log['id']}: غير موجودة في Redis - المهمة مفقودة!")
            else:
                print(f"   ⚠️  سجل {log['id']}: لا يوجد task_id")
                
    # فحص الطابور (Queue)
    queue_length = r.llen('celery')
    print(f'\n📋 عدد المهام في الطابور: {queue_length}')
    
except Exception as e:
    print(f'❌ خطأ في Redis: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '='*80)
print('💡 الخلاصة:')
print('   - إذا كانت المهام غير موجودة في Redis: المهام فُقدت ولم تُنفذ')
print('   - إذا كان الطابور فارغاً: Celery Worker قد لا يعمل أو أنهى المهام')
print('   - الحل: حذف السجلات العالقة وإعادة المحاولة')
