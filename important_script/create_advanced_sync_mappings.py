"""
سكريبت إنشاء 11 تعيين جديد مطابق لتعيين 'المول 2024' في المزامنة المتقدمة مع إضافة رقم بجانب الاسم
شغّله عبر: python manage.py shell < create_advanced_sync_mappings.py
"""

from odoo_db_manager.google_sync_advanced import GoogleSheetMapping

try:
    original = GoogleSheetMapping.objects.get(name="النحاس 2025")
except GoogleSheetMapping.DoesNotExist:
    print("[ERROR] لا يوجد تعيين باسم 'النحاس 2025'")
    exit()

for i in range(1, 15):
    new_mapping = GoogleSheetMapping.objects.create(
        name=f"النحاس 2025 {i}",
        spreadsheet_id=original.spreadsheet_id,
        sheet_name=original.sheet_name,
        is_active=original.is_active,
        header_row=original.header_row,
        start_row=original.start_row,
        column_mappings=original.column_mappings,
        auto_create_customers=original.auto_create_customers,
        auto_create_orders=original.auto_create_orders,
        auto_create_inspections=original.auto_create_inspections,
        update_existing=original.update_existing,
        conflict_resolution=original.conflict_resolution,
        enable_reverse_sync=original.enable_reverse_sync,
        reverse_sync_fields=original.reverse_sync_fields,
        row_filter_conditions=original.row_filter_conditions,
        data_validation_rules=original.data_validation_rules,
        default_customer_category=original.default_customer_category,
        default_customer_type=original.default_customer_type,
        default_branch=original.default_branch,
        use_current_date_as_created=original.use_current_date_as_created,
    )
    print(f"تم إنشاء تعيين: {new_mapping.name}")

print("[DONE] تم إنشاء جميع التعيينات الجديدة.")
