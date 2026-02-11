#!/usr/bin/env python
"""
🔧 إصلاح شامل لشجرة حسابات العملاء
=====================================

المشكلة:
--------
- جميع حسابات العملاء (13,919) موجودة تحت "1210 - الأثاث والتجهيزات" (خطأ!)
- يجب نقلها إلى "1121 - العملاء" تحت "1120 - الذمم المدينة"

الحل:
-----
1. نقل جميع حسابات العملاء من parent=1210 إلى parent=1121
2. تحديث أكواد الحسابات من 1210xxxxx إلى 1121xxxxx
3. تحديث جميع المراجع في الكود

"""

import os
import sys
import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from accounting.models import Account
from django.db import transaction
from django.db.models import Q


def main():
    print('=' * 80)
    print('🔧 إصلاح شامل لشجرة حسابات العملاء')
    print('=' * 80)
    
    # التحقق من الحسابات الأساسية
    print('\n📋 التحقق من الحسابات الأساسية...')
    print('-' * 80)
    
    parent_1210 = Account.objects.filter(code='1210').first()
    parent_1121 = Account.objects.filter(code='1121').first()
    
    if not parent_1210:
        print('❌ الحساب 1210 غير موجود!')
        return
    
    if not parent_1121:
        print('❌ الحساب 1121 غير موجود!')
        print('💡 يجب إنشاؤه أولاً من لوحة الإدارة')
        return
    
    print(f'✅ الحساب المصدر: [{parent_1210.code}] {parent_1210.name}')
    print(f'✅ الحساب الهدف:   [{parent_1121.code}] {parent_1121.name}')
    
    # عدّ حسابات العملاء المراد نقلها
    customer_accounts = Account.objects.filter(
        parent=parent_1210,
        customer__isnull=False
    )
    
    total_count = customer_accounts.count()
    print(f'\n📊 عدد حسابات العملاء المراد نقلها: {total_count:,}')
    
    if total_count == 0:
        print('✅ لا توجد حسابات تحتاج نقل!')
        return
    
    # عرض عينة
    print('\n📌 عينة من الحسابات (أول 5):')
    for acc in customer_accounts[:5]:
        print(f'   [{acc.code}] {acc.name} - عميل: {acc.customer.name}')
    
    # طلب التأكيد
    print('\n' + '⚠️ ' * 20)
    confirm = input(f'\n❓ هل تريد المتابعة ونقل {total_count:,} حساب؟ (yes/no): ').strip().lower()
    
    if confirm != 'yes':
        print('❌ تم الإلغاء')
        return
    
    # تنفيذ النقل
    print('\n🚀 بدء عملية النقل...')
    print('-' * 80)
    
    success_count = 0
    error_count = 0
    
    with transaction.atomic():
        for i, acc in enumerate(customer_accounts, 1):
            try:
                old_code = acc.code
                
                # تحديث الكود: استبدال 1210 بـ 1121
                if acc.code.startswith('1210'):
                    new_code = '1121' + acc.code[4:]
                    
                    # التحقق من عدم وجود تضارب
                    if Account.objects.filter(code=new_code).exclude(id=acc.id).exists():
                        print(f'⚠️  تحذير: الكود {new_code} موجود مسبقاً، تخطي {acc.code}')
                        error_count += 1
                        continue
                    
                    acc.code = new_code
                
                # تحديث الحساب الأب
                acc.parent = parent_1121
                acc.save(update_fields=['code', 'parent'])
                
                success_count += 1
                
                # تقدم العملية
                if i % 1000 == 0:
                    print(f'   معالجة: {i:,} / {total_count:,} ({i*100//total_count}%) ✓')
                
            except Exception as e:
                print(f'❌ خطأ في معالجة [{acc.code}]: {e}')
                error_count += 1
    
    # النتائج النهائية
    print('\n' + '=' * 80)
    print('✅ اكتملت عملية النقل!')
    print('=' * 80)
    print(f'✅ نجح: {success_count:,} حساب')
    print(f'❌ فشل: {error_count:,} حساب')
    print(f'📊 الإجمالي: {total_count:,} حساب')
    
    # التحقق النهائي
    print('\n📋 التحقق النهائي:')
    print('-' * 80)
    
    accounts_under_1121 = Account.objects.filter(parent=parent_1121, customer__isnull=False).count()
    accounts_under_1210 = Account.objects.filter(parent=parent_1210, customer__isnull=False).count()
    
    print(f'تحت [{parent_1121.code}] {parent_1121.name}: {accounts_under_1121:,} حساب')
    print(f'تحت [{parent_1210.code}] {parent_1210.name}: {accounts_under_1210:,} حساب')
    
    if accounts_under_1121 == success_count and accounts_under_1210 == 0:
        print('\n🎉 تمت العملية بنجاح! جميع حسابات العملاء الآن في المكان الصحيح')
    else:
        print('\n⚠️  تحذير: قد تكون هناك بعض المشاكل، يرجى المراجعة')
    
    print('\n⚠️  ملاحظة مهمة:')
    print('   - يجب تحديث accounting/signals.py ليستخدم الحساب 1121 بدلاً من 1210')
    print('   - يجب تحديث أي كود آخر يرجع إلى الحساب 1210 لحسابات العملاء')


if __name__ == '__main__':
    main()
