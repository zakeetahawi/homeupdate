# 📁 ملفات إدارية

> ⚠️ **هام**: هذا المجلد يحتوي على أدوات إدارية وسكريبتات صيانة فقط.
> **يمكن حذف هذا المجلد بالكامل دون أن يتوقف المشروع!**

---

## 📊 أدوات المراقبة والتشخيص

| الملف | الوصف |
|-------|-------|
| `monitor_indexes.py` | مراقبة فهارس قاعدة البيانات |
| `monitor_celery_startup.py` | مراقبة بدء Celery |
| `monitor_system.sh` | مراقبة النظام |
| `diagnose_tasks.py` | تشخيص المهام |
| `watch_upload_progress.py` | مراقبة تقدم الرفع |

## 🔧 أدوات الإصلاح

| الملف | الوصف |
|-------|-------|
| `fix_celery_issue.sh` | إصلاح مشاكل Celery |
| `auto_fix_services.sh` | إصلاح الخدمات تلقائياً |
| `reset_inventory_keep_orders.py` | إعادة تعيين المخزون |
| `rebuild_status_logs.py` | إعادة بناء سجلات الحالة |

## 🔒 أدوات الأمان

| الملف | الوصف |
|-------|-------|
| `security_pentest.py` | فحص الثغرات الأمنية |
| `web_security_scanner.py` | فاحص أمان الويب |
| `security_audit.py` | تدقيق أمني |

## ⚡ أدوات الأداء

| الملف | الوصف |
|-------|-------|
| `optimize_performance_100x.py` | تحسين الأداء |
| `apply_ultimate_indexes.py` | تطبيق الفهارس |
| `ULTIMATE_DATABASE_INDEXES_SIMPLE.sql` | SQL للفهارس |

## ✅ أدوات الفحص

| الملف | الوصف |
|-------|-------|
| `check_duplicate_products_warehouses.py` | فحص المنتجات المكررة |
| `check_products_manufacturing.py` | فحص منتجات التصنيع |
| `check_products_without_warehouse.py` | فحص منتجات بدون مستودع |
| `check_stuck_tasks.py` | فحص المهام المعلقة |
| `check_wizard_options.py` | فحص خيارات المعالج |
| `audit_all_warehouses.py` | تدقيق المستودعات |

## 🚀 سكريبتات التشغيل

| الملف | الوصف |
|-------|-------|
| `RUN_SERVER.sh` | تشغيل السيرفر |
| `start_dev.sh` | تشغيل وضع التطوير |
| `start_optimized.sh` | تشغيل محسّن |
| `start_optimized_daemon.sh` | تشغيل كـ daemon |
| `stop_daemon.sh` | إيقاف الـ daemon |

## 📄 ملفات التقارير

| الملف | الوصف |
|-------|-------|
| `security_report.json` | تقرير الأمان |
| `indexing_report.json` | تقرير الفهرسة |
| `performance_optimization_report.json` | تقرير الأداء |

## ⚙️ ملفات الإعدادات

| الملف | الوصف |
|-------|-------|
| `database_config_local.json` | إعدادات DB المحلية |
| `database_config_secondary.json` | إعدادات DB الثانوية |
| `db_settings.json` | إعدادات DB |

---

## 🎯 طريقة الاستخدام

```bash
# تشغيل فحص الأمان
cd ملفات_إدارية
python security_pentest.py

# تشغيل السيرفر
./RUN_SERVER.sh
```

---

📅 آخر تحديث: ديسمبر 2025
