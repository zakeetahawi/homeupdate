#!/bin/bash
# حذف جميع ملفات الترحيلات (ما عدا __init__.py) من كل التطبيقات المحلية

echo "حذف ملفات الترحيلات..."

# حذف ملفات الترحيلات من كل التطبيقات
rm -f accounts/migrations/0*.py
rm -f customers/migrations/0*.py
rm -f factory/migrations/0*.py
rm -f inspections/migrations/0*.py
rm -f installations/migrations/0*.py
rm -f inventory/migrations/0*.py
rm -f orders/migrations/0*.py
rm -f odoo_db_manager/migrations/0*.py
rm -f reports/migrations/0*.py

echo "حذف قاعدة البيانات وإعادة إنشائها..."

# حذف قاعدة البيانات crm_system وإعادة إنشائها
sudo -u postgres psql -c "DROP DATABASE IF EXISTS crm_system;"
sudo -u postgres psql -c "CREATE DATABASE crm_system;"

echo "إنشاء الترحيلات من جديد..."

# إنشاء الترحيلات من جديد
python manage.py makemigrations

echo "تنفيذ الترحيلات..."

# تنفيذ الترحيلات
python manage.py migrate

echo "تمت العملية بنجاح!"
