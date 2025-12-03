#!/usr/bin/env python
"""إعادة تعيين كلمة مرور zakee.tahawi"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from accounts.models import User

username = 'zakee.tahawi'
new_password = '2beornot2beE@#$'

user = User.objects.get(username=username)
user.set_password(new_password)
user.save()

print(f"✅ تم إعادة تعيين كلمة المرور لـ {username}")
print(f"🔑 كلمة المرور الجديدة: {new_password}")
