"""
خدمة المزامنة السريعة - محسنة للأداء العالي
Fast Sync Service - Optimized for High Performance
"""

import logging
import json
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from .google_sync_advanced import GoogleSheetMapping, GoogleSyncTask
from .google_sheets_import import GoogleSheetsImporter
from customers.models import Customer
from orders.models import Order
from inspections.models import Inspection
from accounts.models import Branch, Salesperson

logger = logging.getLogger(__name__)


class FastSyncService:
    """خدمة المزامنة السريعة - أقل من دقيقة"""

    def __init__(self, mapping: GoogleSheetMapping):
        self.mapping = mapping
        self.importer = GoogleSheetsImporter()
        self.stats = {
            'total_rows': 0,
            'processed_rows': 0,
            'successful_rows': 0,
            'failed_rows': 0,
            'customers_created': 0,
            'customers_updated': 0,
            'customers_skipped': 0,
            'orders_created': 0,
            'orders_skipped': 0,
            'inspections_created': 0,
            'manufacturing_orders_created': 0,
            'manufacturing_orders_failed': 0,
            'errors': []
        }

    def sync_from_sheets(self, task: GoogleSyncTask = None) -> Dict[str, Any]:
        """مزامنة سريعة من Google Sheets"""
        try:
            self.importer.initialize()
            if not task:
                task = GoogleSyncTask.objects.create(
                    mapping=self.mapping,
                    task_type='import',
                    created_by=None
                )
            
            task.status = 'running'
            task.started_at = timezone.now()
            task.save()

            # جلب البيانات
            sheet_data = self._get_sheet_data()
            if not sheet_data:
                raise Exception("لا توجد بيانات في الجدول")

            task.rows_processed = len(sheet_data)
            task.save()

            # معالجة سريعة
            self._process_sheet_data_fast(sheet_data, task)

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
            logger.error(f"خطأ في المزامنة السريعة: {str(e)}")
            if task:
                task.status = 'failed'
                task.error_log = str(e)
                task.save()
            return {'success': False, 'error': str(e)}

    def _process_sheet_data_fast(self, sheet_data: List[List[str]], task: GoogleSyncTask):
        """معالجة سريعة للبيانات - محسنة للأداء"""
        if not sheet_data or len(sheet_data) < 2:
            print("[FAST_SYNC] لا توجد بيانات كافية")
            return

        headers = sheet_data[0]
        total_rows = len(sheet_data) - 1
        self.stats['total_rows'] = total_rows
        
        print(f"[FAST_SYNC] بدء معالجة سريعة لـ {total_rows} صف...")
        
        # تحميل البيانات الموجودة مسبقاً (تحسين كبير)
        existing_customers = {}
        existing_customers_by_name = {}
        
        for c in Customer.objects.select_related('branch').all():
            if c.phone:
                existing_customers[c.phone] = c
            existing_customers_by_name[c.name.lower()] = c
        
        print(f"[FAST_SYNC] تم تحميل {len(existing_customers)} عميل موجود")
        
        # معالجة بدفعات صغيرة وسريعة
        batch_size = 5  # دفعات صغيرة جداً للسرعة القصوى
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_rows = sheet_data[1 + batch_start:1 + batch_end]
            
            # طباعة التقدم كل 25 صف فقط
            if batch_start % 25 == 0:
                progress = (batch_start / total_rows) * 100
                print(f"[FAST_SYNC] {progress:.0f}% - الصف {batch_start + 1}")
            
            # معاملة سريعة
            with transaction.atomic():
                for i, row in enumerate(batch_rows):
                    try:
                        mapped_data = self._map_row_data(headers, row)
                        customer_name = mapped_data.get('customer_name', '').strip()
                        
                        if not customer_name:
                            self.stats['customers_skipped'] += 1
                            continue

                        # البحث السريع عن العميل
                        customer = self._find_or_create_customer_fast(
                            mapped_data, existing_customers, existing_customers_by_name
                        )
                        
                        if not customer:
                            self.stats['customers_skipped'] += 1
                            continue

                        # معالجة الطلبات بسرعة
                        self._process_orders_fast(mapped_data, customer)
                        
                        self.stats['processed_rows'] += 1
                        self.stats['successful_rows'] += 1
                        
                    except Exception as e:
                        self.stats['failed_rows'] += 1
                        self.stats['errors'].append(f"خطأ في الصف {batch_start + i + 2}: {str(e)}")

        print(f"[FAST_SYNC] اكتملت المعالجة السريعة - {self.stats['successful_rows']} صف ناجح")
        self._print_fast_summary()

    def _find_or_create_customer_fast(self, mapped_data: Dict[str, str], 
                                     existing_customers: Dict, existing_customers_by_name: Dict) -> Optional[Customer]:
        """البحث السريع أو إنشاء عميل"""
        customer_name = mapped_data.get('customer_name', '').strip()
        customer_phone = mapped_data.get('customer_phone', '').strip()
        
        # البحث السريع
        if customer_phone and customer_phone in existing_customers:
            return existing_customers[customer_phone]
        
        if customer_name.lower() in existing_customers_by_name:
            return existing_customers_by_name[customer_name.lower()]
        
        # إنشاء سريع
        if self.mapping.auto_create_customers:
            try:
                customer_data = {
                    'name': customer_name,
                    'phone': customer_phone,
                    'phone2': mapped_data.get('customer_phone2', ''),
                    'email': mapped_data.get('customer_email', ''),
                    'address': mapped_data.get('customer_address', ''),
                }
                
                # إضافة كود العميل إذا توفر
                customer_code = mapped_data.get('customer_code', '').strip()
                if customer_code:
                    customer_data['code'] = customer_code
                
                # إضافة الإعدادات الافتراضية
                if hasattr(self.mapping, 'default_customer_category') and self.mapping.default_customer_category:
                    customer_data['category'] = self.mapping.default_customer_category
                    
                if hasattr(self.mapping, 'default_customer_type') and self.mapping.default_customer_type:
                    customer_data['customer_type'] = self.mapping.default_customer_type
                    
                if hasattr(self.mapping, 'default_branch') and self.mapping.default_branch:
                    customer_data['branch'] = self.mapping.default_branch
                
                customer = Customer.objects.create(**customer_data)
                
                # معالجة تاريخ الإنشاء بعد إنشاء العميل
                created_at_str = ''
                for key in ['customer_created_at', 'customer_date', 'customer_registration_date']:
                    val = mapped_data.get(key, '').strip()
                    if val:
                        created_at_str = val
                        break
                
                if created_at_str:
                    created_at_dt = self._parse_date_fast(created_at_str)
                    if created_at_dt:
                        customer.created_at = created_at_dt
                        customer.save(update_fields=['created_at'])
                
                logger.info(f"[FAST_SYNC] تم إنشاء عميل جديد: {customer.name} (تصنيف: {customer.category}, نوع: {customer.customer_type})")
                
                # تحديث الكاش
                if customer_phone:
                    existing_customers[customer_phone] = customer
                existing_customers_by_name[customer_name.lower()] = customer
                
                self.stats['customers_created'] += 1
                return customer
                
            except Exception:
                return None
        
        return None

    def _process_orders_fast(self, mapped_data: Dict[str, str], customer: Customer):
        """معالجة سريعة للطلبات"""
        raw_order_type = mapped_data.get('order_type', '').strip()
        inspection_date = mapped_data.get('inspection_date', '').strip()
        
        # تحديد نوع الطلب بسرعة
        order_type = self._map_order_type_fast(raw_order_type)
        has_valid_inspection_date = self._is_valid_inspection_date_fast(inspection_date)

        # إنشاء الطلب الأساسي
        if order_type and order_type in ['installation', 'accessory', 'tailoring']:
            main_order = self._create_order_fast(mapped_data, customer, order_type)
            
            # إنشاء أمر تصنيع سريع
            try:
                self._create_manufacturing_order_fast(mapped_data, main_order)
                self.stats['manufacturing_orders_created'] += 1
            except:
                self.stats['manufacturing_orders_failed'] += 1
        else:
            self.stats['orders_skipped'] += 1

        # إنشاء طلب معاينة إذا كان التاريخ صالحاً
        if has_valid_inspection_date:
            inspection_mapped_data = mapped_data.copy()
            inspection_mapped_data['order_date'] = inspection_date
            inspection_order = self._create_order_fast(inspection_mapped_data, customer, 'inspection')
            
            # إنشاء المعاينة سريعاً
            try:
                self._create_inspection_fast(mapped_data, inspection_order)
                self.stats['inspections_created'] += 1
            except:
                pass

    def _map_order_type_fast(self, order_type_value: str) -> str:
        """تحويل سريع لنوع الطلب"""
        if not order_type_value:
            return None
            
        value = order_type_value.strip().lower().replace('إ', 'ا')
        
        if value in ['تركيب', 'installation']:
            return 'installation'
        elif value in ['اكسسوار', 'إكسسوار', 'accessory']:
            return 'accessory'
        elif value in ['تفصيل', 'تسليم', 'توصيل', 'tailoring']:
            return 'tailoring'
        
        return None

    def _is_valid_inspection_date_fast(self, value: str) -> bool:
        """فحص سريع لصحة تاريخ المعاينة"""
        if not value or not value.strip():
            return False
        
        value_str = value.strip().lower()
        
        # رفض الكلمات العربية الشائعة
        if any(word in value_str for word in ['عميل', 'لاحق', 'غير', 'بدون', 'فارغ']):
            return False
        
        # فحص بسيط للتاريخ
        return bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value_str))

    def _parse_date_fast(self, value: str) -> Optional[datetime]:
        """تحليل سريع للتاريخ"""
        if not value:
            return None
        
        # محاولة الصيغ الشائعة فقط
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return timezone.make_aware(dt)
            except:
                continue
        
        return None

    def _create_order_fast(self, mapped_data: Dict[str, str], customer: Customer, order_type: str) -> Order:
        """إنشاء سريع للطلب - مع فحص التكرار"""
        contract_number = mapped_data.get('contract_number', '').strip()
        invoice_number = mapped_data.get('invoice_number', '').strip()
        
        # فحص سريع للطلبات المكررة
        query = Order.objects.filter(
            customer=customer,
            selected_types__contains=[order_type]
        )
        
        if contract_number:
            query = query.filter(contract_number=contract_number)
        elif invoice_number and invoice_number != "لا يوجد رقم فاتورة":
            query = query.filter(invoice_number=invoice_number)
        
        existing_order = query.first()
        if existing_order:
            logger.info(f"[FAST_SYNC] طلب موجود مسبقاً: {existing_order.order_number}")
            return existing_order
        
        order_data = {
            'customer': customer,
            'status': 'normal',
            'selected_types': [order_type],
            'notes': mapped_data.get('order_notes', '').strip(),
            'contract_number': contract_number,
            'invoice_number': invoice_number or "لا يوجد رقم فاتورة",
        }
        
        # تاريخ الطلب
        order_date = mapped_data.get('order_date', '')
        parsed_date = self._parse_date_fast(order_date)
        if parsed_date:
            order_data['order_date'] = parsed_date
        
        # الفرع
        if customer.branch:
            order_data['branch'] = customer.branch
        elif hasattr(self.mapping, 'default_branch') and self.mapping.default_branch:
            order_data['branch'] = self.mapping.default_branch
        
        order = Order.objects.create(**order_data)
        self.stats['orders_created'] += 1
        logger.info(f"[FAST_SYNC] تم إنشاء طلب جديد: {order.order_number}")
        return order

    def _create_manufacturing_order_fast(self, mapped_data: Dict[str, str], order: Order):
        """إنشاء سريع لأمر التصنيع"""
        from manufacturing.models import ManufacturingOrder
        
        # فحص سريع للوجود
        if ManufacturingOrder.objects.filter(order=order).exists():
            return
        
        order_types = order.selected_types or []
        manufacturing_type = 'custom'
        
        if 'installation' in order_types:
            manufacturing_type = 'installation'
        elif 'accessory' in order_types:
            manufacturing_type = 'accessory'
        
        manufacturing_data = {
            'order': order,
            'order_type': manufacturing_type,
            'status': 'pending_approval',
            'order_date': order.order_date or timezone.now().date(),
            'expected_delivery_date': (order.order_date or timezone.now().date()) + timedelta(days=14),
            'contract_number': order.contract_number or '',
            'invoice_number': order.invoice_number or '',
            'notes': mapped_data.get('order_notes', '') or '',
        }
        
        ManufacturingOrder.objects.create(**manufacturing_data)

    def _create_inspection_fast(self, mapped_data: Dict[str, str], order: Order):
        """إنشاء سريع للمعاينة - مع ضمان عدم التكرار للطلب الواحد"""
        inspection_date = mapped_data.get('inspection_date', '').strip()
        parsed_date = self._parse_date_fast(inspection_date)
        
        if not parsed_date:
            return
        
        # فحص سريع للتكرار بناءً على الطلب (وليس العميل والتاريخ)
        if Inspection.objects.filter(order=order).exists():
            logger.info(f"[FAST_SYNC] معاينة موجودة مسبقاً للطلب {order.order_number}")
            return
        
        inspection_data = {
            'order': order,
            'customer': order.customer,
            'branch': order.branch,
            'scheduled_date': parsed_date.date(),
            'request_date': parsed_date.date() - timedelta(days=1),
            'notes': mapped_data.get('inspection_notes', ''),
        }
        
        try:
            Inspection.objects.create(**inspection_data)
            logger.info(f"[FAST_SYNC] تم إنشاء معاينة جديدة للطلب {order.order_number}")
        except Exception as e:
            logger.error(f"[FAST_SYNC] فشل إنشاء المعاينة للطلب {order.order_number}: {str(e)}")
            raise

    def _get_sheet_data(self) -> List[List[str]]:
        """جلب البيانات من Google Sheets"""
        try:
            return self.importer.get_sheet_data(self.mapping.sheet_name)
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات: {str(e)}")
            raise

    def _map_row_data(self, headers: List[str], row_data: List[str]) -> Dict[str, str]:
        """تحويل بيانات الصف إلى قاموس"""
        mapped_data = {}
        column_mappings = self.mapping.get_column_mappings()
        
        for i, header in enumerate(headers):
            if i < len(row_data) and header in column_mappings:
                field_type = column_mappings[header]
                if field_type != 'ignore':
                    mapped_data[field_type] = row_data[i].strip() if row_data[i] else ''
        
        return mapped_data

    def _print_fast_summary(self):
        """طباعة ملخص سريع"""
        print("\n" + "="*50)
        print("⚡ ملخص المزامنة السريعة")
        print("="*50)
        print(f"📋 إجمالي الصفوف: {self.stats['total_rows']}")
        print(f"✅ ناجحة: {self.stats['successful_rows']}")
        print(f"❌ فاشلة: {self.stats['failed_rows']}")
        print(f"👥 عملاء جدد: {self.stats['customers_created']}")
        print(f"📦 طلبات منشأة: {self.stats['orders_created']}")
        print(f"🔍 معاينات منشأة: {self.stats['inspections_created']}")
        print(f"🏭 أوامر تصنيع منشأة: {self.stats['manufacturing_orders_created']}")
        print(f"⏭️ عملاء متخطين: {self.stats['customers_skipped']}")
        
        if self.stats['errors']:
            print(f"⚠️ أخطاء: {len(self.stats['errors'])}")
        
        print("="*50)
        print("✅ انتهت المزامنة السريعة")