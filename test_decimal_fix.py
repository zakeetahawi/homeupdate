#!/usr/bin/env python
"""
سكريبت اختبار سريع لإصلاح مشكلة Decimal
"""
import os
import sys
import django
from pathlib import Path

# إعداد Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from inventory.models import Warehouse, Product, Category
from inventory.views_bulk import process_excel_upload, process_stock_update
from accounts.models import User
from decimal import Decimal

def print_colored(message, color="white"):
    """طباعة رسائل ملونة"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m", 
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[97m"
    }
    end_color = "\033[0m"
    print(f"{colors.get(color, colors['white'])}{message}{end_color}")

def test_decimal_fix():
    """اختبار إصلاح مشكلة Decimal"""
    print_colored("🚀 اختبار إصلاح مشكلة Decimal...", "blue")
    print("=" * 50)
    
    try:
        # الحصول على المستخدم والمستودع
        user = User.objects.filter(is_active=True).first()
        warehouse = Warehouse.objects.filter(is_active=True).first()
        
        if not user or not warehouse:
            print_colored("❌ لا يوجد مستخدم أو مستودع نشط", "red")
            return False
        
        print_colored(f"✅ المستخدم: {user.username}", "green")
        print_colored(f"✅ المستودع: {warehouse.name}", "green")
        
        # اختبار إضافة منتج واحد
        print_colored("\n📊 اختبار إضافة منتج واحد...", "blue")
        
        # إنشاء ملف بسيط مع منتج واحد
        import pandas as pd
        from io import BytesIO
        
        test_data = {
            'اسم المنتج': ['منتج اختبار'],
            'الكود': ['TEST001'],
            'الفئة': ['اختبار'],
            'السعر': [100.50],
            'الكمية': [10.0],
            'الوصف': ['منتج للاختبار'],
            'الحد الأدنى': [5],
            'العملة': ['EGP'],
            'الوحدة': ['قطعة']
        }
        
        df = pd.DataFrame(test_data)
        
        # حفظ كملف مؤقت
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            
            # قراءة الملف
            with open(tmp_file.name, 'rb') as f:
                file_data = f.read()
            
            # حذف الملف المؤقت
            import os
            os.unlink(tmp_file.name)
        
        # إنشاء ملف مرفوع
        uploaded_file = SimpleUploadedFile(
            'test_product.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # اختبار معالجة الملف
        result = process_excel_upload(
            uploaded_file,
            warehouse,
            False,  # لا تستبدل المنتجات الموجودة
            user
        )
        
        if result['success']:
            print_colored("✅ تم معالجة الملف بنجاح", "green")
            print_colored(f"📋 المنتجات المعالجة: {result['total_processed']}", "white")
            print_colored(f"🆕 المنتجات الجديدة: {result['created_count']}", "green")
            print_colored(f"🔄 المنتجات المحدثة: {result['updated_count']}", "yellow")
            
            if result['errors']:
                print_colored("⚠️ الأخطاء:", "yellow")
                for error in result['errors'][:3]:
                    print_colored(f"  - {error}", "yellow")
        else:
            print_colored(f"❌ فشل في معالجة الملف: {result['message']}", "red")
            return False
        
        # اختبار تحديث المخزون
        print_colored("\n📊 اختبار تحديث المخزون...", "blue")
        
        # إنشاء ملف تحديث مخزون
        stock_data = {
            'كود المنتج': ['TEST001'],
            'الكمية': [15.0],
            'ملاحظات': ['تحديث اختبار']
        }
        
        df_stock = pd.DataFrame(stock_data)
        
        # حفظ كملف مؤقت
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df_stock.to_excel(tmp_file.name, index=False)
            
            # قراءة الملف
            with open(tmp_file.name, 'rb') as f:
                file_data = f.read()
            
            # حذف الملف المؤقت
            os.unlink(tmp_file.name)
        
        # إنشاء ملف مرفوع
        uploaded_file = SimpleUploadedFile(
            'test_stock.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # اختبار معالجة الملف
        result = process_stock_update(
            uploaded_file,
            warehouse,
            'replace',  # استبدال الكمية
            'اختبار تحديث المخزون',
            user
        )
        
        if result['success']:
            print_colored("✅ تم تحديث المخزون بنجاح", "green")
            print_colored(f"📋 المنتجات المحدثة: {result['updated_count']}", "white")
            
            if result['errors']:
                print_colored("⚠️ الأخطاء:", "yellow")
                for error in result['errors'][:3]:
                    print_colored(f"  - {error}", "yellow")
        else:
            print_colored(f"❌ فشل في تحديث المخزون: {result['message']}", "red")
            return False
        
        return True
        
    except Exception as e:
        print_colored(f"❌ خطأ في الاختبار: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        return False

def main():
    """الدالة الرئيسية"""
    print_colored("🚀 بدء اختبار إصلاح مشكلة Decimal...", "blue")
    print("=" * 50)
    
    if test_decimal_fix():
        print_colored("\n✅ تم إصلاح مشكلة Decimal بنجاح", "green")
        print_colored("🎉 يمكنك الآن رفع ملفات الإكسل بدون مشاكل", "green")
    else:
        print_colored("\n❌ فشل في إصلاح مشكلة Decimal", "red")
        print_colored("🔧 يرجى مراجعة الأخطاء أعلاه", "red")
    
    print_colored("\n🏁 انتهى الاختبار", "blue")

if __name__ == "__main__":
    main() 