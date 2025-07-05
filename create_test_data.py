#!/usr/bin/env python
"""
ملف قديم لإنشاء بيانات اختبارية لجميع الأقسام

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

User = get_user_model()

def create_test_data():
    print("🚀 بدء إنشاء البيانات الاختبارية...")
    
    # 1. إنشاء المستخدمين
    print("👥 إنشاء المستخدمين...")
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'مدير',
            'last_name': 'النظام',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ تم إنشاء المستخدم الإداري")
    
    # 2. إنشاء الفروع
    print("🏢 إنشاء الفروع...")
    branches_data = [
        {'name': 'الفرع الرئيسي', 'address': 'القاهرة - مصر الجديدة', 'phone': '01234567890'},
        {'name': 'فرع الإسكندرية', 'address': 'الإسكندرية - سيدي جابر', 'phone': '01234567891'},
        {'name': 'فرع الجيزة', 'address': 'الجيزة - المهندسين', 'phone': '01234567892'},
        {'name': 'فرع المنصورة', 'address': 'المنصورة - وسط البلد', 'phone': '01234567893'},
    ]
    
    branches = []
    for branch_data in branches_data:
        try:
            branch = Branch.objects.get(name=branch_data['name'])
            print(f"📋 الفرع موجود: {branch.name}")
        except Branch.DoesNotExist:
            branch = Branch.objects.create(**branch_data)
            print(f"✅ تم إنشاء فرع: {branch.name}")
        branches.append(branch)
    
    # 3. إنشاء مندوبي المبيعات
    print("💼 إنشاء مندوبي المبيعات...")
    salespersons_data = [
        {'name': 'أحمد محمد', 'phone': '01111111111', 'employee_id': '001'},
        {'name': 'فاطمة علي', 'phone': '01222222222', 'employee_id': '002'},
        {'name': 'محمد حسن', 'phone': '01333333333', 'employee_id': '003'},
        {'name': 'نورا سالم', 'phone': '01444444444', 'employee_id': '004'},
    ]
    
    salespersons = []
    for sp_data in salespersons_data:
        try:
            sp = Salesperson.objects.get(employee_id=sp_data['employee_id'])
            print(f"📋 المندوب موجود: {sp.name}")
        except Salesperson.DoesNotExist:
            sp = Salesperson.objects.create(**sp_data)
            print(f"✅ تم إنشاء مندوب: {sp.name}")
        salespersons.append(sp)
    
    # 4. إنشاء العملاء
    print("👤 إنشاء العملاء...")
    customers_data = [
        {
            'name': 'محمد أحمد السيد',
            'phone': '01500000001',
            'address': 'القاهرة - مدينة نصر - شارع مصطفى النحاس',
            'email': 'mohamed@example.com',
            'customer_type': 'individual',
            'status': 'active'
        },
        {
            'name': 'شركة الخواجة للمقاولات',
            'phone': '01500000002',
            'address': 'الجيزة - المهندسين - شارع جامعة الدول العربية',
            'email': 'company@example.com',
            'customer_type': 'company',
            'status': 'active'
        },
        {
            'name': 'سارة محمود علي',
            'phone': '01500000003',
            'address': 'الإسكندرية - سيدي جابر - شارع الحرية',
            'email': 'sara@example.com',
            'customer_type': 'individual',
            'status': 'active'
        },
        {
            'name': 'أحمد عبد الرحمن',
            'phone': '01500000004',
            'address': 'المنصورة - وسط البلد - شارع الجمهورية',
            'email': 'ahmed@example.com',
            'customer_type': 'individual',
            'status': 'vip'
        },
        {
            'name': 'مؤسسة النور للتجارة',
            'phone': '01500000005',
            'address': 'القاهرة - مصر الجديدة - شارع الحجاز',
            'email': 'nour@example.com',
            'customer_type': 'company',
            'status': 'vip'
        }
    ]
    
    customers = []
    for customer_data in customers_data:
        try:
            customer = Customer.objects.get(phone=customer_data['phone'])
            print(f"📋 العميل موجود: {customer.name}")
        except Customer.DoesNotExist:
            customer = Customer.objects.create(**customer_data)
            print(f"✅ تم إنشاء عميل: {customer.name}")
        customers.append(customer)
    
    # 5. إنشاء فئات المنتجات
    print("📦 إنشاء فئات المنتجات...")
    categories_data = [
        {'name': 'شبابيك ألومنيوم', 'description': 'شبابيك من الألومنيوم عالي الجودة'},
        {'name': 'أبواب ألومنيوم', 'description': 'أبواب من الألومنيوم المقاوم'},
        {'name': 'اكسسوارات', 'description': 'اكسسوارات ومكملات الألومنيوم'},
        {'name': 'زجاج', 'description': 'أنواع مختلفة من الزجاج'},
    ]
    
    categories = []
    for cat_data in categories_data:
        try:
            category = Category.objects.get(name=cat_data['name'])
            print(f"📋 الفئة موجودة: {category.name}")
        except Category.DoesNotExist:
            category = Category.objects.create(**cat_data)
            print(f"✅ تم إنشاء فئة: {category.name}")
        categories.append(category)

    # 6. إنشاء المنتجات
    print("🛠️ إنشاء المنتجات...")
    products_data = [
        {
            'name': 'شباك ألومنيوم 120x100',
            'description': 'شباك ألومنيوم مقاس 120x100 سم',
            'category': categories[0],
            'price': Decimal('1500.00'),
            'cost': Decimal('1200.00'),
            'stock_quantity': 50,
            'unit': 'قطعة'
        },
        {
            'name': 'باب ألومنيوم 200x90',
            'description': 'باب ألومنيوم مقاس 200x90 سم',
            'category': categories[1],
            'price': Decimal('2500.00'),
            'cost': Decimal('2000.00'),
            'stock_quantity': 30,
            'unit': 'قطعة'
        },
        {
            'name': 'مقبض ألومنيوم فاخر',
            'description': 'مقبض من الألومنيوم عالي الجودة',
            'category': categories[2],
            'price': Decimal('150.00'),
            'cost': Decimal('100.00'),
            'stock_quantity': 200,
            'unit': 'قطعة'
        },
        {
            'name': 'زجاج شفاف 6 مم',
            'description': 'زجاج شفاف سماكة 6 مم',
            'category': categories[3],
            'price': Decimal('80.00'),
            'cost': Decimal('60.00'),
            'stock_quantity': 100,
            'unit': 'متر مربع'
        }
    ]

    products = []
    for product_data in products_data:
        try:
            product = Product.objects.get(name=product_data['name'])
            print(f"📋 المنتج موجود: {product.name}")
        except Product.DoesNotExist:
            product = Product.objects.create(**product_data)
            print(f"✅ تم إنشاء منتج: {product.name}")
        products.append(product)
    
    # 7. إنشاء خطوط الإنتاج
    print("🏭 إنشاء خطوط الإنتاج...")
    production_lines_data = [
        {
            'name': 'خط إنتاج الشبابيك',
            'description': 'خط متخصص في إنتاج الشبابيك',
            'is_active': True
        },
        {
            'name': 'خط إنتاج الأبواب',
            'description': 'خط متخصص في إنتاج الأبواب',
            'is_active': True
        },
        {
            'name': 'خط التشطيب والتجميع',
            'description': 'خط التشطيب النهائي والتجميع',
            'is_active': True
        }
    ]
    
    production_lines = []
    for line_data in production_lines_data:
        try:
            line = ProductionLine.objects.get(name=line_data['name'])
            print(f"📋 خط الإنتاج موجود: {line.name}")
        except ProductionLine.DoesNotExist:
            line = ProductionLine.objects.create(**line_data)
            print(f"✅ تم إنشاء خط إنتاج: {line.name}")
        production_lines.append(line)

    # 8. إنشاء فرق التركيب
    print("👷 إنشاء فرق التركيب...")
    teams_data = [
        {
            'name': 'فريق القاهرة الأول',
            'technician_1_name': 'محمد الفني',
            'technician_1_phone': '01600000001',
            'technician_2_name': 'أحمد المساعد',
            'technician_2_phone': '01600000002',
            'branch': branches[0],
            'is_active': True
        },
        {
            'name': 'فريق الإسكندرية',
            'technician_1_name': 'علي الفني',
            'technician_1_phone': '01600000003',
            'technician_2_name': 'حسن المساعد',
            'technician_2_phone': '01600000004',
            'branch': branches[1],
            'is_active': True
        },
        {
            'name': 'فريق الجيزة',
            'technician_1_name': 'سامي الفني',
            'technician_1_phone': '01600000005',
            'technician_2_name': 'كريم المساعد',
            'technician_2_phone': '01600000006',
            'branch': branches[2],
            'is_active': True
        }
    ]

    teams = []
    for team_data in teams_data:
        try:
            team = InstallationTeamNew.objects.get(name=team_data['name'])
            print(f"📋 الفريق موجود: {team.name}")
        except InstallationTeamNew.DoesNotExist:
            team = InstallationTeamNew.objects.create(**team_data)
            print(f"✅ تم إنشاء فريق: {team.name}")
        teams.append(team)
    
    print("🎉 تم إنشاء جميع البيانات الاختبارية بنجاح!")
    print(f"📊 الإحصائيات:")
    print(f"   - الفروع: {len(branches)}")
    print(f"   - مندوبي المبيعات: {len(salespersons)}")
    print(f"   - العملاء: {len(customers)}")
    print(f"   - فئات المنتجات: {len(categories)}")
    print(f"   - المنتجات: {len(products)}")
    print(f"   - خطوط الإنتاج: {len(production_lines)}")
    print(f"   - فرق التركيب: {len(teams)}")

if __name__ == '__main__':
    create_test_data()
