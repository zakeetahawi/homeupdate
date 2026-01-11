"""
هجرة البيانات لإنشاء شجرة الحسابات الافتراضية
"""

from django.db import migrations


def create_default_chart_of_accounts(apps, schema_editor):
    """إنشاء شجرة الحسابات الافتراضية"""
    AccountType = apps.get_model("accounting", "AccountType")
    Account = apps.get_model("accounting", "Account")

    # إنشاء أنواع الحسابات
    asset_type = AccountType.objects.create(
        name="الأصول",
        name_en="Assets",
        category="asset",
        code_prefix="1",
        normal_balance="debit",
        description="الأصول الثابتة والمتداولة",
    )

    liability_type = AccountType.objects.create(
        name="الالتزامات",
        name_en="Liabilities",
        category="liability",
        code_prefix="2",
        normal_balance="credit",
        description="الالتزامات قصيرة وطويلة الأجل",
    )

    equity_type = AccountType.objects.create(
        name="حقوق الملكية",
        name_en="Equity",
        category="equity",
        code_prefix="3",
        normal_balance="credit",
        description="رأس المال والأرباح المحتجزة",
    )

    revenue_type = AccountType.objects.create(
        name="الإيرادات",
        name_en="Revenue",
        category="revenue",
        code_prefix="4",
        normal_balance="credit",
        description="إيرادات المبيعات والخدمات",
    )

    expense_type = AccountType.objects.create(
        name="المصروفات",
        name_en="Expenses",
        category="expense",
        code_prefix="5",
        normal_balance="debit",
        description="مصروفات التشغيل والإدارة",
    )

    # ===== شجرة الأصول =====
    assets_root = Account.objects.create(
        code="1000",
        name="الأصول",
        name_en="Assets",
        account_type=asset_type,
        is_system_account=True,
        allow_transactions=False,
    )

    # الأصول المتداولة
    current_assets = Account.objects.create(
        code="1100",
        name="الأصول المتداولة",
        name_en="Current Assets",
        account_type=asset_type,
        parent=assets_root,
        is_system_account=True,
        allow_transactions=False,
    )

    # النقدية والبنوك
    cash_bank = Account.objects.create(
        code="1110",
        name="النقدية والبنوك",
        name_en="Cash and Banks",
        account_type=asset_type,
        parent=current_assets,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="1111",
        name="الصندوق",
        name_en="Cash",
        account_type=asset_type,
        parent=cash_bank,
    )
    Account.objects.create(
        code="1112",
        name="البنك",
        name_en="Bank",
        account_type=asset_type,
        parent=cash_bank,
    )
    Account.objects.create(
        code="1113",
        name="الشيكات تحت التحصيل",
        name_en="Checks Under Collection",
        account_type=asset_type,
        parent=cash_bank,
    )

    # الذمم المدينة
    receivables = Account.objects.create(
        code="1120",
        name="الذمم المدينة",
        name_en="Receivables",
        account_type=asset_type,
        parent=current_assets,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="1121",
        name="العملاء",
        name_en="Customers",
        account_type=asset_type,
        parent=receivables,
    )
    Account.objects.create(
        code="1122",
        name="أوراق القبض",
        name_en="Notes Receivable",
        account_type=asset_type,
        parent=receivables,
    )
    Account.objects.create(
        code="1123",
        name="سلف ومقدمات للموردين",
        name_en="Advances to Suppliers",
        account_type=asset_type,
        parent=receivables,
    )
    Account.objects.create(
        code="1124",
        name="ذمم موظفين",
        name_en="Employee Receivables",
        account_type=asset_type,
        parent=receivables,
    )

    # المخزون
    inventory = Account.objects.create(
        code="1130",
        name="المخزون",
        name_en="Inventory",
        account_type=asset_type,
        parent=current_assets,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="1131",
        name="مخزون الأقمشة",
        name_en="Fabric Inventory",
        account_type=asset_type,
        parent=inventory,
    )
    Account.objects.create(
        code="1132",
        name="مخزون الإكسسوارات",
        name_en="Accessories Inventory",
        account_type=asset_type,
        parent=inventory,
    )
    Account.objects.create(
        code="1133",
        name="مخزون المواد الخام",
        name_en="Raw Materials Inventory",
        account_type=asset_type,
        parent=inventory,
    )
    Account.objects.create(
        code="1134",
        name="مخزون المنتجات تامة الصنع",
        name_en="Finished Goods",
        account_type=asset_type,
        parent=inventory,
    )
    Account.objects.create(
        code="1135",
        name="مخزون تحت التصنيع",
        name_en="Work in Progress",
        account_type=asset_type,
        parent=inventory,
    )

    # الأصول الثابتة
    fixed_assets = Account.objects.create(
        code="1200",
        name="الأصول الثابتة",
        name_en="Fixed Assets",
        account_type=asset_type,
        parent=assets_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="1210",
        name="الأثاث والتجهيزات",
        name_en="Furniture and Fixtures",
        account_type=asset_type,
        parent=fixed_assets,
    )
    Account.objects.create(
        code="1220",
        name="المعدات والآلات",
        name_en="Equipment and Machinery",
        account_type=asset_type,
        parent=fixed_assets,
    )
    Account.objects.create(
        code="1230",
        name="السيارات",
        name_en="Vehicles",
        account_type=asset_type,
        parent=fixed_assets,
    )
    Account.objects.create(
        code="1240",
        name="أجهزة الكمبيوتر",
        name_en="Computers",
        account_type=asset_type,
        parent=fixed_assets,
    )
    Account.objects.create(
        code="1250",
        name="مجمع الإهلاك",
        name_en="Accumulated Depreciation",
        account_type=asset_type,
        parent=fixed_assets,
    )

    # ===== شجرة الالتزامات =====
    liabilities_root = Account.objects.create(
        code="2000",
        name="الالتزامات",
        name_en="Liabilities",
        account_type=liability_type,
        is_system_account=True,
        allow_transactions=False,
    )

    # الالتزامات المتداولة
    current_liabilities = Account.objects.create(
        code="2100",
        name="الالتزامات المتداولة",
        name_en="Current Liabilities",
        account_type=liability_type,
        parent=liabilities_root,
        is_system_account=True,
        allow_transactions=False,
    )

    # الذمم الدائنة
    payables = Account.objects.create(
        code="2110",
        name="الذمم الدائنة",
        name_en="Payables",
        account_type=liability_type,
        parent=current_liabilities,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="2111",
        name="الموردين",
        name_en="Suppliers",
        account_type=liability_type,
        parent=payables,
    )
    Account.objects.create(
        code="2112",
        name="أوراق الدفع",
        name_en="Notes Payable",
        account_type=liability_type,
        parent=payables,
    )
    Account.objects.create(
        code="2113",
        name="سلف ومقدمات من العملاء",
        name_en="Customer Advances",
        account_type=liability_type,
        parent=payables,
    )

    # المستحقات
    accruals = Account.objects.create(
        code="2120",
        name="المستحقات",
        name_en="Accruals",
        account_type=liability_type,
        parent=current_liabilities,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="2121",
        name="رواتب مستحقة",
        name_en="Salaries Payable",
        account_type=liability_type,
        parent=accruals,
    )
    Account.objects.create(
        code="2122",
        name="ضرائب مستحقة",
        name_en="Taxes Payable",
        account_type=liability_type,
        parent=accruals,
    )
    Account.objects.create(
        code="2123",
        name="تأمينات اجتماعية مستحقة",
        name_en="Social Insurance Payable",
        account_type=liability_type,
        parent=accruals,
    )
    Account.objects.create(
        code="2124",
        name="مصروفات مستحقة أخرى",
        name_en="Other Accrued Expenses",
        account_type=liability_type,
        parent=accruals,
    )

    # ===== شجرة حقوق الملكية =====
    equity_root = Account.objects.create(
        code="3000",
        name="حقوق الملكية",
        name_en="Equity",
        account_type=equity_type,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="3100",
        name="رأس المال",
        name_en="Capital",
        account_type=equity_type,
        parent=equity_root,
    )
    Account.objects.create(
        code="3200",
        name="الأرباح المحتجزة",
        name_en="Retained Earnings",
        account_type=equity_type,
        parent=equity_root,
    )
    Account.objects.create(
        code="3300",
        name="أرباح/خسائر العام",
        name_en="Current Year Earnings",
        account_type=equity_type,
        parent=equity_root,
    )
    Account.objects.create(
        code="3400",
        name="الاحتياطيات",
        name_en="Reserves",
        account_type=equity_type,
        parent=equity_root,
    )

    # ===== شجرة الإيرادات =====
    revenue_root = Account.objects.create(
        code="4000",
        name="الإيرادات",
        name_en="Revenue",
        account_type=revenue_type,
        is_system_account=True,
        allow_transactions=False,
    )

    # إيرادات المبيعات
    sales_revenue = Account.objects.create(
        code="4100",
        name="إيرادات المبيعات",
        name_en="Sales Revenue",
        account_type=revenue_type,
        parent=revenue_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="4110",
        name="مبيعات الستائر",
        name_en="Curtain Sales",
        account_type=revenue_type,
        parent=sales_revenue,
    )
    Account.objects.create(
        code="4120",
        name="مبيعات المفروشات",
        name_en="Furnishing Sales",
        account_type=revenue_type,
        parent=sales_revenue,
    )
    Account.objects.create(
        code="4130",
        name="مبيعات الإكسسوارات",
        name_en="Accessories Sales",
        account_type=revenue_type,
        parent=sales_revenue,
    )

    # إيرادات الخدمات
    service_revenue = Account.objects.create(
        code="4200",
        name="إيرادات الخدمات",
        name_en="Service Revenue",
        account_type=revenue_type,
        parent=revenue_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="4210",
        name="إيرادات التركيب",
        name_en="Installation Revenue",
        account_type=revenue_type,
        parent=service_revenue,
    )
    Account.objects.create(
        code="4220",
        name="إيرادات التفصيل",
        name_en="Tailoring Revenue",
        account_type=revenue_type,
        parent=service_revenue,
    )
    Account.objects.create(
        code="4230",
        name="إيرادات الصيانة",
        name_en="Maintenance Revenue",
        account_type=revenue_type,
        parent=service_revenue,
    )

    # إيرادات أخرى
    Account.objects.create(
        code="4900",
        name="إيرادات أخرى",
        name_en="Other Revenue",
        account_type=revenue_type,
        parent=revenue_root,
    )

    # ===== شجرة المصروفات =====
    expense_root = Account.objects.create(
        code="5000",
        name="المصروفات",
        name_en="Expenses",
        account_type=expense_type,
        is_system_account=True,
        allow_transactions=False,
    )

    # تكلفة المبيعات
    cogs = Account.objects.create(
        code="5100",
        name="تكلفة المبيعات",
        name_en="Cost of Sales",
        account_type=expense_type,
        parent=expense_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="5110",
        name="تكلفة الأقمشة",
        name_en="Fabric Cost",
        account_type=expense_type,
        parent=cogs,
    )
    Account.objects.create(
        code="5120",
        name="تكلفة الإكسسوارات",
        name_en="Accessories Cost",
        account_type=expense_type,
        parent=cogs,
    )
    Account.objects.create(
        code="5130",
        name="تكلفة التصنيع",
        name_en="Manufacturing Cost",
        account_type=expense_type,
        parent=cogs,
    )
    Account.objects.create(
        code="5140",
        name="تكلفة التركيب",
        name_en="Installation Cost",
        account_type=expense_type,
        parent=cogs,
    )

    # مصروفات الرواتب
    salaries = Account.objects.create(
        code="5200",
        name="مصروفات الرواتب",
        name_en="Salary Expenses",
        account_type=expense_type,
        parent=expense_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="5210",
        name="رواتب الموظفين",
        name_en="Employee Salaries",
        account_type=expense_type,
        parent=salaries,
    )
    Account.objects.create(
        code="5220",
        name="أجور العمال",
        name_en="Worker Wages",
        account_type=expense_type,
        parent=salaries,
    )
    Account.objects.create(
        code="5230",
        name="عمولات المبيعات",
        name_en="Sales Commissions",
        account_type=expense_type,
        parent=salaries,
    )
    Account.objects.create(
        code="5240",
        name="مكافآت وحوافز",
        name_en="Bonuses and Incentives",
        account_type=expense_type,
        parent=salaries,
    )
    Account.objects.create(
        code="5250",
        name="تأمينات اجتماعية",
        name_en="Social Insurance",
        account_type=expense_type,
        parent=salaries,
    )

    # مصروفات إدارية
    admin = Account.objects.create(
        code="5300",
        name="مصروفات إدارية",
        name_en="Administrative Expenses",
        account_type=expense_type,
        parent=expense_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="5310",
        name="إيجار المحل",
        name_en="Shop Rent",
        account_type=expense_type,
        parent=admin,
    )
    Account.objects.create(
        code="5320",
        name="كهرباء ومياه",
        name_en="Electricity and Water",
        account_type=expense_type,
        parent=admin,
    )
    Account.objects.create(
        code="5330",
        name="اتصالات وإنترنت",
        name_en="Communications",
        account_type=expense_type,
        parent=admin,
    )
    Account.objects.create(
        code="5340",
        name="أدوات مكتبية",
        name_en="Office Supplies",
        account_type=expense_type,
        parent=admin,
    )
    Account.objects.create(
        code="5350",
        name="صيانة وإصلاحات",
        name_en="Maintenance and Repairs",
        account_type=expense_type,
        parent=admin,
    )
    Account.objects.create(
        code="5360",
        name="نظافة",
        name_en="Cleaning",
        account_type=expense_type,
        parent=admin,
    )

    # مصروفات تسويقية
    marketing = Account.objects.create(
        code="5400",
        name="مصروفات تسويقية",
        name_en="Marketing Expenses",
        account_type=expense_type,
        parent=expense_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="5410",
        name="إعلانات",
        name_en="Advertising",
        account_type=expense_type,
        parent=marketing,
    )
    Account.objects.create(
        code="5420",
        name="عينات",
        name_en="Samples",
        account_type=expense_type,
        parent=marketing,
    )
    Account.objects.create(
        code="5430",
        name="هدايا وضيافة",
        name_en="Gifts and Hospitality",
        account_type=expense_type,
        parent=marketing,
    )

    # مصروفات النقل
    transport = Account.objects.create(
        code="5500",
        name="مصروفات النقل",
        name_en="Transportation Expenses",
        account_type=expense_type,
        parent=expense_root,
        is_system_account=True,
        allow_transactions=False,
    )
    Account.objects.create(
        code="5510",
        name="بنزين ووقود",
        name_en="Fuel",
        account_type=expense_type,
        parent=transport,
    )
    Account.objects.create(
        code="5520",
        name="صيانة السيارات",
        name_en="Vehicle Maintenance",
        account_type=expense_type,
        parent=transport,
    )
    Account.objects.create(
        code="5530",
        name="نقل بضائع",
        name_en="Freight",
        account_type=expense_type,
        parent=transport,
    )

    # مصروفات أخرى
    Account.objects.create(
        code="5900",
        name="مصروفات متنوعة",
        name_en="Miscellaneous Expenses",
        account_type=expense_type,
        parent=expense_root,
    )


def reverse_migration(apps, schema_editor):
    """حذف البيانات عند التراجع"""
    Account = apps.get_model("accounting", "Account")
    AccountType = apps.get_model("accounting", "AccountType")

    Account.objects.all().delete()
    AccountType.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_chart_of_accounts, reverse_migration),
    ]
