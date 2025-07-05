#!/usr/bin/env python
"""
ملف قديم لإنشاء بيانات اختبارية للتركيبات

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
    customers = Customer.objects.all()[:5]
    
    if not customers:
        print("❌ لا توجد عملاء في النظام")
        return
    
    installations_data = [
        {
            'customer_name': 'محمد أحمد السيد',
            'customer_phone': '01500000001',
            'customer_address': 'القاهرة - مدينة نصر',
            'windows_count': 4,
            'location_type': 'residential',
            'priority': 'normal',
            'status': 'pending',
            'order_date': date.today(),
            'scheduled_date': date.today() + timedelta(days=7),
            'salesperson_name': 'أحمد محمد',
            'branch_name': 'الفرع الرئيسي'
        },
        {
            'customer_name': 'سارة محمود علي',
            'customer_phone': '01500000003',
            'customer_address': 'الإسكندرية - سيدي جابر',
            'windows_count': 6,
            'location_type': 'residential',
            'priority': 'high',
            'status': 'in_production',
            'order_date': date.today() - timedelta(days=3),
            'scheduled_date': date.today() + timedelta(days=5),
            'salesperson_name': 'فاطمة علي',
            'branch_name': 'فرع الإسكندرية'
        },
        {
            'customer_name': 'أحمد عبد الرحمن',
            'customer_phone': '01500000004',
            'customer_address': 'المنصورة - وسط البلد',
            'windows_count': 8,
            'location_type': 'commercial',
            'priority': 'urgent',
            'status': 'ready',
            'order_date': date.today() - timedelta(days=10),
            'scheduled_date': date.today() + timedelta(days=2),
            'salesperson_name': 'محمد حسن',
            'branch_name': 'فرع المنصورة'
        }
    ]
    
    created_count = 0
    for installation_data in installations_data:
        try:
            # إنشاء التركيب
            installation = InstallationNew(
                customer_name=installation_data['customer_name'],
                customer_phone=installation_data['customer_phone'],
                customer_address=installation_data['customer_address'],
                windows_count=installation_data['windows_count'],
                location_type=installation_data['location_type'],
                priority=installation_data['priority'],
                status=installation_data['status'],
                order_date=installation_data['order_date'],
                scheduled_date=installation_data['scheduled_date'],
                salesperson_name=installation_data['salesperson_name'],
                branch_name=installation_data['branch_name']
            )
            installation.save()

            print(f"✅ تم إنشاء تركيب: {installation.customer_name} - {installation.windows_count} شباك")
            created_count += 1

        except Exception as e:
            print(f"❌ خطأ في إنشاء تركيب {installation_data['customer_name']}: {e}")
    
    print(f"\n🎉 تم إنشاء {created_count} تركيب جديد!")
    print(f"📊 إجمالي التركيبات في النظام: {InstallationNew.objects.count()}")
    
    # عرض إحصائيات الحالات
    print("\n📈 إحصائيات الحالات:")
    statuses = InstallationNew.objects.values_list('status', flat=True).distinct()
    for status in statuses:
        count = InstallationNew.objects.filter(status=status).count()
        print(f"   - {status}: {count}")

if __name__ == '__main__':
    create_simple_installations()
