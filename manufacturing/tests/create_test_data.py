import json
import os
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal

import django
from django.core.exceptions import ValidationError as DjangoValidationError

# إعداد بيئة Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Branch, Salesperson
from customers.models import Customer
from inventory.models import Category as ProductCategory
from inventory.models import Product
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order, OrderItem

User = get_user_model()


def create_test_data():
    """إنشاء بيانات تجريبية لاختبار التكامل بين الطلبات وأوامر التصنيع"""
    print("\nبدء إنشاء البيانات التجريبية...")

    # التأكد من وجود مستخدم مسؤول
    admin_user, created = User.objects.get_or_create(
        username="admin",
        defaults={"email": "admin@example.com", "is_staff": True, "is_superuser": True},
    )
    if created:
        admin_user.set_password("admin123")
        admin_user.save()
        print("تم إنشاء مستخدم مسؤول جديد")

    # الحصول على الفروع
    branches = list(Branch.objects.all())
    if not branches:
        branches = [
            Branch.objects.create(name="الفرع الرئيسي", address="عنوان الفرع الرئيسي")
        ]
        print("تم إنشاء فرع افتراضي")

    # إنشاء بائعين إذا لم يكن هناك بائعين
    salespeople = list(Salesperson.objects.all())
    if not salespeople:
        salesperson = Salesperson.objects.create(
            user=admin_user, phone="+966501234567", branch=branches[0]
        )
        salespeople.append(salesperson)
        print("تم إنشاء بائع افتراضي")

    # إنشاء عملاء تجريبيين
    customers = []
    for i in range(1, 6):
        customer, created = Customer.objects.get_or_create(
            name=f"عميل تجريبي {i}",
            defaults={
                "phone": f"+96650123456{i}",
                "email": f"customer{i}@example.com",
                "address": f"عنوان العميل {i} - الرياض",
                "notes": f"ملاحظات خاصة بالعميل {i}",
            },
        )
        if created:
            print(f"تم إنشاء عميل جديد: {customer.name}")
        customers.append(customer)

    # إنشاء فئات منتجات
    categories = []
    for cat_name in ["أبواب", "نوافذ", "مطابخ", "ديكورات", "إكسسوارات"]:
        category, created = ProductCategory.objects.get_or_create(name=cat_name)
        if created:
            print(f"تم إنشاء فئة منتجات: {category.name}")
        categories.append(category)

    # إنشاء منتجات تجريبية
    products = []
    for i in range(1, 11):
        product, created = Product.objects.get_or_create(
            name=f"منتج تجريبي {i}",
            defaults={
                "category": random.choice(categories),
                "price": Decimal(random.randint(100, 5000)),
                "description": f"وصف المنتج التجريبي رقم {i}",
                "minimum_stock": random.randint(5, 20),
            },
        )
        if created:
            print(f"تم إنشاء منتج جديد: {product.name}")
        products.append(product)

    # إنشاء طلبات تجريبية
    orders = []
    for i in range(5):
        try:
            # إنشاء طلب جديد
            order = Order.objects.create(
                customer=random.choice(customers),
                salesperson=random.choice(salespeople),
                delivery_type=random.choice(["home", "branch"]),
                delivery_address=(
                    "عنوان التوصيل التجريبي" if random.choice([True, False]) else ""
                ),
                order_number=f"{timezone.now().strftime('%y')}-{random.randint(10, 99)}-{i+1:02d}",
                status=random.choice(["normal", "vip"]),
                selected_types=json.dumps(
                    [random.choice(["installation", "tailoring", "inspection"])]
                ),
                order_type="service",
                service_types=json.dumps(
                    [random.choice(["installation", "tailoring", "inspection"])]
                ),
                order_status=random.choice(
                    ["pending_approval", "pending", "in_progress", "ready_install", "completed"]
                ),
                invoice_number=f"INV-{random.randint(100, 999)}",
                contract_number=f"CT-{random.randint(100, 999)}",
                payment_verified=random.choice([True, False]),
                total_amount=Decimal(random.randint(1000, 5000)),
                paid_amount=Decimal(random.randint(0, 5000)),
                notes=f"ملاحظات الطلب التجريبي رقم {i+1}",
                created_by=admin_user,
                branch=random.choice(branches),
                final_price=Decimal(random.randint(1000, 5000)),
                expected_delivery_date=timezone.now().date()
                + timedelta(days=random.randint(1, 30)),
            )

            # إضافة عناصر للطلب
            for j in range(random.randint(1, 3)):  # 1-3 عناصر لكل طلب
                product = random.choice(products)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 5),
                    unit_price=product.price,
                    item_type=random.choice(["fabric", "accessory"]),
                    processing_status=random.choice(
                        ["pending", "processing", "warehouse", "factory"]
                    ),
                    notes=f"ملاحظات العنصر {j+1}",
                )

            print(f"تم إنشاء طلب جديد: {order.contract_number}")
            orders.append(order)

        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء الطلب: {str(e)}")
            continue

    # إنشاء أوامر تصنيع للطلبات التي تتطلب تصنيعاً
    def create_manufacturing_order(order):
        """إنشاء أمر تصنيع مرتبط بالطلب"""
        try:
            # التحقق مما إذا كان هناك أمر تصنيع موجود بالفعل لهذا الطلب
            if ManufacturingOrder.objects.filter(order=order).exists():
                print(f"يوجد بالفعل أمر تصنيع للطلب: {order.id}")
                return None

            # التأكد من وجود تاريخ تسليم متوقع
            expected_delivery = (
                order.expected_delivery_date
                or (timezone.now() + timedelta(days=30)).date()
            )

            # إنشاء أمر التصنيع
            mo = ManufacturingOrder.objects.create(
                order=order,
                order_type=(
                    order.order_type
                    if order.order_type in ["installation", "detail"]
                    else "custom"
                ),
                contract_number=f"CT-{random.randint(100, 999)}",
                invoice_number=f"INV-{random.randint(1000, 9999)}",
                order_date=order.order_date or timezone.now().date(),
                expected_delivery_date=expected_delivery,
                notes=f"أمر تصنيع للطلب {order.id}",
                status="pending",
            )

            print(f"تم إنشاء أمر تصنيع للطلب: {order.contract_number}")

            # إنشاء عناصر أمر التصنيع من عناصر الطلب
            for item in order.items.all():
                try:
                    ManufacturingOrderItem.objects.create(
                        manufacturing_order=mo,
                        product_name=(
                            item.product.name if item.product else "منتج غير محدد"
                        ),
                        quantity=item.quantity or 1,
                        specifications=item.notes or "لا توجد مواصفات محددة",
                        status="pending",
                    )
                except Exception as e:
                    print(f"خطأ في إنشاء عنصر أمر التصنيع: {str(e)}")

            return mo

        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء أمر التصنيع: {str(e)}")
            return None

    manufacturing_orders = []
    for order in Order.objects.all():
        mo = create_manufacturing_order(order)
        if mo:
            manufacturing_orders.append(mo)

    print("\nتم إنشاء البيانات التجريبية بنجاح!")
    print(f"- عدد العملاء: {len(customers)}")
    print(f"- عدد المنتجات: {len(products)}")
    print(f"- عدد الطلبات: {len(orders)}")
    print(f"- عدد أوامر التصنيع: {len(manufacturing_orders)}")
    print("\nيمكنك تسجيل الدخول باستخدام:")
    print("اسم المستخدم: admin")
    print("كلمة المرور: admin123")
    print("\nرابط لوحة التحكم: http://127.0.0.1:8000/admin/")
    print("رابط قائمة أوامر التصنيع: http://127.0.0.1:8000/manufacturing/")


if __name__ == "__main__":
    create_test_data()
