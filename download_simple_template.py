#!/usr/bin/env python
"""
سكريبت لتحميل قالب بسيط من الواجهة
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

from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser
from inventory.views_bulk import download_excel_template
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

def create_simple_template():
    """إنشاء قالب بسيط بدون تنسيقات معقدة"""
    print_colored("🚀 بدء إنشاء قالب بسيط...", "blue")
    print("=" * 50)
    
    try:
        # إنشاء DataFrame بدلاً من openpyxl مباشرة
        print_colored("📊 إنشاء بيانات القالب...", "white")
        
        # إنشاء بيانات القالب للمنتجات
        products_data = {
            'اسم المنتج': ['لابتوب HP', 'طابعة Canon', 'ماوس لاسلكي', 'شاشة LED'],
            'الكود': ['LAP001', 'PRN001', 'MOU001', 'MON001'],
            'الفئة': ['أجهزة كمبيوتر', 'طابعات', 'ملحقات', 'شاشات'],
            'السعر': [15000, 2500, 150, 800],
            'الكمية': [10, 5, 20, 8],
            'الوصف': ['لابتوب HP بروسيسور i5', 'طابعة ليزر ملونة', 'ماوس لاسلكي عالي الجودة', 'شاشة LED 24 بوصة'],
            'الحد الأدنى': [5, 2, 10, 3],
            'العملة': ['EGP', 'EGP', 'EGP', 'EGP'],
            'الوحدة': ['قطعة', 'قطعة', 'قطعة', 'قطعة']
        }
        
        # إنشاء DataFrame للمنتجات
        df_products = pd.DataFrame(products_data)
        print_colored("✅ تم إنشاء بيانات المنتجات", "green")
        
        # إنشاء DataFrame لتحديث المخزون
        stock_data = {
            'كود المنتج': ['LAP001', 'PRN001', 'MOU001'],
            'الكمية': [25, 15, 30],
            'ملاحظات': ['تحديث بعد الجرد', 'إضافة مخزون جديد', 'تحديث الكمية']
        }
        
        df_stock = pd.DataFrame(stock_data)
        print_colored("✅ تم إنشاء بيانات المخزون", "green")
        
        # حفظ كملف إكسل بسيط
        print_colored("💾 حفظ الملف...", "white")
        
        # إنشاء ملف مؤقت
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # حفظ صفحة المنتجات
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df_products.to_excel(writer, sheet_name='المنتجات', index=False)
                df_stock.to_excel(writer, sheet_name='تحديث المخزون', index=False)
            
            # قراءة الملف المحفوظ
            with open(tmp_file.name, 'rb') as f:
                file_content = f.read()
            
            # حذف الملف المؤقت
            import os
            os.unlink(tmp_file.name)
        
        # حفظ الملف في المجلد الحالي
        template_filename = 'products_template_simple.xlsx'
        with open(template_filename, 'wb') as f:
            f.write(file_content)
        
        print_colored(f"✅ تم حفظ القالب: {template_filename}", "green")
        print_colored(f"📊 حجم الملف: {len(file_content)} بايت", "white")
        
        # اختبار قراءة الملف
        print_colored("\n🔍 اختبار قراءة القالب...", "blue")
        df_test = pd.read_excel(template_filename, sheet_name='المنتجات')
        print_colored(f"✅ تم قراءة القالب بنجاح", "green")
        print_colored(f"📋 عدد الصفوف: {len(df_test)}", "white")
        print_colored(f"📊 الأعمدة: {list(df_test.columns)}", "white")
        
        return True
        
    except Exception as e:
        print_colored(f"❌ خطأ في إنشاء القالب: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        return False

def test_template_upload():
    """اختبار رفع القالب"""
    print_colored("\n🔍 اختبار رفع القالب...", "blue")
    
    try:
        from django.core.files.uploadedfile import SimpleUploadedFile
        from inventory.forms import ProductExcelUploadForm
        from inventory.models import Warehouse
        
        # قراءة الملف
        with open('products_template_simple.xlsx', 'rb') as f:
            file_data = f.read()
        
        # الحصول على مستودع
        warehouse = Warehouse.objects.filter(is_active=True).first()
        if not warehouse:
            print_colored("❌ لا يوجد مستودع نشط", "red")
            return False
        
        # إنشاء ملف مرفوع
        uploaded_file = SimpleUploadedFile(
            'products_template_simple.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # اختبار النموذج
        form_data = {
            'warehouse': warehouse.id,
            'overwrite_existing': False
        }
        
        form = ProductExcelUploadForm(data=form_data, files={'excel_file': uploaded_file})
        
        if form.is_valid():
            print_colored("✅ النموذج صحيح - يمكن رفع القالب", "green")
            return True
        else:
            print_colored("❌ النموذج غير صحيح:", "red")
            for field, errors in form.errors.items():
                for error in errors:
                    print_colored(f"  - {field}: {error}", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ خطأ في اختبار رفع القالب: {str(e)}", "red")
        return False

def main():
    """الدالة الرئيسية"""
    print_colored("🚀 بدء إنشاء قالب بسيط...", "blue")
    print("=" * 50)
    
    # إنشاء القالب
    if create_simple_template():
        print_colored("\n✅ تم إنشاء القالب بنجاح", "green")
        
        # اختبار رفع القالب
        if test_template_upload():
            print_colored("\n✅ يمكن استخدام القالب في النظام", "green")
        else:
            print_colored("\n❌ مشكلة في رفع القالب", "red")
    else:
        print_colored("\n❌ فشل في إنشاء القالب", "red")
    
    print_colored("\n📋 التعليمات:", "blue")
    print_colored("1. استخدم الملف: products_template_simple.xlsx", "white")
    print_colored("2. املأ البيانات في الصفحة الأولى (المنتجات)", "white")
    print_colored("3. احفظ الملف", "white")
    print_colored("4. ارفع الملف من واجهة النظام", "white")
    
    print_colored("\n🏁 انتهى إنشاء القالب", "blue")

if __name__ == "__main__":
    main() 