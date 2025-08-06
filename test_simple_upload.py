#!/usr/bin/env python
"""
سكريبت لاختبار رفع ملفات الإكسل البسيطة
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

from accounts.models import User
from inventory.models import Warehouse, Product, Category
from inventory.forms import ProductExcelUploadForm, BulkStockUpdateForm
import pandas as pd
from io import BytesIO

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

def test_simple_files():
    """اختبار الملفات البسيطة"""
    print_colored("🚀 بدء اختبار الملفات البسيطة...", "blue")
    print("=" * 50)
    
    # التحقق من وجود مستودع
    try:
        warehouse = Warehouse.objects.filter(is_active=True).first()
        if not warehouse:
            print_colored("❌ لا يوجد مستودع نشط في النظام", "red")
            return False
        print_colored(f"✅ تم العثور على مستودع: {warehouse.name}", "green")
    except Exception as e:
        print_colored(f"❌ خطأ في الوصول للمستودعات: {str(e)}", "red")
        return False
    
    # اختبار ملف المنتجات البسيط
    print_colored("\n🔍 اختبار ملف المنتجات البسيط...", "blue")
    try:
        # قراءة الملف البسيط
        with open('simple_products.xlsx', 'rb') as f:
            file_data = f.read()
        
        print_colored(f"📊 حجم الملف: {len(file_data)} بايت", "white")
        
        # قراءة الملف باستخدام pandas
        df = pd.read_excel(BytesIO(file_data), engine='openpyxl')
        print_colored("✅ تم قراءة الملف بنجاح", "green")
        print_colored(f"📋 عدد الصفوف: {len(df)}", "white")
        print_colored(f"📊 الأعمدة: {list(df.columns)}", "white")
        print_colored("📄 البيانات:", "white")
        print(df.head())
        
        # اختبار النموذج
        from django.core.files.uploadedfile import SimpleUploadedFile
        uploaded_file = SimpleUploadedFile(
            'simple_products.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        form_data = {
            'warehouse': warehouse.id,
            'overwrite_existing': False
        }
        
        form = ProductExcelUploadForm(data=form_data, files={'excel_file': uploaded_file})
        
        if form.is_valid():
            print_colored("✅ النموذج صحيح", "green")
            return True
        else:
            print_colored("❌ النموذج غير صحيح:", "red")
            for field, errors in form.errors.items():
                for error in errors:
                    print_colored(f"  - {field}: {error}", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ خطأ في اختبار ملف المنتجات: {str(e)}", "red")
        return False
    
    # اختبار ملف المخزون البسيط
    print_colored("\n🔍 اختبار ملف المخزون البسيط...", "blue")
    try:
        # قراءة الملف البسيط
        with open('simple_stock_update.xlsx', 'rb') as f:
            file_data = f.read()
        
        print_colored(f"📊 حجم الملف: {len(file_data)} بايت", "white")
        
        # قراءة الملف باستخدام pandas
        df = pd.read_excel(BytesIO(file_data), engine='openpyxl')
        print_colored("✅ تم قراءة الملف بنجاح", "green")
        print_colored(f"📋 عدد الصفوف: {len(df)}", "white")
        print_colored(f"📊 الأعمدة: {list(df.columns)}", "white")
        print_colored("📄 البيانات:", "white")
        print(df.head())
        
        # اختبار النموذج
        from django.core.files.uploadedfile import SimpleUploadedFile
        uploaded_file = SimpleUploadedFile(
            'simple_stock_update.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        form_data = {
            'warehouse': warehouse.id,
            'update_type': 'replace',
            'reason': 'تحديث من ملف إكسل'
        }
        
        form = BulkStockUpdateForm(data=form_data, files={'excel_file': uploaded_file})
        
        if form.is_valid():
            print_colored("✅ النموذج صحيح", "green")
            return True
        else:
            print_colored("❌ النموذج غير صحيح:", "red")
            for field, errors in form.errors.items():
                for error in errors:
                    print_colored(f"  - {field}: {error}", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ خطأ في اختبار ملف المخزون: {str(e)}", "red")
        return False

def create_test_warehouse():
    """إنشاء مستودع تجريبي إذا لم يكن موجوداً"""
    try:
        from accounts.models import Branch, User
        
        # التحقق من وجود فرع
        branch = Branch.objects.first()
        if not branch:
            print_colored("❌ لا يوجد فرع في النظام", "red")
            return False
        
        # التحقق من وجود مستخدم
        user = User.objects.filter(is_active=True).first()
        if not user:
            print_colored("❌ لا يوجد مستخدم نشط في النظام", "red")
            return False
        
        # إنشاء مستودع تجريبي
        warehouse, created = Warehouse.objects.get_or_create(
            code='TEST001',
            defaults={
                'name': 'المستودع التجريبي',
                'branch': branch,
                'manager': user,
                'address': 'عنوان تجريبي',
                'is_active': True,
                'notes': 'مستودع تجريبي للاختبار'
            }
        )
        
        if created:
            print_colored("✅ تم إنشاء مستودع تجريبي", "green")
        else:
            print_colored("✅ المستودع التجريبي موجود بالفعل", "green")
        
        return True
        
    except Exception as e:
        print_colored(f"❌ خطأ في إنشاء المستودع التجريبي: {str(e)}", "red")
        return False

def main():
    """الدالة الرئيسية"""
    print_colored("🚀 بدء اختبار رفع الملفات البسيطة...", "blue")
    print("=" * 50)
    
    # إنشاء مستودع تجريبي إذا لزم الأمر
    if not create_test_warehouse():
        return
    
    # اختبار الملفات البسيطة
    if test_simple_files():
        print_colored("\n✅ تم اختبار الملفات البسيطة بنجاح", "green")
        print_colored("📋 يمكنك الآن استخدام هذه الملفات في النظام", "white")
    else:
        print_colored("\n❌ فشل في اختبار الملفات البسيطة", "red")
    
    print_colored("\n🏁 انتهى الاختبار", "blue")

if __name__ == "__main__":
    main() 