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
    
    # إعدادات المزامنة الأساسية
    sync_databases = models.BooleanField(_('مزامنة قواعد البيانات'), default=True)
    sync_users = models.BooleanField(_('مزامنة المستخدمين'), default=True)
    sync_customers = models.BooleanField(_('مزامنة العملاء'), default=True)
    sync_orders = models.BooleanField(_('مزامنة الطلبات'), default=True)
    sync_products = models.BooleanField(_('مزامنة المنتجات'), default=True)
    sync_settings = models.BooleanField(_('مزامنة الإعدادات'), default=True)
    sync_inspections = models.BooleanField(_('مزامنة المعاينات'), default=True)

    # إعدادات المزامنة الجديدة
    sync_manufacturing_orders = models.BooleanField(_('مزامنة أوامر التصنيع'), default=True)
    sync_technicians = models.BooleanField(_('مزامنة الفنيين'), default=True)
    sync_installation_teams = models.BooleanField(_('مزامنة فرق التركيب'), default=True)
    sync_suppliers = models.BooleanField(_('مزامنة الموردين'), default=True)
    sync_salespersons = models.BooleanField(_('مزامنة البائعين'), default=True)

    # إعدادات المزامنة الشاملة
    sync_comprehensive_customers = models.BooleanField(_('مزامنة العملاء الشاملة'), default=False)
    sync_comprehensive_users = models.BooleanField(_('مزامنة المستخدمين الشاملة'), default=False)
    sync_comprehensive_inventory = models.BooleanField(_('مزامنة المنتجات والمخزون الشاملة'), default=False)
    sync_comprehensive_system = models.BooleanField(_('مزامنة إعدادات النظام الشاملة'), default=False)
    
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
                logger.error("لم يتم تحميل ملف بيانات الاعتماد")
                return None

            file_path = self.credentials_file.path
            if not os.path.exists(file_path):
                logger.error(f"ملف بيانات الاعتماد غير موجود في المسار: {file_path}")
                return None
            
            try:
                # قراءة ملف بيانات الاعتماد
                with open(file_path, 'r', encoding='utf-8') as f:
                    credentials_raw = f.read()
                try:
                    credentials = json.loads(credentials_raw)
                except Exception:
                    credentials = credentials_raw  # fallback to raw string

                # إذا بقي نص، حاول تحويله إلى dict
                if isinstance(credentials, str):
                    try:
                        credentials = json.loads(credentials)
                    except Exception:
                        logger.error("ملف بيانات الاعتماد ليس بالتنسيق المتوقع (نص غير قابل للتحويل)")
                        return None

                # التحقق من نوع بيانات الاعتماد
                if not isinstance(credentials, dict):
                    logger.error("ملف بيانات الاعتماد ليس بالتنسيق المتوقع")
                    return None

                if credentials.get('type') != 'service_account':
                    logger.error("نوع بيانات الاعتماد غير صحيح - يجب أن يكون حساب خدمة")
                    return None

                # التحقق من وجود الحقول المطلوبة
                required_fields = ['client_email', 'private_key', 'project_id']
                missing_fields = [field for field in required_fields if field not in credentials]
                if missing_fields:
                    logger.error(f"حقول مفقودة في ملف بيانات الاعتماد: {', '.join(missing_fields)}")
                    return None

                return credentials

            except json.JSONDecodeError as e:
                logger.error(f"فشل تحليل ملف بيانات الاعتماد كـ JSON: {str(e)}")
                return None
                
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


def sync_with_google_sheets(config_id=None, manual=False, full_backup=False, selected_tables=None):
    """
    مزامنة بيانات التطبيق مع Google Sheets
    Args:
        config_id: معرف إعداد المزامنة (اختياري)
        manual: ما إذا كانت المزامنة يدوية أم تلقائية
        full_backup: إذا True يتم مزامنة كل الجداول دفعة واحدة (نسخة احتياطية شاملة)
        selected_tables: قائمة بأسماء الجداول المطلوب مزامنتها فقط (تلغي full_backup إذا تم تحديدها)
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

        # التحقق من حالة المزامنة التلقائية
        if not manual and not config.is_sync_due():
            message = f"لم يحن وقت المزامنة بعد. آخر مزامنة: {config.last_sync}"
            logger.info(message)
            return {'status': 'info', 'message': message}
        
        # الحصول على بيانات الاعتماد
        credentials = config.get_credentials()
        if not credentials:
            message = "فشل قراءة بيانات الاعتماد. تأكد من تحميل ملف اعتماد حساب خدمة صالح."
            logger.error(message)
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            return {'status': 'error', 'message': message}
        
        # إنشاء خدمة Google Sheets
        sheets_service = create_sheets_service(credentials)
        if not sheets_service:
            message = f"فشل الاتصال بـ Google Sheets. تأكد من صحة بيانات الاعتماد ومشاركة جدول البيانات مع البريد: {credentials.get('client_email', 'غير معروف')}"
            logger.error(message)
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            return {'status': 'error', 'message': message}
        
        try:
            # التحقق من الوصول إلى جدول البيانات
            sheets_service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
        except Exception as e:
            message = f"فشل الوصول إلى جدول البيانات. تأكد من صحة المعرف ومشاركة الجدول مع حساب الخدمة."
            logger.error(f"{message}: {str(e)}")
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            return {'status': 'error', 'message': message}
        
        # مزامنة البيانات
        sync_results = {}

        # إذا تم تحديد جداول محددة، مزامنة فقط الجداول المختارة
        if selected_tables and isinstance(selected_tables, list) and len(selected_tables) > 0:
            if 'databases' in selected_tables:
                db_result = sync_databases(sheets_service, config.spreadsheet_id)
                sync_results['databases'] = db_result
            if 'users' in selected_tables:
                users_result = sync_users(sheets_service, config.spreadsheet_id)
                sync_results['users'] = users_result
            if 'customers' in selected_tables:
                customers_result = sync_customers(sheets_service, config.spreadsheet_id)
                sync_results['customers'] = customers_result
            if 'orders' in selected_tables:
                orders_result = sync_orders(sheets_service, config.spreadsheet_id)
                sync_results['orders'] = orders_result
            if 'products' in selected_tables:
                products_result = sync_products(sheets_service, config.spreadsheet_id)
                sync_results['products'] = products_result
            if 'inspections' in selected_tables:
                inspections_result = sync_inspections(sheets_service, config.spreadsheet_id)
                sync_results['inspections'] = inspections_result
            if 'settings' in selected_tables:
                settings_result = sync_settings(sheets_service, config.spreadsheet_id)
                sync_results['settings'] = settings_result
            if 'branches' in selected_tables:
                branches_result = sync_branches(sheets_service, config.spreadsheet_id)
                sync_results['branches'] = branches_result
            # الدوال الجديدة للمزامنة الشاملة
            if 'manufacturing_orders' in selected_tables:
                manufacturing_result = sync_manufacturing_orders(sheets_service, config.spreadsheet_id)
                sync_results['manufacturing_orders'] = manufacturing_result
            if 'technicians' in selected_tables:
                technicians_result = sync_technicians(sheets_service, config.spreadsheet_id)
                sync_results['technicians'] = technicians_result
            if 'installation_teams' in selected_tables:
                teams_result = sync_installation_teams(sheets_service, config.spreadsheet_id)
                sync_results['installation_teams'] = teams_result
            if 'suppliers' in selected_tables:
                suppliers_result = sync_suppliers(sheets_service, config.spreadsheet_id)
                sync_results['suppliers'] = suppliers_result
            if 'salespersons' in selected_tables:
                salespersons_result = sync_salespersons(sheets_service, config.spreadsheet_id)
                sync_results['salespersons'] = salespersons_result
            # المزامنة الشاملة
            if 'comprehensive_customers' in selected_tables:
                comp_customers_result = sync_comprehensive_customers(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_customers'] = comp_customers_result
            if 'comprehensive_users' in selected_tables:
                comp_users_result = sync_comprehensive_users(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_users'] = comp_users_result
            if 'comprehensive_inventory' in selected_tables:
                comp_inventory_result = sync_comprehensive_inventory(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_inventory'] = comp_inventory_result
            if 'comprehensive_system' in selected_tables:
                comp_system_result = sync_comprehensive_system_settings(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_system'] = comp_system_result

        # إذا لم يتم تحديد جداول، أو تم اختيار full_backup=True، مزامنة كل الجداول دفعة واحدة
        else:
            # الجداول الأساسية
            db_result = sync_databases(sheets_service, config.spreadsheet_id)
            sync_results['databases'] = db_result
            users_result = sync_users(sheets_service, config.spreadsheet_id)
            sync_results['users'] = users_result
            customers_result = sync_customers(sheets_service, config.spreadsheet_id)
            sync_results['customers'] = customers_result
            orders_result = sync_orders(sheets_service, config.spreadsheet_id)
            sync_results['orders'] = orders_result
            products_result = sync_products(sheets_service, config.spreadsheet_id)
            sync_results['products'] = products_result
            inspections_result = sync_inspections(sheets_service, config.spreadsheet_id)
            sync_results['inspections'] = inspections_result
            settings_result = sync_settings(sheets_service, config.spreadsheet_id)
            sync_results['settings'] = settings_result
            branches_result = sync_branches(sheets_service, config.spreadsheet_id)
            sync_results['branches'] = branches_result

            # الجداول الجديدة للمزامنة الشاملة
            manufacturing_result = sync_manufacturing_orders(sheets_service, config.spreadsheet_id)
            sync_results['manufacturing_orders'] = manufacturing_result
            technicians_result = sync_technicians(sheets_service, config.spreadsheet_id)
            sync_results['technicians'] = technicians_result
            teams_result = sync_installation_teams(sheets_service, config.spreadsheet_id)
            sync_results['installation_teams'] = teams_result
            suppliers_result = sync_suppliers(sheets_service, config.spreadsheet_id)
            sync_results['suppliers'] = suppliers_result
            salespersons_result = sync_salespersons(sheets_service, config.spreadsheet_id)
            sync_results['salespersons'] = salespersons_result

            # المزامنة الشاملة (اختيارية)
            if config.sync_comprehensive_customers:
                comp_customers_result = sync_comprehensive_customers(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_customers'] = comp_customers_result
            if config.sync_comprehensive_users:
                comp_users_result = sync_comprehensive_users(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_users'] = comp_users_result
            if config.sync_comprehensive_inventory:
                comp_inventory_result = sync_comprehensive_inventory(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_inventory'] = comp_inventory_result
            if config.sync_comprehensive_system:
                comp_system_result = sync_comprehensive_system_settings(sheets_service, config.spreadsheet_id)
                sync_results['comprehensive_system'] = comp_system_result

        # تحديث وقت آخر مزامنة
        config.update_last_sync()
        
        # تسجيل نجاح المزامنة
        message = "تمت المزامنة مع Google Sheets بنجاح"
        logger.info(message)
        GoogleSyncLog.objects.create(
            config=config,
            status='success',
            message=message,
            details=sync_results
        )
        
        return {'status': 'success', 'message': message, 'results': sync_results}
    
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة مع Google Sheets: {str(e)}"
        logger.error(message)
        
        if 'config' in locals():
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
        
        return {'status': 'error', 'message': message}

# ========== مزامنة جدول الفروع ==========
def sync_branches(service, spreadsheet_id):
    """
    مزامنة جدول الفروع مع Google Sheets مع جميع الحقول (حتى غير المعروضة في لوحة الإدارة)
    """
    try:
        Branch = apps.get_model('accounts', 'Branch')
        branches = Branch.objects.all()
        fields = [f.name for f in Branch._meta.get_fields() if not f.many_to_many and not f.one_to_many]
        header = []
        for f in fields:
            field_obj = Branch._meta.get_field(f)
            if field_obj.is_relation and hasattr(field_obj, 'related_model') and not field_obj.many_to_one and not field_obj.one_to_one:
                continue
            if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                header.append(f"{f}_display")
            else:
                header.append(f)
        data = [header]
        for branch in branches:
            row = []
            for f in fields:
                field_obj = Branch._meta.get_field(f)
                value = getattr(branch, f, '')
                if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                    if value:
                        if hasattr(value, 'name'):
                            row.append(str(value.name))
                        elif hasattr(value, 'get_full_name'):
                            row.append(str(value.get_full_name()))
                        else:
                            row.append(str(value))
                    else:
                        row.append('')
                else:
                    row.append(str(value) if value is not None else '')
            data.append(row)
        sheet_name = 'الفروع'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(branches)} فرع"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة الفروع: {str(e)}"
        logger.error(message)
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
        from google.oauth2 import service_account
        import json
        
        if not credentials:
            raise ValueError("لم يتم توفير بيانات الاعتماد")

        # التحقق من نوع بيانات الاعتماد
        if isinstance(credentials, dict):
            if credentials.get('type') != 'service_account':
                raise ValueError("بيانات الاعتماد ليست من نوع حساب الخدمة")

            # التحقق من وجود الحقول المطلوبة
            required_fields = ['client_email', 'private_key', 'project_id']
            missing_fields = [field for field in required_fields if field not in credentials]
            if missing_fields:
                raise ValueError(f"حقول مفقودة في بيانات الاعتماد: {', '.join(missing_fields)}")

            try:
                creds = service_account.Credentials.from_service_account_info(
                    credentials,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            except Exception as e:
                raise ValueError(f"فشل إنشاء بيانات الاعتماد من المعلومات المقدمة: {str(e)}")

        elif isinstance(credentials, str):
            if not os.path.exists(credentials):
                raise ValueError(f"ملف بيانات الاعتماد غير موجود: {credentials}")

            try:
                creds = service_account.Credentials.from_service_account_file(
                    credentials,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            except Exception as e:
                raise ValueError(f"فشل قراءة بيانات الاعتماد من الملف: {str(e)}")
        else:
            raise ValueError("نوع بيانات الاعتماد غير مدعوم")

        try:
            # إنشاء خدمة Google Sheets
            service = build('sheets', 'v4', credentials=creds)

            # اختبار الاتصال لتأكيد صحة بيانات الاعتماد
            service.spreadsheets().get(spreadsheetId='1').execute()
            
            return service

        except Exception as e:
            error_msg = str(e).lower()
            if 'not found' in error_msg:
                # هذا متوقع لأننا استخدمنا معرف غير موجود للاختبار
                return service
            elif 'permission' in error_msg:
                raise ValueError("تأكد من مشاركة جدول البيانات مع البريد الإلكتروني لحساب الخدمة")
            else:
                raise ValueError(f"فشل اختبار الاتصال: {str(e)}")

    except Exception as e:
        logger.error(f"حدث خطأ أثناء إنشاء خدمة Google Sheets: {str(e)}")
        return None


def sync_databases(service, spreadsheet_id):
    """
    مزامنة قواعد البيانات مع Google Sheets مع جميع الحقول (حتى غير المعروضة في لوحة الإدارة)
    """
    try:
        Database = apps.get_model('odoo_db_manager', 'Database')
        databases = Database.objects.all()
        fields = [f.name for f in Database._meta.get_fields() if not f.many_to_many and not f.one_to_many]
        header = []
        for f in fields:
            field_obj = Database._meta.get_field(f)
            if field_obj.is_relation and hasattr(field_obj, 'related_model') and not field_obj.many_to_one and not field_obj.one_to_one:
                continue
            if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                header.append(f"{f}_display")
            else:
                header.append(f)
        data = [header]
        for db in databases:
            row = []
            for f in fields:
                field_obj = Database._meta.get_field(f)
                value = getattr(db, f, '')
                if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                    if value:
                        if hasattr(value, 'name'):
                            row.append(str(value.name))
                        elif hasattr(value, 'get_full_name'):
                            row.append(str(value.get_full_name()))
                        else:
                            row.append(str(value))
                    else:
                        row.append('')
                else:
                    row.append(str(value) if value is not None else '')
            data.append(row)
        sheet_name = 'قواعد البيانات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(databases)} قاعدة بيانات"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة قواعد البيانات: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_users(service, spreadsheet_id):
    """
    مزامنة المستخدمين مع Google Sheets مع جميع الحقول (حتى غير المعروضة في لوحة الإدارة)
    """
    try:
        User = apps.get_model('accounts', 'User')
        users = User.objects.all()
        fields = [f.name for f in User._meta.get_fields() if not f.many_to_many and not f.one_to_many]
        header = []
        for f in fields:
            field_obj = User._meta.get_field(f)
            if field_obj.is_relation and hasattr(field_obj, 'related_model') and not field_obj.many_to_one and not field_obj.one_to_one:
                continue
            if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                header.append(f"{f}_display")
            else:
                header.append(f)
        data = [header]
        for user in users:
            row = []
            for f in fields:
                field_obj = User._meta.get_field(f)
                value = getattr(user, f, '')
                if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                    if value:
                        if hasattr(value, 'name'):
                            row.append(str(value.name))
                        elif hasattr(value, 'get_full_name'):
                            row.append(str(value.get_full_name()))
                        else:
                            row.append(str(value))
                    else:
                        row.append('')
                else:
                    row.append(str(value) if value is not None else '')
            data.append(row)
        sheet_name = 'المستخدمين'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(users)} مستخدم"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة المستخدمين: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_customers(service, spreadsheet_id):
    """
    مزامنة العملاء مع Google Sheets مع جميع الحقول (حتى غير المعروضة في لوحة الإدارة)
    """
    try:
        Customer = apps.get_model('customers', 'Customer')
        customers = Customer.objects.all()
        # استخراج جميع الحقول من الموديل ديناميكياً
        fields = [f.name for f in Customer._meta.get_fields() if not f.many_to_many and not f.one_to_many]
        # إضافة الحقول المرتبطة (عرض الاسم بدلاً من الـID)
        header = []
        for f in fields:
            field_obj = Customer._meta.get_field(f)
            if field_obj.is_relation and hasattr(field_obj, 'related_model') and not field_obj.many_to_one and not field_obj.one_to_one:
                continue  # تجاهل العلاقات many-to-many
            if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                header.append(f"{f}_display")
            else:
                header.append(f)
        data = [header]
        for customer in customers:
            row = []
            for f in fields:
                field_obj = Customer._meta.get_field(f)
                value = getattr(customer, f, '')
                if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                    # إذا كان الحقل علاقة، حاول جلب اسم العنصر المرتبط
                    if value:
                        if hasattr(value, 'name'):
                            row.append(str(value.name))
                        elif hasattr(value, 'get_full_name'):
                            row.append(str(value.get_full_name()))
                        else:
                            row.append(str(value))
                    else:
                        row.append('')
                else:
                    row.append(str(value) if value is not None else '')
            data.append(row)
        sheet_name = 'العملاء'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(customers)} عميل"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة العملاء: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_inspections(service, spreadsheet_id):
    """
    مزامنة جدول المعاينات مع Google Sheets مع جميع التفاصيل المطلوبة
    """
    try:
        logger.info("بدء مزامنة المعاينات")
        Inspection = apps.get_model('inspections', 'Inspection')
        inspections = Inspection.objects.all()
        data = [[
            'رقم العقد', 'رقم الطلب', 'نوع الطلب', 'العميل', 'تاريخ الطلب', 'تاريخ التنفيذ', 'عدد الشبابيك', 'فني المعاينة', 'البائع', 'ملف المعاينة', 'رابط ملف جوجل درايف', 'اسم ملف جوجل درايف', 'الحالة', 'النتيجة', 'الإجراءات'
        ]]
        count = 0
        for inspection in inspections:
            file_link = inspection.google_drive_file_url if getattr(inspection, 'google_drive_file_url', None) else ''
            order_number = str(getattr(inspection, 'order_id', ''))
            order_type = 'معاينة'
            customer_name = inspection.customer.name if inspection.customer else ''
            request_date = inspection.request_date.strftime('%Y-%m-%d') if getattr(inspection, 'request_date', None) else ''
            scheduled_date = inspection.scheduled_date.strftime('%Y-%m-%d') if getattr(inspection, 'scheduled_date', None) else ''
            windows_count = inspection.windows_count if getattr(inspection, 'windows_count', None) is not None else ''
            inspector_name = ''
            if hasattr(inspection, 'inspector') and inspection.inspector:
                inspector_name = getattr(inspection.inspector, 'name', str(inspection.inspector))
            responsible_employee_name = ''
            if hasattr(inspection, 'responsible_employee') and inspection.responsible_employee:
                responsible_employee_name = getattr(inspection.responsible_employee, 'name', str(inspection.responsible_employee))
            inspection_file_url = inspection.inspection_file.url if getattr(inspection, 'inspection_file', None) else ''
            google_drive_file_name = inspection.google_drive_file_name if getattr(inspection, 'google_drive_file_name', None) else ''
            status = inspection.status if getattr(inspection, 'status', None) else ''
            result = inspection.result if getattr(inspection, 'result', None) else ''
            notes = inspection.notes if getattr(inspection, 'notes', None) else ''
            data.append([
                str(inspection.id), order_number, order_type, customer_name, request_date, scheduled_date, windows_count,
                inspector_name, responsible_employee_name, inspection_file_url, file_link, google_drive_file_name, status, result, notes
            ])
            count += 1
        logger.info(f"بيانات المعاينات المرسلة إلى update_sheet: {data}")
        result = update_sheet(service, spreadsheet_id, 'المعاينات', data)
        logger.info("انتهت مزامنة المعاينات")
        return {'status': 'success', 'message': f"تمت مزامنة {result} معاينة"}
    except Exception as e:
        logger.error(f"حدث خطأ أثناء مزامنة المعاينات: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def sync_orders(service, spreadsheet_id):
    """
    مزامنة الطلبات مع Google Sheets مع ربطها بالعملاء وضمان عدم فقدان أي سجل
    """
    try:
        Order = apps.get_model('orders', 'Order')
        orders = Order.objects.select_related('customer', 'branch', 'salesperson').all()

        # تحديد العناوين المخصصة للطلبات مع ربط العملاء
        header = [
            'معرف الطلب', 'رقم الطلب', 'اسم العميل', 'رقم هاتف العميل', 'عنوان العميل',
            'نوع الطلب', 'حالة التتبع', 'حالة الطلب', 'الأولوية', 'الفرع', 'البائع',
            'المبلغ الإجمالي', 'المبلغ المدفوع', 'المبلغ المتبقي', 'تاريخ الطلب', 'تاريخ التسليم المتوقع',
            'نوع التسليم', 'عنوان التسليم', 'ملاحظات', 'تاريخ الإنشاء', 'تاريخ التحديث'
        ]

        data = [header]
        for order in orders:
            # التأكد من وجود العميل وعدم فقدان أي بيانات
            customer_name = order.customer.name if order.customer else 'عميل غير محدد'
            customer_phone = order.customer.phone if order.customer else ''
            customer_address = order.customer.address if order.customer else ''

            # حساب المبلغ المتبقي
            remaining_amount = (order.total_amount or 0) - (order.paid_amount or 0)

            row = [
                str(order.id),
                order.order_number or '',
                customer_name,
                customer_phone,
                customer_address,
                order.get_order_type_display() if order.order_type else '',
                order.get_tracking_status_display() if order.tracking_status else '',
                order.get_status_display() if hasattr(order, 'status') and order.status else '',
                order.get_priority_display() if hasattr(order, 'priority') and order.priority else '',
                order.branch.name if order.branch else '',
                order.salesperson.name if order.salesperson else '',
                str(order.total_amount) if order.total_amount else '0',
                str(order.paid_amount) if order.paid_amount else '0',
                str(remaining_amount),
                order.order_date.strftime('%Y-%m-%d') if order.order_date else '',
                order.expected_delivery_date.strftime('%Y-%m-%d') if hasattr(order, 'expected_delivery_date') and order.expected_delivery_date else '',
                order.get_delivery_type_display() if hasattr(order, 'delivery_type') and order.delivery_type else '',
                order.delivery_address if hasattr(order, 'delivery_address') and order.delivery_address else '',
                order.notes if hasattr(order, 'notes') and order.notes else '',
                order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                order.modified_at.strftime('%Y-%m-%d %H:%M') if hasattr(order, 'modified_at') and order.modified_at else ''
            ]
            data.append(row)

        sheet_name = 'الطلبات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(orders)} طلب مع ربطها بالعملاء"}
    except Exception as e:
        logger.error(f"حدث خطأ أثناء مزامنة الطلبات: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def sync_products(service, spreadsheet_id):
    """
    مزامنة المنتجات مع Google Sheets مع جميع الحقول (حتى غير المعروضة في لوحة الإدارة)
    ويضاف عمود "الكمية المتوفرة في المخزن" (available_quantity أو stock_quantity)
    """
    try:
        Product = apps.get_model('inventory', 'Product')
        products = Product.objects.all()
        fields = [f.name for f in Product._meta.get_fields() if not f.many_to_many and not f.one_to_many]
        # إضافة عمود الكمية المتوفرة إذا لم يكن موجوداً
        extra_col = None
        for possible in ['available_quantity', 'stock_quantity', 'quantity_available', 'qty_available']:
            if hasattr(Product, possible):
                extra_col = possible
                break
            # تحقق من أول عنصر
            if products and hasattr(products[0], possible):
                extra_col = possible
                break
        header = []
        for f in fields:
            field_obj = Product._meta.get_field(f)
            if field_obj.is_relation and hasattr(field_obj, 'related_model') and not field_obj.many_to_one and not field_obj.one_to_one:
                continue
            if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                header.append(f"{f}_display")
            else:
                header.append(f)
        if extra_col and extra_col not in header:
            header.append('الكمية المتوفرة')
        data = [header]
        for product in products:
            row = []
            for f in fields:
                field_obj = Product._meta.get_field(f)
                value = getattr(product, f, '')
                if field_obj.is_relation and hasattr(field_obj, 'related_model'):
                    if value:
                        if hasattr(value, 'name'):
                            row.append(str(value.name))
                        elif hasattr(value, 'get_full_name'):
                            row.append(str(value.get_full_name()))
                        else:
                            row.append(str(value))
                    else:
                        row.append('')
                else:
                    row.append(str(value) if value is not None else '')
            # أضف الكمية المتوفرة
            if extra_col:
                row.append(str(getattr(product, extra_col, '')))
            data.append(row)
        sheet_name = 'المنتجات'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(products)} منتج"}
    except Exception as e:
        logger.error(f"حدث خطأ أثناء مزامنة المنتجات: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def sync_settings(service, spreadsheet_id):
    """
    مزامنة إعدادات الشركة والنظام بشكل تفصيلي في صفحة واحدة
    """
    try:
        CompanyInfo = apps.get_model('accounts', 'CompanyInfo')
        SystemSettings = apps.get_model('accounts', 'SystemSettings')
        company_info = CompanyInfo.objects.first()
        system_settings = SystemSettings.objects.first()
        data = [[
            'الإصدار', 'تاريخ الإطلاق', 'المطور', 'ساعات العمل', 'اسم الشركة', 'حقوق النشر',
            'العنوان', 'الهاتف', 'البريد الإلكتروني', 'الرقم الضريبي', 'السجل التجاري', 'الموقع الإلكتروني',
            'روابط التواصل الاجتماعي', 'الوصف', 'فيسبوك', 'تويتر', 'إنستغرام', 'لينكدإن', 'حول', 'رؤية', 'مهمة',
            'اللون الأساسي', 'اللون الثانوي', 'لون التمييز'
        ]]
        if company_info:
            social_links = json.dumps(company_info.social_links) if company_info.social_links else '{}'
            data.append([
                company_info.version, company_info.release_date, company_info.developer, company_info.working_hours,
                company_info.name, company_info.copyright_text, company_info.address, company_info.phone,
                company_info.email, company_info.tax_number, company_info.commercial_register, company_info.website,
                social_links, company_info.description, company_info.facebook, company_info.twitter,
                company_info.instagram, company_info.linkedin, company_info.about, company_info.vision,
                company_info.mission, company_info.primary_color, company_info.secondary_color, company_info.accent_color
            ])
        else:
            data.append([''] * 24)
        if system_settings:
            data.append([
                system_settings.version, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''
            ])
        else:
            data.append([''] * 24)
        sheet_name = 'إعدادات الشركة والنظام'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': 'تمت مزامنة إعدادات الشركة والنظام بنجاح'}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة إعدادات الشركة والنظام: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_manufacturing_orders(service, spreadsheet_id):
    """
    مزامنة أوامر التصنيع مع Google Sheets مع ربطها بالطلبات والعملاء
    """
    try:
        ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')
        manufacturing_orders = ManufacturingOrder.objects.select_related('order', 'order__customer').all()

        # تحديد العناوين المخصصة لأوامر التصنيع
        header = [
            'معرف أمر التصنيع', 'رقم أمر التصنيع', 'رقم الطلب', 'اسم العميل', 'رقم هاتف العميل',
            'رقم العقد', 'نوع الطلب', 'الحالة', 'الأولوية', 'تاريخ البدء المتوقع', 'تاريخ الانتهاء المتوقع',
            'تاريخ الإكمال الفعلي', 'ملاحظات التصنيع', 'تاريخ الإنشاء', 'تاريخ التحديث'
        ]

        data = [header]
        for manufacturing_order in manufacturing_orders:
            # جلب بيانات العميل من خلال الطلب
            customer_name = manufacturing_order.order.customer.name if manufacturing_order.order and manufacturing_order.order.customer else ''
            customer_phone = manufacturing_order.order.customer.phone if manufacturing_order.order and manufacturing_order.order.customer else ''
            order_number = manufacturing_order.order.order_number if manufacturing_order.order else ''

            row = [
                str(manufacturing_order.id),
                manufacturing_order.manufacturing_code,
                order_number,
                customer_name,
                customer_phone,
                manufacturing_order.contract_number or '',
                manufacturing_order.get_order_type_display() if manufacturing_order.order_type else '',
                manufacturing_order.get_status_display(),
                manufacturing_order.get_priority_display() if hasattr(manufacturing_order, 'priority') else '',
                manufacturing_order.expected_start_date.strftime('%Y-%m-%d') if manufacturing_order.expected_start_date else '',
                manufacturing_order.expected_completion_date.strftime('%Y-%m-%d') if manufacturing_order.expected_completion_date else '',
                manufacturing_order.completion_date.strftime('%Y-%m-%d') if manufacturing_order.completion_date else '',
                manufacturing_order.manufacturing_notes or '',
                manufacturing_order.created_at.strftime('%Y-%m-%d %H:%M') if manufacturing_order.created_at else '',
                manufacturing_order.updated_at.strftime('%Y-%m-%d %H:%M') if manufacturing_order.updated_at else ''
            ]
            data.append(row)

        sheet_name = 'أوامر التصنيع'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(manufacturing_orders)} أمر تصنيع"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة أوامر التصنيع: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_technicians(service, spreadsheet_id):
    """
    مزامنة الفنيين مع Google Sheets
    """
    try:
        Technician = apps.get_model('installations', 'Technician')
        technicians = Technician.objects.all()

        header = [
            'معرف الفني', 'اسم الفني', 'رقم الهاتف', 'التخصص', 'القسم', 'الراتب',
            'تاريخ التوظيف', 'نشط', 'ملاحظات', 'تاريخ الإنشاء', 'تاريخ التحديث'
        ]

        data = [header]
        for technician in technicians:
            row = [
                str(technician.id),
                technician.name,
                technician.phone or '',
                technician.specialization or '',
                technician.get_department_display() if technician.department else '',
                str(technician.salary) if hasattr(technician, 'salary') and technician.salary else '',
                technician.hire_date.strftime('%Y-%m-%d') if hasattr(technician, 'hire_date') and technician.hire_date else '',
                'نعم' if technician.is_active else 'لا',
                technician.notes or '',
                technician.created_at.strftime('%Y-%m-%d %H:%M') if technician.created_at else '',
                technician.updated_at.strftime('%Y-%m-%d %H:%M') if technician.updated_at else ''
            ]
            data.append(row)

        sheet_name = 'الفنيين'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(technicians)} فني"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة الفنيين: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_installation_teams(service, spreadsheet_id):
    """
    مزامنة فرق التركيب مع Google Sheets
    """
    try:
        InstallationTeam = apps.get_model('installations', 'InstallationTeam')
        teams = InstallationTeam.objects.prefetch_related('technicians', 'drivers').all()

        header = [
            'معرف الفريق', 'اسم الفريق', 'الفنيين', 'السائقين', 'نشط',
            'ملاحظات', 'تاريخ الإنشاء', 'تاريخ التحديث'
        ]

        data = [header]
        for team in teams:
            # جمع أسماء الفنيين
            technician_names = ', '.join([tech.name for tech in team.technicians.all()])
            # جمع أسماء السائقين
            driver_names = ', '.join([driver.name for driver in team.drivers.all()])

            row = [
                str(team.id),
                team.name,
                technician_names,
                driver_names,
                'نعم' if team.is_active else 'لا',
                team.notes or '',
                team.created_at.strftime('%Y-%m-%d %H:%M') if team.created_at else '',
                team.updated_at.strftime('%Y-%m-%d %H:%M') if team.updated_at else ''
            ]
            data.append(row)

        sheet_name = 'فرق التركيب'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(teams)} فريق تركيب"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة فرق التركيب: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_suppliers(service, spreadsheet_id):
    """
    مزامنة الموردين مع Google Sheets
    """
    try:
        Supplier = apps.get_model('inventory', 'Supplier')
        suppliers = Supplier.objects.all()

        header = [
            'معرف المورد', 'اسم المورد', 'جهة الاتصال', 'رقم الهاتف', 'البريد الإلكتروني',
            'العنوان', 'الرقم الضريبي', 'ملاحظات'
        ]

        data = [header]
        for supplier in suppliers:
            row = [
                str(supplier.id),
                supplier.name,
                supplier.contact_person or '',
                supplier.phone or '',
                supplier.email or '',
                supplier.address or '',
                supplier.tax_number or '',
                supplier.notes or ''
            ]
            data.append(row)

        sheet_name = 'الموردين'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(suppliers)} مورد"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة الموردين: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_salespersons(service, spreadsheet_id):
    """
    مزامنة البائعين مع Google Sheets
    """
    try:
        Salesperson = apps.get_model('accounts', 'Salesperson')
        salespersons = Salesperson.objects.select_related('branch').all()

        header = [
            'معرف البائع', 'اسم البائع', 'الرقم الوظيفي', 'الفرع', 'رقم الهاتف',
            'البريد الإلكتروني', 'العنوان', 'نشط', 'ملاحظات', 'تاريخ الإنشاء', 'تاريخ التحديث'
        ]

        data = [header]
        for salesperson in salespersons:
            row = [
                str(salesperson.id),
                salesperson.name,
                salesperson.employee_number or '',
                salesperson.branch.name if salesperson.branch else '',
                salesperson.phone or '',
                salesperson.email or '',
                salesperson.address or '',
                'نعم' if salesperson.is_active else 'لا',
                salesperson.notes or '',
                salesperson.created_at.strftime('%Y-%m-%d %H:%M') if salesperson.created_at else '',
                salesperson.updated_at.strftime('%Y-%m-%d %H:%M') if salesperson.updated_at else ''
            ]
            data.append(row)

        sheet_name = 'البائعين'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(salespersons)} بائع"}
    except Exception as e:
        message = f"حدث خطأ أثناء مزامنة البائعين: {str(e)}"
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
        logger.info(f"بدء تحديث ورقة: {sheet_name} بعدد صفوف: {len(data)}")
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
            logger.info(f"إنشاء ورقة جديدة: {sheet_name}")
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
        logger.info(f"تم تحديث ورقة: {sheet_name} بنجاح")
        
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
                logger.info(f"تم تنسيق ورقة: {sheet_name} بنجاح")
            except Exception as format_error:
                logger.warning(f"حدث خطأ أثناء تنسيق ورقة: {sheet_name} - {str(format_error)}")
        
        updated_rows = result.get('updatedRows', 0)
        if updated_rows == 0:
            # إذا لم يتم إرجاع عدد الصفوف المحدثة، استخدم عدد الصفوف في البيانات كبديل
            updated_rows = len(data) - 1  # خصم صف العناوين

        return updated_rows
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تحديث ورقة: {sheet_name} - {str(e)}")
        return 0


# ========== دوال المزامنة المجمعة للصفحات الشاملة ==========

def sync_comprehensive_customers(service, spreadsheet_id):
    """
    مزامنة شاملة للعملاء مع طلباتهم ومعايناتهم وأوامر التصنيع
    """
    try:
        Customer = apps.get_model('customers', 'Customer')
        Order = apps.get_model('orders', 'Order')
        Inspection = apps.get_model('inspections', 'Inspection')
        ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')

        customers = Customer.objects.prefetch_related(
            'customer_orders',
            'inspections',
            'customer_orders__manufacturing_order'
        ).all()

        header = [
            'معرف العميل', 'كود العميل', 'اسم العميل', 'رقم الهاتف', 'رقم الهاتف الثاني',
            'البريد الإلكتروني', 'العنوان', 'نوع المكان', 'الفرع', 'تصنيف العميل',
            'عدد الطلبات', 'عدد المعاينات', 'عدد أوامر التصنيع', 'إجمالي قيمة الطلبات',
            'آخر طلب', 'آخر معاينة', 'الحالة', 'تاريخ الإنشاء'
        ]

        data = [header]
        for customer in customers:
            # حساب الإحصائيات
            orders_count = customer.customer_orders.count()
            inspections_count = customer.inspections.count()
            manufacturing_orders_count = customer.customer_orders.filter(manufacturing_order__isnull=False).count()

            # حساب إجمالي قيمة الطلبات
            total_orders_value = sum([order.total_amount or 0 for order in customer.customer_orders.all()])

            # آخر طلب ومعاينة
            last_order = customer.customer_orders.order_by('-created_at').first()
            last_inspection = customer.inspections.order_by('-request_date').first()

            row = [
                str(customer.id),
                customer.code or '',
                customer.name,
                customer.phone or '',
                customer.phone2 or '',
                customer.email or '',
                customer.address or '',
                customer.get_location_type_display() if customer.location_type else '',
                customer.branch.name if customer.branch else '',
                customer.category.name if customer.category else '',
                str(orders_count),
                str(inspections_count),
                str(manufacturing_orders_count),
                str(total_orders_value),
                last_order.order_number if last_order else '',
                last_inspection.contract_number if last_inspection else '',
                customer.get_status_display(),
                customer.created_at.strftime('%Y-%m-%d') if customer.created_at else ''
            ]
            data.append(row)

        sheet_name = 'العملاء الشامل'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(customers)} عميل مع بياناتهم الشاملة"}
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة الشاملة للعملاء: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_comprehensive_users(service, spreadsheet_id):
    """
    مزامنة شاملة للمستخدمين والبائعين والموظفين
    """
    try:
        User = apps.get_model('accounts', 'User')
        Salesperson = apps.get_model('accounts', 'Salesperson')
        Employee = apps.get_model('accounts', 'Employee')

        # جمع جميع المستخدمين مع بياناتهم
        users = User.objects.select_related('branch').all()

        header = [
            'معرف المستخدم', 'اسم المستخدم', 'الاسم الأول', 'الاسم الأخير', 'البريد الإلكتروني',
            'الفرع', 'نشط', 'موظف', 'مدير', 'فني معاينة', 'بائع', 'مدير فرع',
            'مدير منطقة', 'مدير عام', 'مسؤول مصنع', 'آخر دخول', 'تاريخ الانضمام'
        ]

        data = [header]
        for user in users:
            row = [
                str(user.id),
                user.username,
                user.first_name or '',
                user.last_name or '',
                user.email or '',
                user.branch.name if user.branch else '',
                'نعم' if user.is_active else 'لا',
                'نعم' if user.is_staff else 'لا',
                'نعم' if user.is_superuser else 'لا',
                'نعم' if user.is_inspection_technician else 'لا',
                'نعم' if user.is_salesperson else 'لا',
                'نعم' if user.is_branch_manager else 'لا',
                'نعم' if user.is_region_manager else 'لا',
                'نعم' if user.is_general_manager else 'لا',
                'نعم' if user.is_factory_manager else 'لا',
                user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
                user.date_joined.strftime('%Y-%m-%d') if user.date_joined else ''
            ]
            data.append(row)

        sheet_name = 'المستخدمين الشامل'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(users)} مستخدم مع بياناتهم الشاملة"}
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة الشاملة للمستخدمين: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_comprehensive_inventory(service, spreadsheet_id):
    """
    مزامنة شاملة للمنتجات والمخزون والمستودعات
    """
    try:
        Product = apps.get_model('inventory', 'Product')
        Category = apps.get_model('inventory', 'Category')
        Warehouse = apps.get_model('inventory', 'Warehouse')
        StockTransaction = apps.get_model('inventory', 'StockTransaction')

        products = Product.objects.select_related('category').all()

        header = [
            'معرف المنتج', 'كود المنتج', 'اسم المنتج', 'الفئة', 'السعر', 'العملة',
            'الوحدة', 'الوصف', 'الحد الأدنى للمخزون', 'الكمية المتوفرة', 'قيمة المخزون',
            'تاريخ الإنشاء', 'تاريخ التحديث'
        ]

        data = [header]
        for product in products:
            # حساب الكمية المتوفرة من المعاملات المخزنية
            try:
                stock_transactions = StockTransaction.objects.filter(product=product)
                available_quantity = sum([
                    trans.quantity if trans.transaction_type == 'in' else -trans.quantity
                    for trans in stock_transactions
                ])
            except:
                available_quantity = 0

            # حساب قيمة المخزون
            stock_value = available_quantity * (product.price or 0)

            row = [
                str(product.id),
                product.code or '',
                product.name,
                product.category.name if product.category else '',
                str(product.price) if product.price else '0',
                product.currency or 'EGP',
                product.get_unit_display() if product.unit else '',
                product.description or '',
                str(product.minimum_stock),
                str(available_quantity),
                str(stock_value),
                product.created_at.strftime('%Y-%m-%d') if product.created_at else '',
                product.updated_at.strftime('%Y-%m-%d') if product.updated_at else ''
            ]
            data.append(row)

        sheet_name = 'المنتجات والمخزون الشامل'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة {len(products)} منتج مع بيانات المخزون الشاملة"}
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة الشاملة للمنتجات والمخزون: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}


def sync_comprehensive_system_settings(service, spreadsheet_id):
    """
    مزامنة شاملة لإعدادات النظام والفروع والموردين والفنيين
    """
    try:
        Branch = apps.get_model('accounts', 'Branch')
        Supplier = apps.get_model('inventory', 'Supplier')
        Technician = apps.get_model('installations', 'Technician')
        InstallationTeam = apps.get_model('installations', 'InstallationTeam')
        Driver = apps.get_model('installations', 'Driver')

        # جمع إحصائيات شاملة
        branches_count = Branch.objects.count()
        suppliers_count = Supplier.objects.count()
        technicians_count = Technician.objects.count()
        teams_count = InstallationTeam.objects.count()
        drivers_count = Driver.objects.count()

        header = [
            'نوع البيانات', 'العدد الإجمالي', 'النشط', 'غير النشط', 'ملاحظات'
        ]

        data = [header]

        # إحصائيات الفروع
        active_branches = Branch.objects.filter(is_active=True).count()
        data.append([
            'الفروع',
            str(branches_count),
            str(active_branches),
            str(branches_count - active_branches),
            'إجمالي الفروع في النظام'
        ])

        # إحصائيات الموردين
        data.append([
            'الموردين',
            str(suppliers_count),
            str(suppliers_count),  # لا يوجد حقل is_active للموردين
            '0',
            'إجمالي الموردين في النظام'
        ])

        # إحصائيات الفنيين
        active_technicians = Technician.objects.filter(is_active=True).count()
        data.append([
            'الفنيين',
            str(technicians_count),
            str(active_technicians),
            str(technicians_count - active_technicians),
            'إجمالي الفنيين في النظام'
        ])

        # إحصائيات فرق التركيب
        active_teams = InstallationTeam.objects.filter(is_active=True).count()
        data.append([
            'فرق التركيب',
            str(teams_count),
            str(active_teams),
            str(teams_count - active_teams),
            'إجمالي فرق التركيب في النظام'
        ])

        # إحصائيات السائقين
        active_drivers = Driver.objects.filter(is_active=True).count()
        data.append([
            'السائقين',
            str(drivers_count),
            str(active_drivers),
            str(drivers_count - active_drivers),
            'إجمالي السائقين في النظام'
        ])

        sheet_name = 'إعدادات النظام الشامل'
        result = update_sheet(service, spreadsheet_id, sheet_name, data)
        return {'status': 'success', 'message': f"تمت مزامنة إعدادات النظام الشاملة"}
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة الشاملة لإعدادات النظام: {str(e)}"
        logger.error(message)
        return {'status': 'error', 'message': message}
