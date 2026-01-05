#!/usr/bin/env python
"""
سكريبت ربط المستخدمين بالأجهزة المصرح بها
يربط كل مستخدم بأجهزة فرعه تلقائياً
"""
import os
import sys
import django
from django.db import transaction

# إضافة المسار الأساسي للمشروع
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from accounts.models import User, BranchDevice, Branch


def sync_users_to_devices(branch_name=None, dry_run=False):
    """
    ربط المستخدمين بأجهزة فروعهم
    
    Args:
        branch_name: اسم الفرع (اختياري - إذا لم يحدد سيتم معالجة كل الفروع)
        dry_run: إذا كان True، فقط يعرض ما سيتم فعله دون تنفيذ
    """
    print("=" * 80)
    print("🔄 سكريبت ربط المستخدمين بالأجهزة المصرح بها")
    print("=" * 80)
    print()
    
    if dry_run:
        print("⚠️  وضع المعاينة (Dry Run) - لن يتم حفظ أي تغييرات")
        print()
    
    # تحديد الفروع المراد معالجتها
    if branch_name:
        branches = Branch.objects.filter(name=branch_name)
        if not branches.exists():
            print(f"❌ الفرع '{branch_name}' غير موجود")
            return
    else:
        branches = Branch.objects.all()
    
    total_users_updated = 0
    total_devices_linked = 0
    
    for branch in branches:
        print(f"🏢 الفرع: {branch.name}")
        print("-" * 80)
        
        # الحصول على مستخدمي الفرع النشطين
        users = User.objects.filter(branch=branch, is_active=True)
        users_count = users.count()
        
        # الحصول على أجهزة الفرع النشطة
        devices = BranchDevice.objects.filter(branch=branch, is_active=True)
        devices_count = devices.count()
        
        print(f"   👥 عدد المستخدمين النشطين: {users_count}")
        print(f"   💻 عدد الأجهزة النشطة: {devices_count}")
        
        if users_count == 0:
            print(f"   ⚠️  لا يوجد مستخدمين نشطين في هذا الفرع")
            print()
            continue
        
        if devices_count == 0:
            print(f"   ⚠️  لا يوجد أجهزة نشطة في هذا الفرع")
            print()
            continue
        
        print()
        print(f"   📋 تفاصيل الأجهزة:")
        for device in devices:
            print(f"      • {device.device_name} (مستخدمين حاليين: {device.authorized_users.count()})")
        print()
        
        # ربط كل مستخدم بأجهزة فرعه
        branch_users_updated = 0
        branch_devices_linked = 0
        
        for user in users:
            user_devices_before = user.authorized_devices.count()
            
            if not dry_run:
                with transaction.atomic():
                    # إضافة جميع أجهزة الفرع للمستخدم (بدون حذف الموجودة)
                    new_devices = 0
                    for device in devices:
                        if device not in user.authorized_devices.all():
                            user.authorized_devices.add(device)
                            new_devices += 1
                    
                    user_devices_after = user.authorized_devices.count()
                    
                    if new_devices > 0:
                        print(f"   ✅ {user.username}: أضيف {new_devices} جهاز (الإجمالي: {user_devices_after})")
                        branch_users_updated += 1
                        branch_devices_linked += new_devices
                    else:
                        print(f"   ℹ️  {user.username}: مرتبط بالفعل بكل الأجهزة ({user_devices_after})")
            else:
                # وضع المعاينة
                missing_devices = []
                for device in devices:
                    if device not in user.authorized_devices.all():
                        missing_devices.append(device.device_name)
                
                if missing_devices:
                    print(f"   📝 {user.username}: سيتم إضافة {len(missing_devices)} جهاز: {', '.join(missing_devices)}")
                    branch_users_updated += 1
                    branch_devices_linked += len(missing_devices)
                else:
                    print(f"   ℹ️  {user.username}: مرتبط بالفعل بكل الأجهزة ({user_devices_before})")
        
        print()
        print(f"   📊 نتائج الفرع:")
        print(f"      • مستخدمين تم تحديثهم: {branch_users_updated}")
        print(f"      • أجهزة تم ربطها: {branch_devices_linked}")
        print()
        
        total_users_updated += branch_users_updated
        total_devices_linked += branch_devices_linked
    
    print("=" * 80)
    print("📊 النتيجة النهائية:")
    print("=" * 80)
    print(f"   🏢 عدد الفروع المعالجة: {branches.count()}")
    print(f"   👥 إجمالي المستخدمين المحدثين: {total_users_updated}")
    print(f"   💻 إجمالي الأجهزة المربوطة: {total_devices_linked}")
    print()
    
    if dry_run:
        print("⚠️  وضع المعاينة - لم يتم حفظ أي تغييرات")
        print("   لتنفيذ التغييرات، شغل السكريبت بدون --dry-run")
    else:
        print("✅ تم حفظ جميع التغييرات بنجاح!")
    
    print("=" * 80)


def show_current_status():
    """عرض الحالة الحالية للنظام"""
    print("=" * 80)
    print("📊 الحالة الحالية للنظام")
    print("=" * 80)
    print()
    
    branches = Branch.objects.all()
    
    for branch in branches:
        users = User.objects.filter(branch=branch, is_active=True)
        devices = BranchDevice.objects.filter(branch=branch, is_active=True)
        
        if users.count() == 0 and devices.count() == 0:
            continue
        
        print(f"🏢 {branch.name}")
        print(f"   👥 مستخدمين: {users.count()}")
        print(f"   💻 أجهزة: {devices.count()}")
        
        # عرض المستخدمين الذين ليس لديهم أجهزة
        users_without_devices = [u for u in users if u.authorized_devices.count() == 0]
        if users_without_devices:
            print(f"   ⚠️  مستخدمين بدون أجهزة: {len(users_without_devices)}")
            for user in users_without_devices[:5]:  # عرض أول 5 فقط
                print(f"      • {user.username}")
            if len(users_without_devices) > 5:
                print(f"      ... و {len(users_without_devices) - 5} آخرين")
        
        print()
    
    print("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ربط المستخدمين بأجهزة فروعهم')
    parser.add_argument('--branch', '-b', help='اسم الفرع (اختياري)')
    parser.add_argument('--dry-run', '-d', action='store_true', 
                       help='معاينة فقط دون حفظ التغييرات')
    parser.add_argument('--status', '-s', action='store_true',
                       help='عرض الحالة الحالية فقط')
    
    args = parser.parse_args()
    
    if args.status:
        show_current_status()
    else:
        sync_users_to_devices(branch_name=args.branch, dry_run=args.dry_run)
