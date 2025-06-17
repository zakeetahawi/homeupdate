"""
خدمة استيراد البيانات من Google Sheets
"""
import logging
from django.apps import apps
from django.db import transaction
from .google_sync import create_sheets_service, GoogleSyncConfig

logger = logging.getLogger(__name__)

class ImportService:
    def __init__(self):
        self.sheets_service = None
        self.config = None

    def initialize(self):
        """تهيئة الخدمة"""
        self.config = GoogleSyncConfig.get_active_config()
        if not self.config:
            raise Exception("لا يوجد إعداد مزامنة نشط")
        self.sheets_service = create_sheets_service(self.config)

    def get_available_sheets(self):
        """جلب قائمة الجداول المتاحة"""
        if not self.sheets_service:
            self.initialize()

        available_sheets = [
            {'name': 'العملاء', 'key': 'customers', 'icon': 'fas fa-users'},
            {'name': 'المستخدمين', 'key': 'users', 'icon': 'fas fa-user'},
            {'name': 'قواعد البيانات', 'key': 'databases', 'icon': 'fas fa-database'},
            {'name': 'الطلبات', 'key': 'orders', 'icon': 'fas fa-shopping-cart'},
            {'name': 'المنتجات', 'key': 'products', 'icon': 'fas fa-box'},
            {'name': 'المعاينات', 'key': 'inspections', 'icon': 'fas fa-search'},
            {'name': 'الإعدادات', 'key': 'settings', 'icon': 'fas fa-cog'},
        ]

        # إضافة عدد السجلات لكل جدول
        for sheet in available_sheets:
            try:
                count = self.get_sheet_record_count(sheet['key'])
                sheet['record_count'] = count
            except:
                sheet['record_count'] = 0

        return available_sheets

    def get_sheet_data(self, sheet_name, page_range=None):
        """جلب بيانات جدول محدد"""
        if not self.sheets_service:
            self.initialize()

        try:
            if page_range:
                range_name = f"{sheet_name}!A{page_range['start']}:Z{page_range['end']}"
            else:
                range_name = f"{sheet_name}!A:Z"

            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.config.spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                return []

            # تحويل البيانات إلى قاموس
            headers = values[0]
            data = []
            for row in values[1:]:
                # ملء الصفوف الناقصة
                while len(row) < len(headers):
                    row.append('')
                data.append(dict(zip(headers, row)))

            return data

        except Exception as e:
            logger.error(f"خطأ في جلب بيانات الجدول {sheet_name}: {str(e)}")
            raise

    def get_sheet_record_count(self, sheet_key):
        """الحصول على عدد السجلات في جدول"""
        data = self.get_sheet_data(sheet_key)
        return len(data)

    def import_data(self, sheet_name, data, clear_existing=False):
        """استيراد البيانات حسب نوع الجدول"""
        importers = {
            'customers': self.import_customers,
            'users': self.import_users,
            'databases': self.import_databases,
            'orders': self.import_orders,
            'products': self.import_products,
            'inspections': self.import_inspections,
            'settings': self.import_settings,
        }

        if sheet_name not in importers:
            raise ValueError(f"جدول غير معروف: {sheet_name}")

        return importers[sheet_name](data, clear_existing)

    def import_customers(self, data, clear_existing=False):
        """استيراد بيانات العملاء"""
        Customer = apps.get_model('customers', 'Customer')

        with transaction.atomic():
            if clear_existing:
                Customer.objects.all().delete()

            imported = 0
            updated = 0
            failed = 0
            errors = []

            for row in data:
                try:
                    # البحث عن العميل الموجود
                    customer = None
                    if row.get('معرف'):
                        customer = Customer.objects.filter(id=row['معرف']).first()

                    if customer:
                        # تحديث العميل الموجود
                        customer.name = row.get('الاسم', customer.name)
                        customer.phone = row.get('رقم الهاتف', customer.phone)
                        customer.address = row.get('العنوان', customer.address)
                        customer.save()
                        updated += 1
                    else:
                        # إنشاء عميل جديد
                        Customer.objects.create(
                            name=row.get('الاسم', ''),
                            phone=row.get('رقم الهاتف', ''),
                            address=row.get('العنوان', ''),
                            interests=row.get('الاهتمامات', ''),
                            notes=row.get('الملاحظات', '')
                        )
                        imported += 1

                except Exception as e:
                    failed += 1
                    errors.append(f"خطأ في السطر {row}: {str(e)}")

            return {
                'imported': imported,
                'updated': updated,
                'failed': failed,
                'errors': errors
            }
