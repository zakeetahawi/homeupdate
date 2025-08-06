#!/usr/bin/env python3
"""
سكريبت إنشاء قالب بسيط يعمل بشكل صحيح
"""

import pandas as pd
import os

def create_working_template():
    """إنشاء قالب بسيط يعمل بشكل صحيح"""
    print("🔧 إنشاء قالب بسيط يعمل...")
    
    try:
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
        
        # إنشاء بيانات تحديث المخزون
        stock_data = {
            'كود المنتج': ['LAP001', 'PRN001', 'MOU001'],
            'الكمية': [25, 15, 30],
            'ملاحظات': ['تحديث بعد الجرد', 'إضافة مخزون جديد', 'تحديث الكمية']
        }
        
        df_stock = pd.DataFrame(stock_data)
        
        # حفظ كملف إكسل بسيط
        file_path = 'working_template.xlsx'
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_products.to_excel(writer, sheet_name='المنتجات', index=False)
            df_stock.to_excel(writer, sheet_name='تحديث المخزون', index=False)
        
        print(f"✅ تم إنشاء القالب البسيط: {file_path}")
        print(f"📊 عدد المنتجات: {len(df_products)}")
        print(f"📊 عدد تحديثات المخزون: {len(df_stock)}")
        
        return file_path
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء القالب: {str(e)}")
        return None

def test_template():
    """اختبار القالب"""
    print("🧪 اختبار القالب...")
    
    file_path = create_working_template()
    if not file_path:
        return False
    
    try:
        # اختبار قراءة الملف
        df_products = pd.read_excel(file_path, sheet_name='المنتجات')
        df_stock = pd.read_excel(file_path, sheet_name='تحديث المخزون')
        
        print("✅ تم قراءة القالب بنجاح")
        print(f"📋 المنتجات: {len(df_products)} صف")
        print(f"📋 المخزون: {len(df_stock)} صف")
        
        print("\n📄 بيانات المنتجات:")
        print(df_products)
        
        print("\n📄 بيانات المخزون:")
        print(df_stock)
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار القالب: {str(e)}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء إنشاء قالب بسيط يعمل...")
    print("=" * 50)
    
    if test_template():
        print("✅ القالب جاهز للاستخدام")
        print("\n📋 التعليمات:")
        print("1. استخدم ملف working_template.xlsx")
        print("2. املأ البيانات المطلوبة")
        print("3. احفظ الملف")
        print("4. ارفعه في النظام")
    else:
        print("❌ فشل في إنشاء القالب")
    
    print("=" * 50)
    print("🏁 انتهى إنشاء القالب")

if __name__ == "__main__":
    main() 