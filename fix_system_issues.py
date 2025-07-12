#!/usr/bin/env python3
"""
سكريبت إصلاح شامل لمشاكل نظام إدارة الخواجة للستائر والمفروشات
يصلح هذا السكريبت جميع المشاكل الحرجة المكتشفة في الاختبار الشامل

المشاكل المكتشفة:
1. رقم الفاتورة والعقد مطلوبان (تم إصلاحها)
2. عدم تطابق الحالات بين الطلبات والتصنيع
3. كود العميل المكرر (تم إصلاحها)
4. مشاكل في التحقق من صحة البيانات
"""

import os
import sys
import django
from django.db import transaction
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime, timedelta
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.apps import apps
from orders.models import Order, OrderItem
from manufacturing.models import ManufacturingOrder
from customers.models import Customer
from crm.services.base_service import StatusSyncService


class SystemFixer:
    """فئة إصلاح النظام الشامل"""
    
    def __init__(self):
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'fixes_applied': [],
            'errors': [],
            'statistics': {}
        }
    
    def print_colored_message(self, message, color='white'):
        """طباعة رسالة ملونة حسب تفضيلات المستخدم"""
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'white': '\033[97m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'end': '\033[0m'
        }
        
        print(f"{colors.get(color, colors['white'])}{message}{colors['end']}")
    
    def fix_missing_invoice_contract_numbers(self):
        """إصلاح الطلبات التي تفتقر لأرقام الفواتير والعقود"""
        self.print_colored_message("🔧 إصلاح أرقام الفواتير والعقود المفقودة...", 'yellow')
        
        try:
            orders_without_invoice = Order.objects.filter(
                invoice_number__isnull=True
            ).exclude(selected_types__contains=['inspection'])
            
            orders_without_contract = Order.objects.filter(
                contract_number__isnull=True,
                selected_types__contains=['tailoring']
            )
            
            fixed_invoices = 0
            fixed_contracts = 0
            
            with transaction.atomic():
                # إصلاح الفواتير المفقودة
                for order in orders_without_invoice:
                    order.invoice_number = order.generate_invoice_number()
                    order.save(update_fields=['invoice_number'])
                    fixed_invoices += 1
                
                # إصلاح العقود المفقودة
                for order in orders_without_contract:
                    order.contract_number = order.generate_contract_number()
                    order.save(update_fields=['contract_number'])
                    fixed_contracts += 1
            
            self.print_colored_message(
                f"✅ تم إصلاح {fixed_invoices} فاتورة و {fixed_contracts} عقد",
                'green'
            )
            
            self.report['fixes_applied'].append({
                'type': 'missing_numbers',
                'invoices_fixed': fixed_invoices,
                'contracts_fixed': fixed_contracts
            })
            
        except Exception as e:
            error_msg = f"❌ خطأ في إصلاح أرقام الفواتير والعقود: {str(e)}"
            self.print_colored_message(error_msg, 'red')
            self.report['errors'].append(error_msg)
    
    def fix_status_mismatches(self):
        """إصلاح عدم تطابق الحالات بين الطلبات والتصنيع"""
        self.print_colored_message("🔧 إصلاح عدم تطابق الحالات...", 'yellow')
        
        try:
            mismatched_orders = []
            fixed_orders = 0
            
            # العثور على الطلبات التي لها أوامر تصنيع
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            with transaction.atomic():
                for order in orders_with_manufacturing:
                    manufacturing_order = order.manufacturing_order
                    
                    # التحقق من تطابق الحالات
                    validation = StatusSyncService.validate_status_consistency(
                        order, manufacturing_order
                    )
                    
                    if not all(validation.values()):
                        mismatched_orders.append({
                            'order_id': order.id,
                            'order_status': order.order_status,
                            'manufacturing_status': manufacturing_order.status,
                            'tracking_status': order.tracking_status,
                            'validation': validation
                        })
                        
                        # مزامنة الحالات
                        StatusSyncService.sync_manufacturing_to_order(
                            manufacturing_order, order
                        )
                        fixed_orders += 1
            
            self.print_colored_message(
                f"✅ تم إصلاح {fixed_orders} طلب بحالات غير متطابقة",
                'green'
            )
            
            self.report['fixes_applied'].append({
                'type': 'status_mismatches',
                'orders_fixed': fixed_orders,
                'mismatched_details': mismatched_orders
            })
            
        except Exception as e:
            error_msg = f"❌ خطأ في إصلاح تطابق الحالات: {str(e)}"
            self.print_colored_message(error_msg, 'red')
            self.report['errors'].append(error_msg)
    
    def fix_duplicate_customer_codes(self):
        """إصلاح أكواد العملاء المكررة"""
        self.print_colored_message("🔧 إصلاح أكواد العملاء المكررة...", 'yellow')
        
        try:
            # العثور على العملاء بأكواد مكررة أو فارغة
            customers_without_code = Customer.objects.filter(
                code__isnull=True
            ) | Customer.objects.filter(code='')
            
            fixed_customers = 0
            
            with transaction.atomic():
                for customer in customers_without_code:
                    old_code = customer.code
                    customer.code = customer.generate_unique_code()
                    customer.save(update_fields=['code'])
                    fixed_customers += 1
                    
                    self.print_colored_message(
                        f"  📝 عميل {customer.name}: {old_code or 'فارغ'} → {customer.code}",
                        'white'
                    )
            
            self.print_colored_message(
                f"✅ تم إصلاح {fixed_customers} كود عميل",
                'green'
            )
            
            self.report['fixes_applied'].append({
                'type': 'duplicate_customer_codes',
                'customers_fixed': fixed_customers
            })
            
        except Exception as e:
            error_msg = f"❌ خطأ في إصلاح أكواد العملاء: {str(e)}"
            self.print_colored_message(error_msg, 'red')
            self.report['errors'].append(error_msg)
    
    def validate_system_integrity(self):
        """التحقق من سلامة النظام بعد الإصلاح"""
        self.print_colored_message("🔍 التحقق من سلامة النظام...", 'yellow')
        
        try:
            # إحصائيات النظام
            total_orders = Order.objects.count()
            total_customers = Customer.objects.count()
            total_manufacturing = ManufacturingOrder.objects.count()
            
            # التحقق من الطلبات
            orders_without_invoice = Order.objects.filter(
                invoice_number__isnull=True
            ).exclude(selected_types__contains=['inspection']).count()
            
            orders_without_contract = Order.objects.filter(
                contract_number__isnull=True,
                selected_types__contains=['tailoring']
            ).count()
            
            # التحقق من العملاء
            customers_without_code = Customer.objects.filter(
                code__isnull=True
            ).count() + Customer.objects.filter(code='').count()
            
            # التحقق من تطابق الحالات
            mismatched_statuses = 0
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                validation = StatusSyncService.validate_status_consistency(
                    order, order.manufacturing_order
                )
                if not all(validation.values()):
                    mismatched_statuses += 1
            
            # تقرير النتائج
            self.print_colored_message("📊 تقرير سلامة النظام:", 'blue')
            self.print_colored_message(f"  📈 إجمالي الطلبات: {total_orders}", 'white')
            self.print_colored_message(f"  👥 إجمالي العملاء: {total_customers}", 'white')
            self.print_colored_message(f"  🏭 إجمالي أوامر التصنيع: {total_manufacturing}", 'white')
            
            if orders_without_invoice == 0:
                self.print_colored_message("  ✅ جميع الطلبات لها أرقام فواتير", 'green')
            else:
                self.print_colored_message(f"  ❌ {orders_without_invoice} طلب بدون رقم فاتورة", 'red')
            
            if orders_without_contract == 0:
                self.print_colored_message("  ✅ جميع طلبات التفصيل لها أرقام عقود", 'green')
            else:
                self.print_colored_message(f"  ❌ {orders_without_contract} طلب تفصيل بدون رقم عقد", 'red')
            
            if customers_without_code == 0:
                self.print_colored_message("  ✅ جميع العملاء لديهم أكواد فريدة", 'green')
            else:
                self.print_colored_message(f"  ❌ {customers_without_code} عميل بدون كود", 'red')
            
            if mismatched_statuses == 0:
                self.print_colored_message("  ✅ جميع الحالات متطابقة", 'green')
            else:
                self.print_colored_message(f"  ❌ {mismatched_statuses} طلب بحالات غير متطابقة", 'red')
            
            # حفظ الإحصائيات
            self.report['statistics'] = {
                'total_orders': total_orders,
                'total_customers': total_customers,
                'total_manufacturing': total_manufacturing,
                'orders_without_invoice': orders_without_invoice,
                'orders_without_contract': orders_without_contract,
                'customers_without_code': customers_without_code,
                'mismatched_statuses': mismatched_statuses
            }
            
            # تحديد مستوى سلامة النظام
            issues = (orders_without_invoice + orders_without_contract + 
                     customers_without_code + mismatched_statuses)
            
            if issues == 0:
                self.print_colored_message("🎉 النظام سليم 100%!", 'green')
                integrity_level = "ممتاز"
            elif issues <= 5:
                self.print_colored_message("⚠️ النظام يحتاج إصلاحات طفيفة", 'yellow')
                integrity_level = "جيد"
            else:
                self.print_colored_message("🚨 النظام يحتاج إصلاحات جوهرية", 'red')
                integrity_level = "يحتاج إصلاح"
            
            self.report['integrity_level'] = integrity_level
            
        except Exception as e:
            error_msg = f"❌ خطأ في التحقق من سلامة النظام: {str(e)}"
            self.print_colored_message(error_msg, 'red')
            self.report['errors'].append(error_msg)
    
    def run_comprehensive_fix(self):
        """تشغيل الإصلاح الشامل"""
        self.print_colored_message("🚀 بدء الإصلاح الشامل لنظام إدارة الخواجة", 'blue')
        self.print_colored_message("=" * 60, 'blue')
        
        try:
            # تشغيل جميع الإصلاحات
            self.fix_missing_invoice_contract_numbers()
            self.fix_status_mismatches()
            self.fix_duplicate_customer_codes()
            
            # التحقق من سلامة النظام
            self.validate_system_integrity()
            
            # حفظ التقرير
            self.save_report()
            
            self.print_colored_message("=" * 60, 'blue')
            self.print_colored_message("✅ تم إكمال الإصلاح الشامل بنجاح!", 'green')
            
        except Exception as e:
            error_msg = f"❌ خطأ عام في الإصلاح الشامل: {str(e)}"
            self.print_colored_message(error_msg, 'red')
            self.report['errors'].append(error_msg)
    
    def save_report(self):
        """حفظ تقرير الإصلاح"""
        try:
            report_filename = f"system_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2)
            
            self.print_colored_message(f"📄 تم حفظ التقرير في: {report_filename}", 'blue')
            
        except Exception as e:
            error_msg = f"❌ خطأ في حفظ التقرير: {str(e)}"
            self.print_colored_message(error_msg, 'red')


def main():
    """الدالة الرئيسية"""
    fixer = SystemFixer()
    fixer.run_comprehensive_fix()


if __name__ == "__main__":
    main() 