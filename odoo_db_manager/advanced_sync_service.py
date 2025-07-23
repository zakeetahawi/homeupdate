"""
خدمة المزامنة المتقدمة مع Google Sheets - محدثة حسب المتطلبات الجديدة
Advanced Google Sheets Sync Service - Updated
"""

import logging
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.conf import settings

from .google_sync_advanced import (
    GoogleSheetMapping, GoogleSyncTask, GoogleSyncConflict, GoogleSyncSchedule
)
from .google_sheets_import import GoogleSheetsImporter
from customers.models import Customer, CustomerCategory
from orders.models import Order
# from orders.extended_models import ExtendedOrder  # TODO: إعادة التنفيذ باستخدام ManufacturingOrder
from inspections.models import Inspection
# Removed installations app import - will be reimplemented with new models
from accounts.models import Branch, Salesperson

logger = logging.getLogger(__name__)


class AdvancedSyncService:
    def _create_manufacturing_order(self, mapped_data: Dict[str, str], order: Order):
        """إنشاء أمر تصنيع للطلب الأساسي مع تعيين التاريخ من الطلب"""
        try:
            from manufacturing.models import ManufacturingOrder
            from datetime import timedelta
            
            # التحقق من عدم وجود أمر تصنيع مسبق للطلب
            existing_order = ManufacturingOrder.objects.filter(order=order).first()
            if existing_order:
                return existing_order
            
            # تحديد نوع أمر التصنيع حس�� نوع الطلب
            order_types = order.selected_types or []
            manufacturing_type = 'custom'  # افتراضي
            
            if 'installation' in order_types:
                manufacturing_type = 'installation'
            elif 'accessory' in order_types:
                manufacturing_type = 'accessory'
            elif 'tailoring' in order_types:
                manufacturing_type = 'custom'
            
            # بيانات أمر التصنيع
            manufacturing_data = {
                'order': order,
                'order_type': manufacturing_type,
                'status': 'pending_approval',
                'order_date': order.order_date or timezone.now().date(),
                'expected_delivery_date': (order.order_date or timezone.now().date()) + timedelta(days=14),
                'contract_number': order.contract_number or '',
                'invoice_number': order.invoice_number or '',
                'notes': mapped_data.get('order_notes', '') or order.notes or '',
            }
            
            # إنشاء أمر التصنيع
            manufacturing_order = ManufacturingOrder.objects.create(**manufacturing_data)
            
            return manufacturing_order
            
        except Exception as e:
            raise Exception(f"فشل إنشاء أمر التصنيع: {str(e)}")
    def _map_order_type(self, order_type_value: str) -> str:
        """
        تحويل نوع الطلب من العربية إلى القيم البرمجية المعتمدة في النظام.
        يدعم فقط: تركيب، اكسسوار، تفصيل، تسليم
        ملاحظة: المعاينات يتم إنشاؤها منفصلة حسب تاريخ المعاينة
        """
        mapping = {
            'تركيب': 'installation',
            'installation': 'installation',
            'اكسسوار': 'accessory',
            'إكسسوار': 'accessory',
            'accessory': 'accessory',
            'تفصيل': 'tailoring',
            'tailoring': 'tailoring',
            'تسليم': 'tailoring',  # حسب طلبك: تسليم = تفصيل
            'توصيل': 'tailoring',
        }
        return mapping.get(order_type_value.strip().lower().replace('إ','ا'), None)
    def _create_inspection(self, mapped_data: Dict[str, str], order: Order) -> Inspection:
        """إنشاء معاينة مرتبطة بالطلب مع تعيين التاريخ من الجدول أو من الطلب إذا لم يوجد"""
        from inspections.models import Inspection
        from datetime import timedelta
        from django.utils import timezone

        # التحقق من وجود معاينة مرتبطة بنفس الطلب
        existing_inspection = Inspection.objects.filter(order=order).first()
        if existing_inspection:
            logger.info(f"معاينة موجودة مسبقاً للطلب {order.order_number}: {existing_inspection.id}")
            return existing_inspection

        inspection_data = {
            'order': order,
            'customer': order.customer,
            'branch': order.branch,
        }

        # معالجة تاريخ المعاينة: من الجدول أو من الطلب
        inspection_date = mapped_data.get('inspection_date', '').strip()
        if not inspection_date:
            # إذا لم يوجد تاريخ معاينة، استخدم تاريخ الطلب
            if hasattr(order, 'order_date') and order.order_date:
                inspection_date = str(order.order_date)
        parsed_date = self._parse_date(inspection_date)
        if parsed_date:
            inspection_data['scheduled_date'] = parsed_date
            inspection_data['request_date'] = parsed_date - timedelta(days=1)
        else:
            raise Exception("لن يتم إنشاء معاينة: لا يوجد تاريخ معاينة صالح.")

        if mapped_data.get('inspection_notes'):
            inspection_data['notes'] = mapped_data['inspection_notes']

        try:
            inspection = Inspection.objects.create(**inspection_data)
            self.stats['inspections_created'] += 1
            logger.info(f"تم إنشاء معاينة جديدة للطلب {order.order_number}: {inspection.id}")
            return inspection
        except Exception as e:
            import traceback
            logger.error(f"[CREATE_INSPECTION] خطأ: {str(e)}")
            logger.error(f"[CREATE_INSPECTION] بيانات المعاينة: {inspection_data}")
            print(traceback.format_exc())
            raise Exception(f"فشل إنشاء معاينة جديدة: {str(e)}")
    """خدمة المزامنة المتقدمة - محدثة"""

    def __init__(self, mapping: GoogleSheetMapping):
        self.mapping = mapping
        self.importer = GoogleSheetsImporter()
        self.conflicts = []
        self.stats = {
            'total_rows': 0,
            'processed_rows': 0,
            'successful_rows': 0,
            'failed_rows': 0,
            'customers_created': 0,
            'customers_updated': 0,
            'customers_skipped': 0,
            'orders_created': 0,
            'orders_updated': 0,
            'orders_skipped': 0,
            'inspections_created': 0,
            'inspections_skipped': 0,
            'manufacturing_orders_created': 0,
            'manufacturing_orders_failed': 0,
            'errors': [],
            'warnings': [],
            'detailed_errors': []
        }

    def sync_from_sheets(self, task: GoogleSyncTask = None, use_fast_mode: bool = True) -> Dict[str, Any]:
        """مزامنة البيانات من Google Sheets - مع خيار المزامنة السريعة"""
        
        # استخدام المزامنة السريعة افتراضياً
        if use_fast_mode:
            from .fast_sync_service import FastSyncService
            fast_service = FastSyncService(self.mapping)
            return fast_service.sync_from_sheets(task)
        
        # المزامنة التفصيلية (البطيئة)
        try:
            self.importer.initialize()
            if not task:
                task = GoogleSyncTask.objects.create(
                    mapping=self.mapping,
                    task_type='import',
                    created_by=None
                )
            
            # بدء المهمة
            task.status = 'running'
            task.started_at = timezone.now()
            task.save()

            # جلب البيانات من Google Sheets
            sheet_data = self._get_sheet_data()
            if not sheet_data:
                raise Exception("لا توجد بيانات في الجدول")

            # تحديث إحصائيات المهمة
            task.rows_processed = len(sheet_data)
            task.save()

            # معالجة البيانات
            self._process_sheet_data(sheet_data, task)

            # إكمال المهمة
            task.status = 'completed'
            task.completed_at = timezone.now()
            task.result = json.dumps(self.stats, ensure_ascii=False)
            task.rows_successful = self.stats['successful_rows']
            task.rows_failed = self.stats['failed_rows']
            task.save()

            # تحديث التعيين
            self.mapping.last_sync = timezone.now()
            self.mapping.last_row_processed = self.stats['processed_rows'] + self.mapping.start_row - 1
            self.mapping.save(update_fields=['last_sync', 'last_row_processed'])

            return {
                'success': True,
                'stats': self.stats,
                'task_id': task.id
            }

        except Exception as e:
            logger.error(f"خطأ في المزامنة: {str(e)}")
            if task:
                task.status = 'failed'
                task.error_log = str(e)
                task.save()
            return {'success': False, 'error': str(e)}

    def _process_sheet_data(self, sheet_data: List[List[str]], task: GoogleSyncTask):
        """
        تسلسل المزامنة المحدث:
        1. إضافة العملاء
        2. إضافة الطلب الأساسي (تركيب/تسليم/اكسسوار)
        3. إضافة طلب معاينة منفصل إذا وُجد تاريخ معاينة
        4. إنشاء المعاينة مرتبطة بطلب المعاينة
        5. إنشاء أمر تصنيع للطلب الأساسي
        """
        if not sheet_data or len(sheet_data) < 2:
            logger.warning("لا توجد بيانات كافية في Google Sheets.")
            print("[SYNC] لا توجد بيانات كافية في Google Sheets.")
            return

        headers = sheet_data[0]
        total_rows = len(sheet_data) - 1
        self.stats['total_rows'] = total_rows
        
        print(f"[SYNC] بدء معالجة {total_rows} صف...")
        
        # معالجة البيانات بالدفعات لتحسين الأداء
        batch_size = 50
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_rows = sheet_data[1 + batch_start:1 + batch_end]
            
            print(f"[SYNC] معالجة الدفعة: الصفوف {batch_start + 2} إلى {batch_end + 1}")
            
            # معالجة الدفعة داخل معاملة واحدة
            with transaction.atomic():
                for i, row in enumerate(batch_rows):
                    row_index = batch_start + i + 2
                    try:
                        mapped_data = self._map_row_data(headers, row)
                        customer_name = mapped_data.get('customer_name', '').strip()
                        raw_order_type = mapped_data.get('order_type', '').strip()
                        inspection_date = mapped_data.get('inspection_date', '').strip()
                        
                        # تسجيل تفاصيل الصف
                        row_details = {
                            'row': row_index,
                            'customer_name': customer_name,
                            'order_type': raw_order_type,
                            'inspection_date': inspection_date,
                            'actions': []
                        }
                        
                        # معالجة العميل
                        customer = self._process_customer(mapped_data, row_index, task)
                        if not customer:
                            self.stats['customers_skipped'] += 1
                            row_details['actions'].append(f"❌ تخطي: لا يوجد اسم عميل صالح")
                            self.stats['detailed_errors'].append(row_details)
                            continue

                        row_details['customer_id'] = customer.id
                        row_details['actions'].append(f"✅ عميل: {customer.name}")

                        # تحديد نوع الطلب الأساسي
                        order_type = self._map_order_type(raw_order_type)
                        
                        # التحقق من صحة تاريخ المعاينة
                        has_valid_inspection_date = self._is_valid_inspection_date(inspection_date)

                        # تحديد معرف فريد للطلب بناءً على العميل ونوع الطلب ورقم العقد/الفاتورة
                        contract_number = mapped_data.get('contract_number', '').strip()
                        invoice_number = mapped_data.get('invoice_number', '').strip()
                        
                        # إنشاء الطلب الأساسي (تركيب/تسليم/اكسسوار) فقط
                        main_order = None
                        if order_type and order_type in ['installation', 'accessory', 'tailoring']:
                            # التحقق من وجود طلب مماثل للعميل بنفس النوع
                            existing_main_order = self._find_existing_order(customer, order_type, contract_number, invoice_number)
                            
                            if existing_main_order:
                                main_order = existing_main_order
                                row_details['actions'].append(f"🔄 طلب موجود {order_type}: {main_order.order_number}")
                                
                                # تحديث الطلب الموجود إذا لزم الأمر
                                if self.mapping.update_existing:
                                    updated = self._update_order(main_order, mapped_data, customer)
                                    if updated:
                                        self.stats['orders_updated'] += 1
                                        row_details['actions'].append(f"✅ تم تحديث الطلب: {main_order.order_number}")
                            else:
                                main_order = self._create_order(mapped_data, customer, order_type)
                                row_details['actions'].append(f"✅ طلب جديد {order_type}: {main_order.order_number}")
                            
                            # إنشاء أمر تصنيع للطلب الأساسي (إذا لم يكن موجوداً)
                            try:
                                manufacturing_order = self._create_manufacturing_order(mapped_data, main_order)
                                if manufacturing_order:
                                    self.stats['manufacturing_orders_created'] += 1
                                    row_details['actions'].append(f"✅ أمر تصنيع للطلب: {main_order.order_number}")
                            except Exception as e:
                                self.stats['manufacturing_orders_failed'] += 1
                                row_details['actions'].append(f"❌ فشل أمر التصنيع: {str(e)}")
                        else:
                            self.stats['orders_skipped'] += 1
                            if not order_type:
                                row_details['actions'].append(f"❌ نوع طلب غير معروف: '{raw_order_type}'")
                            else:
                                row_details['actions'].append(f"❌ نوع طلب غير مدعوم: '{order_type}'")

                        # إنشاء طلب معاينة منفصل فقط إذا كان تاريخ المعاينة صالحاً
                        if has_valid_inspection_date:
                            parsed_inspection_date = self._parse_date(inspection_date)
                            if parsed_inspection_date:
                                # البحث عن طلب معاينة موجود أو إنشاء جديد
                                inspection_order = self._find_or_create_inspection_order(
                                    mapped_data, customer, inspection_date, contract_number, invoice_number
                                )
                                
                                if inspection_order:
                                    # التحقق من وجود معاينة مرتبطة بهذا الطلب
                                    existing_inspection = Inspection.objects.filter(order=inspection_order).first()
                                    
                                    if not existing_inspection:
                                        row_details['actions'].append(f"✅ طلب معاينة: {inspection_order.order_number}")
                                        
                                        # إنشاء المعاينة مرتبطة بطلب المعاينة
                                        try:
                                            inspection = self._create_inspection(mapped_data, inspection_order)
                                            row_details['actions'].append(f"✅ معاينة جديدة: {parsed_inspection_date.date()}")
                                        except Exception as e:
                                            row_details['actions'].append(f"❌ فشل إنشاء المعاينة: {str(e)}")
                                    else:
                                        row_details['actions'].append(f"🔄 طلب معاينة موجود: {inspection_order.order_number}")
                                        row_details['actions'].append(f"⚠️ معاينة موجودة مسبقاً للطلب: {existing_inspection.id}")
                        else:
                            if inspection_date:
                                row_details['actions'].append(f"❌ تاريخ معاينة غير صالح: '{inspection_date}'")

                        self.stats['processed_rows'] += 1
                        self.stats['successful_rows'] += 1
                        self.stats['detailed_errors'].append(row_details)
                        
                    except Exception as e:
                        self.stats['failed_rows'] += 1
                        error_msg = f"خطأ في الصف {row_index}: {str(e)}"
                        self.stats['errors'].append(error_msg)
                        
                        # تسجيل تفاصيل الخطأ
                        error_details = {
                            'row': row_index,
                            'customer_name': mapped_data.get('customer_name', '') if 'mapped_data' in locals() else '',
                            'order_type': mapped_data.get('order_type', '') if 'mapped_data' in locals() else '',
                            'actions': [f"❌ خطأ فادح: {str(e)}"]
                        }
                        self.stats['detailed_errors'].append(error_details)
            
            # طباعة التقدم بعد كل دفعة
            progress = (batch_end / total_rows) * 100
            print(f"[SYNC] التقدم: {progress:.1f}% - تمت معالجة {batch_end} من {total_rows} صف")

        # طباعة تقرير مفصل
        self._print_detailed_report()

    def _print_detailed_report(self):
        """طباعة تقرير مفصل عن نتائج المزامنة"""
        print("\n" + "="*80)
        print("📊 تقرير مفصل عن نتائج المزامنة")
        print("="*80)
        
        # إحصائيات عامة
        print(f"📋 إجمالي الصفوف: {self.stats['total_rows']}")
        print(f"✅ صفوف ناجحة: {self.stats['successful_rows']}")
        print(f"❌ صفوف فاشلة: {self.stats['failed_rows']}")
        print(f"⚡ معدل النجاح: {(self.stats['successful_rows']/self.stats['total_rows']*100):.1f}%")
        
        print("\n" + "-"*50)
        print("👥 إحصائيات العملاء:")
        print(f"  ✅ عم��اء جدد: {self.stats['customers_created']}")
        print(f"  🔄 عملاء محدثين: {self.stats['customers_updated']}")
        print(f"  ⏭️ عملاء متخطين: {self.stats['customers_skipped']}")
        
        print("\n" + "-"*50)
        print("📦 إحصائيات الطلبات:")
        print(f"  ✅ طلبات منشأة: {self.stats['orders_created']}")
        print(f"  🔄 طلبات محدثة: {self.stats['orders_updated']}")
        print(f"  ⏭️ طلبات متخطية: {self.stats['orders_skipped']}")
        
        print("\n" + "-"*50)
        print("🔍 إحصائيات المعاينات:")
        print(f"  ✅ معاينات منشأة: {self.stats['inspections_created']}")
        print(f"  ⏭️ معاينات متخطية: {self.stats['inspections_skipped']}")
        
        print("\n" + "-"*50)
        print("🏭 إحصائيات أوامر التصنيع:")
        print(f"  ✅ أوامر تصنيع منشأة: {self.stats['manufacturing_orders_created']}")
        print(f"  ❌ أوامر تصنيع فاشلة: {self.stats['manufacturing_orders_failed']}")
        
        # حساب الطلبات الأساسية (التي تحتاج أوامر تصنيع)
        basic_orders = self.stats['orders_created'] - self.stats['inspections_created']
        print(f"  📊 الطلبات الأساسية (تحتاج أوامر تصنيع): {basic_orders}")
        print(f"  ⚠️ ملاحظة: أوامر التصنيع تُنشأ فقط للطلبات ��لأساسية، وليس لطلبات المعاينة")
        
        # تحليل أسباب تخطي الطلبات
        if self.stats['orders_skipped'] > 0:
            print("\n" + "-"*50)
            print("🔍 تحليل ��سباب تخطي الطلبات:")
            
            unknown_types = 0
            unsupported_types = 0
            unknown_type_examples = set()
            
            for error in self.stats['detailed_errors']:
                for action in error.get('actions', []):
                    if 'نوع طلب غير معروف' in action:
                        unknown_types += 1
                        # استخراج نوع الطلب من الرسالة
                        if "'" in action:
                            type_value = action.split("'")[1]
                            unknown_type_examples.add(type_value)
                    elif 'نوع طلب غير مدعوم' in action:
                        unsupported_types += 1
            
            print(f"  ❓ أنواع طلبات غير معروفة: {unknown_types}")
            print(f"  🚫 أنواع طلبات غير مدعومة: {unsupported_types}")
            
            if unknown_type_examples:
                print(f"  📝 أمثلة على الأنواع غير المعروفة:")
                for example in sorted(unknown_type_examples):
                    print(f"     - '{example}'")
        
        # عرض أمثلة على الأخطاء
        if self.stats['errors']:
            print("\n" + "-"*50)
            print("❌ أمثلة على الأخطاء:")
            for i, error in enumerate(self.stats['errors'][:5]):  # أول 5 أخطاء
                print(f"  {i+1}. {error}")
            if len(self.stats['errors']) > 5:
                print(f"  ... و {len(self.stats['errors']) - 5} أخطاء أخرى")
        
        # عرض تفاصيل بعض الصفوف
        if self.stats['detailed_errors']:
            print("\n" + "-"*50)
            print("📝 تفاصيل بعض الصفوف:")
            
            # عرض أول 10 صفوف مع تفاصيلها
            for i, row_detail in enumerate(self.stats['detailed_errors'][:10]):
                print(f"\n  📄 الصف {row_detail['row']}:")
                print(f"     👤 العميل: {row_detail.get('customer_name', 'غير محدد')}")
                print(f"     📦 نوع الطلب: {row_detail.get('order_type', 'غير محدد')}")
                print(f"     📅 تاريخ المعاينة: {row_detail.get('inspection_date', 'غير محدد')}")
                print(f"     🔧 الإجراءات:")
                for action in row_detail.get('actions', []):
                    print(f"        {action}")
            
            if len(self.stats['detailed_errors']) > 10:
                print(f"\n  ... و {len(self.stats['detailed_errors']) - 10} صف آخر")
        
        print("\n" + "="*80)
        print("✅ انتهاء التقرير المفصل")
        print("="*80)

    def _get_sheet_data(self) -> List[List[str]]:
        # جلب البيانات من Google Sheets
        try:
            return self.importer.get_sheet_data(self.mapping.sheet_name)
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات من Google Sheets: {str(e)}", exc_info=True)
            raise

    def _map_row_data(self, headers: List[str], row_data: List[str]) -> Dict[str, str]:
        # تحويل بيانات الصف إلى قاموس حسب التعيينات
        mapped_data = {}
        column_mappings = self.mapping.get_column_mappings()
        
        for i, header in enumerate(headers):
            if i < len(row_data) and header in column_mappings:
                field_type = column_mappings[header]
                if field_type != 'ignore':
                    mapped_data[field_type] = row_data[i].strip() if row_data[i] else ''
        
        return mapped_data

    def _process_customer(self, mapped_data: Dict[str, str], row_index: int, task: GoogleSyncTask) -> Optional[Customer]:
        """
        معالجة بيانات العميل بأداء محسن - البحث بالهاتف أولاً ثم بالاسم
        """
        try:
            customer_name = mapped_data.get('customer_name', '').strip()
            if not customer_name:
                return None

            customer_phone = mapped_data.get('customer_phone', '').strip()
            
            # البحث بالهاتف أولاً (أسرع وأكثر دقة)
            if customer_phone:
                customer = Customer.objects.filter(phone=customer_phone).first()
                if customer:
                    if self.mapping.update_existing:
                        self._update_customer(customer, mapped_data)
                        self.stats['customers_updated'] += 1
                    return customer
            
            # البحث بالاسم إذا لم يوجد هاتف أو لم يتم العثور على العميل
            if not customer_phone:
                customer = Customer.objects.filter(name__iexact=customer_name).first()
                if customer:
                    if self.mapping.update_existing:
                        self._update_customer(customer, mapped_data)
                        self.stats['customers_updated'] += 1
                    return customer
                
            # إنشاء عميل جديد
            if self.mapping.auto_create_customers:
                customer = self._create_customer(mapped_data)
                if customer:
                    self.stats['customers_created'] += 1
                return customer
                
            return None

        except Exception as e:
            error_msg = f"خطأ في الصف {row_index}: {str(e)}"
            self.stats['errors'].append(error_msg)
            return None

    def _parse_date(self, value):
        """محاولة تصحيح وتحويل أي قيمة إلى datetime مع المنطقة الزمنية أو None إذا غير صالح"""
        from dateutil import parser
        from dateutil.parser import ParserError
        if not value or not str(value).strip():
            return None
        try:
            if isinstance(value, (datetime, date)):
                dt = datetime.combine(value, datetime.min.time()) if isinstance(value, date) and not isinstance(value, datetime) else value
                # التأكد من وجود المنطقة الزمنية
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
                return dt
            
            # محاولة التحليل بالصيغ الشائعة أولاً (أسرع)
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    dt = datetime.strptime(str(value).strip(), fmt)
                    return timezone.make_aware(dt)
                except Exception:
                    continue
            
            # استخدام dateutil كحل أخير
            dt = parser.parse(str(value).strip(), dayfirst=True, yearfirst=False, fuzzy=True)
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt)
            return dt
        except (ValueError, ParserError, TypeError):
            return None

    def _is_valid_inspection_date(self, value):
        """التحقق من صحة تاريخ المعاينة - رفض النصوص العربية والحقول الفارغة"""
        if not value or not str(value).strip():
            return False
        
        value_str = str(value).strip()
        
        # قائمة الكلمات المرفوضة
        rejected_phrases = [
            'طرف العميل', 'العميل', 'لاحقا', 'لاحقاً', 'غير محدد', 'غير معروف',
            'بدون', 'لا يوجد', 'فارغ', 'تحديد لاحق', 'حسب العميل', 'عند العميل',
            'customer', 'later', 'unknown', 'none', 'empty', 'n/a', 'na', 'tbd'
        ]
        
        # رفض إذا كان النص يحتوي على كلمات مرفوضة
        for phrase in rejected_phrases:
            if phrase in value_str.lower():
                return False
        
        # رفض إذا كان النص يحتوي على أحرف عربية فقط
        if any('\u0600' <= char <= '\u06FF' for char in value_str):
            return False
        
        # محاولة تحليل التاريخ
        try:
            parsed_date = self._parse_date(value_str)
            return parsed_date is not None
        except:
            return False
    
    def _create_customer(self, mapped_data: Dict[str, str]) -> Customer:
        """إنشاء عميل جديد مع تعيين created_at حسب إعدادات المزامنة المتقدمة"""
        customer_data = {
            'name': mapped_data.get('customer_name', ''),
            'phone': mapped_data.get('customer_phone', ''),
            'phone2': mapped_data.get('customer_phone2', ''),
            'email': mapped_data.get('customer_email', ''),
            'address': mapped_data.get('customer_address', ''),
        }
        if hasattr(self.mapping, 'default_customer_category') and self.mapping.default_customer_category:
            customer_data['category'] = self.mapping.default_customer_category
        if hasattr(self.mapping, 'default_customer_type') and self.mapping.default_customer_type:
            customer_data['customer_type'] = self.mapping.default_customer_type
        if hasattr(self.mapping, 'default_branch') and self.mapping.default_branch:
            customer_data['branch'] = self.mapping.default_branch
        customer_code = mapped_data.get('customer_code', '').strip()
        if customer_code:
            customer_data['code'] = customer_code
        
        # تعيين created_at حسب إعدادات المزامنة المتقدمة
        # إذا كان الخيار "استخدام التاريخ الحالي كتاريخ الإضافة" مفعل، استخدم التاريخ الحالي
        # وإلا استخدم تاريخ الطلب كتاريخ إضافة العميل
        if not getattr(self.mapping, 'use_current_date_as_created', False):
            # استخدام تاريخ الطلب كتاريخ إضافة العميل (الخيار المطلوب)
            created_at_str = mapped_data.get('order_date', '').strip()
            if created_at_str:
                created_at_dt = self._parse_date(created_at_str)
                if created_at_dt:
                    customer_data['created_at'] = created_at_dt
                    logger.info(f"تم تعيين تاريخ إضافة العميل من تاريخ الطلب: {created_at_dt}")
        # إذا كان الخيار مفعل، سيتم استخدام التاريخ الحالي تلقائياً (default=timezone.now)
        
        try:
            customer = Customer.objects.create(**customer_data)
            return customer
        except IntegrityError as e:
            raise Exception(f"فشل إنشاء عميل جديد: {str(e)}")

    def _update_customer(self, customer: Customer, mapped_data: Dict[str, str]) -> bool:
        """
        تحديث بيانات العميل الموجود فقط إذا تغيرت البيانات
        
        العائد:
    # bool: True if updated, False if no change
        """
        updates = {}
        
        # تحديث البيانات
        fields_to_update = ['phone2', 'email', 'address']
        mapping_fields = ['customer_phone2', 'customer_email', 'customer_address']
        
        for customer_field, mapping_field in zip(fields_to_update, mapping_fields):
            new_value = mapped_data.get(mapping_field, '').strip()
            if new_value and getattr(customer, customer_field) != new_value:
                updates[customer_field] = new_value
        
        # تحديث الحقول التي تغيرت فقط
        if updates:
            Customer.objects.filter(id=customer.id).update(**updates)
            logger.info(f"تم تحديث بيانات العميل {customer.id} - التغييرات: {', '.join(updates.keys())}")
            return True
            
        return False

    def _create_order(self, mapped_data: Dict[str, str], customer: Customer, order_type: str = None) -> Order:
        """إنشاء طلب محسن بعملية حفظ واحدة مع تعيين تاريخ الطلب من الجدول"""
        
        order_data = {
            'customer': customer,
            'status': mapped_data.get('order_status', 'normal') or 'normal',
            'notes': mapped_data.get('order_notes', '').strip(),
            'contract_number': mapped_data.get('contract_number', '').strip(),
        }
        
        # رقم الفاتورة
        invoice_number = mapped_data.get('invoice_number', '').strip()
        order_data['invoice_number'] = invoice_number if invoice_number else "لا يوجد رقم فاتورة"
        
        # نوع الطلب
        if order_type:
            order_data['selected_types'] = [order_type]
        
        # تاريخ الطلب - تعيينه مباشرة قبل الإنشاء
        order_date = mapped_data.get('order_date', '')
        parsed_order_date = self._parse_date(order_date)
        if parsed_order_date:
            order_data['order_date'] = parsed_order_date
        
        # حالة التتبع
        tracking_status = mapped_data.get('tracking_status', '')
        if tracking_status:
            status_mapping = {
                'قيد الانتظار': 'pending',
                'قيد المعالجة': 'processing',
                'في المستودع': 'warehouse',
                'في المصنع': 'factory',
                'قيد القص': 'cutting',
                'جاهز للتسليم': 'ready',
                'تم التسليم': 'delivered',
            }
            order_data['tracking_status'] = status_mapping.get(tracking_status, 'pending')
        
        # المبالغ
        try:
            if mapped_data.get('total_amount'):
                order_data['total_amount'] = float(mapped_data['total_amount'])
        except (ValueError, TypeError):
            pass
        try:
            if mapped_data.get('paid_amount'):
                order_data['paid_amount'] = float(mapped_data['paid_amount'])
        except (ValueError, TypeError):
            pass
        
        # نوع التسليم
        delivery_type = mapped_data.get('delivery_type', '')
        if delivery_type:
            delivery_mapping = {
                'توصيل للمنزل': 'home',
                'استلام من الفرع': 'branch',
            }
            order_data['delivery_type'] = delivery_mapping.get(delivery_type, 'branch')
        
        # عنوان التسليم
        delivery_address = mapped_data.get('delivery_address', '')
        if delivery_address:
            order_data['delivery_address'] = delivery_address
        
        # البائع
        salesperson_name = mapped_data.get('salesperson', '')
        if salesperson_name:
            salesperson = Salesperson.objects.filter(name__icontains=salesperson_name).first()
            if salesperson:
                order_data['salesperson'] = salesperson
        
        # الفرع
        branch = customer.branch
        if hasattr(self.mapping, 'default_branch') and self.mapping.default_branch:
            branch = self.mapping.default_branch
        if branch:
            order_data['branch'] = branch
        
        # رقم الطلب
        order_number = mapped_data.get('order_number', '').strip()
        if order_number:
            order_data['order_number'] = order_number
        
        try:
            # إنشاء الطلب بعملية واحدة مع جميع البيانات
            order = Order.objects.create(**order_data)
            self.stats['orders_created'] += 1
            return order
        except Exception as e:
            raise Exception(f"فشل إنشاء طلب جديد: {str(e)}")

    def _find_existing_order(self, customer: Customer, order_type: str, contract_number: str = '', invoice_number: str = '') -> Optional[Order]:
        """
        البحث عن طلب موجود للعميل بنفس النوع ورقم العقد/الفاتورة لتجنب التكرار
        """
        try:
            # البحث بناءً على العميل ونوع الطلب
            query = Order.objects.filter(
                customer=customer,
                selected_types__contains=[order_type]
            )
            
            # إضافة شروط إضافية للبحث الدقيق
            if contract_number:
                query = query.filter(contract_number=contract_number)
            elif invoice_number and invoice_number != "لا يوجد رقم فاتورة":
                query = query.filter(invoice_number=invoice_number)
            
            # إرجاع أول طلب مطابق
            return query.first()
            
        except Exception as e:
            logger.warning(f"خطأ في البحث عن طلب موجود: {str(e)}")
            return None

    def _find_or_create_inspection_order(self, mapped_data: Dict[str, str], customer: Customer, 
                                       inspection_date: str, contract_number: str = '', 
                                       invoice_number: str = '') -> Optional[Order]:
        """
        البحث عن طلب معاينة موجود أو إنشاء جديد
        """
        try:
            parsed_inspection_date = self._parse_date(inspection_date)
            if not parsed_inspection_date:
                return None
            
            # البحث عن طلب معاينة موجود لنفس العميل في نفس التاريخ
            existing_order = Order.objects.filter(
                customer=customer,
                selected_types__contains=['inspection'],
                order_date__date=parsed_inspection_date.date()
            ).first()
            
            if existing_order:
                return existing_order
            
            # إنشاء طلب معاينة جديد
            inspection_mapped_data = mapped_data.copy()
            inspection_mapped_data['order_date'] = inspection_date
            
            inspection_order = self._create_order(inspection_mapped_data, customer, 'inspection')
            return inspection_order
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء/البحث عن طلب المعاينة: {str(e)}")
            return None

    def _update_order(self, order: Order, mapped_data: Dict[str, str], customer: Customer) -> bool:
        """
        Update the existing order only if data has changed.

        Returns:
            bool: True if updated, False if no change
        """
        updates = {}
        
        # تحديث حالة التتبع
        tracking_status = mapped_data.get('tracking_status', '')
        if tracking_status and tracking_status != order.tracking_status:
            updates['tracking_status'] = tracking_status
            
        # ��حديث المبالغ إذا تغيرت
        try:
            total_amount = mapped_data.get('total_amount')
            if total_amount and float(total_amount) != order.total_amount:
                updates['total_amount'] = float(total_amount)
        except (ValueError, TypeError):
            pass
            
        try:
            paid_amount = mapped_data.get('paid_amount')
            if paid_amount and float(paid_amount) != order.paid_amount:
                updates['paid_amount'] = float(paid_amount)
        except (ValueError, TypeError):
            pass
            
        # تحديث الملاحظات إذا تغيرت
        notes = mapped_data.get('notes', '')
        if notes and notes != order.notes:
            updates['notes'] = notes
        
        # تحديث الحقول التي تغيرت فقط
        if updates:
            Order.objects.filter(id=order.id).update(**updates)
            logger.info(f"تم تحديث الطلب {order.id} - التغييرات: {', '.join(updates.keys())}")
            return True
            
        return False

    def _process_inspection(self, mapped_data: Dict[str, str], customer: Customer, order: Order, row_index: int, task: GoogleSyncTask):
        """معالجة بيانات المعاينة مع رقم العقد"""
        try:
            from dateutil import parser
            from dateutil.parser import ParserError
            # تاريخ اليوم كقيمة افتراضية
            today = timezone.now().date()
            inspection_data = {
                'customer': customer,
                'order': order,
                'branch': customer.branch or order.branch,
                'request_date': today,
                'scheduled_date': today + timedelta(days=1),  # تاريخ افتراضي: غداً
                'notes': mapped_data.get('notes', ''),
                'contract_number': mapped_data.get('contract_number', ''),
            }
            # محاولة تحليل تاريخ المعاينة كما هو
            inspection_date = (mapped_data.get('inspection_date') or '').strip()
            if inspection_date:
                try:
                    parsed_date = parser.parse(inspection_date, dayfirst=True, yearfirst=False, fuzzy=True)
                    if isinstance(parsed_date, datetime):
                        inspection_data['scheduled_date'] = parsed_date.date() if hasattr(parsed_date, 'date') else parsed_date
                        inspection_data['request_date'] = (parsed_date.date() if hasattr(parsed_date, 'date') else parsed_date) - timedelta(days=1)
                    elif isinstance(parsed_date, date):
                        inspection_data['scheduled_date'] = parsed_date
                        inspection_data['request_date'] = parsed_date - timedelta(days=1)
                except (ValueError, ParserError):
                    inspection_data['notes'] = f"تاريخ المعاينة: {inspection_date}\n{inspection_data.get('notes', '')}"
            # نتيجة المعاينة
            inspection_result = mapped_data.get('inspection_result', '')
            if inspection_result:
                result_mapping = {
                    'مقبول': 'approved',
                    'مرفوض': 'rejected',
                    'يحتاج مراجعة': 'pending',
                }
                inspection_data['result'] = result_mapping.get(inspection_result, 'approved')
            else:
                inspection_data['result'] = 'approved'  # جميع المعاينات تعتبر مكتملة وناجحة
            windows_count = mapped_data.get('windows_count', '')
            if windows_count:
                try:
                    inspection_data['windows_count'] = int(windows_count)
                except (ValueError, TypeError):
                    pass
            inspection = Inspection.objects.create(**inspection_data)
            return inspection
        except Exception as e:
            self.stats['errors'].append(f"خطأ في معالجة المعاينة في الصف {row_index}: {str(e)}")
            raise

    def _update_inspection(self, inspection: Inspection, mapped_data: Dict[str, str]) -> bool:
        """
        Update the existing inspection data only if changed.

        Returns:
            bool: True if updated, False if no change
        """
        from dateutil import parser
        from dateutil.parser import ParserError
        
        updates = {}
        
        # تحديث نتيجة المعاينة
        inspection_result = mapped_data.get('inspection_result', '')
        if inspection_result:
            result_mapping = {
                'مقبول': 'approved',
                'مرفوض': 'rejected',
                'يحتاج مراجعة': 'pending',
            }
            new_result = result_mapping.get(inspection_result, inspection.result if hasattr(inspection, 'result') else 'pending')
            if hasattr(inspection, 'result') and new_result != inspection.result:
                updates['result'] = new_result
        
        # تحديث عدد الشبابيك
        windows_count = mapped_data.get('windows_count', '')
        if windows_count:
            try:
                new_count = int(windows_count)
                if hasattr(inspection, 'windows_count') and new_count != inspection.windows_count:
                    updates['windows_count'] = new_count
            except (ValueError, TypeError):
                pass
        
        # تحديث تاريخ المعاينة
        inspection_date = mapped_data.get('inspection_date', '')
        if inspection_date:
            try:
                parsed_date = parser.parse(inspection_date, dayfirst=True, yearfirst=False, fuzzy=True).date()
                if hasattr(inspection, 'scheduled_date') and parsed_date != inspection.scheduled_date:
                    updates['scheduled_date'] = parsed_date
            except (ValueError, ParserError):
                pass
        
        # تحديث الملاحظات
        notes = mapped_data.get('notes', '')
        if notes and hasattr(inspection, 'notes') and notes != inspection.notes:
            updates['notes'] = notes
        
        # تحديث الحقول التي تغيرت فقط
        if updates:
            Inspection.objects.filter(id=inspection.id).update(**updates)
            logger.info(f"تم تحديث المعاينة {inspection.id} - التغييرات: {', '.join(updates.keys())}")
            return True
            
        return False

    def _process_installation(self, mapped_data: Dict[str, str], customer: Customer, order: Order, row_index: int, task: GoogleSyncTask):
        """معالجة بيانات التركيب"""
        try:
            # التحقق من وجود تركيب للطلب
            existing_installation = Installation.objects.filter(order=order).first()
            if existing_installation:
                return existing_installation

            installation_data = {
                'order': order,
                'scheduled_date': timezone.now().date() + timedelta(days=7),
                'notes': mapped_data.get('notes', ''),
            }

            # حالة التركيب
            installation_status = mapped_data.get('installation_status', '')
            if installation_status:
                status_mapping = {
                    'قيد الانتظار': 'pending',
                    'مجدولة': 'scheduled',
                    'قيد التنفيذ': 'in_progress',
                    'مكتملة': 'completed',
                    'ملغية': 'cancelled',
                }
                installation_data['status'] = status_mapping.get(installation_status, 'pending')

            installation = Installation.objects.create(**installation_data)
            # Removed installations counter - will be reimplemented
            return installation
            
        except Exception as e:
            self.stats['errors'].append(f"خطأ في معالجة التركيب في الصف {row_index}: {str(e)}")
            raise


class SyncScheduler:
    """جدولة المزامنة التلقائية"""
    
    def __init__(self):
        self.schedules = []
        
    def run_scheduled_syncs(self):
        """تشغيل المزامنة المجدولة"""
        due_schedules = GoogleSyncSchedule.objects.filter(
            is_active=True,
            next_run__lte=timezone.now()
        )
        
        for schedule in due_schedules:
            try:
                # تشغيل المزامنة
                service = AdvancedSyncService(schedule.mapping)
                result = service.sync_from_sheets()
                
                # تسجيل النتيجة
                schedule.record_execution(success=result.get('success', False))
                
            except Exception as e:
                logger.error(f"خطأ في تشغيل الجدولة {schedule.id}: {str(e)}")
                schedule.record_execution(success=False)
