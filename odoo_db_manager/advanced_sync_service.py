"""
خدمة المزامنة المتقدمة مع Google Sheets - محدثة حسب المتطلبات الجديدة
Advanced Google Sheets Sync Service - Updated
"""

import logging
import json
import time
from datetime import datetime, timedelta
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
from orders.extended_models import ExtendedOrder
from inspections.models import Inspection
from installations.models import Installation, InstallationTeam
from accounts.models import Branch, Salesperson

logger = logging.getLogger(__name__)


class AdvancedSyncService:
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
            'installations_created': 0,
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
        """معالجة بيانات الجدول حسب المتطلبات الجديدة"""
        headers = sheet_data[self.mapping.header_row - 1] if len(sheet_data) >= self.mapping.header_row else []
        data_rows = sheet_data[self.mapping.start_row - 1:] if len(sheet_data) >= self.mapping.start_row else []
        
        self.stats['total_rows'] = len(data_rows)
        customer_cache = {}
        imported_orders = set()
        imported_inspections = set()

        for row_index, row_data in enumerate(data_rows, self.mapping.start_row):
            try:
                if not row_data or all(not cell.strip() for cell in row_data):
                    continue  # تجاهل الصفوف الفارغة

                # تحويل البيانات إلى قاموس
                mapped_data = self._map_row_data(headers, row_data)
                sheet_row_number = row_index

                # التحقق من وجود البيانات الأساسية
                customer_name = mapped_data.get('customer_name', '').strip()
                customer_phone = mapped_data.get('customer_phone', '').strip()
                invoice_number = mapped_data.get('invoice_number', '').strip()

                if not customer_name or not customer_phone:
                    self.stats['warnings'].append(f"الصف {sheet_row_number}: اسم العميل أو رقم الهاتف مفقود")
                    continue

                # التحقق من رقم الفاتورة أو رقم الطلب (أحدهما مطلوب)
                order_number = mapped_data.get('order_number', '').strip()
                if not invoice_number and not order_number:
                    self.stats['errors'].append(f"الصف {sheet_row_number}: رقم الفاتورة أو رقم الطلب مطلوب")
                    self.stats['failed_rows'] += 1
                    continue
                
                # إنشاء رقم فاتورة افتراضي إذا لم يوجد
                if not invoice_number and order_number:
                    invoice_number = f"INV-{order_number}"
                    mapped_data['invoice_number'] = invoice_number
                    logger.info(f"الصف {sheet_row_number}: تم إنشاء رقم فاتورة افتراضي: {invoice_number}")

                # معالجة العميل
                customer_key = (customer_name, customer_phone)
                customer = customer_cache.get(customer_key)
                if not customer:
                    customer = self._process_customer(mapped_data, sheet_row_number, task)
                    if customer:
                        customer_cache[customer_key] = customer

                if not customer:
                    self.stats['errors'].append(f"الصف {sheet_row_number}: فشل في إنشاء أو العثور على العميل")
                    self.stats['failed_rows'] += 1
                    continue

                # معالجة الطلب (كل صف = طلب حسب المتطلبات الجديدة)
                order_key = f"invoice_{invoice_number}" if invoice_number else f"order_{order_number}"
                if order_key in imported_orders:
                    self.stats['warnings'].append(f"الصف {sheet_row_number}: طلب مكرر بالمفتاح {order_key}")
                    continue

                # البحث عن الطلب الموجود (أولاً برقم الطلب إذا كان متوفراً، ثم برقم الفاتورة)
                order = None
                if order_number:
                    order = Order.objects.filter(order_number=order_number).first()
                    logger.info(f"الصف {sheet_row_number}: البحث برقم الطلب {order_number} - النتيجة: {'موجود' if order else 'غير موجود'}")
                
                if not order and invoice_number:
                    order = Order.objects.filter(invoice_number=invoice_number).first()
                    logger.info(f"الصف {sheet_row_number}: البحث برقم الفاتورة {invoice_number} - النتيجة: {'موجود' if order else 'غير موجود'}")
                
                if not order:
                    # إنشاء طلب جديد
                    order = self._create_order(mapped_data, customer)
                    if order:
                        imported_orders.add(order_key)
                        self.stats['orders_created'] += 1
                        logger.info(f"تم إنشاء طلب جديد: رقم الفاتورة {invoice_number}")
                else:
                    # تحديث الطلب الموجود إذا كان مفعل
                    if self.mapping.update_existing:
                        self._update_order(order, mapped_data, customer)
                        self.stats['orders_updated'] += 1
                    imported_orders.add(order_key)

                # معالجة المعاينة (شروط صارمة: فقط عند وجود تاريخ صحيح)
                inspection_date = mapped_data.get('inspection_date', '').strip()
                
                # التحقق من صحة تاريخ المعاينة
                valid_inspection_date = None
                if inspection_date:
                    try:
                        valid_inspection_date = datetime.strptime(inspection_date, '%Y-%m-%d').date()
                        logger.info(f"الصف {sheet_row_number}: تاريخ معاينة صحيح: {valid_inspection_date}")
                    except ValueError:
                        try:
                            # محاولة تنسيقات تاريخ أخرى
                            valid_inspection_date = datetime.strptime(inspection_date, '%d/%m/%Y').date()
                            logger.info(f"الصف {sheet_row_number}: تاريخ معاينة صحيح (تنسيق مختلف): {valid_inspection_date}")
                        except ValueError:
                            logger.warning(f"الصف {sheet_row_number}: تاريخ معاينة غير صحيح: {inspection_date}")
                            valid_inspection_date = None
                
                # إنشاء المعاينة فقط عند وجود تاريخ صحيح
                if self.mapping.auto_create_inspections and order and valid_inspection_date:
                    # مفتاح المعاينة لمنع التكرار
                    inspection_key = f"order_{order.id}"
                    if inspection_key not in imported_inspections:
                        # التحقق من عدم وجود معاينة لنفس الطلب
                        existing_inspection = Inspection.objects.filter(order=order).first()
                        
                        if not existing_inspection:
                            # تمرير التاريخ الصحيح المحقق مسبقاً
                            inspection = self._process_inspection(mapped_data, customer, order, sheet_row_number, task, valid_inspection_date)
                            if inspection:
                                imported_inspections.add(inspection_key)
                                self.stats['inspections_created'] += 1
                                logger.info(f"تم إنشاء معاينة جديدة للطلب رقم {invoice_number} بتاريخ {valid_inspection_date}")
                        else:
                            # تحديث المعاينة الموجودة إذا كان مفعل
                            if self.mapping.update_existing:
                                self._update_inspection(existing_inspection, mapped_data)
                                imported_inspections.add(inspection_key)

                # معالجة التركيب إذا كان مفعل
                if self.mapping.auto_create_installations and order:
                    self._process_installation(mapped_data, customer, order, sheet_row_number, task)

                self.stats['processed_rows'] += 1
                self.stats['successful_rows'] += 1

            except Exception as e:
                self.stats['failed_rows'] += 1
                self.stats['errors'].append(f"خطأ في الصف {sheet_row_number}: {str(e)}")
                logger.error(f"خطأ في معالجة الصف {sheet_row_number}: {str(e)}")

    def _get_sheet_data(self) -> List[List[str]]:
        """جلب البيانات من Google Sheets"""
        try:
            return self.importer.get_sheet_data(self.mapping.sheet_name)
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات من Google Sheets: {str(e)}", exc_info=True)
            raise

    def _map_row_data(self, headers: List[str], row_data: List[str]) -> Dict[str, str]:
        """تحويل بيانات الصف إلى قاموس حسب التعيينات"""
        mapped_data = {}
        column_mappings = self.mapping.get_column_mappings()
        
        for i, header in enumerate(headers):
            if i < len(row_data) and header in column_mappings:
                field_type = column_mappings[header]
                if field_type != 'ignore':
                    mapped_data[field_type] = row_data[i].strip() if row_data[i] else ''
        
        return mapped_data

    def _process_customer(self, mapped_data: Dict[str, str], row_index: int, task: GoogleSyncTask) -> Optional[Customer]:
        """معالجة بيانات العميل"""
        try:
            customer_name = mapped_data.get('customer_name', '').strip()
            customer_phone = mapped_data.get('customer_phone', '').strip()
            
            if not customer_name or not customer_phone:
                return None

            # البحث عن العميل الموجود (أولاً بالكود إذا كان متوفراً، ثم بالهاتف)
            customer_code = mapped_data.get('customer_code', '').strip()
            if customer_code:
                customer = Customer.objects.filter(code=customer_code).first()
            else:
                customer = Customer.objects.filter(phone=customer_phone).first()
            
            if customer:
                # تحديث العميل الموجود إذا كان مفعل
                if self.mapping.update_existing:
                    self._update_customer(customer, mapped_data)
                    self.stats['customers_updated'] += 1
            else:
                # إنشاء عميل جديد
                if self.mapping.auto_create_customers:
                    customer = self._create_customer(mapped_data)
                    if customer:
                        self.stats['customers_created'] += 1
                        
            return customer
            
        except Exception as e:
            self.stats['errors'].append(f"خطأ في معالجة العميل في الصف {row_index}: {str(e)}")
            raise

    def _create_customer(self, mapped_data: Dict[str, str]) -> Customer:
        """إنشاء عميل جديد"""
        customer_data = {
            'name': mapped_data.get('customer_name', ''),
            'phone': mapped_data.get('customer_phone', ''),
            'phone2': mapped_data.get('customer_phone2', ''),
            'email': mapped_data.get('customer_email', ''),
            'address': mapped_data.get('customer_address', ''),
        }

        # إضافة الإعدادات الافتراضية (إذا كانت موجودة في mapping)
        if hasattr(self.mapping, 'default_customer_category') and self.mapping.default_customer_category:
            customer_data['category'] = self.mapping.default_customer_category
        if hasattr(self.mapping, 'default_customer_type') and self.mapping.default_customer_type:
            customer_data['customer_type'] = self.mapping.default_customer_type
        if hasattr(self.mapping, 'default_branch') and self.mapping.default_branch:
            customer_data['branch'] = self.mapping.default_branch

        # استخدام كود العميل من البيانات إذا كان متوفر
        customer_code = mapped_data.get('customer_code', '').strip()
        if customer_code:
            customer_data['code'] = customer_code

        try:
            return Customer.objects.create(**customer_data)
        except IntegrityError as e:
            raise Exception(f"فشل إنشاء عميل جديد: {str(e)}")

    def _update_customer(self, customer: Customer, mapped_data: Dict[str, str]):
        """تحديث بيانات العميل الموجود"""
        updated = False
        
        # تحديث البيانات
        fields_to_update = ['name', 'phone2', 'email', 'address']
        mapping_fields = ['customer_name', 'customer_phone2', 'customer_email', 'customer_address']
        
        for customer_field, mapping_field in zip(fields_to_update, mapping_fields):
            new_value = mapped_data.get(mapping_field, '').strip()
            if new_value and getattr(customer, customer_field) != new_value:
                setattr(customer, customer_field, new_value)
                updated = True
        
        if updated:
            customer.save()

    def _create_order(self, mapped_data: Dict[str, str], customer: Customer) -> Order:
        """إنشاء طلب جديد"""
        logger.info(f"[CREATE_ORDER] محاولة إنشاء طلب للعميل: {customer.name}")
        logger.info(f"[CREATE_ORDER] البيانات المتاحة: {mapped_data}")
        
        order_data = {
            'customer': customer,
            'invoice_number': mapped_data.get('invoice_number', ''),
            'contract_number': mapped_data.get('contract_number', ''),
            'notes': mapped_data.get('notes', ''),
            'status': 'normal',  # حالة افتراضية  
            'tracking_status': 'pending',  # حالة التتبع الافتراضية
        }

        # تحديد نوع الطلب (سيتم إنشاء ExtendedOrder منفصل لاحقاً)
        order_type = mapped_data.get('order_type', 'fabric').lower()

        # تاريخ الطلب
        order_date = mapped_data.get('order_date', '')
        if order_date:
            try:
                order_data['order_date'] = datetime.strptime(order_date, '%Y-%m-%d').date()
            except ValueError:
                order_data['order_date'] = timezone.now().date()
        else:
            order_data['order_date'] = timezone.now().date()

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

        # استخدام رقم الطلب من البيانات إذا كان متوفراً
        order_number = mapped_data.get('order_number', '').strip()
        if order_number:
            order_data['order_number'] = order_number

        logger.info(f"[CREATE_ORDER] بيانات الطلب النهائية: {order_data}")
        
        try:
            order = Order.objects.create(**order_data)
            logger.info(f"[CREATE_ORDER] تم إنشاء الطلب بنجاح: {order.order_number if hasattr(order, 'order_number') else 'N/A'}")
            
            # إنشاء ExtendedOrder للمعلومات الإضافية
            self._create_extended_order(order, order_type, mapped_data)
            
            return order
        except IntegrityError as e:
            logger.error(f"[CREATE_ORDER] خطأ IntegrityError: {str(e)}")
            logger.error(f"[CREATE_ORDER] بيانات الطلب: {order_data}")
            raise Exception(f"فشل إنشاء طلب جديد: {str(e)}")
        except Exception as e:
            logger.error(f"[CREATE_ORDER] خطأ عام: {str(e)}")
            logger.error(f"[CREATE_ORDER] بيانات الطلب: {order_data}")
            raise Exception(f"فشل إنشاء طلب جديد: {str(e)}")

    def _create_extended_order(self, order: Order, order_type: str, mapped_data: Dict[str, str]):
        """إنشاء معلومات إضافية للطلب (ExtendedOrder)"""
        try:
            # تحديد نوع الطلب الرئيسي وأنواعه الفرعية
            if order_type in ['fabric', 'accessories']:
                order_type_main = 'goods'
                goods_type = order_type
                service_type = None
            else:
                order_type_main = 'services' 
                goods_type = None
                service_type = order_type

            extended_data = {
                'order': order,
                'order_type': order_type_main,
                'goods_type': goods_type,
                'service_type': service_type,
            }

            # إضافة بيانات إضافية إذا كانت متوفرة
            additional_notes = mapped_data.get('additional_notes', '')
            if additional_notes:
                extended_data['additional_notes'] = additional_notes

            ExtendedOrder.objects.create(**extended_data)
            logger.info(f"[CREATE_EXTENDED_ORDER] تم إنشاء معلومات إضافية للطلب: {order_type}")
            
        except Exception as e:
            logger.warning(f"[CREATE_EXTENDED_ORDER] فشل في إنشاء معلومات إضافية: {str(e)}")
            # لا نرفع خطأ هنا لأن الطلب الأساسي تم إنشاؤه بنجاح

    def _update_order(self, order: Order, mapped_data: Dict[str, str], customer: Customer):
        """تحديث الطلب الموجود"""
        updated = False
        
        # تحديث حالة التتبع
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
            new_status = status_mapping.get(tracking_status, order.tracking_status)
            if new_status != order.tracking_status:
                order.tracking_status = new_status
                updated = True

        # تحديث المبالغ
        try:
            total_amount = mapped_data.get('total_amount')
            if total_amount and float(total_amount) != order.total_amount:
                order.total_amount = float(total_amount)
                updated = True
        except (ValueError, TypeError):
            pass

        try:
            paid_amount = mapped_data.get('paid_amount')
            if paid_amount and float(paid_amount) != order.paid_amount:
                order.paid_amount = float(paid_amount)
                updated = True
        except (ValueError, TypeError):
            pass

        # تحديث الملاحظات
        notes = mapped_data.get('notes', '')
        if notes and notes != order.notes:
            order.notes = notes
            updated = True

        if updated:
            order.save()

    def _process_inspection(self, mapped_data: Dict[str, str], customer: Customer, order: Order, row_index: int, task: GoogleSyncTask):
        """معالجة بيانات المعاينة مع رقم العقد"""
        try:
            inspection_data = {
                'customer': customer,
                'order': order,
                'branch': customer.branch or order.branch,
                'request_date': timezone.now().date(),
                'scheduled_date': timezone.now().date() + timedelta(days=1),
                'notes': mapped_data.get('notes', ''),
                'contract_number': mapped_data.get('contract_number', ''),  # رقم العقد من الجدول
            }

            # تاريخ المعاينة
            inspection_date = mapped_data.get('inspection_date', '')
            if inspection_date:
                try:
                    parsed_date = datetime.strptime(inspection_date, '%Y-%m-%d').date()
                    inspection_data['scheduled_date'] = parsed_date
                    inspection_data['request_date'] = parsed_date - timedelta(days=1)  # تاريخ الطلب قبل يوم
                except ValueError:
                    pass

            # نتيجة المعاينة
            inspection_result = mapped_data.get('inspection_result', '')
            if inspection_result:
                result_mapping = {
                    'مقبول': 'approved',
                    'مرفوض': 'rejected',
                    'يحتاج مراجعة': 'pending',
                }
                inspection_data['result'] = result_mapping.get(inspection_result, 'pending')

            # عدد الشبابيك
            windows_count = mapped_data.get('windows_count', '')
            if windows_count:
                try:
                    inspection_data['windows_count'] = int(windows_count)
                except (ValueError, TypeError):
                    pass

            # توليد كود المعاينة (حسب نظام التكويد)
            if hasattr(Inspection, "generate_code") and callable(getattr(Inspection, "generate_code")):
                inspection_data['code'] = Inspection.generate_code()

            inspection = Inspection.objects.create(**inspection_data)
            return inspection
            
        except Exception as e:
            self.stats['errors'].append(f"خطأ في معالجة المعاينة في الصف {row_index}: {str(e)}")
            raise

    def _update_inspection(self, inspection: Inspection, mapped_data: Dict[str, str]):
        """تحديث بيانات المعاينة الموجودة"""
        updated = False
        
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
                inspection.result = new_result
                updated = True
        
        # تحديث عدد الشبابيك
        windows_count = mapped_data.get('windows_count', '')
        if windows_count:
            try:
                new_count = int(windows_count)
                if hasattr(inspection, 'windows_count') and new_count != inspection.windows_count:
                    inspection.windows_count = new_count
                    updated = True
            except (ValueError, TypeError):
                pass
        
        # تحديث تاريخ المعاينة
        inspection_date = mapped_data.get('inspection_date', '')
        if inspection_date:
            try:
                parsed_date = datetime.strptime(inspection_date, '%Y-%m-%d').date()
                if hasattr(inspection, 'scheduled_date') and parsed_date != inspection.scheduled_date:
                    inspection.scheduled_date = parsed_date
                    updated = True
            except ValueError:
                pass
        
        # تحديث الملاحظات
        notes = mapped_data.get('notes', '')
        if notes and hasattr(inspection, 'notes') and notes != inspection.notes:
            inspection.notes = notes
            updated = True
        
        if updated:
            inspection.save()

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
            self.stats['installations_created'] += 1
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
