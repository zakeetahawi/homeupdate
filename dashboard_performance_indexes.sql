-- ===================================================================
-- تحسينات الأداء للـ Dashboard - Indexes إضافية
-- PERFORMANCE IMPROVEMENTS FOR DASHBOARD - Additional Indexes
-- ===================================================================

-- فهارس للاستعلامات الأكثر تكراراً في الـ Dashboard
CREATE INDEX IF NOT EXISTS idx_orders_branch_date_status ON orders_order(branch_id, order_date, order_status);
CREATE INDEX IF NOT EXISTS idx_orders_date_range ON orders_order(order_date) WHERE order_date >= '2024-01-01';
CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders_order(order_status, order_date);

-- فهارس للعملاء حسب التاريخ والفرع
CREATE INDEX IF NOT EXISTS idx_customers_branch_created ON customers_customer(branch_id, created_at);
CREATE INDEX IF NOT EXISTS idx_customers_status_branch ON customers_customer(status, branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_created_date ON customers_customer(created_at DESC);

-- فهارس للتصنيع
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_branch ON manufacturing_manufacturingorder(order_id, branch_id);
CREATE INDEX IF NOT EXISTS idx_manufacturing_status_created ON manufacturing_manufacturingorder(status, created_at);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_date ON manufacturing_manufacturingorder(order__order_date) WHERE order__order_date IS NOT NULL;

-- فهارس للمعاينات
CREATE INDEX IF NOT EXISTS idx_inspections_branch_date ON inspections_inspection(branch_id, inspection_date);
CREATE INDEX IF NOT EXISTS idx_inspections_status_date ON inspections_inspection(status, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_inspections_order_date ON inspections_inspection(order_id, created_at);

-- فهارس للتركيبات
CREATE INDEX IF NOT EXISTS idx_installations_order_branch ON installations_installationschedule(order_id, branch_id);
CREATE INDEX IF NOT EXISTS idx_installations_status_date ON installations_installationschedule(status, created_at);

-- فهارس مركبة للأداء الأمثل
CREATE INDEX IF NOT EXISTS idx_orders_composite ON orders_order(branch_id, order_date, order_status, total_amount);
CREATE INDEX IF NOT EXISTS idx_customers_composite ON customers_customer(branch_id, status, customer_type, created_at);
CREATE INDEX IF NOT EXISTS idx_manufacturing_composite ON manufacturing_manufacturingorder(status, created_at, order__branch_id);

-- فهارس للاستعلامات الشهرية (للرسوم البيانية)
CREATE INDEX IF NOT EXISTS idx_orders_monthly ON orders_order(EXTRACT(year FROM order_date), EXTRACT(month FROM order_date), branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_monthly ON customers_customer(EXTRACT(year FROM created_at), EXTRACT(month FROM created_at), branch_id);
CREATE INDEX IF NOT EXISTS idx_inspections_monthly ON inspections_inspection(EXTRACT(year FROM inspection_date), EXTRACT(month FROM inspection_date), branch_id);

-- فهارس للتحليلات
CREATE INDEX IF NOT EXISTS idx_user_activity_date ON user_activity_useractivitylog(created_at DESC, user_id);
CREATE INDEX IF NOT EXISTS idx_user_performance_date ON accounts_user(last_login DESC) WHERE last_login IS NOT NULL;

-- فهارس للمقارنات الزمنية
CREATE INDEX IF NOT EXISTS idx_orders_comparison ON orders_order(order_date, branch_id, order_status) WHERE order_date >= '2023-01-01';
CREATE INDEX IF NOT EXISTS idx_customers_comparison ON customers_customer(created_at, branch_id, status) WHERE created_at >= '2023-01-01';

-- إحصائيات الفهارس للأداء الأمثل
ANALYZE orders_order;
ANALYZE customers_customer;
ANALYZE manufacturing_manufacturingorder;
ANALYZE inspections_inspection;
ANALYZE installations_installationschedule;
ANALYZE user_activity_useractivitylog;
ANALYZE accounts_user;