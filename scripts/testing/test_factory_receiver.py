#!/usr/bin/env python
"""
سكريبت اختبار دور "مسؤول استلام مصنع"
====================================

هذا السكريبت يقوم بفحص وإنشاء مستخدم تجريبي بدور مسؤول استلام مصنع
ويتحقق من جميع الصلاحيات والمجموعات.

الاستخدام:
----------
python test_factory_receiver.py
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from accounts.models import User
from django.db import IntegrityError


def print_header(title):
    """طباعة عنوان منسق"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_group_exists():
    """التحقق من وجود مجموعة مسؤول استلام مصنع"""
    print_header("1. التحقق من المجموعة")
    
    try:
        group = Group.objects.get(name='مسؤول استلام مصنع')
        print(f"✅ المجموعة موجودة: {group.name}")
        print(f"   عدد الصلاحيات: {group.permissions.count()}")
        
        print("\n📋 الصلاحيات:")
        for perm in group.permissions.all().select_related('content_type'):
            print(f"   → {perm.content_type.app_label}.{perm.codename}")
            print(f"      {perm.name}")
        
        return group
    except Group.DoesNotExist:
        print("❌ المجموعة غير موجودة!")
        return None


def check_model_field():
    """التحقق من وجود حقل is_factory_receiver"""
    print_header("2. التحقق من حقل User Model")
    
    if hasattr(User, 'is_factory_receiver'):
        print("✅ حقل is_factory_receiver موجود في User model")
        
        # عرض عدد المستخدمين
        receiver_count = User.objects.filter(is_factory_receiver=True).count()
        print(f"   عدد مسؤولي الاستلام الحاليين: {receiver_count}")
        
        return True
    else:
        print("❌ حقل is_factory_receiver غير موجود!")
        return False


def check_role_hierarchy():
    """التحقق من ROLE_HIERARCHY"""
    print_header("3. التحقق من ROLE_HIERARCHY")
    
    from accounts.models import ROLE_HIERARCHY
    
    if 'factory_receiver' in ROLE_HIERARCHY:
        role_data = ROLE_HIERARCHY['factory_receiver']
        print("✅ factory_receiver موجود في ROLE_HIERARCHY")
        print(f"   المستوى: {role_data.get('level')}")
        print(f"   الاسم: {role_data.get('display')}")
        print(f"   يرث من: {role_data.get('inherits_from')}")
        print(f"   الصلاحيات: {', '.join(role_data.get('permissions', []))}")
        return True
    else:
        print("❌ factory_receiver غير موجود في ROLE_HIERARCHY!")
        return False


def create_test_user():
    """إنشاء مستخدم تجريبي"""
    print_header("4. إنشاء مستخدم تجريبي")
    
    username = 'factory_receiver_test'
    
    # التحقق من وجود المستخدم
    if User.objects.filter(username=username).exists():
        print(f"⚠️  المستخدم {username} موجود مسبقاً")
        user = User.objects.get(username=username)
        
        # تحديث الدور
        user.is_factory_receiver = True
        user.is_staff = True
        user.is_active = True
        user.save()
        print("   تم تحديث الدور إلى is_factory_receiver=True")
    else:
        # إنشاء مستخدم جديد
        try:
            user = User.objects.create_user(
                username=username,
                password='test123',
                email='factory_receiver@test.com',
                first_name='مسؤول',
                last_name='الاستلام التجريبي',
                is_factory_receiver=True,
                is_staff=True,
                is_active=True
            )
            print(f"✅ تم إنشاء المستخدم: {username}")
            print(f"   كلمة المرور: test123")
        except IntegrityError as e:
            print(f"❌ خطأ في إنشاء المستخدم: {e}")
            return None
    
    # إضافة المستخدم للمجموعة
    group = Group.objects.get(name='مسؤول استلام مصنع')
    user.groups.add(group)
    print(f"✅ تم إضافة المستخدم لمجموعة: {group.name}")
    
    return user


def test_user_permissions(user):
    """اختبار صلاحيات المستخدم"""
    print_header("5. اختبار الصلاحيات")
    
    required_permissions = [
        'manufacturing.can_receive_fabric',
        'manufacturing.can_deliver_to_production_line',
        'manufacturing.can_view_fabric_receipts',
        'manufacturing.view_manufacturingorder',
    ]
    
    print(f"المستخدم: {user.username}")
    print(f"الدور: {user.get_user_role()}")
    print(f"عرض الدور: {user.get_user_role_display()}")
    print(f"\nالمجموعات ({user.groups.count()}):")
    for group in user.groups.all():
        print(f"   → {group.name}")
    
    print(f"\nفحص الصلاحيات المطلوبة:")
    all_passed = True
    
    for perm in required_permissions:
        app_label, codename = perm.split('.')
        has_perm = user.has_perm(perm)
        status = "✅" if has_perm else "❌"
        print(f"   {status} {perm}")
        
        if not has_perm:
            all_passed = False
    
    if all_passed:
        print("\n✅ جميع الصلاحيات موجودة!")
    else:
        print("\n⚠️  بعض الصلاحيات مفقودة!")
    
    return all_passed


def test_user_role_method(user):
    """اختبار method get_user_role"""
    print_header("6. اختبار Method get_user_role")
    
    role = user.get_user_role()
    expected_role = 'factory_receiver'
    
    if role == expected_role:
        print(f"✅ get_user_role() يعيد: '{role}'")
        print(f"✅ يتطابق مع القيمة المتوقعة: '{expected_role}'")
        return True
    else:
        print(f"❌ get_user_role() يعيد: '{role}'")
        print(f"❌ لا يتطابق مع القيمة المتوقعة: '{expected_role}'")
        return False


def generate_summary(results):
    """إنشاء ملخص النتائج"""
    print_header("📊 ملخص النتائج")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"إجمالي الاختبارات: {total}")
    print(f"✅ ناجح: {passed}")
    print(f"❌ فاشل: {failed}")
    print(f"النسبة: {(passed/total)*100:.1f}%")
    
    print("\nتفاصيل الاختبارات:")
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}")
    
    if passed == total:
        print("\n🎉 جميع الاختبارات نجحت!")
    else:
        print("\n⚠️  بعض الاختبارات فشلت. يرجى مراجعة التفاصيل أعلاه.")


def main():
    """الدالة الرئيسية"""
    print("\n" + "🏭" * 35)
    print("  اختبار دور مسؤول استلام مصنع")
    print("🏭" * 35)
    
    results = {}
    
    # 1. التحقق من المجموعة
    group = check_group_exists()
    results['وجود المجموعة'] = group is not None
    
    # 2. التحقق من الحقل
    field_exists = check_model_field()
    results['وجود الحقل'] = field_exists
    
    # 3. التحقق من ROLE_HIERARCHY
    hierarchy_exists = check_role_hierarchy()
    results['ROLE_HIERARCHY'] = hierarchy_exists
    
    # 4 & 5. إنشاء واختبار المستخدم
    if group and field_exists:
        user = create_test_user()
        
        if user:
            results['إنشاء المستخدم'] = True
            
            # اختبار الصلاحيات
            perms_ok = test_user_permissions(user)
            results['الصلاحيات'] = perms_ok
            
            # اختبار method
            role_ok = test_user_role_method(user)
            results['get_user_role()'] = role_ok
        else:
            results['إنشاء المستخدم'] = False
            results['الصلاحيات'] = False
            results['get_user_role()'] = False
    else:
        print("\n⚠️  لا يمكن إكمال الاختبارات بسبب فشل الفحوصات الأولية")
        results['إنشاء المستخدم'] = False
        results['الصلاحيات'] = False
        results['get_user_role()'] = False
    
    # ملخص النتائج
    generate_summary(results)
    
    print("\n" + "=" * 70)
    print("تم الانتهاء من الاختبار")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
