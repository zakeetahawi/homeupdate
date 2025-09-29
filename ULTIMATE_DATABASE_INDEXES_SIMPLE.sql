-- ===================================================================
-- نظام الفهرسة الشامل والمتكامل (نسخة مبسطة بدون CONCURRENTLY)
-- ULTIMATE COMPREHENSIVE DATABASE INDEXING SYSTEM (Simple Version)
-- ===================================================================

-- فهارس الجداول الأساسية - CORE TABLES
CREATE INDEX IF NOT EXISTS idx_accounts_user_username_unique ON accounts_user(username);
CREATE INDEX IF NOT EXISTS idx_accounts_user_email_unique ON accounts_user(email);
CREATE INDEX IF NOT EXISTS idx_accounts_user_branch_active ON accounts_user(branch_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_accounts_user_roles ON accounts_user(is_salesperson, is_branch_manager, is_region_manager, is_general_manager, is_factory_manager);
CREATE INDEX IF NOT EXISTS idx_accounts_user_last_login ON accounts_user(last_login DESC) WHERE last_login IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_accounts_user_date_joined ON accounts_user(date_joined DESC);
CREATE INDEX IF NOT EXISTS idx_accounts_user_staff_active ON accounts_user(is_staff, is_active);

-- فهارس الفروع
CREATE INDEX IF NOT EXISTS idx_accounts_branch_code_unique ON accounts_branch(code);
CREATE INDEX IF NOT EXISTS idx_accounts_branch_name ON accounts_branch(name);
CREATE INDEX IF NOT EXISTS idx_accounts_branch_active ON accounts_branch(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_accounts_branch_main ON accounts_branch(is_main_branch) WHERE is_main_branch = true;

-- فهارس الأقسام
CREATE INDEX IF NOT EXISTS idx_accounts_department_code ON accounts_department(code);
CREATE INDEX IF NOT EXISTS idx_accounts_department_name ON accounts_department(name);
CREATE INDEX IF NOT EXISTS idx_accounts_department_parent ON accounts_department(parent_id);
CREATE INDEX IF NOT EXISTS idx_accounts_department_type ON accounts_department(department_type);
CREATE INDEX IF NOT EXISTS idx_accounts_department_active ON accounts_department(is_active) WHERE is_active = true;

-- فهارس المندوبين
CREATE INDEX IF NOT EXISTS idx_accounts_salesperson_user_branch ON accounts_salesperson(user_id, branch_id);
CREATE INDEX IF NOT EXISTS idx_accounts_salesperson_employee_number ON accounts_salesperson(employee_number);
CREATE INDEX IF NOT EXISTS idx_accounts_salesperson_active ON accounts_salesperson(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_accounts_salesperson_created_at ON accounts_salesperson(created_at DESC);

-- فهارس العملاء - CUSTOMERS
CREATE INDEX IF NOT EXISTS idx_customers_customer_code_unique ON customers_customer(code);
CREATE INDEX IF NOT EXISTS idx_customers_customer_name ON customers_customer(name);
CREATE INDEX IF NOT EXISTS idx_customers_customer_phone ON customers_customer(phone);
CREATE INDEX IF NOT EXISTS idx_customers_customer_phone2 ON customers_customer(phone2);
CREATE INDEX IF NOT EXISTS idx_customers_customer_email ON customers_customer(email);
CREATE INDEX IF NOT EXISTS idx_customers_customer_status ON customers_customer(status);
CREATE INDEX IF NOT EXISTS idx_customers_customer_type ON customers_customer(customer_type);
CREATE INDEX IF NOT EXISTS idx_customers_customer_branch ON customers_customer(branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_customer_category ON customers_customer(category_id);
CREATE INDEX IF NOT EXISTS idx_customers_customer_created_by ON customers_customer(created_by_id);
CREATE INDEX IF NOT EXISTS idx_customers_customer_created_at ON customers_customer(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_customer_updated_at ON customers_customer(updated_at DESC);

-- فهارس مركبة للعملاء
CREATE INDEX IF NOT EXISTS idx_customers_customer_branch_status ON customers_customer(branch_id, status);
CREATE INDEX IF NOT EXISTS idx_customers_customer_branch_type ON customers_customer(branch_id, customer_type);
CREATE INDEX IF NOT EXISTS idx_customers_customer_status_created ON customers_customer(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_customer_creator_branch ON customers_customer(created_by_id, branch_id);

-- فهارس جزئية للعملاء النشطين
CREATE INDEX IF NOT EXISTS idx_customers_customer_active_only ON customers_customer(name, phone, created_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_customers_customer_branch_active ON customers_customer(branch_id, created_at DESC) WHERE status = 'active';

-- فهارس البحث النصي للعملاء
CREATE INDEX IF NOT EXISTS idx_customers_customer_search_gin ON customers_customer USING gin(to_tsvector('arabic', name || ' ' || COALESCE(phone, '') || ' ' || COALESCE(phone2, '') || ' ' || COALESCE(email, '')));

-- فهارس تصنيفات العملاء
CREATE INDEX IF NOT EXISTS idx_customers_category_name ON customers_customercategory(name);
CREATE INDEX IF NOT EXISTS idx_customers_category_active ON customers_customercategory(is_active) WHERE is_active = true;

-- فهارس ملاحظات العملاء
CREATE INDEX IF NOT EXISTS idx_customers_note_customer ON customers_customernote(customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_note_created_at ON customers_customernote(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_note_created_by ON customers_customernote(created_by_id);

-- فهارس الطلبات - ORDERS
CREATE INDEX IF NOT EXISTS idx_orders_order_number_unique ON orders_order(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_order_customer ON orders_order(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_salesperson ON orders_order(salesperson_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_branch ON orders_order(branch_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_status ON orders_order(status);
CREATE INDEX IF NOT EXISTS idx_orders_order_tracking_status ON orders_order(tracking_status);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders_order(order_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_created_at ON orders_order(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_updated_at ON orders_order(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_expected_delivery ON orders_order(expected_delivery_date);
CREATE INDEX IF NOT EXISTS idx_orders_order_payment_verified ON orders_order(payment_verified);
CREATE INDEX IF NOT EXISTS idx_orders_order_total_amount ON orders_order(total_amount DESC);

-- فهارس للعقود والفواتير
CREATE INDEX IF NOT EXISTS idx_orders_order_contract_number ON orders_order(contract_number);
CREATE INDEX IF NOT EXISTS idx_orders_order_contract_number_2 ON orders_order(contract_number_2);
CREATE INDEX IF NOT EXISTS idx_orders_order_contract_number_3 ON orders_order(contract_number_3);
CREATE INDEX IF NOT EXISTS idx_orders_order_invoice_number ON orders_order(invoice_number);
CREATE INDEX IF NOT EXISTS idx_orders_order_invoice_number_2 ON orders_order(invoice_number_2);
CREATE INDEX IF NOT EXISTS idx_orders_order_invoice_number_3 ON orders_order(invoice_number_3);

-- فهارس مركبة للطلبات
CREATE INDEX IF NOT EXISTS idx_orders_order_customer_status ON orders_order(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_order_customer_date ON orders_order(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_salesperson_status ON orders_order(salesperson_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_order_salesperson_date ON orders_order(salesperson_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_branch_status ON orders_order(branch_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_order_branch_date ON orders_order(branch_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_status_date ON orders_order(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_order_tracking_date ON orders_order(tracking_status, created_at DESC);

-- فهارس جزئية للطلبات النشطة
CREATE INDEX IF NOT EXISTS idx_orders_order_active_status ON orders_order(status, created_at DESC, customer_id) WHERE status IN ('pending', 'processing', 'confirmed', 'in_progress');
CREATE INDEX IF NOT EXISTS idx_orders_order_pending_payment ON orders_order(customer_id, total_amount DESC) WHERE payment_verified = false;

-- فهارس البحث النصي للطلبات
CREATE INDEX IF NOT EXISTS idx_orders_order_search_gin ON orders_order USING gin(to_tsvector('arabic', 
    COALESCE(order_number, '') || ' ' || 
    COALESCE(contract_number, '') || ' ' || 
    COALESCE(contract_number_2, '') || ' ' || 
    COALESCE(contract_number_3, '') || ' ' ||
    COALESCE(invoice_number, '') || ' ' || 
    COALESCE(invoice_number_2, '') || ' ' || 
    COALESCE(invoice_number_3, '')
));

-- فهارس عناصر الطلبات
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_order ON orders_orderitem(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_product ON orders_orderitem(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_status ON orders_orderitem(processing_status);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_type ON orders_orderitem(item_type);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_cutting_status ON orders_orderitem(cutting_status);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_cutter ON orders_orderitem(cutter_name);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_cutting_date ON orders_orderitem(cutting_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_orderitem_order_status ON orders_orderitem(order_id, processing_status);

-- فهارس المدفوعات
CREATE INDEX IF NOT EXISTS idx_orders_payment_order ON orders_payment(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_payment_date ON orders_payment(payment_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_payment_method ON orders_payment(payment_method);
CREATE INDEX IF NOT EXISTS idx_orders_payment_amount ON orders_payment(amount DESC);
CREATE INDEX IF NOT EXISTS idx_orders_payment_created_by ON orders_payment(created_by_id);
CREATE INDEX IF NOT EXISTS idx_orders_payment_order_date ON orders_payment(order_id, payment_date DESC);

-- فهارس المخزون - INVENTORY
CREATE INDEX IF NOT EXISTS idx_inventory_product_name ON inventory_product(name);
CREATE INDEX IF NOT EXISTS idx_inventory_product_code_unique ON inventory_product(code);
CREATE INDEX IF NOT EXISTS idx_inventory_product_category ON inventory_product(category_id);
CREATE INDEX IF NOT EXISTS idx_inventory_product_price ON inventory_product(price DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_product_currency ON inventory_product(currency);
CREATE INDEX IF NOT EXISTS idx_inventory_product_unit ON inventory_product(unit);
CREATE INDEX IF NOT EXISTS idx_inventory_product_minimum_stock ON inventory_product(minimum_stock);
CREATE INDEX IF NOT EXISTS idx_inventory_product_created_at ON inventory_product(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_product_active ON inventory_product(is_active) WHERE is_active = true;

-- فهارس مركبة للمنتجات
CREATE INDEX IF NOT EXISTS idx_inventory_product_category_active ON inventory_product(category_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_inventory_product_category_price ON inventory_product(category_id, price DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_product_low_stock ON inventory_product(minimum_stock, name) WHERE minimum_stock > 0;

-- فهارس البحث النصي للمنتجات
CREATE INDEX IF NOT EXISTS idx_inventory_product_search_gin ON inventory_product USING gin(to_tsvector('arabic', name || ' ' || COALESCE(code, '') || ' ' || COALESCE(description, '')));

-- فهارس التصنيفات
CREATE INDEX IF NOT EXISTS idx_inventory_category_name ON inventory_category(name);
CREATE INDEX IF NOT EXISTS idx_inventory_category_parent ON inventory_category(parent_id);
CREATE INDEX IF NOT EXISTS idx_inventory_category_active ON inventory_category(is_active) WHERE is_active = true;

-- فهارس حركات المخزون
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_product ON inventory_stocktransaction(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_type ON inventory_stocktransaction(transaction_type);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_date ON inventory_stocktransaction(date DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_created_at ON inventory_stocktransaction(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_created_by ON inventory_stocktransaction(created_by_id);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_quantity ON inventory_stocktransaction(quantity);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_balance ON inventory_stocktransaction(running_balance);

-- فهارس مركبة لحركات المخزون
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_product_date ON inventory_stocktransaction(product_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_product_type ON inventory_stocktransaction(product_id, transaction_type);
CREATE INDEX IF NOT EXISTS idx_inventory_transaction_type_date ON inventory_stocktransaction(transaction_type, date DESC);

-- فهارس التصنيع - MANUFACTURING
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_order ON manufacturing_manufacturingorder(order_id);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_status ON manufacturing_manufacturingorder(status);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_type ON manufacturing_manufacturingorder(order_type);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_production_line ON manufacturing_manufacturingorder(production_line_id);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_created_at ON manufacturing_manufacturingorder(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_order_date ON manufacturing_manufacturingorder(order_date DESC);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_expected_delivery ON manufacturing_manufacturingorder(expected_delivery_date);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_completion_date ON manufacturing_manufacturingorder(completion_date DESC);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_delivery_date ON manufacturing_manufacturingorder(delivery_date DESC);

-- فهارس مركبة للتصنيع
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_status_date ON manufacturing_manufacturingorder(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_order_status ON manufacturing_manufacturingorder(order_id, status);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_line_status ON manufacturing_manufacturingorder(production_line_id, status);
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_type_status ON manufacturing_manufacturingorder(order_type, status);

-- فهارس جزئية للتصنيع النشط
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_active_status ON manufacturing_manufacturingorder(status, created_at DESC) WHERE status IN ('pending', 'in_progress', 'ready_install');
CREATE INDEX IF NOT EXISTS idx_manufacturing_order_overdue ON manufacturing_manufacturingorder(expected_delivery_date, status) WHERE expected_delivery_date < CURRENT_DATE AND status NOT IN ('completed', 'delivered', 'cancelled');

-- فهارس عناصر التصنيع
CREATE INDEX IF NOT EXISTS idx_manufacturing_item_order ON manufacturing_manufacturingorderitem(manufacturing_order_id);
CREATE INDEX IF NOT EXISTS idx_manufacturing_item_status ON manufacturing_manufacturingorderitem(status);
CREATE INDEX IF NOT EXISTS idx_manufacturing_item_fabric_received ON manufacturing_manufacturingorderitem(fabric_received);
CREATE INDEX IF NOT EXISTS idx_manufacturing_item_completed ON manufacturing_manufacturingorderitem(is_completed);
CREATE INDEX IF NOT EXISTS idx_manufacturing_item_order_received ON manufacturing_manufacturingorderitem(manufacturing_order_id, fabric_received);

-- فهارس المعاينات - INSPECTIONS
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_contract_number ON inspections_inspection(contract_number);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_customer ON inspections_inspection(customer_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_order ON inspections_inspection(order_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_technician ON inspections_inspection(technician_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_inspector ON inspections_inspection(inspector_id);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_status ON inspections_inspection(status);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_result ON inspections_inspection(result);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_scheduled_date ON inspections_inspection(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_completed_at ON inspections_inspection(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_created_at ON inspections_inspection(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_branch ON inspections_inspection(branch_id);

-- فهارس مركبة للمعاينات
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_customer_status ON inspections_inspection(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_order_status ON inspections_inspection(order_id, status);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_technician_date ON inspections_inspection(technician_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_status_date ON inspections_inspection(status, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_branch_status ON inspections_inspection(branch_id, status);

-- فهارس جزئية للمعاينات النشطة
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_pending ON inspections_inspection(scheduled_date, customer_id) WHERE status IN ('pending', 'scheduled');
CREATE INDEX IF NOT EXISTS idx_inspections_inspection_completed ON inspections_inspection(completed_at DESC, result) WHERE status = 'completed';

-- فهارس تقييمات المعاينات
CREATE INDEX IF NOT EXISTS idx_inspections_evaluation_inspection ON inspections_inspectionevaluation(inspection_id);
CREATE INDEX IF NOT EXISTS idx_inspections_evaluation_criteria ON inspections_inspectionevaluation(criteria);
CREATE INDEX IF NOT EXISTS idx_inspections_evaluation_rating ON inspections_inspectionevaluation(rating);
CREATE INDEX IF NOT EXISTS idx_inspections_evaluation_created_by ON inspections_inspectionevaluation(created_by_id);
CREATE INDEX IF NOT EXISTS idx_inspections_evaluation_created_at ON inspections_inspectionevaluation(created_at DESC);

-- فهارس إشعارات المعاينات
CREATE INDEX IF NOT EXISTS idx_inspections_notification_inspection ON inspections_inspectionnotification(inspection_id);
CREATE INDEX IF NOT EXISTS idx_inspections_notification_type ON inspections_inspectionnotification(notification_type);
CREATE INDEX IF NOT EXISTS idx_inspections_notification_sent ON inspections_inspectionnotification(sent);
CREATE INDEX IF NOT EXISTS idx_inspections_notification_sent_at ON inspections_inspectionnotification(sent_at DESC);

-- فهارس تقارير المعاينات
CREATE INDEX IF NOT EXISTS idx_inspections_report_type ON inspections_inspectionreport(report_type);
CREATE INDEX IF NOT EXISTS idx_inspections_report_branch ON inspections_inspectionreport(branch_id);
CREATE INDEX IF NOT EXISTS idx_inspections_report_date_from ON inspections_inspectionreport(date_from);
CREATE INDEX IF NOT EXISTS idx_inspections_report_date_to ON inspections_inspectionreport(date_to);
CREATE INDEX IF NOT EXISTS idx_inspections_report_created_at ON inspections_inspectionreport(created_at DESC);

-- فهارس التركيبات - INSTALLATIONS
CREATE INDEX IF NOT EXISTS idx_installations_schedule_order ON installations_installationschedule(order_id);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_team ON installations_installationschedule(team_id);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_status ON installations_installationschedule(status);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_scheduled_date ON installations_installationschedule(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_scheduled_time ON installations_installationschedule(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_created_at ON installations_installationschedule(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_completed_at ON installations_installationschedule(completed_at DESC);

-- فهارس مركبة للتركيبات
CREATE INDEX IF NOT EXISTS idx_installations_schedule_order_status ON installations_installationschedule(order_id, status);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_team_date ON installations_installationschedule(team_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_date_status ON installations_installationschedule(scheduled_date, status);
CREATE INDEX IF NOT EXISTS idx_installations_schedule_team_status ON installations_installationschedule(team_id, status);

-- فهارس جزئية للتركيبات النشطة
CREATE INDEX IF NOT EXISTS idx_installations_schedule_pending ON installations_installationschedule(scheduled_date, team_id) WHERE status IN ('scheduled', 'in_progress');
CREATE INDEX IF NOT EXISTS idx_installations_schedule_today ON installations_installationschedule(scheduled_time, team_id) WHERE scheduled_date = CURRENT_DATE;

-- فهارس فرق التركيب
CREATE INDEX IF NOT EXISTS idx_installations_team_name ON installations_installationteam(name);
CREATE INDEX IF NOT EXISTS idx_installations_team_active ON installations_installationteam(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_installations_team_created_at ON installations_installationteam(created_at DESC);

-- فهارس الفنيين
CREATE INDEX IF NOT EXISTS idx_installations_technician_name ON installations_technician(name);
CREATE INDEX IF NOT EXISTS idx_installations_technician_phone ON installations_technician(phone);
CREATE INDEX IF NOT EXISTS idx_installations_technician_active ON installations_technician(is_active) WHERE is_active = true;

-- فهارس السائقين
CREATE INDEX IF NOT EXISTS idx_installations_driver_name ON installations_driver(name);
CREATE INDEX IF NOT EXISTS idx_installations_driver_phone ON installations_driver(phone);
CREATE INDEX IF NOT EXISTS idx_installations_driver_active ON installations_driver(is_active) WHERE is_active = true;

-- فهارس الشكاوى - COMPLAINTS
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_customer ON complaints_complaint(customer_id);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_order ON complaints_complaint(order_id);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_status ON complaints_complaint(status);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_priority ON complaints_complaint(priority);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_type ON complaints_complaint(complaint_type_id);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_created_at ON complaints_complaint(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_resolved_at ON complaints_complaint(resolved_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_assigned_to ON complaints_complaint(assigned_to_id);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_created_by ON complaints_complaint(created_by_id);

-- فهارس مركبة للشكاوى
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_customer_status ON complaints_complaint(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_order_status ON complaints_complaint(order_id, status);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_status_priority ON complaints_complaint(status, priority);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_assigned_status ON complaints_complaint(assigned_to_id, status);
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_type_status ON complaints_complaint(complaint_type_id, status);

-- فهارس جزئية للشكاوى النشطة
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_unresolved ON complaints_complaint(created_at DESC, priority) WHERE status NOT IN ('resolved', 'closed');
CREATE INDEX IF NOT EXISTS idx_complaints_complaint_high_priority ON complaints_complaint(created_at DESC, assigned_to_id) WHERE priority = 'high';

-- فهارس أنواع الشكاوى
CREATE INDEX IF NOT EXISTS idx_complaints_type_name ON complaints_complainttype(name);
CREATE INDEX IF NOT EXISTS idx_complaints_type_active ON complaints_complainttype(is_active) WHERE is_active = true;

-- فهارس التقارير - REPORTS
CREATE INDEX IF NOT EXISTS idx_reports_report_type ON reports_report(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_report_created_by ON reports_report(created_by_id);
CREATE INDEX IF NOT EXISTS idx_reports_report_created_at ON reports_report(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_report_date_from ON reports_report(date_from);
CREATE INDEX IF NOT EXISTS idx_reports_report_date_to ON reports_report(date_to);
CREATE INDEX IF NOT EXISTS idx_reports_report_status ON reports_report(status);

-- فهارس مركبة للتقارير
CREATE INDEX IF NOT EXISTS idx_reports_report_type_date ON reports_report(report_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_report_creator_date ON reports_report(created_by_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_report_date_range ON reports_report(date_from, date_to);

-- فهارس الإشعارات - NOTIFICATIONS
CREATE INDEX IF NOT EXISTS idx_notifications_notification_type ON notifications_notification(notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_priority ON notifications_notification(priority);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_created_at ON notifications_notification(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_created_by ON notifications_notification(created_by_id);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_content_type ON notifications_notification(content_type_id);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_object_id ON notifications_notification(object_id);

-- فهارس مركبة للإشعارات
CREATE INDEX IF NOT EXISTS idx_notifications_notification_type_date ON notifications_notification(notification_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_priority_date ON notifications_notification(priority, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_notification_content_object ON notifications_notification(content_type_id, object_id);

-- فهارس رؤية الإشعارات
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_user ON notifications_notificationvisibility(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_notification ON notifications_notificationvisibility(notification_id);
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_read ON notifications_notificationvisibility(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_created_at ON notifications_notificationvisibility(created_at DESC);

-- فهارس مركبة لرؤية الإشعارات
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_user_read ON notifications_notificationvisibility(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_user_date ON notifications_notificationvisibility(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_visibility_unread ON notifications_notificationvisibility(user_id, created_at DESC) WHERE is_read = false;

-- فهارس إعدادات الإشعارات
CREATE INDEX IF NOT EXISTS idx_notifications_settings_user ON notifications_notificationsettings(user_id);

-- فهارس نشاط المستخدمين - USER ACTIVITY
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user ON user_activity_useractivitylog(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_action ON user_activity_useractivitylog(action_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_entity_type ON user_activity_useractivitylog(entity_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_entity_id ON user_activity_useractivitylog(entity_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_timestamp ON user_activity_useractivitylog(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_success ON user_activity_useractivitylog(success);

-- فهارس مركبة لنشاط المستخدمين
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_timestamp ON user_activity_useractivitylog(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_action ON user_activity_useractivitylog(user_id, action_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_entity ON user_activity_useractivitylog(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_action_timestamp ON user_activity_useractivitylog(action_type, timestamp DESC);

-- فهارس جزئية لنشاط المستخدمين
CREATE INDEX IF NOT EXISTS idx_user_activity_log_successful ON user_activity_useractivitylog(user_id, timestamp DESC) WHERE success = true;
CREATE INDEX IF NOT EXISTS idx_user_activity_log_failed ON user_activity_useractivitylog(user_id, timestamp DESC) WHERE success = false;

-- فهارس جلسات المستخدمين
CREATE INDEX IF NOT EXISTS idx_user_activity_session_user ON user_activity_usersession(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_session_login_time ON user_activity_usersession(login_time DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_session_logout_time ON user_activity_usersession(logout_time DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_session_active ON user_activity_usersession(is_active) WHERE is_active = true;

-- فهارس النسخ الاحتياطي - BACKUP SYSTEM (إذا كانت موجودة)
CREATE INDEX IF NOT EXISTS idx_backup_system_backup_type ON backup_system_databasebackup(backup_type);
CREATE INDEX IF NOT EXISTS idx_backup_system_backup_created_at ON backup_system_databasebackup(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_system_backup_success ON backup_system_databasebackup(success);
CREATE INDEX IF NOT EXISTS idx_backup_system_backup_size ON backup_system_databasebackup(file_size DESC);

-- فهارس مهام النسخ الاحتياطي
CREATE INDEX IF NOT EXISTS idx_backup_system_job_status ON backup_system_backupjob(status);
CREATE INDEX IF NOT EXISTS idx_backup_system_job_created_at ON backup_system_backupjob(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_system_job_started_at ON backup_system_backupjob(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_system_job_completed_at ON backup_system_backupjob(completed_at DESC);

-- فهارس للاستعلامات المعقدة والتقارير
CREATE INDEX IF NOT EXISTS idx_orders_monthly_stats ON orders_order(EXTRACT(YEAR FROM created_at), EXTRACT(MONTH FROM created_at), status);
CREATE INDEX IF NOT EXISTS idx_manufacturing_monthly_stats ON manufacturing_manufacturingorder(EXTRACT(YEAR FROM created_at), EXTRACT(MONTH FROM created_at), status);
CREATE INDEX IF NOT EXISTS idx_installations_monthly_stats ON installations_installationschedule(EXTRACT(YEAR FROM scheduled_date), EXTRACT(MONTH FROM scheduled_date), status);
CREATE INDEX IF NOT EXISTS idx_inspections_monthly_stats ON inspections_inspection(EXTRACT(YEAR FROM scheduled_date), EXTRACT(MONTH FROM scheduled_date), status);

-- فهارس للبحث المتقدم والتحليلات
CREATE INDEX IF NOT EXISTS idx_customers_revenue_analysis ON customers_customer(branch_id, customer_type, created_at DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_orders_revenue_analysis ON orders_order(branch_id, salesperson_id, total_amount DESC, created_at DESC) WHERE payment_verified = true;
CREATE INDEX IF NOT EXISTS idx_manufacturing_performance ON manufacturing_manufacturingorder(production_line_id, status, expected_delivery_date, completion_date);

-- فهارس للعمليات الإدارية
CREATE INDEX IF NOT EXISTS idx_admin_user_management ON accounts_user(is_staff, is_active, last_login DESC);
CREATE INDEX IF NOT EXISTS idx_admin_branch_management ON accounts_branch(is_active, is_main_branch, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_system_monitoring ON user_activity_useractivitylog(action_type, timestamp DESC) WHERE action_type IN ('login', 'logout', 'create', 'update', 'delete');

-- فهارس الجداول الافتراضية في Django
CREATE INDEX IF NOT EXISTS idx_django_session_expire_date ON django_session(expire_date);
CREATE INDEX IF NOT EXISTS idx_django_session_session_key ON django_session(session_key);

-- فهارس الصلاحيات
CREATE INDEX IF NOT EXISTS idx_auth_permission_codename ON auth_permission(codename);
CREATE INDEX IF NOT EXISTS idx_auth_permission_content_type ON auth_permission(content_type_id);
CREATE INDEX IF NOT EXISTS idx_auth_permission_name ON auth_permission(name);

-- فهارس المجموعات
CREATE INDEX IF NOT EXISTS idx_auth_group_name ON auth_group(name);

-- فهارس أنواع المحتوى
CREATE INDEX IF NOT EXISTS idx_django_content_type_app_model ON django_content_type(app_label, model);

-- فهارس المهام المجدولة
CREATE INDEX IF NOT EXISTS idx_django_apscheduler_job_next_run_time ON django_apscheduler_djangojob(next_run_time);
CREATE INDEX IF NOT EXISTS idx_django_apscheduler_job_enabled ON django_apscheduler_djangojob(enabled) WHERE enabled = true;

-- تحليل جميع الجداول الرئيسية لتحسين خطط الاستعلام
ANALYZE accounts_user;
ANALYZE accounts_branch;
ANALYZE accounts_department;
ANALYZE accounts_salesperson;
ANALYZE customers_customer;
ANALYZE customers_customercategory;
ANALYZE customers_customernote;
ANALYZE orders_order;
ANALYZE orders_orderitem;
ANALYZE orders_payment;
ANALYZE inventory_product;
ANALYZE inventory_category;
ANALYZE inventory_stocktransaction;
ANALYZE manufacturing_manufacturingorder;
ANALYZE manufacturing_manufacturingorderitem;
ANALYZE inspections_inspection;
ANALYZE inspections_inspectionevaluation;
ANALYZE inspections_inspectionnotification;
ANALYZE inspections_inspectionreport;
ANALYZE installations_installationschedule;
ANALYZE installations_installationteam;
ANALYZE complaints_complaint;
ANALYZE complaints_complainttype;
ANALYZE reports_report;
ANALYZE notifications_notification;
ANALYZE notifications_notificationvisibility;
ANALYZE user_activity_useractivitylog;
ANALYZE user_activity_usersession;
