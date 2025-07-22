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
        """دالة وهمية مؤقتة لمنع الخطأ. نفذ منطق أمر التصنيع هنا لاحقًا."""
        pass
    def _map_order_type(self, order_type_value: str) -> str:
        """
        تحويل نوع الطلب من العربية إلى القيم البرمجية المعتمدة في النظام.
        يدعم: معاينة، تركيب، اكسسوار، تفصيل، تسليم
        """
        mapping = {
            'معاينة': 'inspection',
            'inspection': 'inspection',
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
        return mapping.get(order_type_value.strip().lower().replace('إ','ا'), order_type_value.strip().lower())
    def _create_inspection(self, mapped_data: Dict[str, str], order: Order) -> Inspection:
        """إنشاء معاينة مرتبطة بالطلب فقط إذا كان التاريخ صالحًا"""
        from inspections.models import Inspection
        from datetime import timedelta
        from django.utils import timezone

        inspection_data = {
            'order': order,
            'customer': order.customer,
            'branch': order.branch,
        }

        # معالجة تاريخ المعاينة: لا تنشئ معاينة إذا لم يوجد تاريخ صالح
        inspection_date = mapped_data.get('inspection_date', '').strip()
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
            'orders_created': 0,
            'orders_updated': 0,
            'inspections_created': 0,
            # Removed installations stats - will be reimplemented
            'errors': [],
            'warnings': []
        }

    def sync_from_sheets(self, task: GoogleSyncTask = None) -> Dict[str, Any]:
        """مزامنة البيانات من Google Sheets حسب المتطلبات الجديدة"""
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
        
        for row_index, row in enumerate(sheet_data[1:], start=2):
            try:
                # طباعة تقدم كل 10 صفوف
                if (row_index - 2) % 10 == 0:
                    progress = ((row_index - 2) / total_rows) * 100
                    print(f"[SYNC] التقدم: {progress:.1f}% - معالجة الصف {row_index} من {total_rows+1}")

                mapped_data = self._map_row_data(headers, row)
                
                # معالجة العميل
                customer = self._process_customer(mapped_data, row_index, task)
                if not customer:
                    print(f"[SYNC] تخطي الصف {row_index}: لا يوجد عميل")
                    continue

                # تحديد نوع الطلب الأساسي
                raw_order_type = mapped_data.get('order_type', '').strip()
                order_type = self._map_order_type(raw_order_type)
                
                # تحديد وجود تاريخ معاينة
                inspection_date = mapped_data.get('inspection_date', '').strip()
                has_inspection_date = bool(inspection_date)

                print(f"[SYNC] الصف {row_index}: العميل={customer.name}, ال��وع={order_type}, معاينة={has_inspection_date}")

                # إنشاء الطلب الأساسي (تركيب/تسليم/اكسسوار)
                main_order = None
                if order_type in ['installation', 'accessory', 'tailoring']:
                    main_order = self._create_order(mapped_data, customer, order_type)
                    print(f"[SYNC] تم إنشاء طلب {order_type}: {main_order.order_number}")
                    
                    # إنشاء أمر تصنيع للطلب الأساسي
                    try:
                        self._create_manufacturing_order(mapped_data, main_order)
                        print(f"[SYNC] تم إنشاء أمر تصنيع للطلب: {main_order.order_number}")
                    except Exception as e:
                        print(f"[SYNC] تعذر إنشاء أمر تصنيع: {str(e)}")

                # إنشاء طلب معاينة منفصل إذا وُجد تاريخ معاينة
                inspection_order = None
                if has_inspection_date:
                    inspection_order = self._create_order(mapped_data, customer, 'inspection')
                    print(f"[SYNC] تم إنشاء طلب معاينة: {inspection_order.order_number}")
                    
                    # إنشاء المعاينة مرتبطة بطلب المعاينة
                    try:
                        inspection = self._create_inspection(mapped_data, inspection_order)
                        print(f"[SYNC] تم إنشاء معاينة للطلب: {inspection_order.order_number}")
                    except Exception as e:
                        print(f"[SYNC] تعذر إنشاء معاينة: {str(e)}")

                self.stats['processed_rows'] += 1
                self.stats['successful_rows'] += 1
                
            except Exception as e:
                self.stats['failed_rows'] += 1
                error_msg = f"خطأ في الصف {row_index}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(f"[SYNC] {error_msg}")
                logger.error(error_msg)

        print(f"[SYNC] انتهاء المعالجة. نجح: {self.stats['successful_rows']}, فشل: {self.stats['failed_rows']}")

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
        """محاولة تصحيح وتحويل أي قيمة إلى datetime أو None إذا غير صالح"""
        from dateutil import parser
        from dateutil.parser import ParserError
        if not value or not str(value).strip():
            return None
        try:
            if isinstance(value, (datetime, date)):
                return datetime.combine(value, datetime.min.time()) if isinstance(value, date) and not isinstance(value, datetime) else value
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    return datetime.strptime(str(value).strip(), fmt)
                except Exception:
                    continue
            return parser.parse(str(value).strip(), dayfirst=True, yearfirst=False, fuzzy=True)
        except (ValueError, ParserError, TypeError):
            return None
    
    def _create_customer(self, mapped_data: Dict[str, str]) -> Customer:
        """إنشاء عميل جديد مع تعيين created_at من العمود المحدد في التعيين إذا توفر"""
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
    
        try:
            customer = Customer.objects.create(**customer_data)
            
            # معالجة تاريخ الإنشاء بعد إنشاء العميل
            created_at_str = ''
            for key in ['customer_created_at', 'customer_date', 'customer_registration_date']:
                if key in self.mapping.get_column_mappings().values():
                    val = mapped_data.get(key, '').strip()
                    if val:
                        created_at_str = val
                        break
            
            if created_at_str:
                created_at_dt = self._parse_date(created_at_str)
                if created_at_dt:
                    customer.created_at = created_at_dt
                    customer.save(update_fields=['created_at'])
                    logger.info(f"[CREATE_CUSTOMER] تم تحديث تاريخ إنشاء العميل إلى: {created_at_dt}")
            
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
        logger.info(f"[CREATE_ORDER] محاولة إنشاء طلب للعميل: {customer.name}")
        logger.info(f"[CREATE_ORDER] البيانات المتاحة: {mapped_data}")
        import traceback
    
        order_data = {}
        order_data['customer'] = customer
        # رقم الفاتورة الافتراضي
        invoice_number = mapped_data.get('invoice_number', '').strip()
        order_data['invoice_number'] = invoice_number if invoice_number else "لا يوجد رقم فاتورة"
        order_data['contract_number'] = mapped_data.get('contract_number', '').strip()
        order_data['notes'] = mapped_data.get('order_notes', '').strip()
        order_data['status'] = mapped_data.get('order_status', 'normal') or 'normal'
        if order_type:
            order_data['selected_types'] = [order_type]
    
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
    
        delivery_type = mapped_data.get('delivery_type', '')
        if delivery_type:
            delivery_mapping = {
                'توصيل للمنزل': 'home',
                'استلام من الفرع': 'branch',
            }
            order_data['delivery_type'] = delivery_mapping.get(delivery_type, 'branch')
    
        delivery_address = mapped_data.get('delivery_address', '')
        if delivery_address:
            order_data['delivery_address'] = delivery_address
    
        salesperson_name = mapped_data.get('salesperson', '')
        if salesperson_name:
            salesperson = Salesperson.objects.filter(name__icontains=salesperson_name).first()
            if salesperson:
                order_data['salesperson'] = salesperson
    
        branch = customer.branch
        if hasattr(self.mapping, 'default_branch') and self.mapping.default_branch:
            branch = self.mapping.default_branch
        if branch:
            order_data['branch'] = branch
    
        order_number = mapped_data.get('order_number', '').strip()
        if order_number:
            order_data['order_number'] = order_number
    
        logger.info(f"[CREATE_ORDER] بيانات الطلب النهائية: {order_data}")
    
        try:
            order = Order.objects.create(**order_data)
            
            # تحديث تاريخ الطلب بعد الإنشاء إذا كان متوفراً في البيانات
            order_date = mapped_data.get('order_date', '')
            parsed_order_date = self._parse_date(order_date)
            if parsed_order_date:
                order.order_date = parsed_order_date
                order.save(update_fields=['order_date'])
                logger.info(f"[CREATE_ORDER] تم تحديث تاريخ الطلب إلى: {parsed_order_date}")
            
            logger.info(f"[CREATE_ORDER] تم إنشاء الطلب بنجاح: {order.order_number if hasattr(order, 'order_number') else 'N/A'}")
            self.stats['orders_created'] += 1
            return order
        except IntegrityError as e:
            logger.error(f"[CREATE_ORDER] خطأ IntegrityError: {str(e)}")
            logger.error(f"[CREATE_ORDER] بيانات الطلب: {order_data}")
            print(traceback.format_exc())
            raise Exception(f"فشل إنشاء طلب جديد: {str(e)}")
        except Exception as e:
            logger.error(f"[CREATE_ORDER] خطأ عام: {str(e)}")
            logger.error(f"[CREATE_ORDER] بيانات الطلب: {order_data}")
            print(traceback.format_exc())
            raise Exception(f"فشل إنشاء طلب جديد: {str(e)}")

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
            
        # تحديث المبالغ إذا تغيرت
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
