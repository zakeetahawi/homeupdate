#!/usr/bin/env python
"""
سكريبت لفحص وإصلاح الأرقام العربية في الطلبات وأوامر التقطيع والتصنيع
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from manufacturing.models import ManufacturingOrder
from cutting.models import CuttingOrder
from customers.models import Customer
from inspections.models import Inspection
from core.utils import convert_arabic_numbers_to_english
import re


def has_arabic_numbers(text):
    """التحقق من وجود أرقام عربية في النص"""
    if not text:
        return False
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    return any(char in arabic_digits for char in str(text))


def scan_orders():
    """فحص الطلبات"""
    issues = []
    
    fields_to_check = [
        'invoice_number', 'invoice_number_2', 'invoice_number_3',
        'contract_number', 'contract_number_2', 'contract_number_3'
    ]
    
    orders = Order.objects.all()
    
    for order in orders:
        order_issues = {}
        for field in fields_to_check:
            value = getattr(order, field)
            if has_arabic_numbers(value):
                converted = convert_arabic_numbers_to_english(value)
                order_issues[field] = {
                    'old': value,
                    'new': converted
                }
        
        if order_issues:
            issues.append({
                'type': 'Order',
                'id': order.id,
                'number': order.order_number,
                'fields': order_issues
            })
    
    return issues


def scan_manufacturing_orders():
    """فحص أوامر التصنيع"""
    issues = []
    
    fields_to_check = [
        'contract_number', 'invoice_number',
        'exit_permit_number', 'delivery_permit_number'
    ]
    
    manufacturing_orders = ManufacturingOrder.objects.all()
    
    for mo in manufacturing_orders:
        mo_issues = {}
        for field in fields_to_check:
            value = getattr(mo, field)
            if has_arabic_numbers(value):
                converted = convert_arabic_numbers_to_english(value)
                mo_issues[field] = {
                    'old': value,
                    'new': converted
                }
        
        if mo_issues:
            issues.append({
                'type': 'ManufacturingOrder',
                'id': mo.id,
                'number': mo.manufacturing_code,
                'fields': mo_issues
            })
    
    return issues


def scan_cutting_orders():
    """فحص أوامر التقطيع"""
    # أوامر التقطيع لا تحتوي على حقول contract_number و invoice_number
    # هذه الحقول موجودة في Order المرتبط بها
    # لذلك لا نحتاج لفحصها هنا
    return []


def scan_customers():
    """فحص العملاء"""
    issues = []
    
    fields_to_check = ['phone', 'phone2']
    
    customers = Customer.objects.all()
    
    for customer in customers:
        customer_issues = {}
        for field in fields_to_check:
            value = getattr(customer, field, None)
            if has_arabic_numbers(value):
                converted = convert_arabic_numbers_to_english(value)
                customer_issues[field] = {
                    'old': value,
                    'new': converted
                }
        
        if customer_issues:
            issues.append({
                'type': 'Customer',
                'id': customer.id,
                'number': f"{customer.code} - {customer.name}",
                'fields': customer_issues
            })
    
    return issues


def scan_inspections():
    """فحص المعاينات"""
    issues = []
    
    fields_to_check = ['contract_number']
    
    inspections = Inspection.objects.all()
    
    for inspection in inspections:
        inspection_issues = {}
        for field in fields_to_check:
            value = getattr(inspection, field)
            if has_arabic_numbers(value):
                converted = convert_arabic_numbers_to_english(value)
                inspection_issues[field] = {
                    'old': value,
                    'new': converted
                }
        
        if inspection_issues:
            issues.append({
                'type': 'Inspection',
                'id': inspection.id,
                'number': inspection.inspection_code,
                'fields': inspection_issues
            })
    
    return issues


def display_issues(all_issues):
    """عرض المشاكل المكتشفة"""
    print("\n" + "="*80)
    print("🔍 نتائج الفحص - الأرقام العربية المكتشفة")
    print("="*80 + "\n")
    
    total_count = sum(len(issues) for issues in all_issues.values())
    
    if total_count == 0:
        print("✅ لم يتم العثور على أرقام عربية - جميع البيانات صحيحة!")
        return False
    
    for category, issues in all_issues.items():
        if not issues:
            continue
            
        print(f"\n📋 {category} ({len(issues)} سجل)")
        print("-" * 80)
        
        for issue in issues[:10]:  # عرض أول 10 فقط
            print(f"\n  🔹 {issue['type']} #{issue['number']}")
            for field, changes in issue['fields'].items():
                print(f"     {field}:")
                print(f"       قديم: {changes['old']}")
                print(f"       جديد: {changes['new']}")
        
        if len(issues) > 10:
            print(f"\n     ... و {len(issues) - 10} سجل آخر")
    
    print("\n" + "="*80)
    print(f"📊 إجمالي السجلات المتأثرة: {total_count}")
    print("="*80 + "\n")
    
    return True


def apply_fixes(all_issues):
    """تطبيق الإصلاحات"""
    print("\n🔧 بدء تطبيق الإصلاحات...\n")
    
    fixed_count = 0
    
    # إصلاح الطلبات
    for issue in all_issues.get('الطلبات (Orders)', []):
        try:
            order = Order.objects.get(id=issue['id'])
            for field, changes in issue['fields'].items():
                setattr(order, field, changes['new'])
            order.save()
            fixed_count += 1
            print(f"  ✅ تم إصلاح الطلب {issue['number']}")
        except Exception as e:
            print(f"  ❌ خطأ في إصلاح الطلب {issue['number']}: {e}")
    
    # إصلاح أوامر التصنيع
    for issue in all_issues.get('أوامر التصنيع (Manufacturing)', []):
        try:
            mo = ManufacturingOrder.objects.get(id=issue['id'])
            for field, changes in issue['fields'].items():
                setattr(mo, field, changes['new'])
            mo.save()
            fixed_count += 1
            print(f"  ✅ تم إصلاح أمر التصنيع {issue['number']}")
        except Exception as e:
            print(f"  ❌ خطأ في إصلاح أمر التصنيع {issue['number']}: {e}")
    
    # أوامر التقطيع لا تحتاج إصلاح (لا توجد بها حقول مباشرة)
    
    # إصلاح العملاء
    for issue in all_issues.get('العملاء (Customers)', []):
        try:
            customer = Customer.objects.get(id=issue['id'])
            for field, changes in issue['fields'].items():
                setattr(customer, field, changes['new'])
            customer.save()
            fixed_count += 1
            print(f"  ✅ تم إصلاح العميل {issue['number']}")
        except Exception as e:
            print(f"  ❌ خطأ في إصلاح العميل {issue['number']}: {e}")
    
    # إصلاح المعاينات
    for issue in all_issues.get('المعاينات (Inspections)', []):
        try:
            inspection = Inspection.objects.get(id=issue['id'])
            for field, changes in issue['fields'].items():
                setattr(inspection, field, changes['new'])
            inspection.save()
            fixed_count += 1
            print(f"  ✅ تم إصلاح المعاينة {issue['number']}")
        except Exception as e:
            print(f"  ❌ خطأ في إصلاح المعاينة {issue['number']}: {e}")
    
    print(f"\n✅ تم إصلاح {fixed_count} سجل بنجاح!")


def main():
    """الدالة الرئيسية"""
    print("\n🚀 بدء فحص الأرقام العربية في قاعدة البيانات...\n")
    
    # فحص جميع الجداول
    print("⏳ جاري الفحص...")
    
    all_issues = {
        'الطلبات (Orders)': scan_orders(),
        'أوامر التصنيع (Manufacturing)': scan_manufacturing_orders(),
        'أوامر التقطيع (Cutting)': scan_cutting_orders(),
        'العملاء (Customers)': scan_customers(),
        'المعاينات (Inspections)': scan_inspections(),
    }
    
    # عرض النتائج
    has_issues = display_issues(all_issues)
    
    if not has_issues:
        return
    
    # طلب التأكيد
    print("\n⚠️  هل تريد تطبيق الإصلاحات؟")
    print("   سيتم تحويل جميع الأرقام العربية إلى أرقام إنجليزية")
    
    confirmation = input("\n   اكتب 'نعم' أو 'yes' للمتابعة: ").strip().lower()
    
    if confirmation in ['نعم', 'yes', 'y']:
        apply_fixes(all_issues)
        print("\n✅ تم إكمال الإصلاحات بنجاح!")
    else:
        print("\n❌ تم إلغاء العملية")


if __name__ == '__main__':
    main()
