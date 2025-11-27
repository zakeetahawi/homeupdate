#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت إصلاح أصناف أوامر التقطيع - نقل الأصناف للمستودعات الصحيحة
وإنشاء أوامر تقطيع جديدة عند الحاجة
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
from django.db import transaction
from collections import defaultdict
from datetime import datetime


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


def analyze_cutting_order_items():
    """
    تحليل أصناف أوامر التقطيع - تجميع الأصناف حسب المستودع الصحيح لكل منها
    """
    issues = []
    
    for cutting_order in CuttingOrder.objects.select_related('warehouse', 'order').prefetch_related('items__order_item__product'):
        # تجميع الأصناف حسب المستودع الصحيح لكل منها
        items_by_warehouse = defaultdict(list)
        items_without_stock = []
        
        for item in cutting_order.items.all():
            if not item.order_item or not item.order_item.product:
                continue
            
            product = item.order_item.product
            current_warehouse = cutting_order.warehouse
            
            # الحصول على المستودع الصحيح للمنتج
            best_warehouse, best_stock = get_product_warehouse(product)
            current_stock = get_product_stock_in_warehouse(product, current_warehouse)
            
            # إذا كان المنتج في مستودع مختلف عن مستودع أمر التقطيع
            if best_warehouse and best_warehouse.id != current_warehouse.id:
                items_by_warehouse[best_warehouse.id].append({
                    'item': item,
                    'product': product,
                    'warehouse': best_warehouse,
                    'stock': best_stock,
                    'current_stock': current_stock,
                    'severity': 'critical' if current_stock == 0 else 'warning'
                })
            elif best_warehouse is None and current_stock == 0:
                # المنتج غير متوفر في أي مستودع
                items_without_stock.append({
                    'item': item,
                    'product': product,
                    'current_warehouse': current_warehouse
                })
        
        # إذا وُجدت أصناف تحتاج نقل
        if items_by_warehouse or items_without_stock:
            issues.append({
                'cutting_order': cutting_order,
                'cutting_code': cutting_order.cutting_code,
                'order_number': cutting_order.order.order_number if cutting_order.order else 'N/A',
                'invoice_number': cutting_order.order.invoice_number if cutting_order.order else 'N/A',
                'current_warehouse': cutting_order.warehouse,
                'items_by_warehouse': dict(items_by_warehouse),
                'items_without_stock': items_without_stock,
                'total_items': cutting_order.items.count(),
                'items_to_move': sum(len(items) for items in items_by_warehouse.values()),
            })
    
    return issues


def display_issues(issues):
    """
    عرض المشاكل المكتشفة - الأصناف التي تحتاج نقل
    """
    if not issues:
        print("\n✅ لا توجد أصناف تحتاج نقل!")
        print("جميع الأصناف في المستودعات الصحيحة.")
        return False
    
    print("\n" + "=" * 80)
    print("🔍 تقرير فحص أصناف أوامر التقطيع")
    print("=" * 80)
    
    total_items_to_move = sum(i['items_to_move'] for i in issues)
    total_without_stock = sum(len(i['items_without_stock']) for i in issues)
    
    print(f"\n📊 ملخص:")
    print(f"   - أوامر تقطيع بها أصناف تحتاج نقل: {len(issues)}")
    print(f"   - إجمالي الأصناف التي تحتاج نقل: {total_items_to_move}")
    print(f"   - أصناف بدون مخزون: {total_without_stock}")
    
    print("\n" + "-" * 80)
    print("📋 تفاصيل:")
    print("-" * 80)
    
    for idx, issue in enumerate(issues, 1):
        print(f"\n🔵 [{idx}] أمر التقطيع: {issue['cutting_code']}")
        print(f"    رقم الطلب: {issue['order_number']}")
        print(f"    رقم الفاتورة: {issue['invoice_number']}")
        print(f"    المستودع الحالي: {issue['current_warehouse'].name}")
        print(f"    إجمالي الأصناف: {issue['total_items']}")
        print(f"    أصناف تحتاج نقل: {issue['items_to_move']}")
        
        if issue['items_by_warehouse']:
            print(f"\n    📦 توزيع الأصناف حسب المستودعات:")
            for warehouse_id, items in issue['items_by_warehouse'].items():
                warehouse = items[0]['warehouse']
                critical_items = [i for i in items if i['severity'] == 'critical']
                print(f"\n       → مستودع: {warehouse.name}")
                print(f"          عدد الأصناف: {len(items)}")
                print(f"          أصناف حرجة (لا يوجد مخزون في الحالي): {len(critical_items)}")
                
                # عرض أول 3 أصناف
                for item_data in items[:3]:
                    icon = "❌" if item_data['severity'] == 'critical' else "⚠️"
                    print(f"          {icon} {item_data['product'].name}")
                    print(f"             المستودع الحالي: {item_data['current_stock']}")
                    print(f"             {warehouse.name}: {item_data['stock']}")
                
                if len(items) > 3:
                    print(f"          ... و {len(items) - 3} صنف آخر")
        
        if issue['items_without_stock']:
            print(f"\n    ⚠️  أصناف بدون مخزون في أي مستودع: {len(issue['items_without_stock'])}")
            for item_data in issue['items_without_stock'][:3]:
                print(f"       ❌ {item_data['product'].name}")
    
    return True


def generate_cutting_code(order, warehouse):
    """
    توليد كود تقطيع جديد
    """
    # الحصول على آخر رقم تسلسلي لهذا الطلب
    existing_codes = CuttingOrder.objects.filter(
        order=order
    ).values_list('cutting_code', flat=True)
    
    # استخراج الأرقام التسلسلية
    sequence_numbers = []
    for code in existing_codes:
        parts = code.split('-')
        if len(parts) >= 4:
            try:
                seq = int(parts[3])
                sequence_numbers.append(seq)
            except ValueError:
                pass
    
    # الرقم التسلسلي الجديد
    next_seq = max(sequence_numbers) + 1 if sequence_numbers else 1
    
    # توليد الكود الجديد
    return f"C-{order.id}-{order.invoice_number}-{next_seq:04d}"


@transaction.atomic
def fix_cutting_order_items(issue):
    """
    إصلاح أصناف أمر التقطيع - نقل الأصناف للمستودعات الصحيحة
    وإنشاء أوامر تقطيع جديدة عند الحاجة
    """
    cutting_order = issue['cutting_order']
    results = {
        'original_order': cutting_order.cutting_code,
        'moved_items': [],
        'new_orders_created': [],
        'moved_to_existing': [],
        'errors': []
    }
    
    # معالجة كل مستودع
    for warehouse_id, items in issue['items_by_warehouse'].items():
        warehouse = items[0]['warehouse']
        
        # البحث عن أمر تقطيع موجود لهذا المستودع والطلب
        existing_order = CuttingOrder.objects.filter(
            order=cutting_order.order,
            warehouse=warehouse
        ).exclude(id=cutting_order.id).first()
        
        if existing_order:
            # نقل الأصناف إلى أمر التقطيع الموجود
            target_order = existing_order
            action = 'moved_to_existing'
            
            # تسجيل في قائمة الأوامر الموجودة
            results['moved_to_existing'].append({
                'code': target_order.cutting_code,
                'warehouse': warehouse.name,
                'items_count': len(items)
            })
        else:
            # إنشاء أمر تقطيع جديد
            new_code = generate_cutting_code(cutting_order.order, warehouse)
            target_order = CuttingOrder.objects.create(
                cutting_code=new_code,
                order=cutting_order.order,
                warehouse=warehouse,
                status=cutting_order.status,
                notes=f"تم إنشاؤه تلقائياً من {cutting_order.cutting_code} لنقل الأصناف للمستودع الصحيح"
            )
            action = 'moved_to_new'
            
            # تسجيل في قائمة الأوامر الجديدة
            results['new_orders_created'].append({
                'code': new_code,
                'warehouse': warehouse.name,
                'items_count': len(items)
            })
        
        # نقل الأصناف
        for item_data in items:
            item = item_data['item']
            try:
                item.cutting_order = target_order
                item.save()
                
                results['moved_items'].append({
                    'product': item_data['product'].name,
                    'from_warehouse': cutting_order.warehouse.name,
                    'to_warehouse': warehouse.name,
                    'to_order': target_order.cutting_code,
                    'action': action,
                    'stock_in_target': item_data['stock']
                })
            except Exception as e:
                results['errors'].append({
                    'product': item_data['product'].name,
                    'error': str(e)
                })
    
    # التحقق من الأصناف المتبقية في الأمر الأصلي
    remaining_items = cutting_order.items.count()
    if remaining_items == 0:
        # إذا لم يتبق أي أصناف، حذف الأمر
        cutting_order.delete()
        results['original_deleted'] = True
    
    return results


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
    print("  1. إعادة فحص أصناف أوامر التقطيع")
    print("  2. إصلاح جميع الأصناف تلقائياً")
    print("  3. إصلاح أصناف أمر برقم الفاتورة")
    print("  4. إصلاح أصناف أمر بكود التقطيع")
    print("  5. الخروج")
    print("-" * 60)


def main():
    print("\n" + "=" * 80)
    print("🔧 أداة إصلاح أصناف أوامر التقطيع - نقل للمستودعات الصحيحة")
    print("=" * 80)
    
    issues = []
    
    # الفحص الأولي
    print("\n⏳ جاري تحليل أصناف أوامر التقطيع...")
    issues = analyze_cutting_order_items()
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
            print("\n⏳ جاري إعادة تحليل أصناف أوامر التقطيع...")
            issues = analyze_cutting_order_items()
            has_issues = display_issues(issues)
            
        elif choice == '2':
            # إصلاح جميع الأوامر
            if not issues:
                print("\n✅ لا توجد أصناف تحتاج إصلاح!")
                continue
            
            try:
                confirm = input("\n⚠️  هل أنت متأكد من إصلاح جميع الأصناف؟ (نعم/لا): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ تم إلغاء العملية.")
                continue
            
            if confirm in ['نعم', 'yes', 'y', 'ن']:
                print("\n⏳ جاري إصلاح الأصناف...")
                total_moved = 0
                total_new_orders = 0
                
                for issue in issues:
                    print(f"\n📌 معالجة: {issue['cutting_code']}")
                    results = fix_cutting_order_items(issue)
                    
                    if results['moved_items']:
                        print(f"  ✅ تم نقل {len(results['moved_items'])} صنف")
                        total_moved += len(results['moved_items'])
                        
                        # عرض التفاصيل
                        for item in results['moved_items'][:3]:
                            print(f"     - {item['product']}: {item['from_warehouse']} → {item['to_warehouse']}")
                        if len(results['moved_items']) > 3:
                            print(f"     ... و {len(results['moved_items']) - 3} صنف آخر")
                    
                    if results['new_orders_created']:
                        print(f"  🆕 تم إنشاء {len(results['new_orders_created'])} أمر تقطيع جديد:")
                        for order in results['new_orders_created']:
                            print(f"     - {order['code']} (مستودع: {order['warehouse']})")
                        total_new_orders += len(results['new_orders_created'])
                    
                    if results['moved_to_existing']:
                        print(f"  📦 تم نقل أصناف لـ {len(results['moved_to_existing'])} أمر موجود:")
                        for order in results['moved_to_existing']:
                            print(f"     - {order['code']} (مستودع: {order['warehouse']}, أصناف: {order['items_count']})")
                    
                    if results.get('original_deleted'):
                        print(f"  🗑️  تم حذف الأمر الأصلي (لم يتبق به أصناف)")
                    
                    if results['errors']:
                        print(f"  ❌ أخطاء: {len(results['errors'])}")
                        for error in results['errors']:
                            print(f"     - {error['product']}: {error['error']}")
                
                print(f"\n🎉 تم الإصلاح بنجاح!")
                print(f"   - إجمالي الأصناف المنقولة: {total_moved}")
                print(f"   - أوامر تقطيع جديدة: {total_new_orders}")
                
                # إعادة الفحص
                issues = analyze_cutting_order_items()
            else:
                print("❌ تم إلغاء العملية.")
                
        elif choice == '3':
            # إصلاح برقم الفاتورة
            if not issues:
                print("\n✅ لا توجد أصناف تحتاج إصلاح!")
                continue
            
            # عرض أرقام الفواتير المتاحة
            print("\n📋 أرقام الفواتير المتاحة:")
            for i in issues:
                print(f"   - {i['invoice_number']} (كود التقطيع: {i['cutting_code']}, أصناف تحتاج نقل: {i['items_to_move']})")
            
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
            print(f"   أصناف تحتاج نقل: {issue['items_to_move']}")
            
            # عرض المستودعات المستهدفة
            if issue['items_by_warehouse']:
                print(f"\n   📦 المستودعات المستهدفة:")
                for warehouse_id, items in issue['items_by_warehouse'].items():
                    warehouse = items[0]['warehouse']
                    print(f"      - {warehouse.name}: {len(items)} صنف")
            
            try:
                confirm = input("\n⚠️  هل تريد إصلاح هذا الأمر؟ (نعم/لا): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ تم إلغاء العملية.")
                continue
            
            if confirm in ['نعم', 'yes', 'y', 'ن']:
                print(f"\n⏳ جاري إصلاح {issue['cutting_code']}...")
                results = fix_cutting_order_items(issue)
                
                print(f"\n{'='*80}")
                print(f"✅ تم الإصلاح بنجاح!")
                print(f"{'='*80}")
                
                # عرض تفاصيل الأوامر الجديدة المنشأة
                if results['new_orders_created']:
                    print(f"\n🆕 أوامر تقطيع جديدة تم إنشاؤها ({len(results['new_orders_created'])}):")
                    for new_order in results['new_orders_created']:
                        print(f"   📋 {new_order['code']}")
                        print(f"      مستودع: {new_order['warehouse']}")
                        print(f"      عدد الأصناف: {new_order['items_count']}")
                
                # عرض الأصناف المنقولة لأوامر موجودة
                if results['moved_to_existing']:
                    print(f"\n📦 أصناف تم نقلها لأوامر موجودة ({len(results['moved_to_existing'])}):")
                    for existing in results['moved_to_existing']:
                        print(f"   📋 {existing['code']}")
                        print(f"      مستودع: {existing['warehouse']}")
                        print(f"      عدد الأصناف المنقولة: {existing['items_count']}")
                
                # عرض تفاصيل الأصناف المنقولة
                if results['moved_items']:
                    print(f"\n📦 تفاصيل الأصناف المنقولة ({len(results['moved_items'])}):")
                    
                    # تجميع حسب المستودع المستهدف
                    items_by_warehouse = {}
                    for item in results['moved_items']:
                        wh = item['to_warehouse']
                        if wh not in items_by_warehouse:
                            items_by_warehouse[wh] = []
                        items_by_warehouse[wh].append(item)
                    
                    for warehouse, items in items_by_warehouse.items():
                        print(f"\n   → إلى مستودع: {warehouse}")
                        for item in items[:5]:  # عرض أول 5 أصناف
                            action_icon = "🆕" if item['action'] == 'moved_to_new' else "📥"
                            print(f"      {action_icon} {item['product']}")
                            print(f"         من: {item['from_warehouse']} → إلى: {item['to_warehouse']}")
                            print(f"         أمر التقطيع: {item['to_order']}")
                            print(f"         المخزون في المستودع المستهدف: {item['stock_in_target']}")
                        
                        if len(items) > 5:
                            print(f"      ... و {len(items) - 5} صنف آخر")
                
                # عرض ملخص
                print(f"\n{'='*80}")
                print(f"📊 الملخص:")
                print(f"   - أصناف منقولة: {len(results['moved_items'])}")
                print(f"   - أوامر جديدة: {len(results['new_orders_created'])}")
                print(f"   - أوامر موجودة تم النقل إليها: {len(results['moved_to_existing'])}")
                
                if results.get('original_deleted'):
                    print(f"   - ✅ تم حذف الأمر الأصلي (لم يتبق به أصناف)")
                
                if results['errors']:
                    print(f"\n❌ أخطاء ({len(results['errors'])}):")
                    for error in results['errors']:
                        print(f"   - {error['product']}: {error['error']}")
                
                print(f"{'='*80}")
                
                # إعادة الفحص
                issues = analyze_cutting_order_items()
            else:
                print("❌ تم إلغاء العملية.")
                
        elif choice == '4':
            # إصلاح بكود التقطيع
            if not issues:
                print("\n✅ لا توجد أصناف تحتاج إصلاح!")
                continue
            
            # عرض أكواد التقطيع المتاحة
            print("\n📋 أكواد التقطيع المتاحة:")
            for i in issues:
                print(f"   - {i['cutting_code']} (فاتورة: {i['invoice_number']}, أصناف: {i['items_to_move']})")
            
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
            print(f"   أصناف تحتاج نقل: {issue['items_to_move']}")
            
            # عرض المستودعات المستهدفة
            if issue['items_by_warehouse']:
                print(f"\n   📦 المستودعات المستهدفة:")
                for warehouse_id, items in issue['items_by_warehouse'].items():
                    warehouse = items[0]['warehouse']
                    print(f"      - {warehouse.name}: {len(items)} صنف")
            
            try:
                confirm = input("\n⚠️  هل تريد إصلاح هذا الأمر؟ (نعم/لا): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n❌ تم إلغاء العملية.")
                continue
            
            if confirm in ['نعم', 'yes', 'y', 'ن']:
                print(f"\n⏳ جاري إصلاح {issue['cutting_code']}...")
                results = fix_cutting_order_items(issue)
                
                print(f"\n{'='*80}")
                print(f"✅ تم الإصلاح بنجاح!")
                print(f"{'='*80}")
                
                # عرض تفاصيل الأوامر الجديدة المنشأة
                if results['new_orders_created']:
                    print(f"\n🆕 أوامر تقطيع جديدة تم إنشاؤها ({len(results['new_orders_created'])}):")
                    for new_order in results['new_orders_created']:
                        print(f"   📋 {new_order['code']}")
                        print(f"      مستودع: {new_order['warehouse']}")
                        print(f"      عدد الأصناف: {new_order['items_count']}")
                
                # عرض الأصناف المنقولة لأوامر موجودة
                if results['moved_to_existing']:
                    print(f"\n📦 أصناف تم نقلها لأوامر موجودة ({len(results['moved_to_existing'])}):")
                    for existing in results['moved_to_existing']:
                        print(f"   📋 {existing['code']}")
                        print(f"      مستودع: {existing['warehouse']}")
                        print(f"      عدد الأصناف المنقولة: {existing['items_count']}")
                
                # عرض تفاصيل الأصناف المنقولة
                if results['moved_items']:
                    print(f"\n📦 تفاصيل الأصناف المنقولة ({len(results['moved_items'])}):")
                    
                    # تجميع حسب المستودع المستهدف
                    items_by_warehouse = {}
                    for item in results['moved_items']:
                        wh = item['to_warehouse']
                        if wh not in items_by_warehouse:
                            items_by_warehouse[wh] = []
                        items_by_warehouse[wh].append(item)
                    
                    for warehouse, items in items_by_warehouse.items():
                        print(f"\n   → إلى مستودع: {warehouse}")
                        for item in items[:5]:  # عرض أول 5 أصناف
                            action_icon = "🆕" if item['action'] == 'moved_to_new' else "📥"
                            print(f"      {action_icon} {item['product']}")
                            print(f"         من: {item['from_warehouse']} → إلى: {item['to_warehouse']}")
                            print(f"         أمر التقطيع: {item['to_order']}")
                            print(f"         المخزون في المستودع المستهدف: {item['stock_in_target']}")
                        
                        if len(items) > 5:
                            print(f"      ... و {len(items) - 5} صنف آخر")
                
                # عرض ملخص
                print(f"\n{'='*80}")
                print(f"📊 الملخص:")
                print(f"   - أصناف منقولة: {len(results['moved_items'])}")
                print(f"   - أوامر جديدة: {len(results['new_orders_created'])}")
                print(f"   - أوامر موجودة تم النقل إليها: {len(results['moved_to_existing'])}")
                
                if results.get('original_deleted'):
                    print(f"   - ✅ تم حذف الأمر الأصلي (لم يتبق به أصناف)")
                
                if results['errors']:
                    print(f"\n❌ أخطاء ({len(results['errors'])}):")
                    for error in results['errors']:
                        print(f"   - {error['product']}: {error['error']}")
                
                print(f"{'='*80}")
                
                # إعادة الفحص
                issues = analyze_cutting_order_items()
            else:
                print("❌ تم إلغاء العملية.")
                
        elif choice == '5':
            print("\n👋 شكراً لاستخدام الأداة. إلى اللقاء!")
            break
            
        else:
            print("\n❌ اختيار غير صحيح! الرجاء اختيار رقم من 1 إلى 5.")


if __name__ == '__main__':
    main()
