-- ===================================================================
-- فهارس قاعدة البيانات المقترحة لتحسين الأداء
-- Database Indexes Recommendations for Performance Optimization
-- ===================================================================

-- ===================================================================
-- فهارس جدول الطلبات (Orders)
-- ===================================================================

-- فهرس على حالة الطلب (يستخدم كثيراً في التصفية)
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders_order(status);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب والتصفية)
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders_order(created_at);

-- فهرس على تاريخ الطلب (يستخدم في التقارير)
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders_order(order_date);

-- فهرس على المندوب (يستخدم في إحصائيات المندوبين)
CREATE INDEX IF NOT EXISTS idx_orders_salesperson ON orders_order(salesperson_id);

-- فهرس على العميل (يستخدم في عرض طلبات العميل)
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders_order(customer_id);

-- فهرس على الفرع (يستخدم في تصفية الطلبات حسب الفرع)
CREATE INDEX IF NOT EXISTS idx_orders_branch ON orders_order(branch_id);

-- فهرس مركب على الحالة وتاريخ الإنشاء (للاستعلامات المعقدة)
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders_order(status, created_at);

-- فهرس على رقم الطلب (للبحث السريع)
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders_order(order_number);

-- فهارس إضافية مهمة للطلبات
CREATE INDEX IF NOT EXISTS idx_orders_tracking_status ON orders_order(tracking_status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_verified ON orders_order(payment_verified);
CREATE INDEX IF NOT EXISTS idx_orders_expected_delivery ON orders_order(expected_delivery_date);
CREATE INDEX IF NOT EXISTS idx_orders_total_amount ON orders_order(total_amount);

-- ===================================================================
-- فهارس جدول التصنيع (Manufacturing Orders)
-- ===================================================================

-- فهرس على حالة التصنيع (يستخدم كثيراً في التصفية)
CREATE INDEX IF NOT EXISTS idx_manufacturing_status ON manufacturing_manufacturingorder(status);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_manufacturing_created_at ON manufacturing_manufacturingorder(created_at);

-- فهرس على تاريخ الطلب (يستخدم في التقارير)
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_date ON manufacturing_manufacturingorder(order_date);

-- فهرس على تاريخ التسليم المتوقع (مهم للجدولة)
CREATE INDEX IF NOT EXISTS idx_manufacturing_expected_delivery ON manufacturing_manufacturingorder(expected_delivery_date);

-- فهرس على رقم العقد (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_manufacturing_contract_number ON manufacturing_manufacturingorder(contract_number);

-- فهرس على الطلب المرتبط (يستخدم في الربط)
CREATE INDEX IF NOT EXISTS idx_manufacturing_order ON manufacturing_manufacturingorder(order_id);

-- فهرس على خط الإنتاج (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_manufacturing_production_line ON manufacturing_manufacturingorder(production_line_id);

-- فهرس على نوع الطلب (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_type ON manufacturing_manufacturingorder(order_type);

-- فهرس مركب على الحالة وتاريخ الإنشاء
CREATE INDEX IF NOT EXISTS idx_manufacturing_status_created ON manufacturing_manufacturingorder(status, created_at);

-- ===================================================================
-- فهارس جدول التركيبات (Installations)
-- ===================================================================

-- فهرس على حالة التركيب (يستخدم كثيراً في التصفية)
CREATE INDEX IF NOT EXISTS idx_installations_status ON installations_installation(status);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_installations_created_at ON installations_installation(created_at);

-- فهرس على تاريخ التركيب المجدول (مهم للجدولة)
CREATE INDEX IF NOT EXISTS idx_installations_scheduled_date ON installations_installation(scheduled_date);

-- فهرس على الطلب المرتبط (يستخدم في الربط)
CREATE INDEX IF NOT EXISTS idx_installations_order ON installations_installation(order_id);

-- فهرس على العميل (يستخدم في عرض تركيبات العميل)
CREATE INDEX IF NOT EXISTS idx_installations_customer ON installations_installation(customer_id);

-- فهرس على الفرع (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_installations_branch ON installations_installation(branch_id);

-- فهرس على المثبت (يستخدم في إحصائيات المثبتين)
CREATE INDEX IF NOT EXISTS idx_installations_installer ON installations_installation(installer_id);

-- فهرس مركب على الحالة وتاريخ الإنشاء
CREATE INDEX IF NOT EXISTS idx_installations_status_created ON installations_installation(status, created_at);

-- ===================================================================
-- فهارس جدول العملاء (Customers)
-- ===================================================================

-- فهرس على الفرع (يستخدم في تصفية العملاء حسب الفرع)
CREATE INDEX IF NOT EXISTS idx_customers_branch ON customers_customer(branch_id);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers_customer(created_at);

-- فهرس على رقم الهاتف (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers_customer(phone);

-- فهرس على كود العميل (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_customers_code ON customers_customer(code);

-- فهرس على الاسم (يستخدم في البحث والترتيب)
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers_customer(name);

-- فهرس على الفئة (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_customers_category ON customers_customer(category_id);

-- فهرس على الحالة (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers_customer(status);

-- فهرس على من أنشأ العميل (يستخدم في صلاحيات العرض)
CREATE INDEX IF NOT EXISTS idx_customers_created_by ON customers_customer(created_by_id);

-- فهارس إضافية للعملاء
CREATE INDEX IF NOT EXISTS idx_customers_phone2 ON customers_customer(phone2);
CREATE INDEX IF NOT EXISTS idx_customers_birth_date ON customers_customer(birth_date);
CREATE INDEX IF NOT EXISTS idx_customers_customer_type ON customers_customer(customer_type);

-- ===================================================================
-- فهارس جدول المنتجات (Products)
-- ===================================================================

-- فهرس على الفئة (يستخدم في تصفية المنتجات)
CREATE INDEX IF NOT EXISTS idx_products_category ON inventory_product(category_id);

-- فهرس على كود المنتج (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_products_code ON inventory_product(code);

-- فهرس على اسم المنتج (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_products_name ON inventory_product(name);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_products_created_at ON inventory_product(created_at);

-- فهرس على الحد الأدنى للمخزون (يستخدم في تنبيهات المخزون)
CREATE INDEX IF NOT EXISTS idx_products_minimum_stock ON inventory_product(minimum_stock);

-- فهارس إضافية للمنتجات
CREATE INDEX IF NOT EXISTS idx_products_price ON inventory_product(price);
CREATE INDEX IF NOT EXISTS idx_products_unit ON inventory_product(unit);
CREATE INDEX IF NOT EXISTS idx_products_status ON inventory_product(status);

-- ===================================================================
-- فهارس جدول حركات المخزون (Stock Transactions)
-- ===================================================================

-- فهرس على المنتج وتاريخ الحركة (يستخدم في حساب المخزون)
CREATE INDEX IF NOT EXISTS idx_stock_product_date ON inventory_stocktransaction(product_id, date);

-- فهرس على نوع الحركة (وارد/صادر)
CREATE INDEX IF NOT EXISTS idx_stock_transaction_type ON inventory_stocktransaction(transaction_type);

-- فهرس على تاريخ الحركة (يستخدم في التقارير)
CREATE INDEX IF NOT EXISTS idx_stock_date ON inventory_stocktransaction(date);

-- فهرس على المنتج (يستخدم في عرض حركات منتج معين)
CREATE INDEX IF NOT EXISTS idx_stock_product ON inventory_stocktransaction(product_id);

-- فهرس مركب على المنتج ونوع الحركة (للاستعلامات المعقدة)
CREATE INDEX IF NOT EXISTS idx_stock_product_type ON inventory_stocktransaction(product_id, transaction_type);

-- فهارس إضافية لحركات المخزون
CREATE INDEX IF NOT EXISTS idx_stock_quantity ON inventory_stocktransaction(quantity);
CREATE INDEX IF NOT EXISTS idx_stock_reason ON inventory_stocktransaction(reason);
CREATE INDEX IF NOT EXISTS idx_stock_created_by ON inventory_stocktransaction(created_by_id);
CREATE INDEX IF NOT EXISTS idx_stock_running_balance ON inventory_stocktransaction(running_balance);

-- ===================================================================
-- فهارس جدول عناصر الطلبات (Order Items)
-- ===================================================================

-- فهرس على الطلب (يستخدم في عرض عناصر الطلب)
CREATE INDEX IF NOT EXISTS idx_orderitems_order ON orders_orderitem(order_id);

-- فهرس على المنتج (يستخدم في تقارير المبيعات)
CREATE INDEX IF NOT EXISTS idx_orderitems_product ON orders_orderitem(product_id);

-- فهرس مركب على الطلب والمنتج (للاستعلامات المعقدة)
CREATE INDEX IF NOT EXISTS idx_orderitems_order_product ON orders_orderitem(order_id, product_id);

-- فهارس إضافية لعناصر الطلبات
CREATE INDEX IF NOT EXISTS idx_orderitems_quantity ON orders_orderitem(quantity);
CREATE INDEX IF NOT EXISTS idx_orderitems_unit_price ON orders_orderitem(unit_price);
CREATE INDEX IF NOT EXISTS idx_orderitems_total_price ON orders_orderitem(total_price);

-- ===================================================================
-- فهارس جدول المدفوعات (Payments)
-- ===================================================================

-- فهرس على الطلب (يستخدم في عرض مدفوعات الطلب)
CREATE INDEX IF NOT EXISTS idx_payments_order ON orders_payment(order_id);

-- فهرس على تاريخ الدفع (يستخدم في التقارير المالية)
CREATE INDEX IF NOT EXISTS idx_payments_date ON orders_payment(payment_date);

-- فهرس على طريقة الدفع (يستخدم في التقارير)
CREATE INDEX IF NOT EXISTS idx_payments_method ON orders_payment(payment_method);

-- فهارس إضافية للمدفوعات
CREATE INDEX IF NOT EXISTS idx_payments_amount ON orders_payment(amount);
CREATE INDEX IF NOT EXISTS idx_payments_status ON orders_payment(status);
CREATE INDEX IF NOT EXISTS idx_payments_created_by ON orders_payment(created_by_id);

-- ===================================================================
-- فهارس جدول المعاينات (Inspections)
-- ===================================================================

-- فهرس على العميل (يستخدم في عرض معاينات العميل)
CREATE INDEX IF NOT EXISTS idx_inspections_customer ON inspections_inspection(customer_id);

-- فهرس على تاريخ المعاينة المجدولة (يستخدم في الجدولة)
CREATE INDEX IF NOT EXISTS idx_inspections_scheduled_date ON inspections_inspection(scheduled_date);

-- فهرس على حالة المعاينة (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_inspections_status ON inspections_inspection(status);

-- فهرس على الفرع (يستخدم في تصفية المعاينات حسب الفرع)
CREATE INDEX IF NOT EXISTS idx_inspections_branch ON inspections_inspection(branch_id);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_inspections_created_at ON inspections_inspection(created_at);

-- فهارس إضافية للمعاينات
CREATE INDEX IF NOT EXISTS idx_inspections_order ON inspections_inspection(order_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspector ON inspections_inspection(inspector_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_date ON inspections_inspection(inspection_date);

-- ===================================================================
-- فهارس جدول المندوبين (Salespersons)
-- ===================================================================

-- فهرس على الفرع (يستخدم في تصفية المندوبين حسب الفرع)
CREATE INDEX IF NOT EXISTS idx_salespersons_branch ON accounts_salesperson(branch_id);

-- فهرس على الحالة النشطة (يستخدم في عرض المندوبين النشطين فقط)
CREATE INDEX IF NOT EXISTS idx_salespersons_active ON accounts_salesperson(is_active);

-- فهرس على رقم الموظف (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_salespersons_employee_number ON accounts_salesperson(employee_number);

-- فهارس إضافية للمندوبين
CREATE INDEX IF NOT EXISTS idx_salespersons_commission_rate ON accounts_salesperson(commission_rate);
CREATE INDEX IF NOT EXISTS idx_salespersons_created_at ON accounts_salesperson(created_at);

-- ===================================================================
-- فهارس جدول الفروع (Branches)
-- ===================================================================

-- فهرس على الحالة النشطة (يستخدم في عرض الفروع النشطة فقط)
CREATE INDEX IF NOT EXISTS idx_branches_active ON accounts_branch(is_active);

-- فهرس على كود الفرع (يستخدم في البحث)
CREATE INDEX IF NOT EXISTS idx_branches_code ON accounts_branch(code);

-- فهارس إضافية للفروع
CREATE INDEX IF NOT EXISTS idx_branches_name ON accounts_branch(name);
CREATE INDEX IF NOT EXISTS idx_branches_created_at ON accounts_branch(created_at);

-- ===================================================================
-- فهارس جدول المستخدمين (Users)
-- ===================================================================

-- فهرس على الفرع (يستخدم في تصفية المستخدمين حسب الفرع)
CREATE INDEX IF NOT EXISTS idx_users_branch ON accounts_user(branch_id);

-- فهرس على الحالة النشطة (يستخدم في عرض المستخدمين النشطين)
CREATE INDEX IF NOT EXISTS idx_users_active ON accounts_user(is_active);

-- فهرس على تاريخ آخر تسجيل دخول (يستخدم في تقارير النشاط)
CREATE INDEX IF NOT EXISTS idx_users_last_login ON accounts_user(last_login);

-- فهارس إضافية للمستخدمين
CREATE INDEX IF NOT EXISTS idx_users_username ON accounts_user(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON accounts_user(email);
CREATE INDEX IF NOT EXISTS idx_users_date_joined ON accounts_user(date_joined);
CREATE INDEX IF NOT EXISTS idx_users_is_staff ON accounts_user(is_staff);
CREATE INDEX IF NOT EXISTS idx_users_is_superuser ON accounts_user(is_superuser);

-- ===================================================================
-- فهارس جدول سجل النشاط (Activity Log)
-- ===================================================================

-- فهرس على المستخدم (يستخدم في عرض نشاط مستخدم معين)
CREATE INDEX IF NOT EXISTS idx_activity_user ON accounts_activitylog(user_id);

-- فهرس على الوقت (يستخدم في الترتيب والتصفية)
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON accounts_activitylog(timestamp);

-- فهرس على نوع النشاط (يستخدم في التصفية)
CREATE INDEX IF NOT EXISTS idx_activity_type ON accounts_activitylog(type);

-- فهرس مركب على المستخدم والوقت (للاستعلامات المعقدة)
CREATE INDEX IF NOT EXISTS idx_activity_user_timestamp ON accounts_activitylog(user_id, timestamp);

-- فهارس إضافية لسجل النشاط
CREATE INDEX IF NOT EXISTS idx_activity_description ON accounts_activitylog(description);
CREATE INDEX IF NOT EXISTS idx_activity_ip_address ON accounts_activitylog(ip_address);

-- ===================================================================
-- فهارس جدول ملاحظات العملاء (Customer Notes)
-- ===================================================================

-- فهرس على العميل (يستخدم في عرض ملاحظات العميل)
CREATE INDEX IF NOT EXISTS idx_customer_notes_customer ON customers_customernote(customer_id);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_customer_notes_created_at ON customers_customernote(created_at);

-- فهرس على من أنشأ الملاحظة (يستخدم في التتبع)
CREATE INDEX IF NOT EXISTS idx_customer_notes_created_by ON customers_customernote(created_by_id);

-- ===================================================================
-- فهارس جدول التنبيهات (Stock Alerts)
-- ===================================================================

-- فهرس على المنتج (يستخدم في عرض تنبيهات منتج معين)
CREATE INDEX IF NOT EXISTS idx_stock_alerts_product ON inventory_stockalert(product_id);

-- فهرس على الحالة (يستخدم في عرض التنبيهات النشطة)
CREATE INDEX IF NOT EXISTS idx_stock_alerts_status ON inventory_stockalert(status);

-- فهرس على تاريخ الإنشاء (يستخدم في الترتيب)
CREATE INDEX IF NOT EXISTS idx_stock_alerts_created_at ON inventory_stockalert(created_at);

-- فهارس إضافية للتنبيهات
CREATE INDEX IF NOT EXISTS idx_stock_alerts_alert_type ON inventory_stockalert(alert_type);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_created_by ON inventory_stockalert(created_by_id);

-- ===================================================================
-- فهارس مركبة للاستعلامات المعقدة
-- ===================================================================

-- فهرس مركب للطلبات: العميل + الحالة + التاريخ
CREATE INDEX IF NOT EXISTS idx_orders_customer_status_date ON orders_order(customer_id, status, created_at);

-- فهرس مركب للمنتجات: الفئة + الحالة + التاريخ
CREATE INDEX IF NOT EXISTS idx_products_category_status_date ON inventory_product(category_id, status, created_at);

-- فهرس مركب للعملاء: الفرع + الحالة + التاريخ
CREATE INDEX IF NOT EXISTS idx_customers_branch_status_date ON customers_customer(branch_id, status, created_at);

-- فهارس مركبة إضافية
CREATE INDEX IF NOT EXISTS idx_orders_branch_status_date ON orders_order(branch_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_manufacturing_status_date ON manufacturing_manufacturingorder(status, created_at);
CREATE INDEX IF NOT EXISTS idx_installations_status_date ON installations_installation(status, created_at);
CREATE INDEX IF NOT EXISTS idx_inspections_status_date ON inspections_inspection(status, created_at);

-- ===================================================================
-- فهارس للبحث النصي (Text Search)
-- ===================================================================

-- فهرس GIN للبحث النصي في أسماء العملاء (PostgreSQL only)
-- CREATE INDEX IF NOT EXISTS idx_customers_name_gin ON customers_customer USING gin(to_tsvector('arabic', name));

-- فهرس GIN للبحث النصي في أسماء المنتجات (PostgreSQL only)
-- CREATE INDEX IF NOT EXISTS idx_products_name_gin ON inventory_product USING gin(to_tsvector('arabic', name));

-- ===================================================================
-- فهارس جزئية (Partial Indexes) للبيانات النشطة فقط
-- ===================================================================

-- فهرس جزئي للطلبات النشطة فقط
CREATE INDEX IF NOT EXISTS idx_orders_active_status ON orders_order(status, created_at) 
WHERE status IN ('pending', 'processing', 'confirmed');

-- فهرس جزئي للعملاء النشطين فقط
CREATE INDEX IF NOT EXISTS idx_customers_active_status ON customers_customer(branch_id, created_at) 
WHERE status = 'active';

-- فهرس جزئي للمنتجات المتوفرة فقط
CREATE INDEX IF NOT EXISTS idx_products_available ON inventory_product(category_id, name) 
WHERE status = 'active';

-- فهارس جزئية إضافية
CREATE INDEX IF NOT EXISTS idx_manufacturing_active_status ON manufacturing_manufacturingorder(status, created_at)
WHERE status IN ('pending', 'in_progress', 'ready_install');

CREATE INDEX IF NOT EXISTS idx_installations_active_status ON installations_installation(status, created_at)
WHERE status IN ('pending', 'scheduled', 'in_progress');

-- ===================================================================
-- تحليل الجداول لتحسين الأداء
-- ===================================================================

-- تحليل جميع الجداول المهمة لتحسين خطط الاستعلام
ANALYZE orders_order;
ANALYZE customers_customer;
ANALYZE manufacturing_manufacturingorder;
ANALYZE installations_installation;
ANALYZE inventory_product;
ANALYZE inventory_stocktransaction;
ANALYZE inspections_inspection;
ANALYZE accounts_user;
ANALYZE accounts_activitylog;
ANALYZE orders_orderitem;
ANALYZE orders_payment;
ANALYZE customers_customernote;
ANALYZE inventory_stockalert;
ANALYZE accounts_salesperson;
ANALYZE accounts_branch;

-- ===================================================================
-- ملاحظات مهمة:
-- ===================================================================

-- 1. تأكد من تشغيل هذه الأوامر في بيئة الاختبار أولاً
-- 2. راقب أداء قاعدة البيانات بعد إضافة الفهارس
-- 3. بعض الفهارس قد تبطئ عمليات الإدراج والتحديث
-- 4. استخدم EXPLAIN ANALYZE لتحليل خطط الاستعلام
-- 5. احذف الفهارس غير المستخدمة لتوفير مساحة التخزين

-- للتحقق من استخدام الفهارس:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
-- FROM pg_stat_user_indexes 
-- ORDER BY idx_scan DESC;

-- لحذف فهرس غير مستخدم:
-- DROP INDEX IF EXISTS index_name;

-- للتحقق من حجم الفهارس:
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes 
-- ORDER BY pg_relation_size(indexrelid) DESC;