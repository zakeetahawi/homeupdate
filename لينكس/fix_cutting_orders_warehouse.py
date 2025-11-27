#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت إصلاح أوامر التقطيع الموجهة لمستودعات خاطئة
سكريبت تفاعلي - يبقى يعمل حتى تختار الخروج
"""

import os
import sys

# إعداد المسارات
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

from inventory.models import Warehouse, Product, StockTransaction
from cutting.models import CuttingOrder, CuttingOrderItem
from orders.models import Order
from django.db.models import Q
from collections import defaultdict


def get_product_warehouse(product):
    """
    الحصول على المستودع الذي يتوفر فيه المنتج بأكبر كمية
    """
    best_warehouse = None
    best_stock = 0
    
    for warehouse in Warehouse.objects.filter(is_active=True):
        last_trans = StockTransaction.objects.filter(
            product=product,
            warehouse=warehouse
        ).order_by('-transaction_date', '-id').first()
        
        if last_trans and last_trans.running_balance > best_stock:
            best_stock = last_trans.running_balance
            best_warehouse = warehouse
    
    return best_warehouse, best_stock


def get_product_stock_in_warehouse(product, warehouse):
    """
    الحصول على رصيد منتج في مستودع معين
    """
    last_trans = StockTransaction.objects.filter(
        product=product,
        warehouse=warehouse
    ).order_by('-transaction_date', '-id').first()
    
    return last_trans.running_balance if last_trans else 0


def analyze_cutting_orders():
    """
    تحليل أوامر التقطيع وإيجاد الأوامر الموجهة لمستودعات خاطئة
    """
    issues = []
    
    for cutting_order in CuttingOrder.objects.select_related('warehouse', 'order').prefetch_related('items__order_item__product'):
        order_issues = []
        suggested_warehouse = None
        warehouse_votes = defaultdict(int)
        
        for item in cutting_order.items.all():
            if not item.order_item or not item.order_item.product:
                continue
            
            product = item.order_item.product
            current_warehouse = cutting_order.warehouse
            
            # التحقق من توفر المنتج في المستودع الحالي
            current_stock = get_product_stock_in_warehouse(product, current_warehouse)
            
            # الحصول على أفضل مستودع للمنتج
            best_warehouse, best_stock = get_product_warehouse(product)
            
            if best_warehouse and best_warehouse != current_warehouse:
                if current_stock == 0 and best_stock > 0:
                    order_issues.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'current_warehouse': current_warehouse.name,
                        'current_stock': current_stock,
                        'suggested_warehouse': best_warehouse.name,
                        'suggested_warehouse_id': best_warehouse.id,
                        'suggested_stock': best_stock,
                        'severity': 'critical'
                    })
                    warehouse_votes[best_warehouse.id] += 2
                elif current_stock < best_stock:
                    order_issues.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'current_warehouse': current_warehouse.name,
                        'current_stock': current_stock,
                        'suggested_warehouse': best_warehouse.name,
                        'suggested_warehouse_id': best_warehouse.id,
                        'suggested_stock': best_stock,
                        'severity': 'warning'
                    })
                    warehouse_votes[best_warehouse.id] += 1
        
        if order_issues:
            if warehouse_votes:
                suggested_warehouse_id = max(warehouse_votes, key=warehouse_votes.get)
                suggested_warehouse = Warehouse.objects.get(id=suggested_warehouse_id)
            
            issues.append({
                'cutting_order': cutting_order,
                'cutting_code': cutting_order.cutting_code,
                'order_number': cutting_order.order.order_number if cutting_order.order else 'N/A',
                'invoice_number': cutting_order.order.invoice_number if cutting_order.order else 'N/A',
                'current_warehouse': cutting_order.warehouse,
                'suggested_warehouse': suggested_warehouse,
                'items_issues': order_issues,
                'critical_count': sum(1 for i in order_issues if i['severity'] == 'critical'),
                'warning_count': sum(1 for i in order_issues if i['severity'] == 'warning'),
            })
    
    return issues


def display_issues(issues):
    """
    عرض المشاكل المكتشفة
    """
    if not issues:
        print("\n✅ لا توجد مشاكل في أوامر التقطيع!")
        print("جميع أوامر التقطيع موجهة للمستودعات الصحيحة.")
        return False
    
    print("\n" + "=" * 80)
    print("🔍 تقرير فحص أوامر التقطيع")
    print("=" * 80)
    
    critical_orders = [i for i in issues if i['critical_count'] > 0]
    warning_orders = [i for i in issues if i['critical_count'] == 0]
    
    print(f"\n📊 ملخص:")
    print(f"   - إجمالي أوامر التقطيع بمشاكل: {len(issues)}")
    print(f"   - أوامر حرجة (منتجات غير متوفرة): {len(critical_orders)}")
    print(f"   - أوامر تحذيرية (كميات أقل): {len(warning_orders)}")
    
    print("\n" + "-" * 80)
    print("📋 تفاصيل الأوامر:")
    print("-" * 80)
    
    for idx, issue in enumerate(issues, 1):
        severity_icon = "🔴" if issue['critical_count'] > 0 else "🟡"
        print(f"\n{severity_icon} [{idx}] أمر التقطيع: {issue['cutting_code']}")
        print(f"    رقم الطلب: {issue['order_number']}")
        print(f"    رقم الفاتورة: {issue['invoice_number']}")
        print(f"    المستودع الحالي: {issue['current_warehouse'].name}")
        print(f"    المستودع المقترح: {issue['suggested_warehouse'].name if issue['suggested_warehouse'] else 'غير محدد'}")
        print(f"    مشاكل حرجة: {issue['critical_count']} | تحذيرات: {issue['warning_count']}")
        
        print(f"    المنتجات:")
        for item_issue in issue['items_issues'][:5]:
            icon = "❌" if item_issue['severity'] == 'critical' else "⚠️"
            print(f"      {icon} {item_issue['product_name']}")
            print(f"         الحالي ({item_issue['current_warehouse']}): {item_issue['current_stock']}")
            print(f"         المقترح ({item_issue['suggested_warehouse']}): {item_issue['suggested_stock']}")
        
        if len(issue['items_issues']) > 5:
            print(f"      ... و {len(issue['items_issues']) - 5} منتجات أخرى")
    
    return True


def fix_cutting_order(cutting_order, new_warehouse):
    """
    إصلاح أمر تقطيع بتغيير المستودع
    """
    old_warehouse = cutting_order.warehouse
    cutting_order.warehouse = new_warehouse
    cutting_order.save()
    
    return {
        'cutting_code': cutting_order.cutting_code,
        'old_warehouse': old_warehouse.name,
        'new_warehouse': new_warehouse.name
    }


def find_issue_by_invoice(issues, invoice_number):
    """
    البحث عن مشكلة برقم الفاتورة
    """
    for issue in issues:
        if issue['invoice_number'] and str(issue['invoice_number']).strip() == str(invoice_number).strip():
            return issue
    return None


def find_issue_by_cutting_code(issues, cutting_code):
    """
    البحث عن مشكلة بكود التقطيع
    """
    for issue in issues:
        if issue['cutting_code'] and str(issue['cutting_code']).strip() == str(cutting_code).strip():
            return issue
    return None


def show_menu():
    """
    عرض قائمة الخيارات
    """
    print("\n" + "=" * 60)
    print("🛠️  خيارات الإصلاح:")
    print("=" * 60)
    print("  1. إعادة فحص أوامر التقطيع")
    print("  2. إصلاح جميع الأوامر تلقائياً")
    print("  3. إصلاح أمر برقم الفاتورة")
    print("  4. إصلاح أمر بكود التقطيع")
    print("  5. الخروج")
    print("-" * 60)


def main():
    print("\n" + "=" * 80)
    print("🔧 أداة إصلاح أوامر التقطيع الموجهة لمستودعات خاطئة")
    print("=" * 80)
    
    issues = []
    
    # الفحص الأولي
    print("\n⏳ جاري تحليل أوامر التقطيع...")
    issues = analyze_cutting_orders()
    has_issues = display_issues(issues)
    
    # الحلقة التفاعلية الرئيسية
    while True:
        show_menu()
        
        try:
            choice = input("\n👉 اختيارك (1-5): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 تم الخروج.")
            break
        
        if choice == '1':
            # إعادة الفحص
            print("\n⏳ جاري إعادة تحليل أوامر التقطيع...")
            issues = analyze_cutting_orders()
            has_issues = display_issues(issues)
            
        elif choice == '2':
            # إصلاح جميع الأوامر
            if not issues:
                print("\n✅ لا توجد مشاكل تحتاج إصلاح!")
                continue
            
            try:
                confirm = input("\n⚠️  هل أنت متأكد من إصلاح جميع الأوامر؟ (نعم/لا): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ تم إلغاء العملية.")
                continue
            
            if confirm in ['نعم', 'yes', 'y', 'ن']:
                print("\n⏳ جاري إصلاح الأوامر...")
                fixed_count = 0
                for issue in issues:
                    if issue['suggested_warehouse']:
                        result = fix_cutting_order(issue['cutting_order'], issue['suggested_warehouse'])
                        print(f"  ✅ {result['cutting_code']}: {result['old_warehouse']} → {result['new_warehouse']}")
                        fixed_count += 1
                print(f"\n🎉 تم إصلاح {fixed_count} أمر تقطيع بنجاح!")
                # إعادة الفحص
                issues = analyze_cutting_orders()
            else:
                print("❌ تم إلغاء العملية.")
                
        elif choice == '3':
            # إصلاح برقم الفاتورة
            if not issues:
                print("\n✅ لا توجد مشاكل تحتاج إصلاح!")
                continue
            
            # عرض أرقام الفواتير المتاحة
            print("\n📋 أرقام الفواتير المتاحة:")
            for i in issues:
                print(f"   - {i['invoice_number']} (كود التقطيع: {i['cutting_code']})")
            
            try:
                invoice_number = input("\n📝 أدخل رقم الفاتورة: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ تم إلغاء العملية.")
                continue
            
            if not invoice_number:
                print("❌ رقم الفاتورة فارغ!")
                continue
            
            issue = find_issue_by_invoice(issues, invoice_number)
            if not issue:
                print(f"\n❌ لم يتم العثور على أمر تقطيع برقم فاتورة: {invoice_number}")
                continue
            
            print(f"\n📌 تم العثور على الأمر:")
            print(f"   كود التقطيع: {issue['cutting_code']}")
            print(f"   المستودع الحالي: {issue['current_warehouse'].name}")
            print(f"   المستودع المقترح: {issue['suggested_warehouse'].name if issue['suggested_warehouse'] else 'غير محدد'}")
            
            if issue['suggested_warehouse']:
                try:
                    confirm = input("\n⚠️  هل تريد إصلاح هذا الأمر؟ (نعم/لا): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n❌ تم إلغاء العملية.")
                    continue
                
                if confirm in ['نعم', 'yes', 'y', 'ن']:
                    result = fix_cutting_order(issue['cutting_order'], issue['suggested_warehouse'])
                    print(f"\n✅ تم الإصلاح: {result['cutting_code']}: {result['old_warehouse']} → {result['new_warehouse']}")
                    # إعادة الفحص
                    issues = analyze_cutting_orders()
                else:
                    print("❌ تم إلغاء العملية.")
            else:
                print("❌ لا يوجد مستودع مقترح لهذا الأمر.")
                
        elif choice == '4':
            # إصلاح بكود التقطيع
            if not issues:
                print("\n✅ لا توجد مشاكل تحتاج إصلاح!")
                continue
            
            # عرض أكواد التقطيع المتاحة
            print("\n📋 أكواد التقطيع المتاحة:")
            for i in issues:
                print(f"   - {i['cutting_code']} (رقم الفاتورة: {i['invoice_number']})")
            
            try:
                cutting_code = input("\n📝 أدخل كود التقطيع: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ تم إلغاء العملية.")
                continue
            
            if not cutting_code:
                print("❌ كود التقطيع فارغ!")
                continue
            
            issue = find_issue_by_cutting_code(issues, cutting_code)
            if not issue:
                print(f"\n❌ لم يتم العثور على أمر تقطيع بكود: {cutting_code}")
                continue
            
            print(f"\n📌 تم العثور على الأمر:")
            print(f"   رقم الفاتورة: {issue['invoice_number']}")
            print(f"   المستودع الحالي: {issue['current_warehouse'].name}")
            print(f"   المستودع المقترح: {issue['suggested_warehouse'].name if issue['suggested_warehouse'] else 'غير محدد'}")
            
            if issue['suggested_warehouse']:
                try:
                    confirm = input("\n⚠️  هل تريد إصلاح هذا الأمر؟ (نعم/لا): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n❌ تم إلغاء العملية.")
                    continue
                
                if confirm in ['نعم', 'yes', 'y', 'ن']:
                    result = fix_cutting_order(issue['cutting_order'], issue['suggested_warehouse'])
                    print(f"\n✅ تم الإصلاح: {result['cutting_code']}: {result['old_warehouse']} → {result['new_warehouse']}")
                    # إعادة الفحص
                    issues = analyze_cutting_orders()
                else:
                    print("❌ تم إلغاء العملية.")
            else:
                print("❌ لا يوجد مستودع مقترح لهذا الأمر.")
                
        elif choice == '5':
            print("\n👋 شكراً لاستخدام الأداة. إلى اللقاء!")
            break
            
        else:
            print("\n❌ اختيار غير صحيح! الرجاء اختيار رقم من 1 إلى 5.")


if __name__ == '__main__':
    main()
