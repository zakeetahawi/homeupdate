#!/usr/bin/env python
"""
ملف قديم لإنشاء سير عمل بسيط

ملاحظة: تم إيقاف استخدام هذا الملف بعد إعادة هيكلة نظام المصنع والتركيبات.
سيتم تحديثه لاحقاً ليعمل مع النماذج الجديدة.
"""
print("⚠️  هذا الملف قديم ولم يعد يعمل مع الإصدار الحالي من النظام.")
print("⚠️  سيتم تحديثه لاحقاً ليعمل مع نظام المصنع والتركيبات الجديد.")
print("⚠️  لم يتم إنشاء أي بيانات.")

def main():
    pass

if __name__ == '__main__':
    main()

def create_simple_workflow():
    print("🚀 إنشاء سير عمل بسيط...")
    
    # التحقق من وجود عملاء
    customers = Customer.objects.all()[:3]
    if not customers:
        print("❌ لا توجد عملاء في النظام")
        return
    
    print(f"📋 تم العثور على {len(customers)} عميل")
    
    # إنشاء طلبات بسيطة
    for i, customer in enumerate(customers):
        try:
            # إنشاء طلب
            order_number = f'ORD-{date.today().strftime("%Y%m%d")}-{i+1:03d}'
            
            # التحقق من عدم وجود الطلب
            if Order.objects.filter(order_number=order_number).exists():
                print(f"📋 الطلب {order_number} موجود بالفعل")
                continue
            
            order = Order(
                customer=customer,
                order_number=order_number,
                selected_types=['installation'],
                delivery_type='home',
                delivery_address=customer.address,
                notes=f'طلب تركيب للعميل {customer.name}',
                status='normal',
                total_amount=Decimal('5000.00')
            )
            order.save()
            print(f"✅ تم إنشاء طلب: {order.order_number}")
            
            # إنشاء تركيب مرتبط بالطلب
            installation = InstallationNew(
                order=order,
                customer_name=customer.name,
                customer_phone=customer.phone,
                customer_address=customer.address,
                windows_count=3 + i,
                location_type='residential',
                priority='high' if i == 0 else 'normal',
                order_date=date.today(),
                scheduled_date=date.today() + timedelta(days=7 + i),
                status='pending',
                salesperson_name='مندوب المبيعات',
                branch_name='الفرع الرئيسي'
            )
            installation.save()
            print(f"✅ تم إنشاء تركيب: {installation.customer_name} - {installation.windows_count} شباك")
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء طلب للعميل {customer.name}: {e}")
    
    # عرض الإحصائيات
    print(f"\n📊 الإحصائيات النهائية:")
    print(f"   - إجمالي الطلبات: {Order.objects.count()}")
    print(f"   - إجمالي التركيبات: {InstallationNew.objects.count()}")
    
    # عرض التركيبات حسب الحالة
    print(f"\n📈 التركيبات حسب الحالة:")
    statuses = InstallationNew.objects.values_list('status', flat=True).distinct()
    for status in statuses:
        count = InstallationNew.objects.filter(status=status).count()
        print(f"   - {status}: {count}")

if __name__ == '__main__':
    create_simple_workflow()
