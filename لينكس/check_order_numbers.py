#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت فحص صحة أرقام الطلبات
================================
يفحص جميع الطلبات للتأكد من أن رقم الطلب يتطابق مع كود العميل

الاستخدام:
    python check_order_numbers.py [--days N] [--fix] [--verbose]

الخيارات:
    --days N    عدد الأيام للفحص (افتراضي: 7)
    --fix       إصلاح الطلبات التي بها مشاكل
    --verbose   عرض تفاصيل إضافية
    --all       فحص جميع الطلبات (بدون تحديد فترة)

أمثلة:
    python check_order_numbers.py --days 7
    python check_order_numbers.py --days 30 --verbose
    python check_order_numbers.py --fix --days 7
    python check_order_numbers.py --all
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# إعداد Django
project_path = '/home/zakee/homeupdate'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# التأكد من أننا في المجلد الصحيح
os.chdir(project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

from django.utils import timezone
from orders.models import Order
from customers.models import Customer
from django.db import transaction


class Colors:
    """ألوان للطباعة في الترمينال"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title):
    """طباعة عنوان"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}{Colors.END}\n")


def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")


def check_order_number_validity(order):
    """
    فحص صحة رقم الطلب
    يجب أن يبدأ رقم الطلب بكود العميل
    """
    if not order.customer:
        return False, "الطلب بدون عميل"
    
    customer_code = order.customer.code
    if not customer_code:
        return False, "العميل بدون كود"
    
    if not order.order_number:
        return False, "الطلب بدون رقم"
    
    # التحقق من أن رقم الطلب يبدأ بكود العميل
    if not order.order_number.startswith(customer_code):
        expected_prefix = customer_code
        actual_prefix = order.order_number.rsplit('-', 1)[0] if '-' in order.order_number else order.order_number
        return False, f"رقم الطلب ({order.order_number}) لا يبدأ بكود العميل ({customer_code})"
    
    return True, "صحيح"


def get_orders_to_check(days=None, all_orders=False):
    """الحصول على الطلبات للفحص"""
    if all_orders:
        return Order.objects.all().select_related('customer')
    
    if days:
        start_date = timezone.now() - timedelta(days=days)
        return Order.objects.filter(created_at__gte=start_date).select_related('customer')
    
    return Order.objects.all().select_related('customer')


def fix_order_number(order, dry_run=False):
    """إصلاح رقم الطلب"""
    old_number = order.order_number
    new_number = order.generate_unique_order_number()
    
    if dry_run:
        return old_number, new_number, True
    
    try:
        # استخدام update مباشرة لتجنب الـ signals
        from orders.models import Order as OrderModel
        OrderModel.objects.filter(pk=order.pk).update(order_number=new_number)
        return old_number, new_number, True
    except Exception as e:
        return old_number, new_number, False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='فحص صحة أرقام الطلبات',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--days', type=int, default=7,
                       help='عدد الأيام للفحص (افتراضي: 7)')
    parser.add_argument('--fix', action='store_true',
                       help='إصلاح الطلبات التي بها مشاكل')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='عرض تفاصيل إضافية')
    parser.add_argument('--all', action='store_true',
                       help='فحص جميع الطلبات')
    parser.add_argument('--dry-run', action='store_true',
                       help='محاكاة الإصلاح بدون تطبيق التغييرات')
    
    args = parser.parse_args()
    
    print_header("فحص صحة أرقام الطلبات")
    
    # الحصول على الطلبات
    if args.all:
        print_info("فحص جميع الطلبات...")
        orders = get_orders_to_check(all_orders=True)
    else:
        print_info(f"فحص طلبات آخر {args.days} يوم...")
        orders = get_orders_to_check(days=args.days)
    
    total_orders = orders.count()
    print_info(f"إجمالي الطلبات للفحص: {total_orders}")
    
    # إحصائيات
    valid_count = 0
    invalid_count = 0
    invalid_orders = []
    
    print("\n" + "-" * 60)
    
    for order in orders:
        is_valid, message = check_order_number_validity(order)
        
        if is_valid:
            valid_count += 1
            if args.verbose:
                print_success(f"{order.order_number} - {order.customer.name}")
        else:
            invalid_count += 1
            invalid_orders.append({
                'order': order,
                'message': message
            })
            print_error(f"{order.order_number} - {order.customer.name if order.customer else 'بدون عميل'}")
            print(f"   └─ {message}")
    
    # ملخص النتائج
    print_header("ملخص النتائج")
    
    print(f"إجمالي الطلبات المفحوصة: {Colors.BOLD}{total_orders}{Colors.END}")
    print(f"طلبات صحيحة: {Colors.GREEN}{valid_count}{Colors.END}")
    print(f"طلبات بها مشاكل: {Colors.RED}{invalid_count}{Colors.END}")
    
    if invalid_count > 0:
        print_header("الطلبات التي بها مشاكل")
        
        print(f"{'رقم الطلب':<20} {'العميل':<30} {'كود العميل':<15} {'المشكلة'}")
        print("-" * 100)
        
        for item in invalid_orders:
            order = item['order']
            customer_name = order.customer.name if order.customer else 'بدون عميل'
            customer_code = order.customer.code if order.customer else '-'
            print(f"{order.order_number:<20} {customer_name:<30} {customer_code:<15} {item['message']}")
        
        # الإصلاح
        if args.fix or args.dry_run:
            print_header("إصلاح الطلبات" + (" (محاكاة)" if args.dry_run else ""))
            
            fixed_count = 0
            failed_count = 0
            
            for item in invalid_orders:
                order = item['order']
                if not order.customer:
                    print_warning(f"تخطي {order.order_number} - بدون عميل")
                    continue
                
                result = fix_order_number(order, dry_run=args.dry_run)
                
                if len(result) == 3:
                    old_num, new_num, success = result
                    if success:
                        fixed_count += 1
                        action = "سيتم تغيير" if args.dry_run else "تم تغيير"
                        print_success(f"{action}: {old_num} → {new_num}")
                else:
                    old_num, new_num, success, error = result
                    failed_count += 1
                    print_error(f"فشل إصلاح {old_num}: {error}")
            
            print()
            if args.dry_run:
                print_info(f"سيتم إصلاح {fixed_count} طلب")
                print_info("لتطبيق الإصلاحات، قم بتشغيل الأمر بدون --dry-run")
            else:
                print_success(f"تم إصلاح {fixed_count} طلب بنجاح")
                if failed_count > 0:
                    print_error(f"فشل إصلاح {failed_count} طلب")
        else:
            print()
            print_warning("لإصلاح هذه الطلبات، قم بتشغيل الأمر مع --fix")
            print_info("للمحاكاة أولاً: python check_order_numbers.py --dry-run --fix")
    else:
        print()
        print_success("🎉 جميع الطلبات صحيحة!")
    
    print()
    return 0 if invalid_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
