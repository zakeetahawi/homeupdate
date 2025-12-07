#!/usr/bin/env python
"""
أداة لتحديث بصمة جهاز موجود
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import BranchDevice

def update_device_fingerprint(device_name, new_fingerprint):
    """تحديث بصمة جهاز"""
    try:
        device = BranchDevice.objects.get(device_name=device_name)
        old_fingerprint = device.device_fingerprint
        device.device_fingerprint = new_fingerprint
        device.save()
        
        print(f"✅ تم تحديث بصمة الجهاز '{device_name}' بنجاح!")
        print(f"   البصمة القديمة: {old_fingerprint[:16]}...")
        print(f"   البصمة الجديدة: {new_fingerprint[:16]}...")
        print(f"   الفرع: {device.branch.name}")
        
    except BranchDevice.DoesNotExist:
        print(f"❌ الجهاز '{device_name}' غير موجود")
        print("\nالأجهزة المتاحة:")
        for dev in BranchDevice.objects.all():
            print(f"  - {dev.device_name} ({dev.branch.name})")
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("الاستخدام:")
        print(f"  python {sys.argv[0]} <اسم_الجهاز> <البصمة_الجديدة>")
        print("\nمثال:")
        print(f"  python {sys.argv[0]} زكي 2ee032f0dbed423a16fa01869c10fc8c07d55a1f7c8b06f2df5a4ea4fd9ca7ba")
        sys.exit(1)
    
    device_name = sys.argv[1]
    new_fingerprint = sys.argv[2]
    update_device_fingerprint(device_name, new_fingerprint)
