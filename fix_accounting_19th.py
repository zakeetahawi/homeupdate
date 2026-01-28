import os
from datetime import date

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from installation_accounting.models import InstallationCard
from installation_accounting.signals import sync_technician_shares
from installations.models import InstallationSchedule


def backfill_from_19th():
    # التاريخ المحدد: 19 من هذا الشهر (يناير 2026)
    start_date = date(2026, 1, 19)
    print(f"Starting backfill from {start_date}...")

    # جلب التركيبات المكتملة أو التعديلات المكتملة منذ ذلك التاريخ
    # نعتمد على تاريخ الإكمال (completion_date)
    # ملاحظة: التحقق من وجود الطلب (order) مهم لتجنب الأخطاء
    installations = InstallationSchedule.objects.filter(
        status__in=['completed', 'modification_completed'],
        completion_date__gte=start_date,
        order__isnull=False
    ).select_related('order', 'order__customer').prefetch_related('technicians')

    print(f"Found {installations.count()} installations to process.")

    created_count = 0
    updated_count = 0

    for inst in installations:
        # إنشاء أو تحديث بطاقة المحاسبة
        card, created = InstallationCard.objects.update_or_create(
            installation_schedule=inst,
            defaults={
                'windows_count': inst.windows_count or 0,
                'completion_date': inst.completion_date,
            }
        )
        
        # مزامنة حصص الفنيين
        sync_technician_shares(card)

        if created:
            created_count += 1
        else:
            updated_count += 1

    print(f"Processing finished.")
    print(f"Newly Created Cards: {created_count}")
    print(f"Updated Cards: {updated_count}")

if __name__ == "__main__":
    backfill_from_19th()
