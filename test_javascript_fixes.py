#!/usr/bin/env python
"""
اختبار إصلاحات JavaScript
"""
import os
import re
from pathlib import Path

def check_select2_i18n_files():
    """البحث عن ملفات تحمل select2 i18n/ar.js"""
    print("🔍 البحث عن ملفات تحمل select2 i18n/ar.js...")
    
    template_dirs = [
        'templates',
        'orders/templates',
        'inspections/templates', 
        'complaints/templates',
        'accounts/templates',
        'reports/templates'
    ]
    
    found_files = []
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'i18n/ar.js' in content:
                                    found_files.append(file_path)
                        except Exception as e:
                            print(f"خطأ في قراءة {file_path}: {e}")
    
    if found_files:
        print("❌ تم العثور على ملفات تحمل i18n/ar.js:")
        for file_path in found_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ لم يتم العثور على ملفات تحمل i18n/ar.js")
        return True

def check_javascript_errors():
    """البحث عن أخطاء JavaScript محتملة"""
    print("🔍 البحث عن أخطاء JavaScript محتملة...")
    
    # البحث عن متغيرات غير معرفة
    error_patterns = [
        r'\bI\s*=',  # متغير I
        r'\.innerHTML\s*=.*notificationsList',  # استخدام innerHTML بدون تحقق
        r'document\.querySelector.*nextElementSibling.*\.querySelector',  # سلسلة طويلة بدون تحقق
    ]
    
    template_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.html') and 'templates' in root:
                template_files.append(os.path.join(root, file))
    
    issues_found = []
    
    for file_path in template_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in error_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues_found.append(f"{file_path}: {pattern}")
        except Exception as e:
            continue
    
    if issues_found:
        print("⚠️ تم العثور على مشاكل محتملة:")
        for issue in issues_found:
            print(f"   - {issue}")
        return False
    else:
        print("✅ لم يتم العثور على مشاكل JavaScript واضحة")
        return True

def check_notification_elements():
    """التحقق من وجود عناصر الإشعارات في base.html"""
    print("🔍 التحقق من عناصر الإشعارات في base.html...")
    
    base_template = 'templates/base.html'
    
    if not os.path.exists(base_template):
        print("❌ لم يتم العثور على base.html")
        return False
    
    try:
        with open(base_template, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            'id="notificationsDropdown"',
            'id="notification-count-badge"',
            'updateRecentNotifications',
            'updateNotificationCount'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print("❌ عناصر مفقودة:")
            for element in missing_elements:
                print(f"   - {element}")
            return False
        else:
            print("✅ جميع عناصر الإشعارات موجودة")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في قراءة base.html: {e}")
        return False

def check_payment_status_template():
    """التحقق من إصلاح حقل حالة المديونية"""
    print("🔍 التحقق من إصلاح حقل حالة المديونية...")
    
    inspection_form = 'inspections/templates/inspections/inspection_form.html'
    
    if not os.path.exists(inspection_form):
        print("❌ لم يتم العثور على inspection_form.html")
        return False
    
    try:
        with open(inspection_form, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # التحقق من وجود العرض الجديد لحالة المديونية
        if 'form-control-plaintext' in content and 'badge bg-success' in content:
            print("✅ تم تحديث عرض حالة المديونية بنجاح")
            return True
        else:
            print("❌ لم يتم تحديث عرض حالة المديونية")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في قراءة inspection_form.html: {e}")
        return False

def run_all_checks():
    """تشغيل جميع الفحوصات"""
    print("🚀 بدء فحص إصلاحات JavaScript...\n")
    
    checks = [
        ("ملفات Select2 i18n", check_select2_i18n_files),
        ("أخطاء JavaScript", check_javascript_errors),
        ("عناصر الإشعارات", check_notification_elements),
        ("حقل حالة المديونية", check_payment_status_template),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"🧪 فحص: {check_name}")
        print('='*50)
        
        try:
            if check_func():
                print(f"✅ نجح فحص: {check_name}")
                passed += 1
            else:
                print(f"❌ فشل فحص: {check_name}")
                failed += 1
        except Exception as e:
            print(f"💥 خطأ في فحص {check_name}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print("📊 نتائج فحص الإصلاحات:")
    print(f"✅ نجح: {passed}")
    print(f"❌ فشل: {failed}")
    print(f"📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    print('='*50)
    
    if failed == 0:
        print("🎉 جميع الفحوصات نجحت! تم إصلاح مشاكل JavaScript.")
    else:
        print("⚠️ بعض الفحوصات فشلت. يرجى مراجعة الأخطاء أعلاه.")

if __name__ == "__main__":
    run_all_checks()
