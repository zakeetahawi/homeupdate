#!/usr/bin/env python
"""
سكريبت اختبار صلاحيات المعاينات
يختبر ما إذا كان مديري النظام يمكنهم تعديل معاينات فروع أخرى
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_system.settings')
django.setup()

from inspections.models import Inspection
from accounts.models import User, Branch
from django.core.exceptions import ValidationError

print("="*70)
print("اختبار صلاحيات المعاينات")
print("="*70)

# 1. اختبار حسابك
print("\n1️⃣ اختبار حساب zakee.tahawi:")
print("-" * 70)
try:
    admin = User.objects.get(username='zakee.tahawi')
    print(f"✅ المستخدم: {admin.username}")
    print(f"   - is_superuser: {admin.is_superuser}")
    print(f"   - is_staff: {admin.is_staff}")
    print(f"   - is_branch_manager: {getattr(admin, 'is_branch_manager', False)}")
    print(f"   - الفرع: {admin.branch.name if admin.branch else 'N/A'}")
    
    is_allowed = (
        admin.is_superuser or 
        admin.is_staff or 
        getattr(admin, 'is_branch_manager', False)
    )
    print(f"\n   💡 هل مسموح لك بتعديل أي فرع: {'✅ نعم' if is_allowed else '❌ لا'}")
except User.DoesNotExist:
    print("❌ المستخدم غير موجود!")
    exit(1)

# 2. اختبار تعديل معاينة من فرع آخر
print("\n2️⃣ اختبار تعديل معاينة من فرع آخر:")
print("-" * 70)

inspection = Inspection.objects.filter(branch__name='Open Air').first()
if inspection:
    print(f"   المعاينة: #{inspection.id}")
    print(f"   فرع المعاينة: {inspection.branch.name}")
    print(f"   فرعك: {admin.branch.name}")
    print(f"   المنشئ الأصلي: {inspection.created_by.username if inspection.created_by else 'N/A'}")
    
    # حفظ البيانات الأصلية
    original_created_by = inspection.created_by
    original_branch = inspection.branch
    
    # تعيين created_by إليك ومحاولة التحقق
    inspection.created_by = admin
    
    try:
        inspection.clean()
        print("\n   ✅ النتيجة: نجح - لا توجد أخطاء!")
        print("   ✅ يمكنك تعديل المعاينات من أي فرع")
    except ValidationError as e:
        print(f"\n   ❌ النتيجة: فشل - {e.message}")
        print("   ❌ لا يمكنك تعديل معاينات فروع أخرى")
    
    # إعادة البيانات الأصلية
    inspection.created_by = original_created_by
else:
    print("   ⚠️ لا توجد معاينات في فرع Open Air")

# 3. اختبار الكود المصدري
print("\n3️⃣ التحقق من الكود المصدري:")
print("-" * 70)

import inspect
clean_source = inspect.getsource(Inspection.clean)

if 'is_branch_manager' in clean_source:
    print("   ✅ الكود يحتوي على فحص is_branch_manager")
else:
    print("   ❌ الكود لا يحتوي على فحص is_branch_manager")

if 'is_staff' in clean_source:
    print("   ✅ الكود يحتوي على فحص is_staff")
else:
    print("   ❌ الكود لا يحتوي على فحص is_staff")

# 4. نصائح
print("\n4️⃣ نصائح:")
print("-" * 70)
print("""
   إذا كانت النتيجة ✅ نعم لكن لا زالت تظهر لك رسالة الخطأ:
   
   1. امسح cache المتصفح:
      - Chrome: Ctrl+Shift+Delete
      - Firefox: Ctrl+Shift+Delete
   
   2. أعد تحميل الصفحة بالقوة:
      - Ctrl+Shift+R (أو Cmd+Shift+R على Mac)
   
   3. تأكد من أنك تستخدم حساب zakee.tahawi
   
   4. جرب في نافذة تصفح خاص (Incognito/Private)
""")

print("="*70)
print("انتهى الاختبار")
print("="*70)
