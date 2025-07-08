#!/usr/bin/env python
"""
سكريبت لإنشاء ترحيلات نظيفة للتطبيقات بالترتيب الصحيح
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """تنفيذ أمر في السطر الأوامر"""
    print(f"\n$ {command}")
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)
    
    return result.stdout

def main():
    # تحديد مسار المشروع
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("\n=== بدء إنشاء ترحيلات نظيفة ===")
    
    # حذف مجلدات الترحيلات القديمة
    print("\n=== حذف الترحيلات القديمة ===")
    apps = [
        'accounts',
        'contenttypes',
        'sessions',
        'admin',
        'auth',
        'odoo_db_manager',
        'orders',
        'manufacturing',
    ]
    
    for app in apps:
        migrations_dir = os.path.join(project_dir, app, 'migrations')
        if os.path.exists(migrations_dir):
            print(f"حذف مجلد الترحيلات لـ {app}")
            for item in os.listdir(migrations_dir):
                if item != '__init__.py' and item != '__pycache__':
                    item_path = os.path.join(migrations_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        print(f"  - حذف ملف: {item}")
                    elif os.path.isdir(item_path):
                        import shutil
                        shutil.rmtree(item_path)
                        print(f"  - حذف مجلد: {item}")
    
    # حذف ملف قاعدة البيانات
    db_path = os.path.join(project_dir, 'db.sqlite3')
    if os.path.exists(db_path):
        print("\nحذف ملف قاعدة البيانات القديم")
        os.remove(db_path)
    
    # إنشاء ترحيلات التطبيقات بالترتيب الصحيح
    print("\n=== إنشاء الترحيلات الجديدة ===")
    
    # 1. التطبيقات الأساسية أولاً
    core_apps = [
        'contenttypes',
        'auth',
        'admin',
        'sessions',
        'accounts',
    ]
    
    for app in core_apps:
        print(f"\nإنشاء ترحيلات لـ {app}")
        run_command(f"python manage.py makemigrations {app}", cwd=project_dir)
    
    # 2. تطبيق orders
    print("\nإنشاء ترحيلات لـ orders")
    run_command("python manage.py makemigrations orders", cwd=project_dir)
    
    # 3. تطبيق manufacturing
    print("\nإنشاء ترحيلات لـ manufacturing")
    run_command("python manage.py makemigrations manufacturing", cwd=project_dir)
    
    # 4. تطبيق odoo_db_manager
    print("\nإنشاء ترحيلات لـ odoo_db_manager")
    run_command("python manage.py makemigrations odoo_db_manager", cwd=project_dir)
    
    # تنفيذ الترحيلات
    print("\n=== تنفيذ الترحيلات ===")
    run_command("python manage.py migrate", cwd=project_dir)
    
    print("\n=== تم إنشاء الترحيلات وتنفيذها بنجاح ===")

if __name__ == "__main__":
    main()
