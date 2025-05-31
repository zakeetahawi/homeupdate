"""
وحدة مزامنة بيانات التطبيق مع Google Sheets
"""

import os
import json
import logging
import datetime
from pathlib import Path
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.db import connection
from django.apps import apps

# إعداد التسجيل
logger = logging.getLogger(__name__)

class GoogleSyncConfig(models.Model):
    """إعدادات مزامنة غوغل"""
    
    name = models.CharField(_('الاسم'), max_length=100)
    spreadsheet_id = models.CharField(_('معرف جدول البيانات'), max_length=255)
    credentials_file = models.FileField(_('ملف بيانات الاعتماد'), upload_to='google_credentials/')
    is_active = models.BooleanField(_('نشط'), default=True)
    last_sync = models.DateTimeField(_('آخر مزامنة'), null=True, blank=True)
    sync_frequency = models.IntegerField(_('تكرار المزامنة (بالساعات)'), default=24)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    # إعدادات المزامنة
    sync_databases = models.BooleanField(_('مزامنة قواعد البيانات'), default=True)
    sync_users = models.BooleanField(_('مزامنة المستخدمين'), default=True)
    sync_customers = models.BooleanField(_('مزامنة العملاء'), default=True)
    sync_orders = models.BooleanField(_('مزامنة الطلبات'), default=True)
    sync_products = models.BooleanField(_('مزامنة المنتجات'), default=True)
    sync_settings = models.BooleanField(_('مزامنة الإعدادات'), default=True)
    
    class Meta:
        verbose_name = _('إعداد مزامنة غوغل')
        verbose_name_plural = _('إعدادات مزامنة غوغل')
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_active_config(cls):
        """الحصول على الإعداد النشط"""
        return cls.objects.filter(is_active=True).first()
    
    def get_credentials(self):
        """الحصول على بيانات الاعتماد"""
        try:
            if not self.credentials_file:
                return None
            
            # قراءة ملف بيانات الاعتماد
            with open(self.credentials_file.path, 'r') as f:
                credentials = json.load(f)
            
            return credentials
        except Exception as e:
            logger.error(f"حدث خطأ أثناء قراءة بيانات الاعتماد: {str(e)}")
            return None
    
    def is_sync_due(self):
        """التحقق مما إذا كان وقت المزامنة قد حان"""
        if not self.last_sync:
            return True
        
        # حساب الوقت المنقضي منذ آخر مزامنة
        elapsed_time = timezone.now() - self.last_sync
        elapsed_hours = elapsed_time.total_seconds() / 3600
        
        # التحقق مما إذا كان الوقت المنقضي أكبر من تكرار المزامنة
        return elapsed_hours >= self.sync_frequency
    
    def update_last_sync(self):
        """تحديث وقت آخر مزامنة"""
        self.last_sync = timezone.now()
        self.save()


class GoogleSyncLog(models.Model):
    """سجل مزامنة غوغل"""
    
    STATUS_CHOICES = [
        ('success', _('نجاح')),
        ('error', _('خطأ')),
        ('warning', _('تحذير')),
    ]
    
    config = models.ForeignKey(GoogleSyncConfig, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(_('الرسالة'))
    details = models.JSONField(_('التفاصيل'), default=dict, blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل مزامنة غوغل')
        verbose_name_plural = _('سجلات مزامنة غوغل')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_status_display()} - {self.created_at}"


def sync_with_google_sheets(config_id=None, manual=False):
    """
    مزامنة بيانات التطبيق مع Google Sheets
    
    Args:
        config_id: معرف إعداد المزامنة (اختياري)
        manual: ما إذا كانت المزامنة يدوية أم تلقائية
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        # الحصول على إعداد المزامنة
        if config_id:
            config = GoogleSyncConfig.objects.get(id=config_id)
        else:
            config = GoogleSyncConfig.get_active_config()
        
        if not config:
            message = "لا يوجد إعداد مزامنة نشط"
            logger.error(message)
            return {'status': 'error', 'message': message}
        
        # التحقق مما إذا كان وقت المزامنة قد حان (للمزامنة التلقائية فقط)
        if not manual and not config.is_sync_due():
            message = f"لم يحن وقت المزامنة بعد. آخر مزامنة: {config.last_sync}"
            logger.info(message)
            return {'status': 'info', 'message': message}
        
        # الحصول على بيانات الاعتماد
        credentials = config.get_credentials()
        if not credentials:
            message = "لا يمكن قراءة بيانات الاعتماد"
            logger.error(message)
            
            # تسجيل الخطأ
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            
            return {'status': 'error', 'message': message}
        
        # إنشاء خدمة Google Sheets
        sheets_service = create_sheets_service(credentials)
        if not sheets_service:
            message = "فشل إنشاء خدمة Google Sheets"
            logger.error(message)
            
            # تسجيل الخطأ
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            
            return {'status': 'error', 'message': message}
        
        # مزامنة البيانات
        sync_results = {}
        
        # مزامنة قواعد البيانات
        if config.sync_databases:
            db_result = sync_databases(sheets_service, config.spreadsheet_id)
            sync_results['databases'] = db_result
        
        # مزامنة المستخدمين
        if config.sync_users:
            users_result = sync_users(sheets_service, config.spreadsheet_id)
            sync_results['users'] = users_result
        
        # مزامنة العملاء
        if config.sync_customers:
            customers_result = sync_customers(sheets_service, config.spreadsheet_id)
            sync_results['customers'] = customers_result
        
        # مزامنة الطلبات
        if config.sync_orders:
            orders_result = sync_orders(sheets_service, config.spreadsheet_id)
            sync_results['orders'] = orders_result
        
        # مزامنة المنتجات
        if config.sync_products:
            products_result = sync_products(sheets_service, config.spreadsheet_id)
            sync_results['products'] = products_result
        
        # مزامنة الإعدادات
        if config.sync_settings:
            settings_result = sync_settings(sheets_service, config.spreadsheet_id)
            sync_results['settings'] = settings_result
        
        # تحديث وقت آخر مزامنة
        config.update_last_sync()
        
        # تسجيل نجاح المزامنة
        GoogleSyncLog.objects.create(
            config=config,
            status='success',
            message="تمت المزامنة بنجاح",
            details=sync_results
        )
        
        message = "تمت المزامنة مع Google Sheets بنجاح"
        logger.info(message)
        return {'status': 'success', 'message': message, 'results': sync_results}
    
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة مع Google Sheets: {str(e)}"
        logger.error(message)
        
        # تسجيل الخطأ
        if 'config' in locals():
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
        
        return {'status': 'error', 'message': message}


def create_sheets_service(credentials):
    """
    إنشاء خدمة Google Sheets
    
    Args:
        credentials: بيانات الاعتماد
    
    Returns:
        service: خدمة Google Sheets
    """
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google.oauth2 import service_account
        import json
        
        # التحقق من نوع بيانات الاعتماد
        if isinstance(credentials, dict):
            # إذا كانت بيانات الاعتماد هي قاموس، فقد تكون بيانات اعتماد OAuth أو بيانات اعتماد حساب الخدمة
            if 'type' in credentials and credentials['type'] == 'service_account':
                # بيانات اعتماد حساب الخدمة
                creds = service_account.Credentials.from_service_account_info(
                    credentials,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                # بيانات اعتماد OAuth
                creds = Credentials.from_authorized_user_info(
                    credentials,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
        elif isinstance(credentials, str):
            # إذا كانت بيانات الاعتماد هي سلسلة نصية، فقد تكون مسار ملف أو سلسلة JSON
            try:
                # محاولة تحليل السلسلة كـ JSON
                creds_dict = json.loads(credentials)
                if 'type' in creds_dict and creds_dict['type'] == 'service_account':
                    creds = service_account.Credentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                else:
                    creds = Credentials.from_authorized_user_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
            except json.JSONDecodeError:
                # قد تكون مسار ملف
                if credentials.endswith('.json'):
                    creds = service_account.Credentials.from_service_account_file(
                        credentials,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                else:
                    raise ValueError("تنسيق بيانات الاعتماد غير صالح")
        else:
            raise ValueError("نوع بيانات الاعتماد غير مدعوم")
        
        # إنشاء خدمة Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        
        return service
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إنشاء خدمة Google Sheets: {str(e)}")
        return None


def sync_databases(service, spreadsheet_id):
    """
    مزامنة قواعد البيانات مع Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        from odoo_db_manager.models import Database
        
        # الحصول على قواعد البيانات
        databases = Database.objects.all()
        
        # تحويل قواعد البيانات إلى قائمة
        data = [['معرف', 'الاسم', 'النوع', 'نشطة', 'تاريخ الإنشاء', 'تاريخ التحديث', 'معلومات الاتصال']]
        
        for db in databases:
            data.append([
                str(db.id),
                db.name,
                db.get_db_type_display(),
                'نعم' if db.is_active else 'لا',
                db.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                db.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                json.dumps(db.connection_info)
            ])
        
        # تحديث ورقة العمل
        sheet_name = 'قواعد البيانات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        
        return {'status': 'success', 'message': f"تمت مزامنة {len(databases)} قاعدة بيانات"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة قواعد البيانات: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_users(service, spreadsheet_id):
    """
    مزامنة المستخدمين مع Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        # الحصول على نموذج المستخدم
        User = apps.get_model('accounts', 'User')
        
        # الحصول على المستخدمين
        users = User.objects.all()
        
        # تحويل المستخدمين إلى قائمة
        data = [['معرف', 'اسم المستخدم', 'البريد الإلكتروني', 'الاسم الأول', 'الاسم الأخير', 'نشط', 'مشرف', 'تاريخ الانضمام']]
        
        for user in users:
            data.append([
                str(user.id),
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                'نعم' if user.is_active else 'لا',
                'نعم' if user.is_staff else 'لا',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # تحديث ورقة العمل
        sheet_name = 'المستخدمين'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        
        return {'status': 'success', 'message': f"تمت مزامنة {len(users)} مستخدم"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة المستخدمين: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_customers(service, spreadsheet_id):
    """
    مزامنة العملاء مع Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        # الحصول على نموذج العميل
        Customer = apps.get_model('customers', 'Customer')
        
        # الحصول على العملاء
        customers = Customer.objects.all()
        
        # تحويل العملاء إلى قائمة
        data = [['معرف', 'الاسم', 'رقم الهاتف', 'البريد الإلكتروني', 'العنوان', 'تاريخ الإنشاء']]
        
        for customer in customers:
            data.append([
                str(customer.id),
                customer.name,
                customer.phone,
                customer.email,
                customer.address,
                customer.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # تحديث ورقة العمل
        sheet_name = 'العملاء'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        
        return {'status': 'success', 'message': f"تمت مزامنة {len(customers)} عميل"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة العملاء: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_orders(service, spreadsheet_id):
    """
    مزامنة الطلبات مع Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        # الحصول على نموذج الطلب
        Order = apps.get_model('orders', 'Order')
        
        # الحصول على الطلبات
        orders = Order.objects.all()
        
        # تحويل الطلبات إلى قائمة
        data = [['معرف', 'العميل', 'الحالة', 'المبلغ الإجمالي', 'تاريخ الإنشاء']]
        
        for order in orders:
            data.append([
                str(order.id),
                order.customer.name if order.customer else '',
                order.get_status_display(),
                str(order.total_amount),
                order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # تحديث ورقة العمل
        sheet_name = 'الطلبات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        
        return {'status': 'success', 'message': f"تمت مزامنة {len(orders)} طلب"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة الطلبات: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_products(service, spreadsheet_id):
    """
    مزامنة المنتجات مع Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        # الحصول على نموذج المنتج
        Product = apps.get_model('inventory', 'Product')
        
        # الحصول على المنتجات
        products = Product.objects.all()
        
        # تحويل المنتجات إلى قائمة
        data = [['معرف', 'الاسم', 'الوصف', 'السعر', 'الكمية', 'تاريخ الإنشاء']]
        
        for product in products:
            data.append([
                str(product.id),
                product.name,
                product.description,
                str(product.price),
                str(product.quantity),
                product.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # تحديث ورقة العمل
        sheet_name = 'المنتجات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        
        return {'status': 'success', 'message': f"تمت مزامنة {len(products)} منتج"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة المنتجات: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_settings(service, spreadsheet_id):
    """
    مزامنة الإعدادات مع Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
    
    Returns:
        dict: نتيجة المزامنة
    """
    try:
        # الحصول على نموذج الإعدادات
        Setting = apps.get_model('accounts', 'Setting')
        
        # الحصول على الإعدادات
        settings = Setting.objects.all()
        
        # تحويل الإعدادات إلى قائمة
        data = [['معرف', 'المفتاح', 'القيمة', 'الوصف', 'تاريخ التحديث']]
        
        for setting in settings:
            data.append([
                str(setting.id),
                setting.key,
                setting.value,
                setting.description,
                setting.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # تحديث ورقة العمل
        sheet_name = 'الإعدادات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        
        return {'status': 'success', 'message': f"تمت مزامنة {len(settings)} إعداد"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة الإعدادات: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def update_sheet(service, spreadsheet_id, sheet_name, data):
    """
    تحديث ورقة عمل في Google Sheets
    
    Args:
        service: خدمة Google Sheets
        spreadsheet_id: معرف جدول البيانات
        sheet_name: اسم ورقة العمل
        data: البيانات
    
    Returns:
        dict: نتيجة التحديث
    """
    try:
        # التحقق من وجود ورقة العمل
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        sheet_exists = False
        sheet_id = None
        
        for sheet in sheets:
            if sheet.get('properties', {}).get('title') == sheet_name:
                sheet_exists = True
                sheet_id = sheet.get('properties', {}).get('sheetId')
                break
        
        # إنشاء ورقة العمل إذا لم تكن موجودة
        if not sheet_exists:
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            response = service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [request]}
            ).execute()
            
            sheet_id = response.get('replies', [])[0].get('addSheet', {}).get('properties', {}).get('sheetId')
        
        # تحديث البيانات
        range_name = f"{sheet_name}!A1"
        body = {
            'values': data
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        # تنسيق الورقة
        if sheet_id:
            try:
                requests = [
                    # تنسيق الصف الأول (العناوين)
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 0,
                                'endRowIndex': 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': 0.0,
                                        'green': 0.4,
                                        'blue': 0.7
                                    },
                                    'textFormat': {
                                        'foregroundColor': {
                                            'red': 1.0,
                                            'green': 1.0,
                                            'blue': 1.0
                                        },
                                        'bold': True
                                    },
                                    'horizontalAlignment': 'CENTER',
                                    'verticalAlignment': 'MIDDLE'
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)'
                        }
                    },
                    # تنسيق الخلايا
                    {
                        'updateSheetProperties': {
                            'properties': {
                                'sheetId': sheet_id,
                                'gridProperties': {
                                    'frozenRowCount': 1
                                }
                            },
                            'fields': 'gridProperties.frozenRowCount'
                        }
                    }
                ]
                
                # إضافة طلب تعديل حجم الأعمدة فقط إذا كانت البيانات تحتوي على صفوف
                if data and len(data) > 0 and len(data[0]) > 0:
                    requests.append({
                        'autoResizeDimensions': {
                            'dimensions': {
                                'sheetId': sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': len(data[0])
                            }
                        }
                    })
                
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
            except Exception as format_error:
                # تسجيل خطأ التنسيق ولكن لا نتوقف عن العملية
                logger.warning(f"حدث خطأ أثناء تنسيق ورقة العمل: {str(format_error)}")
        
        return {'status': 'success', 'message': f"تم تحديث {result.get('updatedCells')} خلية"}
    
    except Exception as e:
        message = f"حدث خطأ أثناء تحديث ورقة العمل: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}