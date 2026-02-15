#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام تطبيق الفهارس الشامل والمتكامل
ULTIMATE DATABASE INDEXING APPLICATION SYSTEM

هذا السكريبت يطبق جميع الفهارس المحسنة على قاعدة البيانات
مع إمكانية التطبيق على خادم ثانوي أو قاعدة بيانات منفصلة
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import psycopg2

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("ultimate_indexes_application.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class UltimateIndexManager:
    """مدير الفهارس الشامل والمتكامل"""

    def __init__(self, db_config: Dict[str, str]):
        """
        تهيئة مدير الفهارس

        Args:
            db_config: إعدادات قاعدة البيانات
        """
        self.db_config = db_config
        self.connection = None
        self.cursor = None
        self.stats = {
            "total_indexes": 0,
            "successful_indexes": 0,
            "failed_indexes": 0,
            "skipped_indexes": 0,
            "start_time": None,
            "end_time": None,
            "errors": [],
        }

    def connect_to_database(self) -> bool:
        """الاتصال بقاعدة البيانات"""
        try:
            logger.info("🔌 جاري الاتصال بقاعدة البيانات...")
            self.connection = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config["user"],
                password=self.db_config["password"],
            )
            self.cursor = self.connection.cursor()

            # التحقق من الاتصال
            self.cursor.execute("SELECT version();")
            version = self.cursor.fetchone()[0]
            logger.info(f"✅ تم الاتصال بنجاح: {version}")

            return True

        except Exception as e:
            logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {str(e)}")
            return False

    def disconnect_from_database(self):
        """قطع الاتصال بقاعدة البيانات"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("🔌 تم قطع الاتصال بقاعدة البيانات")
        except Exception as e:
            logger.error(f"❌ خطأ في قطع الاتصال: {str(e)}")

    def check_existing_indexes(self) -> Dict[str, bool]:
        """فحص الفهارس الموجودة"""
        try:
            logger.info("🔍 جاري فحص الفهارس الموجودة...")

            query = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            """

            self.cursor.execute(query)
            existing_indexes = {row[0]: True for row in self.cursor.fetchall()}

            logger.info(f"📊 تم العثور على {len(existing_indexes)} فهرس موجود")
            return existing_indexes

        except Exception as e:
            logger.error(f"❌ خطأ في فحص الفهارس الموجودة: {str(e)}")
            return {}

    def parse_sql_file(self, file_path: str) -> List[str]:
        """تحليل ملف SQL واستخراج أوامر إنشاء الفهارس"""
        try:
            logger.info(f"📖 جاري قراءة ملف الفهارس: {file_path}")

            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            # استخراج أوامر CREATE INDEX
            statements = []
            lines = content.split("\n")
            current_statement = ""

            for line in lines:
                line = line.strip()

                # تجاهل التعليقات والأسطر الفارغة
                if not line or line.startswith("--") or line.startswith("/*"):
                    continue

                # إضافة السطر للأمر الحالي
                current_statement += line + " "

                # إذا انتهى الأمر بفاصلة منقوطة
                if line.endswith(";"):
                    statement = current_statement.strip()
                    if statement.upper().startswith("CREATE INDEX"):
                        statements.append(statement)
                    elif statement.upper().startswith("ANALYZE"):
                        statements.append(statement)
                    current_statement = ""

            logger.info(f"📊 تم استخراج {len(statements)} أمر من الملف")
            return statements

        except Exception as e:
            logger.error(f"❌ خطأ في قراءة ملف SQL: {str(e)}")
            return []

    def extract_index_name(self, statement: str) -> Optional[str]:
        """استخراج اسم الفهرس من أمر CREATE INDEX"""
        try:
            # البحث عن اسم الفهرس في الأمر
            parts = statement.split()
            for i, part in enumerate(parts):
                if part.upper() == "EXISTS":
                    if i + 1 < len(parts):
                        return parts[i + 1]
                elif part.upper() == "INDEX" and i + 1 < len(parts):
                    next_part = parts[i + 1]
                    if next_part.upper() not in ["CONCURRENTLY", "IF"]:
                        return next_part
            return None
        except Exception:
            return None

    def apply_index(
        self, statement: str, existing_indexes: Dict[str, bool]
    ) -> Tuple[bool, str]:
        """تطبيق فهرس واحد"""
        try:
            # استخراج اسم الفهرس
            index_name = self.extract_index_name(statement)

            if not index_name:
                return False, "لا يمكن استخراج اسم الفهرس"

            # التحقق من وجود الفهرس
            if index_name in existing_indexes:
                logger.info(f"⏭️  الفهرس موجود بالفعل: {index_name}")
                self.stats["skipped_indexes"] += 1
                return True, "موجود بالفعل"

            # تطبيق الفهرس
            logger.info(f"🔨 جاري إنشاء الفهرس: {index_name}")
            start_time = time.time()

            # تعيين autocommit للفهارس CONCURRENTLY
            if "CONCURRENTLY" in statement.upper():
                old_autocommit = self.connection.autocommit
                self.connection.autocommit = True
                try:
                    self.cursor.execute(statement)
                    self.connection.autocommit = old_autocommit
                except Exception as e:
                    self.connection.autocommit = old_autocommit
                    raise e
            else:
                self.cursor.execute(statement)
                self.connection.commit()

            end_time = time.time()
            duration = end_time - start_time

            logger.info(
                f"✅ تم إنشاء الفهرس بنجاح: {index_name} ({duration:.2f} ثانية)"
            )
            self.stats["successful_indexes"] += 1

            return True, f"تم الإنشاء في {duration:.2f} ثانية"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ فشل إنشاء الفهرس: {error_msg}")
            self.stats["failed_indexes"] += 1
            self.stats["errors"].append(
                {
                    "statement": (
                        statement[:100] + "..." if len(statement) > 100 else statement
                    ),
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # محاولة التراجع عن التغييرات (فقط إذا لم يكن CONCURRENTLY)
            if "CONCURRENTLY" not in statement.upper():
                try:
                    self.connection.rollback()
                except Exception:
                    pass

            return False, error_msg

    def apply_all_indexes(self, sql_file_path: str) -> bool:
        """تطبيق جميع الفهارس من الملف"""
        try:
            logger.info("🚀 بدء تطبيق نظام الفهرسة الشامل...")
            self.stats["start_time"] = datetime.now()

            # قراءة أوامر SQL
            statements = self.parse_sql_file(sql_file_path)
            if not statements:
                logger.error("❌ لم يتم العثور على أوامر صالحة في الملف")
                return False

            self.stats["total_indexes"] = len(statements)

            # فحص الفهارس الموجودة
            existing_indexes = self.check_existing_indexes()

            # تطبيق كل فهرس
            logger.info(f"🔨 جاري تطبيق {len(statements)} أمر...")

            for i, statement in enumerate(statements, 1):
                logger.info(f"📊 التقدم: {i}/{len(statements)}")

                if statement.upper().startswith("ANALYZE"):
                    # تطبيق أمر ANALYZE
                    try:
                        self.cursor.execute(statement)
                        self.connection.commit()
                        logger.info(f"✅ تم تنفيذ ANALYZE بنجاح")
                    except Exception as e:
                        logger.warning(f"⚠️  تحذير في ANALYZE: {str(e)}")
                else:
                    # تطبيق فهرس
                    success, message = self.apply_index(statement, existing_indexes)
                    if not success and "موجود بالفعل" not in message:
                        logger.warning(f"⚠️  تحذير: {message}")

            self.stats["end_time"] = datetime.now()
            duration = (
                self.stats["end_time"] - self.stats["start_time"]
            ).total_seconds()

            # طباعة الإحصائيات النهائية
            logger.info("=" * 60)
            logger.info("📊 إحصائيات تطبيق الفهارس:")
            logger.info(f"📈 إجمالي الأوامر: {self.stats['total_indexes']}")
            logger.info(f"✅ نجح: {self.stats['successful_indexes']}")
            logger.info(f"⏭️  تم تخطيه: {self.stats['skipped_indexes']}")
            logger.info(f"❌ فشل: {self.stats['failed_indexes']}")
            logger.info(f"⏱️  الوقت الإجمالي: {duration:.2f} ثانية")
            logger.info("=" * 60)

            if self.stats["failed_indexes"] > 0:
                logger.warning(f"⚠️  تحذير: فشل {self.stats['failed_indexes']} فهرس")
                return False

            logger.info("🎉 تم تطبيق نظام الفهرسة بنجاح!")
            return True

        except Exception as e:
            logger.error(f"❌ خطأ عام في تطبيق الفهارس: {str(e)}")
            return False

    def generate_report(self, output_file: str = "indexing_report.json"):
        """إنشاء تقرير مفصل عن عملية التطبيق"""
        try:
            # تحويل التواريخ إلى نصوص
            stats_copy = self.stats.copy()
            if stats_copy.get("start_time"):
                stats_copy["start_time"] = stats_copy["start_time"].isoformat()
            if stats_copy.get("end_time"):
                stats_copy["end_time"] = stats_copy["end_time"].isoformat()

            report = {
                "timestamp": datetime.now().isoformat(),
                "database_config": {
                    "host": self.db_config["host"],
                    "port": self.db_config["port"],
                    "database": self.db_config["database"],
                    "user": self.db_config["user"],
                },
                "statistics": stats_copy,
                "success_rate": (
                    self.stats["successful_indexes"]
                    / max(self.stats["total_indexes"], 1)
                )
                * 100,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"📄 تم إنشاء التقرير: {output_file}")

        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء التقرير: {str(e)}")


def load_database_config(config_file: str = None) -> Dict[str, str]:
    """تحميل إعدادات قاعدة البيانات"""

    # إعدادات افتراضية للخادم المحلي
    default_config = {
        "host": "localhost",
        "port": "5432",
        "database": "crm_system",
        "user": "postgres",
        "password": "your_password",
    }

    # محاولة تحميل من ملف إعدادات
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"✅ تم تحميل الإعدادات من: {config_file}")
            return config
        except Exception as e:
            logger.warning(f"⚠️  خطأ في تحميل ملف الإعدادات: {str(e)}")

    # محاولة تحميل من متغيرات البيئة
    env_config = {}
    for key in default_config.keys():
        env_key = f"DB_{key.upper()}"
        if env_key in os.environ:
            env_config[key] = os.environ[env_key]

    if env_config:
        default_config.update(env_config)
        logger.info("✅ تم تحميل الإعدادات من متغيرات البيئة")

    return default_config


def main():
    """الدالة الرئيسية"""
    parser = argparse.ArgumentParser(
        description="نظام تطبيق الفهارس الشامل والمتكامل",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--sql-file",
        default="ULTIMATE_DATABASE_INDEXES.sql",
        help="مسار ملف الفهارس SQL (افتراضي: ULTIMATE_DATABASE_INDEXES.sql)",
    )

    parser.add_argument(
        "--simple",
        action="store_true",
        help="استخدام الفهارس المبسطة بدون CONCURRENTLY (ULTIMATE_DATABASE_INDEXES_SIMPLE.sql)",
    )

    parser.add_argument("--config-file", help="مسار ملف إعدادات قاعدة البيانات (JSON)")

    parser.add_argument("--host", help="عنوان خادم قاعدة البيانات")

    parser.add_argument("--port", help="منفذ قاعدة البيانات")

    parser.add_argument("--database", help="اسم قاعدة البيانات")

    parser.add_argument("--user", help="اسم المستخدم")

    parser.add_argument("--password", help="كلمة المرور")

    parser.add_argument(
        "--report-file",
        default="indexing_report.json",
        help="مسار ملف التقرير (افتراضي: indexing_report.json)",
    )

    args = parser.parse_args()

    # تحميل إعدادات قاعدة البيانات
    db_config = load_database_config(args.config_file)

    # تحديث الإعدادات من المعاملات
    if args.host:
        db_config["host"] = args.host
    if args.port:
        db_config["port"] = args.port
    if args.database:
        db_config["database"] = args.database
    if args.user:
        db_config["user"] = args.user
    if args.password:
        db_config["password"] = args.password

    # تحديد ملف الفهارس
    sql_file = args.sql_file
    if args.simple:
        sql_file = "ULTIMATE_DATABASE_INDEXES_SIMPLE.sql"
        logger.info("🔧 استخدام الفهارس المبسطة بدون CONCURRENTLY")

    # التحقق من وجود ملف SQL
    if not os.path.exists(sql_file):
        logger.error(f"❌ ملف SQL غير موجود: {sql_file}")
        sys.exit(1)

    # إنشاء مدير الفهارس وتطبيق النظام
    manager = UltimateIndexManager(db_config)

    try:
        # الاتصال بقاعدة البيانات
        if not manager.connect_to_database():
            sys.exit(1)

        # تطبيق الفهارس
        success = manager.apply_all_indexes(sql_file)

        # إنشاء التقرير
        manager.generate_report(args.report_file)

        # النتيجة النهائية
        if success:
            logger.info("🎉 تم تطبيق نظام الفهرسة الشامل بنجاح!")
            sys.exit(0)
        else:
            logger.error("❌ فشل في تطبيق بعض الفهارس")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹️  تم إيقاف العملية بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {str(e)}")
        sys.exit(1)
    finally:
        manager.disconnect_from_database()


if __name__ == "__main__":
    main()
