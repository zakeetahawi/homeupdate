#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'home.settings')
django.setup()

from orders.models import Order
from django.db import transaction, connection

# البحث عن طلب موجود للاختبار
test_order = Order.objects.filter(order_number__startswith='1-0001').first()

if test_order:
    print(f'✅ تم العثور على طلب للاختبار: {test_order.order_number}')
    print(f'📊 عدد العناصر: {test_order.items.count()}')
    print(f'📊 عدد السجلات: {test_order.status_logs.count()}')
    print(f'📊 عدد المعاينات: {test_order.inspections.count()}')
    
    # حفظ معلومات الطلب
    order_number = test_order.order_number
    order_id = test_order.pk
    
    print(f'\n🗑️ محاولة حذف الطلب...')
    try:
        with transaction.atomic():
            # حذف سجلات الحالة باستخدام raw SQL
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM orders_orderstatuslog WHERE order_id = %s', [order_id])
                print(f'✅ تم حذف سجلات الحالة')
            
            # حذف الطلب
            test_order.delete()
            print(f'✅ تم حذف الطلب')
            
        print(f'\n🎉🎉🎉 تم حذف الطلب {order_number} بنجاح! 🎉🎉🎉')
        print(f'✅ لم يحدث خطأ IntegrityError')
        
        # التحقق من أن الطلب تم حذفه فعلاً
        if not Order.objects.filter(pk=order_id).exists():
            print(f'✅ تم التأكد من حذف الطلب من قاعدة البيانات')
        else:
            print(f'❌ الطلب لا يزال موجوداً في قاعدة البيانات!')
            
    except Exception as e:
        print(f'❌ حدث خطأ أثناء الحذف: {e}')
        print(f'❌ نوع الخطأ: {type(e).__name__}')
        import traceback
        traceback.print_exc()
else:
    print('❌ لم يتم العثور على طلب للاختبار')

