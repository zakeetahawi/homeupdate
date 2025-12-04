#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مراقبة ومتابعة الفهارس
DATABASE INDEXES MONITORING SYSTEM

هذا السكريبت يراقب أداء الفهارس ويقدم تقارير مفصلة
عن استخدام الفهارس وتوصيات التحسين
"""

import os
import sys
import json
import psycopg2
from datetime import datetime
from typing import Dict, List, Tuple
import argparse
import logging

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indexes_monitoring.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class IndexMonitor:
    """مراقب الفهارس"""
    
    def __init__(self, db_config: Dict[str, str]):
        """تهيئة مراقب الفهارس"""
        self.db_config = db_config
        self.connection = None
        self.cursor = None
    
    def connect_to_database(self) -> bool:
        """الاتصال بقاعدة البيانات"""
        try:
            logger.info("🔌 جاري الاتصال بقاعدة البيانات...")
            self.connection = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            self.cursor = self.connection.cursor()
            logger.info("✅ تم الاتصال بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ فشل الاتصال: {str(e)}")
            return False
    
    def get_index_usage_stats(self) -> List[Dict]:
        """إحصائيات استخدام الفهارس"""
        try:
            query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan as scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                pg_relation_size(indexrelid) as size_bytes
            FROM pg_stat_user_indexes 
            WHERE schemaname = 'public'
            ORDER BY idx_scan DESC;
            """
            
            self.cursor.execute(query)
            results = []
            
            for row in self.cursor.fetchall():
                results.append({
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'scans': row[3] or 0,
                    'tuples_read': row[4] or 0,
                    'tuples_fetched': row[5] or 0,
                    'size_pretty': row[6],
                    'size_bytes': row[7] or 0
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات الفهارس: {str(e)}")
            return []
    
    def get_unused_indexes(self, min_scans: int = 10) -> List[Dict]:
        """الفهارس غير المستخدمة أو قليلة الاستخدام"""
        try:
            query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                pg_relation_size(indexrelid) as size_bytes
            FROM pg_stat_user_indexes 
            WHERE schemaname = 'public'
            AND (idx_scan IS NULL OR idx_scan < %s)
            AND indexname NOT LIKE '%%_pkey'
            ORDER BY pg_relation_size(indexrelid) DESC;
            """
            
            self.cursor.execute(query, (min_scans,))
            results = []
            
            for row in self.cursor.fetchall():
                results.append({
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'scans': row[3] or 0,
                    'size_pretty': row[4],
                    'size_bytes': row[5] or 0
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الفهارس غير المستخدمة: {str(e)}")
            return []
    
    def get_table_sizes(self) -> List[Dict]:
        """أحجام الجداول والفهارس"""
        try:
            query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size,
                pg_total_relation_size(schemaname||'.'||tablename) as total_bytes,
                pg_relation_size(schemaname||'.'||tablename) as table_bytes,
                pg_indexes_size(schemaname||'.'||tablename) as indexes_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """
            
            self.cursor.execute(query)
            results = []
            
            for row in self.cursor.fetchall():
                results.append({
                    'schema': row[0],
                    'table': row[1],
                    'total_size': row[2],
                    'table_size': row[3],
                    'indexes_size': row[4],
                    'total_bytes': row[5] or 0,
                    'table_bytes': row[6] or 0,
                    'indexes_bytes': row[7] or 0
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب أحجام الجداول: {str(e)}")
            return []
    
    def get_slow_queries(self) -> List[Dict]:
        """الاستعلامات البطيئة (إذا كان pg_stat_statements مفعل)"""
        try:
            # التحقق من وجود pg_stat_statements
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                );
            """)
            
            if not self.cursor.fetchone()[0]:
                logger.warning("⚠️  pg_stat_statements غير مفعل")
                return []
            
            query = """
            SELECT 
                query,
                calls,
                total_time,
                mean_time,
                rows
            FROM pg_stat_statements 
            WHERE query NOT LIKE '%pg_stat_statements%'
            ORDER BY mean_time DESC 
            LIMIT 20;
            """
            
            self.cursor.execute(query)
            results = []
            
            for row in self.cursor.fetchall():
                results.append({
                    'query': row[0][:200] + '...' if len(row[0]) > 200 else row[0],
                    'calls': row[1],
                    'total_time': round(row[2], 2),
                    'mean_time': round(row[3], 2),
                    'rows': row[4]
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"⚠️  لا يمكن جلب الاستعلامات البطيئة: {str(e)}")
            return []
    
    def generate_recommendations(self, unused_indexes: List[Dict], 
                               index_stats: List[Dict]) -> List[str]:
        """إنشاء توصيات التحسين"""
        recommendations = []
        
        # توصيات للفهارس غير المستخدمة
        if unused_indexes:
            total_unused_size = sum(idx['size_bytes'] for idx in unused_indexes)
            recommendations.append(
                f"🗑️  يمكن حذف {len(unused_indexes)} فهرس غير مستخدم "
                f"لتوفير {self._format_bytes(total_unused_size)} من المساحة"
            )
            
            # أكبر الفهارس غير المستخدمة
            largest_unused = sorted(unused_indexes, key=lambda x: x['size_bytes'], reverse=True)[:5]
            for idx in largest_unused:
                recommendations.append(
                    f"  - {idx['index']} على جدول {idx['table']} ({idx['size_pretty']})"
                )
        
        # توصيات للفهارس عالية الاستخدام
        high_usage = [idx for idx in index_stats if idx['scans'] > 10000]
        if high_usage:
            recommendations.append(
                f"⚡ {len(high_usage)} فهرس عالي الاستخدام - تأكد من صحة تكوينها"
            )
        
        # توصيات عامة
        recommendations.extend([
            "📊 قم بتشغيل ANALYZE بانتظام لتحديث إحصائيات الجداول",
            "🔄 راقب أداء الاستعلامات بعد إضافة فهارس جديدة",
            "📈 استخدم EXPLAIN ANALYZE لتحليل خطط الاستعلام",
            "🧹 قم بتنظيف الفهارس غير المستخدمة دورياً"
        ])
        
        return recommendations
    
    def _format_bytes(self, bytes_size: int) -> str:
        """تنسيق حجم البايتات"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
    
    def generate_monitoring_report(self, output_file: str = "indexes_monitoring_report.json"):
        """إنشاء تقرير مراقبة شامل"""
        try:
            logger.info("📊 جاري إنشاء تقرير المراقبة...")
            
            # جمع البيانات
            index_stats = self.get_index_usage_stats()
            unused_indexes = self.get_unused_indexes()
            table_sizes = self.get_table_sizes()
            slow_queries = self.get_slow_queries()
            
            # إنشاء التوصيات
            recommendations = self.generate_recommendations(unused_indexes, index_stats)
            
            # إحصائيات عامة
            total_indexes = len(index_stats)
            total_unused = len(unused_indexes)
            total_index_size = sum(idx['size_bytes'] for idx in index_stats)
            total_unused_size = sum(idx['size_bytes'] for idx in unused_indexes)
            
            # إنشاء التقرير
            report = {
                'timestamp': datetime.now().isoformat(),
                'database_info': {
                    'host': self.db_config['host'],
                    'database': self.db_config['database']
                },
                'summary': {
                    'total_indexes': total_indexes,
                    'unused_indexes': total_unused,
                    'total_index_size': self._format_bytes(total_index_size),
                    'unused_index_size': self._format_bytes(total_unused_size),
                    'usage_efficiency': round((total_indexes - total_unused) / max(total_indexes, 1) * 100, 2)
                },
                'index_usage_stats': index_stats[:20],  # أفضل 20 فهرس
                'unused_indexes': unused_indexes,
                'table_sizes': table_sizes[:10],  # أكبر 10 جداول
                'slow_queries': slow_queries,
                'recommendations': recommendations
            }
            
            # حفظ التقرير
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 تم إنشاء تقرير المراقبة: {output_file}")
            
            # طباعة ملخص
            self._print_summary(report)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء تقرير المراقبة: {str(e)}")
            return False
    
    def _print_summary(self, report: Dict):
        """طباعة ملخص التقرير"""
        summary = report['summary']
        
        print("\n" + "=" * 60)
        print("📊 ملخص تقرير مراقبة الفهارس")
        print("=" * 60)
        print(f"📈 إجمالي الفهارس: {summary['total_indexes']}")
        print(f"🗑️  الفهارس غير المستخدمة: {summary['unused_indexes']}")
        print(f"💾 حجم الفهارس الإجمالي: {summary['total_index_size']}")
        print(f"🗑️  حجم الفهارس غير المستخدمة: {summary['unused_index_size']}")
        print(f"⚡ كفاءة الاستخدام: {summary['usage_efficiency']}%")
        
        if report['unused_indexes']:
            print(f"\n🗑️  أكبر الفهارس غير المستخدمة:")
            for idx in sorted(report['unused_indexes'], key=lambda x: x['size_bytes'], reverse=True)[:5]:
                print(f"  - {idx['index']} ({idx['size_pretty']})")
        
        if report['recommendations']:
            print(f"\n💡 التوصيات:")
            for rec in report['recommendations'][:5]:
                print(f"  {rec}")
        
        print("=" * 60)
    
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

def load_database_config(config_file: str = None) -> Dict[str, str]:
    """تحميل إعدادات قاعدة البيانات"""
    default_config = {
        'host': 'localhost',
        'port': '5432',
        'database': 'crm_system',
        'user': 'postgres',
        'password': 'your_password'
    }
    
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✅ تم تحميل الإعدادات من: {config_file}")
            return config
        except Exception as e:
            logger.warning(f"⚠️  خطأ في تحميل ملف الإعدادات: {str(e)}")
    
    return default_config

def main():
    """الدالة الرئيسية"""
    parser = argparse.ArgumentParser(
        description='نظام مراقبة ومتابعة الفهارس',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config-file',
        help='مسار ملف إعدادات قاعدة البيانات (JSON)'
    )
    
    parser.add_argument(
        '--report-file',
        default='indexes_monitoring_report.json',
        help='مسار ملف التقرير (افتراضي: indexes_monitoring_report.json)'
    )
    
    parser.add_argument(
        '--min-scans',
        type=int,
        default=10,
        help='الحد الأدنى لعدد المسحات لاعتبار الفهرس مستخدم (افتراضي: 10)'
    )
    
    args = parser.parse_args()
    
    # تحميل إعدادات قاعدة البيانات
    db_config = load_database_config(args.config_file)
    
    # إنشاء مراقب الفهارس
    monitor = IndexMonitor(db_config)
    
    try:
        # الاتصال بقاعدة البيانات
        if not monitor.connect_to_database():
            sys.exit(1)
        
        # إنشاء تقرير المراقبة
        success = monitor.generate_monitoring_report(args.report_file)
        
        if success:
            logger.info("🎉 تم إنشاء تقرير المراقبة بنجاح!")
            sys.exit(0)
        else:
            logger.error("❌ فشل في إنشاء تقرير المراقبة")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️  تم إيقاف العملية بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {str(e)}")
        sys.exit(1)
    finally:
        monitor.disconnect_from_database()

if __name__ == "__main__":
    main()
