import datetime

from django.db import transaction
from django.utils import timezone

from manufacturing.models import ManufacturingOrder
from orders.models import OrderStatusLog

end = timezone.now()
start = end - datetime.timedelta(days=7)
logs = OrderStatusLog.objects.filter(
    created_at__range=(start, end),
    notes__icontains="مزامنة حالة الطلب",
    changed_by__isnull=True,
).select_related("order")
print("to_fix:", logs.count())
updated = 0
with transaction.atomic():
    for l in logs:
        before = (l.id, l.order.order_number if l.order else None, l.changed_by_id)
        mfg = ManufacturingOrder.objects.filter(order=l.order).first()
        cb = None
        if mfg and getattr(mfg, "created_by", None):
            cb = mfg.created_by
        elif l.order and getattr(l.order, "created_by", None):
            cb = l.order.created_by
        if cb:
            l.changed_by = cb
            l.save(update_fields=["changed_by"])
            updated += 1
            print(
                "UPDATED",
                before,
                "=>",
                l.changed_by_id,
                getattr(l.changed_by, "username", None),
            )
        else:
            print("NO_CHANGED_BY_FOR", before)
print("TOTAL_UPDATED:", updated)
