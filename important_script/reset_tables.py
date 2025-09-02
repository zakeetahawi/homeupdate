"""
سكريبت تصفير جداول العملاء والطلبات والمعاينات وأوامر التصنيع والتركيبات في Django
يمكنك تشغيله عبر: python manage.py shell < reset_tables.py
"""

from customers.models import Customer
from orders.models import Order, OrderItem, Payment, OrderStatusLog, ManufacturingDeletionLog
from inspections.models import Inspection
from manufacturing.models import ManufacturingOrder
from installations.models import InstallationSchedule


print("[INFO] حذف جميع بيانات Inspection ...")
Inspection.objects.all().delete()
print("[INFO] حذف جميع بيانات ManufacturingOrder ...")
ManufacturingOrder.objects.all().delete()
print("[INFO] حذف جميع بيانات OrderStatusLog ...")
OrderStatusLog.objects.all().delete()
print("[INFO] حذف جميع بيانات ManufacturingDeletionLog ...")
ManufacturingDeletionLog.objects.all().delete()
print("[INFO] حذف جميع بيانات OrderItem ...")
OrderItem.objects.all().delete()
print("[INFO] حذف جميع بيانات Payment ...")
Payment.objects.all().delete()
print("[INFO] حذف جميع بيانات Order ...")
Order.objects.all().delete()
print("[INFO] حذف جميع بيانات Customer ...")
Customer.objects.all().delete()
print("[INFO] حذف جميع بيانات InstallationSchedule ...")
InstallationSchedule.objects.all().delete()

print("[DONE] تم تصفير جميع الجداول المطلوبة بالترتيب الصحيح.")
