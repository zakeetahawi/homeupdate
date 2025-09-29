-- ===================================================================
-- فهارس قاعدة البيانات الشاملة والمحسنة - COMPREHENSIVE DATABASE INDEXES
-- Comprehensive and Optimized Database Indexes
-- ===================================================================
-- تم إنشاء هذا الملف ليشمل جميع الفهارس المطلوبة لجميع الجداول
-- في نظام إدارة التركيبات والتصنيع والعملاء والطلبات
-- ===================================================================

-- ===================================================================
-- الجزء الأول: فهارس حرجة للأداء العالي
-- ===================================================================

-- فهارس للجداول الأساسية - ACCOUNTS APP
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_username ON accounts_user(username);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_email ON accounts_user(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_branch_active ON accounts_user(branch_id, is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_is_active ON accounts_user(is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_user_role ON accounts_user(is_salesperson, is_branch_manager, is_region_manager, is_general_manager);

-- فهارس للأدوار والصلاحيات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_role_name ON accounts_role(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_userrole_user_role ON accounts_userrole(user_id, role_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_role_permissions ON accounts_role_permissions(role_id, permission_id);

-- فهارس للفروع
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_branch_name ON accounts_branch(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_branch_code ON accounts_branch(code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_branch_active ON accounts_branch(is_active);

-- فهارس للأقسام
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_department_name ON accounts_department(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_department_code ON accounts_department(code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_department_parent ON accounts_department(parent_id);

-- ===================================================================
-- الجزء الثاني: فهارس للعملاء - CUSTOMERS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_name ON customers_customer(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_phone ON customers_customer(phone);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_email ON customers_customer(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_branch ON customers_customer(branch_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_salesperson ON customers_customer(salesperson_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_created_at ON customers_customer(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_active ON customers_customer(is_active);

-- فهارس مركبة للعملاء
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_branch_active ON customers_customer(branch_id, is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_salesperson_date ON customers_customer(salesperson_id, created_at);

-- فهارس نصية للبحث السريع
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_search
ON customers_customer USING gin(to_tsvector('arabic', name || ' ' || COALESCE(phone, '') || ' ' || COALESCE(email, '')));

-- ===================================================================
-- الجزء الثالث: فهارس للطلبات - ORDERS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_number ON orders_order(order_number);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_customer ON orders_order(customer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_branch ON orders_order(branch_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_salesperson ON orders_order(salesperson_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_status ON orders_order(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_created_at ON orders_order(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_updated_at ON orders_order(updated_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_expected_delivery ON orders_order(expected_delivery_date);

-- فهارس مركبة للطلبات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_customer_status ON orders_order(customer_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_branch_date ON orders_order(branch_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_salesperson_status ON orders_order(salesperson_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_status_date ON orders_order(status, created_at);

-- فهارس للبحث في الطلبات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_search
ON orders_order USING gin(to_tsvector('arabic', order_number || ' ' || COALESCE(contract_number, '') || ' ' || COALESCE(invoice_number, '')));

-- ===================================================================
-- الجزء الرابع: فهارس للتصنيع - MANUFACTURING APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_order ON manufacturing_manufacturingorder(order_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_status ON manufacturing_manufacturingorder(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_created_at ON manufacturing_manufacturingorder(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_completion_date ON manufacturing_manufacturingorder(completion_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_delivery_date ON manufacturing_manufacturingorder(delivery_date);

-- فهارس مركبة للتصنيع
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_status_date ON manufacturing_manufacturingorder(status, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_order_status ON manufacturing_manufacturingorder(order_id, status);

-- فهارس لعناصر التصنيع
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_item_order ON manufacturing_manufacturingorderitem(manufacturing_order_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_item_received ON manufacturing_manufacturingorderitem(fabric_received);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_item_completed ON manufacturing_manufacturingorderitem(is_completed);

-- ===================================================================
-- الجزء الخامس: فهارس للتركيبات - INSTALLATIONS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_order ON installations_installationschedule(order_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_team ON installations_installationschedule(team_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_status ON installations_installationschedule(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_date ON installations_installationschedule(scheduled_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_time ON installations_installationschedule(scheduled_time);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_created_at ON installations_installationschedule(created_at);

-- فهارس مركبة للتركيبات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_order_status ON installations_installationschedule(order_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_team_date ON installations_installationschedule(team_id, scheduled_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_date_status ON installations_installationschedule(scheduled_date, status);

-- فهارس للفرق
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_team_name ON installations_installationteam(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_team_active ON installations_installationteam(is_active);

-- ===================================================================
-- الجزء السادس: فهارس للمخزون - INVENTORY APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_name ON inventory_product(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_code ON inventory_product(code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_category ON inventory_product(category_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_active ON inventory_product(is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_created_at ON inventory_product(created_at);

-- فهارس مركبة للمنتجات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_category_active ON inventory_product(category_id, is_active) WHERE is_active = true;

-- فهارس للبحث في المنتجات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_search
ON inventory_product USING gin(to_tsvector('arabic', name || ' ' || COALESCE(code, '') || ' ' || COALESCE(description, '')));

-- فهارس للتصنيفات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_category_name ON inventory_category(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_category_parent ON inventory_category(parent_id);

-- فهارس للحركات المخزنية
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_transaction_product ON inventory_stocktransaction(product_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_transaction_type ON inventory_stocktransaction(transaction_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_transaction_date ON inventory_stocktransaction(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_transaction_product_date ON inventory_stocktransaction(product_id, created_at);

-- ===================================================================
-- الجزء السابع: فهارس للمعاينات - INSPECTIONS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_order ON inspections_inspection(order_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_technician ON inspections_inspection(technician_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_status ON inspections_inspection(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_date ON inspections_inspection(scheduled_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_completed ON inspections_inspection(completed_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_created_at ON inspections_inspection(created_at);

-- فهارس مركبة للمعاينات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_order_status ON inspections_inspection(order_id, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_inspection_technician_date ON inspections_inspection(technician_id, scheduled_date);

-- ===================================================================
-- الجزء الثامن: فهارس للشكاوى - COMPLAINTS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_order ON complaints_complaint(order_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_customer ON complaints_complaint(customer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_status ON complaints_complaint(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_priority ON complaints_complaint(priority);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_created_at ON complaints_complaint(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_resolved_at ON complaints_complaint(resolved_at);

-- فهارس مركبة للشكاوى
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_status_priority ON complaints_complaint(status, priority);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_complaint_customer_status ON complaints_complaint(customer_id, status);

-- ===================================================================
-- الجزء التاسع: فهارس للتقارير - REPORTS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reports_report_type ON reports_report(report_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reports_report_created_by ON reports_report(created_by_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reports_report_created_at ON reports_report(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reports_report_date_range ON reports_report(date_from, date_to);

-- ===================================================================
-- الجزء العاشر: فهارس للإشعارات - NOTIFICATIONS APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_user ON notifications_notification(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_type ON notifications_notification(notification_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_read ON notifications_notification(is_read);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_created_at ON notifications_notification(created_at);

-- فهارس مركبة للإشعارات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_user_read ON notifications_notification(user_id, is_read);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_notification_type_date ON notifications_notification(notification_type, created_at);

-- ===================================================================
-- الجزء الحادي عشر: فهارس للقطع - CUTTING APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cutting_order_warehouse ON cutting_cuttingorder(warehouse_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cutting_order_status ON cutting_cuttingorder(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cutting_order_created_at ON cutting_cuttingorder(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cutting_order_warehouse_status ON cutting_cuttingorder(warehouse_id, status);

-- ===================================================================
-- الجزء الثاني عشر: فهارس لسجل الأحداث - USER ACTIVITY APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_log_user ON user_activity_useractivitylog(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_log_action ON user_activity_useractivitylog(action_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_log_entity ON user_activity_useractivitylog(entity_type, entity_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_log_timestamp ON user_activity_useractivitylog(timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_log_user_timestamp ON user_activity_useractivitylog(user_id, timestamp);

-- فهارس لجلسات المستخدمين
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_session_user ON user_activity_usersession(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_session_timestamp ON user_activity_usersession(login_time, logout_time);

-- ===================================================================
-- الجزء الثالث عشر: فهارس للنسخ الاحتياطي - BACKUP SYSTEM APP
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backup_system_backup_type ON backup_system_databasebackup(backup_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backup_system_backup_created_at ON backup_system_databasebackup(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backup_system_backup_success ON backup_system_databasebackup(success);

-- ===================================================================
-- الجزء الرابع عشر: فهارس للمهام المجدولة - APSCHEDULER
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_django_apscheduler_job_next_run_time ON django_apscheduler_djangojob(next_run_time);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_django_apscheduler_job_enabled ON django_apscheduler_djangojob(enabled);

-- ===================================================================
-- الجزء الخامس عشر: فهارس للأقسام الإدارية - ADMIN INTERFACE
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_interface_theme_user ON admin_interface_theme(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_interface_theme_active ON admin_interface_theme(active);

-- ===================================================================
-- الجزء السادس عشر: فهارس للتوكنات - TOKEN BLACKLIST
-- ===================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_token_blacklist_outstanding_token_user ON token_blacklist_outstandingtoken(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_token_blacklist_outstanding_token_expires_at ON token_blacklist_outstandingtoken(expires_at);

-- ===================================================================
-- الجزء السابع عشر: فهارس للجداول الافتراضية في Django
-- ===================================================================

-- فهارس للجلسات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_django_session_expire_date ON django_session(expire_date);

-- فهارس للصلاحيات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_auth_permission_codename ON auth_permission(codename);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_auth_permission_content_type ON auth_permission(content_type_id);

-- فهارس للمجموعات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_auth_group_name ON auth_group(name);

-- فهارس للمحتوى
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_django_content_type_app_model ON django_content_type(app_label, model);

-- ===================================================================
-- الجزء الثامن عشر: فهارس إضافية للأداء العالي
-- ===================================================================

-- فهارس للعلاقات المعقدة (N+1 queries prevention)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_manufacturing ON orders_order(id) WHERE is_manufacturing_order = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_installation ON manufacturing_manufacturingorder(order_id, status) WHERE status IN ('ready_install', 'delivered');

-- فهارس للتقارير والإحصائيات
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_month_year ON orders_order(EXTRACT(YEAR FROM created_at), EXTRACT(MONTH FROM created_at));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installations_schedule_month_year ON installations_installationschedule(EXTRACT(YEAR FROM scheduled_date), EXTRACT(MONTH FROM scheduled_date));
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_order_month_year ON manufacturing_manufacturingorder(EXTRACT(YEAR FROM created_at), EXTRACT(MONTH FROM created_at));

-- فهارس للبحث المتقدم
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_combined_search
ON orders_order USING gin(to_tsvector('arabic',
    COALESCE(order_number, '') || ' ' ||
    COALESCE(contract_number, '') || ' ' ||
    COALESCE(invoice_number, '') || ' ' ||
    COALESCE(contract_number_2, '') || ' ' ||
    COALESCE(invoice_number_2, '')
));

-- ===================================================================
-- الجزء التاسع عشر: فهارس للجداول الكبيرة (أكثر من 10000 سجل)
-- ===================================================================

-- فهارس إضافية للجداول الكبيرة
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_customer_date_status ON orders_order(customer_id, created_at, status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_transaction_product_type_date ON inventory_stocktransaction(product_id, transaction_type, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_log_user_action_date ON user_activity_useractivitylog(user_id, action_type, timestamp);

-- ===================================================================
-- الجزء العشرون: فهارس للأداء في الاستعلامات المعقدة
-- ===================================================================

-- فهارس للاستعلامات التي تجمع بين عدة جداول
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_installations_combined ON orders_order(id, customer_id, branch_id, salesperson_id, status, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_manufacturing_installations_combined ON manufacturing_manufacturingorder(order_id, status, created_at, completion_date);

-- فهارس للفرز والترتيب
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_order_sort_date_desc ON orders_order(created_at DESC, id DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_customer_sort_name ON customers_customer(name, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_product_sort_category_name ON inventory_product(category_id, name);

-- ===================================================================
-- ملاحظات مهمة:
-- ===================================================================
-- 1. جميع الفهارس تستخدم CONCURRENTLY لتجنب قفل الجداول أثناء الإنشاء
-- 2. جميع الفهارس تستخدم IF NOT EXISTS لتجنب الأخطاء عند إعادة التشغيل
-- 3. الفهارس مقسمة حسب التطبيقات لسهولة الصيانة والفهم
-- 4. تم تضمين فهارس للبحث النصي باستخدام GIN indexes
-- 5. تم تضمين فهارس للعلاقات المعقدة لمنع مشاكل N+1 queries
-- 6. الفهارس المركبة مصممة لتغطية أنماط الاستعلام الأكثر شيوعاً
-- ===================================================================

-- تحليل الجداول بعد إنشاء الفهارس
ANALYZE orders_order;
ANALYZE customers_customer;
ANALYZE manufacturing_manufacturingorder;
ANALYZE installations_installationschedule;
ANALYZE inventory_product;
ANALYZE inventory_stocktransaction;
ANALYZE inspections_inspection;
ANALYZE complaints_complaint;
ANALYZE accounts_user;
ANALYZE user_activity_useractivitylog;

-- ===================================================================
-- نهاية ملف الفهارس الشاملة
-- ===================================================================