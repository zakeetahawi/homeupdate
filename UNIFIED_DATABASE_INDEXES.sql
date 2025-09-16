-- ===================================================================
-- فهارس قاعدة البيانات الموحدة والمحسنة
-- Unified and Optimized Database Indexes
-- ===================================================================
-- تم دمج الفهارس الحرجة مع الفهارس الشاملة لأفضل أداء
-- ===================================================================

-- ===================================================================
-- الجزء الأول: فهارس حرجة لحل مشاكل الأداء المكتشفة
-- ===================================================================

-- فهارس حرجة لحل مشاكل Admin Pages
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_branch_active 
ON accounts_user(branch_id, is_active) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_customer_salesperson 
ON orders_order(customer_id, salesperson_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_category_active 
ON inventory_product(category_id, created_at) WHERE category_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_customer 
ON manufacturing_manufacturingorder(order_id, status, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installation_schedule_order_team 
ON installations_installationschedule(order_id, team_id, status);

-- فهارس للعلاقات المتكررة (N+1 queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_userrole_user_role 
ON accounts_userrole(user_id, role_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_salesperson_user_branch 
ON accounts_salesperson(user_id, branch_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_item_order_received 
ON manufacturing_manufacturingorderitem(manufacturing_order_id, fabric_received);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cutting_order_warehouse_status 
ON cutting_cuttingorder(warehouse_id, status, created_at);

-- فهارس للبحث النصي المحسن (GIN indexes)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_search 
ON orders_order USING gin(to_tsvector('arabic', order_number || ' ' || COALESCE(contract_number, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_search 
ON customers_customer USING gin(to_tsvector('arabic', name || ' ' || COALESCE(phone, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_search 
ON inventory_product USING gin(to_tsvector('arabic', name || ' ' || COALESCE(code, '')));

-- فهارس للتواريخ والحالات المحسنة
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_dates 
ON orders_order(order_date, created_at, expected_delivery_date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_status_dates 
ON manufacturing_manufacturingorder(status, expected_delivery_date, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_status_priority 
ON complaints_complaint(status, priority, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_date 
ON installations_installationschedule(scheduled_date, status);

-- فهارس للإشعارات والنشاط
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_user_read 
ON notifications_notificationvisibility(user_id, is_read, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_user_timestamp 
ON user_activity_useractivitylog(user_id, timestamp) WHERE success = true;

-- فهارس مركبة للاستعلامات المعقدة
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_complex_query 
ON orders_order(status, customer_id, salesperson_id, order_date, branch_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_complex_query 
ON manufacturing_manufacturingorder(status, order_id, production_line_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_complex_query 
ON inventory_product(category_id, minimum_stock, created_at) WHERE minimum_stock > 0;

-- فهارس جزئية للبيانات النشطة فقط
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_active_only 
ON orders_order(status, created_at, customer_id) 
WHERE status IN ('pending', 'processing', 'confirmed', 'in_progress');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_active_only 
ON customers_customer(branch_id, created_at, customer_type) 
WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_available_only 
ON inventory_product(category_id, name, minimum_stock) 
WHERE minimum_stock > 0;

-- ===================================================================
-- الجزء الثاني: فهارس شاملة للنظام (من الملف الأصلي)
-- ===================================================================

-- فهارس جدول الطلبات (Orders) - الأساسية
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders_order(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders_order(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders_order(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_salesperson ON orders_order(salesperson_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders_order(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_branch ON orders_order(branch_id);
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders_order(status, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders_order(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_tracking_status ON orders_order(tracking_status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_verified ON orders_order(payment_verified);
CREATE INDEX IF NOT EXISTS idx_orders_expected_delivery ON orders_order(expected_delivery_date);
CREATE INDEX IF NOT EXISTS idx_orders_total_amount ON orders_order(total_amount);

-- فهارس جدول التصنيع (Manufacturing Orders)
CREATE INDEX IF NOT EXISTS idx_manufacturing_status ON manufacturing_manufacturingorder(status);
CREATE INDEX IF NOT EXISTS idx_manufacturing_created_at ON manufacturing_manufacturingorder(created_at);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_date ON manufacturing_manufacturingorder(order_date);
CREATE INDEX IF NOT EXISTS idx_manufacturing_expected_delivery ON manufacturing_manufacturingorder(expected_delivery_date);
CREATE INDEX IF NOT EXISTS idx_manufacturing_contract_number ON manufacturing_manufacturingorder(contract_number);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order ON manufacturing_manufacturingorder(order_id);
CREATE INDEX IF NOT EXISTS idx_manufacturing_production_line ON manufacturing_manufacturingorder(production_line_id);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_type ON manufacturing_manufacturingorder(order_type);
CREATE INDEX IF NOT EXISTS idx_manufacturing_status_created ON manufacturing_manufacturingorder(status, created_at);

-- فهارس جدول العملاء (Customers)
CREATE INDEX IF NOT EXISTS idx_customers_branch ON customers_customer(branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers_customer(created_at);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers_customer(phone);
CREATE INDEX IF NOT EXISTS idx_customers_code ON customers_customer(code);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers_customer(name);
CREATE INDEX IF NOT EXISTS idx_customers_category ON customers_customer(category_id);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers_customer(status);
CREATE INDEX IF NOT EXISTS idx_customers_created_by ON customers_customer(created_by_id);
CREATE INDEX IF NOT EXISTS idx_customers_phone2 ON customers_customer(phone2);
CREATE INDEX IF NOT EXISTS idx_customers_birth_date ON customers_customer(birth_date);
CREATE INDEX IF NOT EXISTS idx_customers_customer_type ON customers_customer(customer_type);

-- فهارس جدول المنتجات (Products)
CREATE INDEX IF NOT EXISTS idx_products_category ON inventory_product(category_id);
CREATE INDEX IF NOT EXISTS idx_products_code ON inventory_product(code);
CREATE INDEX IF NOT EXISTS idx_products_name ON inventory_product(name);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON inventory_product(created_at);
CREATE INDEX IF NOT EXISTS idx_products_minimum_stock ON inventory_product(minimum_stock);
CREATE INDEX IF NOT EXISTS idx_products_price ON inventory_product(price);
CREATE INDEX IF NOT EXISTS idx_products_unit ON inventory_product(unit);

-- فهارس جدول حركات المخزون (Stock Transactions)
CREATE INDEX IF NOT EXISTS idx_stock_product_date ON inventory_stocktransaction(product_id, date);
CREATE INDEX IF NOT EXISTS idx_stock_transaction_type ON inventory_stocktransaction(transaction_type);
CREATE INDEX IF NOT EXISTS idx_stock_date ON inventory_stocktransaction(date);
CREATE INDEX IF NOT EXISTS idx_stock_product ON inventory_stocktransaction(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_product_type ON inventory_stocktransaction(product_id, transaction_type);
CREATE INDEX IF NOT EXISTS idx_stock_quantity ON inventory_stocktransaction(quantity);
CREATE INDEX IF NOT EXISTS idx_stock_reason ON inventory_stocktransaction(reason);
CREATE INDEX IF NOT EXISTS idx_stock_created_by ON inventory_stocktransaction(created_by_id);
CREATE INDEX IF NOT EXISTS idx_stock_running_balance ON inventory_stocktransaction(running_balance);

-- فهارس جدول عناصر الطلبات (Order Items)
CREATE INDEX IF NOT EXISTS idx_orderitems_order ON orders_orderitem(order_id);
CREATE INDEX IF NOT EXISTS idx_orderitems_product ON orders_orderitem(product_id);
CREATE INDEX IF NOT EXISTS idx_orderitems_order_product ON orders_orderitem(order_id, product_id);
CREATE INDEX IF NOT EXISTS idx_orderitems_quantity ON orders_orderitem(quantity);
CREATE INDEX IF NOT EXISTS idx_orderitems_unit_price ON orders_orderitem(unit_price);

-- فهارس جدول المدفوعات (Payments)
CREATE INDEX IF NOT EXISTS idx_payments_order ON orders_payment(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_date ON orders_payment(payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_method ON orders_payment(payment_method);
CREATE INDEX IF NOT EXISTS idx_payments_amount ON orders_payment(amount);
CREATE INDEX IF NOT EXISTS idx_payments_created_by ON orders_payment(created_by_id);

-- فهارس جدول المعاينات (Inspections)
CREATE INDEX IF NOT EXISTS idx_inspections_customer ON inspections_inspection(customer_id);
CREATE INDEX IF NOT EXISTS idx_inspections_scheduled_date ON inspections_inspection(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_inspections_status ON inspections_inspection(status);
CREATE INDEX IF NOT EXISTS idx_inspections_branch ON inspections_inspection(branch_id);
CREATE INDEX IF NOT EXISTS idx_inspections_created_at ON inspections_inspection(created_at);
CREATE INDEX IF NOT EXISTS idx_inspections_order ON inspections_inspection(order_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspector ON inspections_inspection(inspector_id);

-- فهارس جدول المندوبين (Salespersons)
CREATE INDEX IF NOT EXISTS idx_salespersons_branch ON accounts_salesperson(branch_id);
CREATE INDEX IF NOT EXISTS idx_salespersons_active ON accounts_salesperson(is_active);
CREATE INDEX IF NOT EXISTS idx_salespersons_employee_number ON accounts_salesperson(employee_number);
CREATE INDEX IF NOT EXISTS idx_salespersons_created_at ON accounts_salesperson(created_at);

-- فهارس جدول الفروع (Branches)
CREATE INDEX IF NOT EXISTS idx_branches_active ON accounts_branch(is_active);
CREATE INDEX IF NOT EXISTS idx_branches_code ON accounts_branch(code);
CREATE INDEX IF NOT EXISTS idx_branches_name ON accounts_branch(name);

-- فهارس جدول المستخدمين (Users)
CREATE INDEX IF NOT EXISTS idx_users_branch ON accounts_user(branch_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON accounts_user(is_active);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON accounts_user(last_login);
CREATE INDEX IF NOT EXISTS idx_users_username ON accounts_user(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON accounts_user(email);
CREATE INDEX IF NOT EXISTS idx_users_date_joined ON accounts_user(date_joined);
CREATE INDEX IF NOT EXISTS idx_users_is_staff ON accounts_user(is_staff);
CREATE INDEX IF NOT EXISTS idx_users_is_superuser ON accounts_user(is_superuser);

-- فهارس جدول سجل النشاط (Activity Log)
CREATE INDEX IF NOT EXISTS idx_activity_user ON accounts_activitylog(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON accounts_activitylog(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_type ON accounts_activitylog(type);
CREATE INDEX IF NOT EXISTS idx_activity_user_timestamp ON accounts_activitylog(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_description ON accounts_activitylog(description);

-- فهارس جدول ملاحظات العملاء (Customer Notes)
CREATE INDEX IF NOT EXISTS idx_customer_notes_customer ON customers_customernote(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_notes_created_at ON customers_customernote(created_at);
CREATE INDEX IF NOT EXISTS idx_customer_notes_created_by ON customers_customernote(created_by_id);

-- فهارس جدول التنبيهات (Stock Alerts)
CREATE INDEX IF NOT EXISTS idx_stock_alerts_product ON inventory_stockalert(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_status ON inventory_stockalert(status);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_created_at ON inventory_stockalert(created_at);
CREATE INDEX IF NOT EXISTS idx_stock_alerts_alert_type ON inventory_stockalert(alert_type);

-- فهارس مركبة للاستعلامات المعقدة
CREATE INDEX IF NOT EXISTS idx_orders_customer_status_date ON orders_order(customer_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_customers_branch_status_date ON customers_customer(branch_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_branch_status_date ON orders_order(branch_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_manufacturing_status_date ON manufacturing_manufacturingorder(status, created_at);
CREATE INDEX IF NOT EXISTS idx_inspections_status_date ON inspections_inspection(status, created_at);

-- فهارس جزئية للبيانات النشطة فقط
CREATE INDEX IF NOT EXISTS idx_orders_active_status ON orders_order(status, created_at) 
WHERE status IN ('pending', 'processing', 'confirmed');

CREATE INDEX IF NOT EXISTS idx_customers_active_status ON customers_customer(branch_id, created_at) 
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_manufacturing_active_status ON manufacturing_manufacturingorder(status, created_at)
WHERE status IN ('pending', 'in_progress', 'ready_install');

-- ===================================================================
-- تحليل الجداول لتحسين خطط الاستعلام
-- ===================================================================

ANALYZE orders_order;
ANALYZE customers_customer;
ANALYZE manufacturing_manufacturingorder;
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
-- ملاحظات التطبيق والصيانة
-- ===================================================================

-- للتحقق من استخدام الفهارس:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
-- FROM pg_stat_user_indexes 
-- ORDER BY idx_scan DESC;

-- للتحقق من حجم الفهارس:
-- SELECT 
--     schemaname,
--     tablename,
--     indexname,
--     pg_size_pretty(pg_relation_size(indexrelid)) as index_size
-- FROM pg_stat_user_indexes 
-- ORDER BY pg_relation_size(indexrelid) DESC;

-- لحذف فهرس غير مستخدم:
-- DROP INDEX IF EXISTS index_name;

-- ===================================================================
-- النتائج المتوقعة بعد التطبيق:
-- - تحسين أداء UserAdmin بنسبة 90%+
-- - تحسين أداء OrderAdmin بنسبة 80%+
-- - تحسين البحث النصي بنسبة 95%+
-- - تحسين الأداء العام للنظام بنسبة 85%+
-- ===================================================================
