#!/usr/bin/env python
"""
سكريبت نهائي لاختبار رفع ملفات الإكسل في النظام
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
from inventory.forms import ProductExcelUploadForm, BulkStockUpdateForm
from inventory.views_bulk import process_excel_upload, process_stock_update
from accounts.models import User
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

def test_system_upload():
    """اختبار رفع الملفات في النظام"""
    print_colored("🚀 بدء اختبار رفع الملفات في النظام...", "blue")
    print("=" * 60)
    
    # التحقق من النظام
    print_colored("🔍 فحص النظام...", "blue")
    
    # التحقق من المستخدمين
    users = User.objects.filter(is_active=True)
    if not users.exists():
        print_colored("❌ لا يوجد مستخدمين نشطين", "red")
        return False
    user = users.first()
    print_colored(f"✅ تم العثور على مستخدم: {user.username}", "green")
    
    # التحقق من المستودعات
    warehouses = Warehouse.objects.filter(is_active=True)
    if not warehouses.exists():
        print_colored("❌ لا يوجد مستودعات نشطة", "red")
        return False
    warehouse = warehouses.first()
    print_colored(f"✅ تم العثور على مستودع: {warehouse.name}", "green")
    
    # التحقق من الفئات
    categories = Category.objects.all()
    print_colored(f"✅ عدد الفئات: {categories.count()}", "green")
    
    # التحقق من المنتجات الموجودة
    products = Product.objects.all()
    print_colored(f"✅ عدد المنتجات الموجودة: {products.count()}", "green")
    
    print_colored("\n📊 اختبار رفع ملف المنتجات...", "blue")
    
    # اختبار رفع ملف المنتجات
    try:
        # قراءة الملف البسيط
        with open('products_template_simple.xlsx', 'rb') as f:
            file_data = f.read()
        
        print_colored(f"📊 حجم الملف: {len(file_data)} بايت", "white")
        
        # إنشاء ملف مرفوع
        uploaded_file = SimpleUploadedFile(
            'products_template_simple.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # معالجة الملف
        result = process_excel_upload(
            uploaded_file,
            warehouse,
            False,  # لا تستبدل المنتجات الموجودة
            user
        )
        
        if result['success']:
            print_colored("✅ تم رفع المنتجات بنجاح", "green")
            print_colored(f"📋 إجمالي المنتجات المعالجة: {result['total_processed']}", "white")
            print_colored(f"🆕 المنتجات الجديدة: {result['created_count']}", "green")
            print_colored(f"🔄 المنتجات المحدثة: {result['updated_count']}", "yellow")
            
            if result['errors']:
                print_colored("⚠️ الأخطاء:", "yellow")
                for error in result['errors'][:3]:
                    print_colored(f"  - {error}", "yellow")
        else:
            print_colored(f"❌ فشل في رفع المنتجات: {result['message']}", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ خطأ في رفع المنتجات: {str(e)}", "red")
        return False
    
    print_colored("\n📊 اختبار رفع ملف تحديث المخزون...", "blue")
    
    # اختبار رفع ملف تحديث المخزون
    try:
        # قراءة ملف المخزون
        with open('simple_stock_update.xlsx', 'rb') as f:
            file_data = f.read()
        
        print_colored(f"📊 حجم الملف: {len(file_data)} بايت", "white")
        
        # إنشاء ملف مرفوع
        uploaded_file = SimpleUploadedFile(
            'simple_stock_update.xlsx',
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # معالجة الملف
        result = process_stock_update(
            uploaded_file,
            warehouse,
            'replace',  # استبدال الكمية
            'تحديث من ملف إكسل',
            user
        )
        
        if result['success']:
            print_colored("✅ تم تحديث المخزون بنجاح", "green")
            print_colored(f"📋 عدد المنتجات المحدثة: {result['updated_count']}", "white")
            
            if result['errors']:
                print_colored("⚠️ الأخطاء:", "yellow")
                for error in result['errors'][:3]:
                    print_colored(f"  - {error}", "yellow")
        else:
            print_colored(f"❌ فشل في تحديث المخزون: {result['message']}", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ خطأ في تحديث المخزون: {str(e)}", "red")
        return False
    
    # عرض النتائج النهائية
    print_colored("\n📊 النتائج النهائية...", "blue")
    
    final_products = Product.objects.all()
    print_colored(f"📋 إجمالي المنتجات: {final_products.count()}", "green")
    
    # عرض بعض المنتجات
    print_colored("\n📋 المنتجات المضافة:", "white")
    for product in final_products.order_by('-created_at')[:5]:
        print_colored(f"  - {product.name} (كود: {product.code}) - المخزون: {product.current_stock}", "white")
    
    return True

def show_instructions():
    """عرض التعليمات للمستخدم"""
    print_colored("\n📋 التعليمات للمستخدم:", "blue")
    print_colored("=" * 50, "white")
    
    print_colored("\n1️⃣ تحميل القالب:", "green")
    print_colored("   - استخدم الملف: products_template_simple.xlsx", "white")
    print_colored("   - افتح الملف في Excel أو LibreOffice", "white")
    
    print_colored("\n2️⃣ ملء البيانات:", "green")
    print_colored("   - املأ البيانات في صفحة 'المنتجات'", "white")
    print_colored("   - تأكد من وجود الأعمدة المطلوبة", "white")
    print_colored("   - استخدم الأرقام فقط في حقول الأسعار والكميات", "white")
    
    print_colored("\n3️⃣ حفظ الملف:", "green")
    print_colored("   - احفظ الملف بنفس التنسيق .xlsx", "white")
    print_colored("   - تجنب إضافة تنسيقات معقدة", "white")
    
    print_colored("\n4️⃣ رفع الملف:", "green")
    print_colored("   - اذهب إلى واجهة النظام", "white")
    print_colored("   - اختر 'رفع ملف' أو 'إضافة منتجات بالجملة'", "white")
    print_colored("   - اختر المستودع المناسب", "white")
    print_colored("   - ارفع الملف واضغط 'رفع'", "white")
    
    print_colored("\n⚠️ ملاحظات مهمة:", "yellow")
    print_colored("   - استخدم الملفات البسيطة المقدمة فقط", "white")
    print_colored("   - تأكد من صحة البيانات قبل الرفع", "white")
    print_colored("   - راجع النتائج بعد الرفع", "white")
    
    print_colored("\n📁 الملفات المتاحة:", "blue")
    print_colored("   - products_template_simple.xlsx (القالب الرئيسي)", "white")
    print_colored("   - simple_products.xlsx (ملف تجريبي)", "white")
    print_colored("   - simple_stock_update.xlsx (تحديث المخزون)", "white")

def main():
    """الدالة الرئيسية"""
    print_colored("🚀 بدء الاختبار النهائي لرفع ملفات الإكسل...", "blue")
    print("=" * 60)
    
    # اختبار النظام
    if test_system_upload():
        print_colored("\n✅ تم اختبار النظام بنجاح", "green")
        print_colored("🎉 يمكنك الآن استخدام رفع ملفات الإكسل", "green")
    else:
        print_colored("\n❌ فشل في اختبار النظام", "red")
        print_colored("🔧 يرجى مراجعة الأخطاء أعلاه", "red")
    
    # عرض التعليمات
    show_instructions()
    
    print_colored("\n🏁 انتهى الاختبار النهائي", "blue")

if __name__ == "__main__":
    main() 