#!/usr/bin/env python
"""
سكريبت لحل التنبيهات الخاطئة
يقوم بمراجعة جميع تنبيهات نفاذ المخزون النشطة
ويحل التنبيهات للمنتجات التي أصبحت متوفرة
"""
import os
import sys
import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import StockAlert, Product
from django.utils import timezone
from django.db import transaction

def fix_false_alerts():
    """حل التنبيهات الخاطئة"""
    
    print('🔧 فحص وإصلاح التنبيهات الخاطئة...')
    print('=' * 100)
    
    # الحصول على جميع تنبيهات النفاذ النشطة
    out_of_stock_alerts = StockAlert.objects.filter(
        alert_type='out_of_stock',
        status='active'
    ).select_related('product')
    
    total_alerts = out_of_stock_alerts.count()
    print(f'إجمالي تنبيهات النفاذ النشطة: {total_alerts}')
    print()
    
    if total_alerts == 0:
        print('✅ لا توجد تنبيهات نشطة!')
        return
    
    # فحص كل تنبيه
    false_alerts = []
    correct_alerts = []
    
    print('جاري الفحص...')
    for i, alert in enumerate(out_of_stock_alerts, 1):
        if i % 10 == 0:
            print(f'  تم فحص {i}/{total_alerts}...', end='\r')
        
        # حساب المخزون الفعلي
        current_stock = alert.product.current_stock
        
        if current_stock > 0:
            false_alerts.append({
                'alert': alert,
                'product': alert.product,
                'stock': current_stock
            })
        else:
            correct_alerts.append(alert)
    
    print(' ' * 50, end='\r')  # مسح السطر
    
    print()
    print('=' * 100)
    print('📊 نتائج الفحص:')
    print('=' * 100)
    print(f'✅ تنبيهات صحيحة (منتج فعلاً نفذ): {len(correct_alerts)}')
    print(f'❌ تنبيهات خاطئة (منتج متوفر): {len(false_alerts)}')
    print(f'📈 نسبة التنبيهات الخاطئة: {(len(false_alerts)/total_alerts*100):.1f}%')
    print()
    
    if not false_alerts:
        print('✅ جميع التنبيهات صحيحة!')
        return
    
    # عرض عينة من التنبيهات الخاطئة
    print('🔴 عينة من التنبيهات الخاطئة:')
    print('-' * 100)
    print(f'{'الكود':<30} {'الاسم':<40} {'الكمية المتوفرة':<20}')
    print('-' * 100)
    
    for item in false_alerts[:10]:
        code = item['product'].code or 'بدون كود'
        name = item['product'].name[:37] + '...' if len(item['product'].name) > 40 else item['product'].name
        stock = f"{item['stock']:.2f}"
        print(f'{code:<30} {name:<40} {stock:<20}')
    
    if len(false_alerts) > 10:
        print(f'... و {len(false_alerts) - 10} تنبيه خاطئ آخر')
    
    print()
    print('=' * 100)
    
    # طلب التأكيد
    response = input(f'❓ هل تريد حل {len(false_alerts)} تنبيه خاطئ؟ (yes/no): ').strip().lower()
    
    if response not in ['yes', 'y', 'نعم']:
        print('❌ تم الإلغاء')
        return
    
    # حل التنبيهات الخاطئة
    print()
    print('🔧 جاري حل التنبيهات الخاطئة...')
    
    resolved_count = 0
    with transaction.atomic():
        for item in false_alerts:
            alert = item['alert']
            alert.status = 'resolved'
            alert.resolved_at = timezone.now()
            alert.save()
            resolved_count += 1
    
    print(f'✅ تم حل {resolved_count} تنبيه خاطئ بنجاح!')
    print()
    
    # إحصائيات نهائية
    remaining_active = StockAlert.objects.filter(
        alert_type='out_of_stock',
        status='active'
    ).count()
    
    print('=' * 100)
    print('📊 الإحصائيات النهائية:')
    print('=' * 100)
    print(f'تنبيهات نشطة متبقية: {remaining_active}')
    print(f'تنبيهات تم حلها: {resolved_count}')
    print()
    print('✅ تم الانتهاء!')


if __name__ == '__main__':
    try:
        fix_false_alerts()
    except KeyboardInterrupt:
        print('\n\n❌ تم الإلغاء بواسطة المستخدم')
    except Exception as e:
        print(f'\n\n❌ خطأ: {e}')
        import traceback
        traceback.print_exc()
