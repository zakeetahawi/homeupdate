#!/usr/bin/env python3
"""
سكريپت استعادة محسن لتجنب مشاكل التعليق
=======================================

هذا السكريپت يوفر:
1. استعادة محسنة مع معالجة أفضل للأخطاء
2. تجنب مشاكل التعليق والذاكرة
3. معالجة تدريجية للبيانات الكبيرة
4. تقرير مفصل عن العملية
"""

import os
import sys
import django
import json
import gc
import psutil
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.db import transaction, connection
from django.core import serializers
from django.apps import apps
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

class OptimizedRestoreManager:
    """مدير الاستعادة المحسن"""

    def __init__(self):
        self.batch_size = 50  # حجم الدفعة لتجنب مشاكل الذاكرة
        self.max_errors = 100  # أقصى عدد أخطاء مسموح
        self.memory_threshold_mb = 500  # عتبة استخدام الذاكرة

        # إحصائيات العملية
        self.stats = {
            'total_items': 0,
            'processed': 0,
            'success': 0,
            'errors': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None,
            'errors_list': []
        }

    def check_memory_usage(self):
        """فحص استخدام الذاكرة"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self.memory_threshold_mb:
            print(f"⚠️ استخدام الذاكرة مرتفع: {memory_mb:.1f} MB")
            # تنظيف الذاكرة
            gc.collect()
            return True

        return False

    def validate_json_file(self, file_path):
        """التحقق من صحة ملف JSON"""
        print(f"🔍 التحقق من ملف: {file_path}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"📊 حجم الملف: {file_size_mb:.1f} MB")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # قراءة عينة من الملف للتحقق
                sample = f.read(1000)
                f.seek(0)

                # محاولة تحليل JSON
                data = json.load(f)

            if not isinstance(data, list):
                if isinstance(data, dict) and 'model' in data:
                    data = [data]
                else:
                    raise ValueError("تنسيق ملف غير صحيح - يجب أن يكون قائمة JSON")

            print(f"✅ الملف صالح - يحتوي على {len(data)} عنصر")
            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"خطأ في تنسيق JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"خطأ في قراءة الملف: {str(e)}")

    def prepare_content_types(self):
        """إعداد أنواع المحتوى المطلوبة"""
        print("🔧 إعداد أنواع المحتوى...")

        required_content_types = [
            ('manufacturing', 'manufacturingorder'),
            ('manufacturing', 'manufacturingorderitem'),
            ('orders', 'order'),
            ('orders', 'orderitem'),
            ('customers', 'customer'),
            ('customers', 'customernote'),
            ('inspections', 'inspection'),
            ('installations', 'installationschedule'),
            ('inventory', 'product'),
            ('inventory', 'category'),
            ('inventory', 'brand'),
            ('accounts', 'department'),
            ('accounts', 'branch'),
        ]

        created_count = 0
        for app_label, model_name in required_content_types:
            try:
                ct, created = ContentType.objects.get_or_create(
                    app_label=app_label,
                    model=model_name
                )
                if created:
                    created_count += 1
            except Exception as e:
                print(f"⚠️ تحذير: لم يتم إنشاء ContentType لـ {app_label}.{model_name}: {str(e)}")

        print(f"✅ تم إنشاء {created_count} نوع محتوى جديد")

    def sort_data_by_dependencies(self, data):
        """ترتيب البيانات حسب التبعيات"""
        print("🔄 ترتيب البيانات حسب التبعيات...")

        # ترتيب محسن لحل مشاكل المفاتيح الخارجية
        priority_order = [
            # النماذج الأساسية أولاً
            'contenttypes.contenttype',
            'auth.user',
            'auth.group',
            'auth.permission',

            # النماذج المرجعية
            'accounts.department',
            'accounts.branch',
            'customers.customertype',
            'customers.customercategory',
            'inventory.category',
            'inventory.brand',
            'inventory.warehouse',

            # النماذج التي تعتمد على المرجعية
            'customers.customer',
            'inventory.product',

            # النماذج التي تعتمد على العملاء والمنتجات
            'orders.order',
            'orders.orderitem',
            'inspections.inspection',
            'manufacturing.manufacturingorder',
            'manufacturing.manufacturingorderitem',
            'installations.installationschedule',

            # النماذج التكميلية
            'customers.customernote',
            'inventory.stocktransaction',
            'reports.report',

            # نماذج النظام أخيراً
            'odoo_db_manager.database',
            'odoo_db_manager.backup',
        ]

        sorted_data = []
        remaining_data = []

        # ترتيب حسب الأولوية
        for model_name in priority_order:
            for item in data:
                if item.get('model') == model_name:
                    sorted_data.append(item)

        # إضافة البيانات المتبقية
        for item in data:
            if item not in sorted_data:
                remaining_data.append(item)

        final_data = sorted_data + remaining_data

        print(f"✅ تم ترتيب {len(final_data)} عنصر")
        return final_data

    def clear_existing_data(self, models_to_clear):
        """حذف البيانات الموجودة بأمان"""
        print("🗑️ حذف البيانات الموجودة...")

        # النماذج المحظورة من الحذف
        protected_models = {
            'auth.user',  # المستخدمين
            'auth.group',
            'auth.permission',
            'contenttypes.contenttype',
            'odoo_db_manager.restoreprogress',  # سجلات الاستعادة
        }

        # فلترة النماذج الآمنة للحذف
        safe_models = [m for m in models_to_clear if m not in protected_models]

        # ترتيب عكسي للحذف
        deletion_order = [
            'customers.customernote',
            'inventory.stocktransaction',
            'orders.orderitem',
            'manufacturing.manufacturingorderitem',
            'installations.installationschedule',
            'inspections.inspection',
            'manufacturing.manufacturingorder',
            'orders.order',
            'inventory.product',
            'customers.customer',
            'inventory.category',
            'inventory.brand',
            'customers.customertype',
            'customers.customercategory',
        ]

        deleted_total = 0
        for model_name in deletion_order:
            if model_name in safe_models:
                try:
                    app_label, model_class = model_name.split('.')
                    model = apps.get_model(app_label, model_class)

                    count_before = model.objects.count()
                    if count_before > 0:
                        deleted_count = model.objects.all().delete()[0]
                        deleted_total += deleted_count
                        print(f"  ✅ حذف {deleted_count} عنصر من {model_name}")

                except Exception as e:
                    print(f"  ⚠️ خطأ في حذف {model_name}: {str(e)}")

        print(f"✅ تم حذف {deleted_total} عنصر إجمالي")

    def process_batch(self, batch_data):
        """معالجة دفعة من البيانات"""
        batch_success = 0
        batch_errors = 0
        batch_errors_list = []

        for i, item in enumerate(batch_data):
            try:
                # معالجة العنصر الواحد في transaction منفصل
                with transaction.atomic():
                    # تنظيف البيانات المشكوك فيها
                    self.clean_item_data(item)

                    # استعادة العنصر
                    for obj in serializers.deserialize('json', json.dumps([item])):
                        obj.save()

                batch_success += 1

            except Exception as e:
                batch_errors += 1
                error_info = {
                    'item_index': self.stats['processed'] + i,
                    'model': item.get('model', 'unknown'),
                    'pk': item.get('pk', 'unknown'),
                    'error': str(e)[:200]
                }
                batch_errors_list.append(error_info)

                # طباعة الأخطاء الأولى فقط
                if len(self.stats['errors_list']) < 10:
                    print(f"    ⚠️ خطأ في العنصر {error_info['item_index']}: {error_info['error'][:100]}...")

        return batch_success, batch_errors, batch_errors_list

    def clean_item_data(self, item):
        """تنظيف بيانات العنصر"""
        fields = item.get('fields', {})
        model_name = item.get('model', '')

        # إصلاحات خاصة لنماذج معينة
        if model_name == 'accounts.systemsettings':
            # إصلاح إعدادات النظام
            if 'default_currency' in fields:
                default_curr = fields.pop('default_currency', 'SAR')
                fields['currency'] = default_curr

            # إزالة الحقول القديمة
            old_fields = ['timezone', 'date_format', 'time_format']
            for field in old_fields:
                fields.pop(field, None)

        # إصلاح القيم المنطقية
        for field_name, field_value in fields.items():
            if isinstance(field_value, str):
                if field_value.lower() in ['true', 'connected', 'active']:
                    fields[field_name] = True
                elif field_value.lower() in ['false', 'disconnected', 'inactive']:
                    fields[field_name] = False

        item['fields'] = fields

    def restore_with_progress(self, file_path, clear_existing=False):
        """تنفيذ الاستعادة مع إظهار التقدم"""
        print("🚀 بدء عملية الاستعادة المحسنة...")
        print("="*50)

        self.stats['start_time'] = timezone.now()

        try:
            # 1. التحقق من الملف وتحميل البيانات
            data = self.validate_json_file(file_path)
            self.stats['total_items'] = len(data)

            # 2. إعداد أنواع المحتوى
            self.prepare_content_types()

            # 3. ترتيب البيانات
            sorted_data = self.sort_data_by_dependencies(data)

            # 4. حذف البيانات الموجودة إذا طُلب
            if clear_existing:
                models_to_clear = list(set(item.get('model') for item in sorted_data))
                self.clear_existing_data(models_to_clear)

            # 5. معالجة البيانات على دفعات
            print(f"📊 بدء معالجة {len(sorted_data)} عنصر على دفعات من {self.batch_size}")

            for batch_start in range(0, len(sorted_data), self.batch_size):
                # فحص الذاكرة
                self.check_memory_usage()

                # تحضير الدفعة
                batch_end = min(batch_start + self.batch_size, len(sorted_data))
                batch = sorted_data[batch_start:batch_end]

                # معالجة الدفعة
                batch_success, batch_errors, batch_errors_list = self.process_batch(batch)

                # تحديث الإحصائيات
                self.stats['processed'] += len(batch)
                self.stats['success'] += batch_success
                self.stats['errors'] += batch_errors
                self.stats['errors_list'].extend(batch_errors_list)

                # عرض التقدم
                progress = (self.stats['processed'] / self.stats['total_items']) * 100
                print(f"📈 التقدم: {progress:.1f}% ({self.stats['processed']}/{self.stats['total_items']}) - "
                      f"نجح: {batch_success}, أخطاء: {batch_errors}")

                # التحقق من عدد الأخطاء
                if self.stats['errors'] > self.max_errors:
                    print(f"⚠️ تم تجاوز الحد الأقصى للأخطاء ({self.max_errors})")
                    break

            self.stats['end_time'] = timezone.now()

            # طباعة التقرير النهائي
            self.print_final_report()

            return {
                'success': True,
                'total_items': self.stats['total_items'],
                'success_count': self.stats['success'],
                'error_count': self.stats['errors'],
                'processed_items': self.stats['processed'],
                'errors': self.stats['errors_list'][:20]  # أول 20 خطأ فقط
            }

        except Exception as e:
            self.stats['end_time'] = timezone.now()
            error_msg = f"خطأ في عملية الاستعادة: {str(e)}"
            print(f"❌ {error_msg}")

            return {
                'success': False,
                'error': error_msg,
                'total_items': self.stats['total_items'],
                'processed_items': self.stats['processed']
            }

    def print_final_report(self):
        """طباعة التقرير النهائي"""
        duration = self.stats['end_time'] - self.stats['start_time']
        duration_seconds = duration.total_seconds()

        print("\n" + "="*60)
        print("📊 تقرير الاستعادة النهائي")
        print("="*60)

        print(f"⏱️ الوقت المستغرق: {duration_seconds:.1f} ثانية")
        print(f"📦 إجمالي العناصر: {self.stats['total_items']}")
        print(f"✅ تم بنجاح: {self.stats['success']}")
        print(f"❌ فشل: {self.stats['errors']}")
        print(f"📊 معدل النجاح: {(self.stats['success']/self.stats['total_items']*100):.1f}%")

        if duration_seconds > 0:
            rate = self.stats['processed'] / duration_seconds
            print(f"⚡ معدل المعالجة: {rate:.1f} عنصر/ثانية")

        if self.stats['errors'] > 0:
            print(f"\n❌ أول 5 أخطاء:")
            for i, error in enumerate(self.stats['errors_list'][:5], 1):
                print(f"  {i}. العنصر {error['item_index']} ({error['model']}): {error['error'][:80]}...")

        print("="*60)

def main():
    """الدالة الرئيسية"""
    if len(sys.argv) < 2:
        print("الاستخدام: python optimized_restore.py <مسار_ملف_النسخة_الاحتياطية> [حذف_البيانات_الموجودة]")
        print("مثال: python optimized_restore.py backup.json true")
        sys.exit(1)

    file_path = sys.argv[1]
    clear_existing = len(sys.argv) > 2 and sys.argv[2].lower() in ['true', '1', 'yes']

    print("🔄 استعادة محسنة للنسخة الاحتياطية")
    print(f"📁 الملف: {file_path}")
    print(f"🗑️ حذف البيانات الموجودة: {'نعم' if clear_existing else 'لا'}")
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # تشغيل الاستعادة
    manager = OptimizedRestoreManager()
    result = manager.restore_with_progress(file_path, clear_existing)

    if result['success']:
        print("\n🎉 تمت الاستعادة بنجاح!")
    else:
        print(f"\n❌ فشلت الاستعادة: {result.get('error', 'خطأ غير محدد')}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف العملية بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ عام: {str(e)}")
        sys.exit(1)
