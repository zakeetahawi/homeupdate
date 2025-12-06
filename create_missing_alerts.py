#!/usr/bin/env python
"""
سكريبت لإنشاء تنبيهات للمنتجات المنتهية من المخزون
يقوم بفحص جميع المنتجات وإنشاء تنبيهات للمنتجات التي نفذت ولا تملك تنبيهات
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

def create_missing_alerts():
    """إنشاء تنبيهات للمنتجات المنتهية بدون تنبيهات"""
    
    print('🔧 فحص المنتجات المنتهية من المخزون...')
    print('=' * 100)
    
    # البحث عن المنتجات المنتهية
    all_products = Product.objects.all()
    out_of_stock_products = []
    
    print('جاري الفحص...')
    for i, product in enumerate(all_products, 1):
        if i % 100 == 0:
            print(f'  تم فحص {i} منتج...', end='\r')
        
        current_stock = product.current_stock
        if current_stock <= 0:
            # التحقق من عدم وجود تنبيه نشط
            has_alert = StockAlert.objects.filter(
                product=product,
                status='active',
                alert_type='out_of_stock'
            ).exists()
            
            if not has_alert:
                out_of_stock_products.append(product)
    
    print(' ' * 50, end='\r')
    
    print()
    print('=' * 100)
    print('📊 نتائج الفحص:')
    print('=' * 100)
    print(f'منتجات منتهية بدون تنبيه: {len(out_of_stock_products)}')
    print()
    
    if not out_of_stock_products:
        print('✅ جميع المنتجات المنتهية لديها تنبيهات!')
        return
    
    # عرض المنتجات
    print('📦 المنتجات التي سيتم إنشاء تنبيهات لها:')
    print('-' * 100)
    print(f'{'الكود':<30} {'الاسم':<50}')
    print('-' * 100)
    
    for product in out_of_stock_products[:20]:
        code = product.code or 'بدون كود'
        name = product.name[:47] + '...' if len(product.name) > 50 else product.name
        print(f'{code:<30} {name:<50}')
    
    if len(out_of_stock_products) > 20:
        print(f'... و {len(out_of_stock_products) - 20} منتج آخر')
    
    print()
    print('=' * 100)
    
    # طلب التأكيد
    response = input(f'❓ هل تريد إنشاء تنبيهات لـ {len(out_of_stock_products)} منتج؟ (yes/no): ').strip().lower()
    
    if response not in ['yes', 'y', 'نعم']:
        print('❌ تم الإلغاء')
        return
    
    # إنشاء التنبيهات
    print()
    print('🔧 جاري إنشاء التنبيهات...')
    
    created_count = 0
    with transaction.atomic():
        for product in out_of_stock_products:
            alert = StockAlert.objects.create(
                product=product,
                alert_type='out_of_stock',
                priority='high',
                title=f'نفذ المخزون: {product.name}',
                message=f'المنتج {product.name} ({product.code}) نفد من المخزون تماماً',
                description=f'المنتج {product.name} ({product.code}) نفد من المخزون تماماً',
                quantity_before=0,
                quantity_after=0,
                threshold_limit=0,
                status='active'
            )
            created_count += 1
    
    print(f'✅ تم إنشاء {created_count} تنبيه بنجاح!')
    print()
    
    # إحصائيات نهائية
    total_active = StockAlert.objects.filter(
        alert_type='out_of_stock',
        status='active'
    ).count()
    
    print('=' * 100)
    print('📊 الإحصائيات النهائية:')
    print('=' * 100)
    print(f'إجمالي تنبيهات النفاذ النشطة: {total_active}')
    print(f'تنبيهات تم إنشاؤها: {created_count}')
    print()
    print('✅ تم الانتهاء!')


if __name__ == '__main__':
    try:
        create_missing_alerts()
    except KeyboardInterrupt:
        print('\n\n❌ تم الإلغاء بواسطة المستخدم')
    except Exception as e:
        print(f'\n\n❌ خطأ: {e}')
        import traceback
        traceback.print_exc()
