"""
Connection Pool مخصص لإدارة اتصالات قاعدة البيانات بكفاءة
Custom Database Connection Pool for efficient database connection management
"""

import threading
import time
import logging
import psycopg2
import psycopg2.pool
from django.conf import settings
from contextlib import contextmanager

logger = logging.getLogger('db_pool')


class DatabaseConnectionPool:
    """
    Connection Pool مخصص لإدارة اتصالات PostgreSQL
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._pool = None
        self._stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_in_use': 0,
            'pool_hits': 0,
            'pool_misses': 0,
        }
        self._create_pool()
    
    def _create_pool(self):
        """إنشاء connection pool"""
        try:
            db_config = settings.DATABASES['default']

            # تجربة إنشاء pool مع معالجة الأخطاء
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,          # الحد الأدنى للاتصالات (مخفض)
                maxconn=5,          # الحد الأقصى للاتصالات (مخفض)
                host=db_config['HOST'],
                port=db_config['PORT'],
                database=db_config['NAME'],
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                # إعدادات إضافية للأداء
                connect_timeout=10,
                application_name='homeupdate_pool',
            )

            logger.info("Database connection pool created successfully")

        except Exception as e:
            logger.warning(f"Failed to create database connection pool: {e}")
            # في حالة الفشل، تعطيل pool
            self._pool = None
    
    @contextmanager
    def get_connection(self):
        """
        الحصول على اتصال من pool مع context manager
        """
        connection = None
        try:
            if self._pool is None:
                self._create_pool()

            if self._pool is None:
                # إذا فشل إنشاء pool، استخدم اتصال مباشر
                db_config = settings.DATABASES['default']
                connection = psycopg2.connect(
                    host=db_config['HOST'],
                    port=db_config['PORT'],
                    database=db_config['NAME'],
                    user=db_config['USER'],
                    password=db_config['PASSWORD'],
                    connect_timeout=10,
                )
                self._stats['pool_misses'] += 1
                logger.debug("Using direct connection (pool unavailable)")
            else:
                connection = self._pool.getconn()
                if connection:
                    self._stats['connections_in_use'] += 1
                    self._stats['pool_hits'] += 1
                    logger.debug("Connection acquired from pool")
                else:
                    self._stats['pool_misses'] += 1
                    logger.warning("Failed to acquire connection from pool")
                    raise Exception("No connection available in pool")

            yield connection

        except Exception as e:
            logger.error(f"Error with database connection: {e}")
            if connection:
                # في حالة الخطأ، أغلق الاتصال
                try:
                    connection.rollback()
                except:
                    pass
            raise

        finally:
            if connection:
                try:
                    if self._pool is not None:
                        # إعادة الاتصال إلى pool
                        self._pool.putconn(connection)
                        self._stats['connections_in_use'] -= 1
                        logger.debug("Connection returned to pool")
                    else:
                        # إغلاق الاتصال المباشر
                        connection.close()
                        logger.debug("Direct connection closed")
                except Exception as e:
                    logger.error(f"Error handling connection cleanup: {e}")
    
    def get_stats(self):
        """إحصائيات pool"""
        if self._pool:
            return {
                **self._stats,
                'pool_size': len(self._pool._pool),
                'available_connections': len([c for c in self._pool._pool if c]),
            }
        return self._stats
    
    def close_all_connections(self):
        """إغلاق جميع الاتصالات"""
        if self._pool:
            try:
                self._pool.closeall()
                logger.info("All connections in pool closed")
                self._stats['connections_closed'] += self._stats['connections_in_use']
                self._stats['connections_in_use'] = 0
            except Exception as e:
                logger.error(f"Error closing pool connections: {e}")
    
    def health_check(self):
        """فحص صحة pool"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Pool health check failed: {e}")
            return False


class SmartConnectionManager:
    """
    مدير اتصالات ذكي يختار بين PgBouncer والاتصال المباشر
    """
    
    def __init__(self):
        self.pool = DatabaseConnectionPool()
        self.use_pgbouncer = True
        self.fallback_attempts = 0
        self.max_fallback_attempts = 3
    
    @contextmanager
    def get_connection(self):
        """
        الحصول على اتصال مع fallback تلقائي
        """
        if self.use_pgbouncer and self.fallback_attempts < self.max_fallback_attempts:
            try:
                # محاولة استخدام PgBouncer
                with self.pool.get_connection() as conn:
                    yield conn
                    return
            except Exception as e:
                logger.warning(f"PgBouncer connection failed: {e}")
                self.fallback_attempts += 1
                
                if self.fallback_attempts >= self.max_fallback_attempts:
                    logger.error("Too many PgBouncer failures, switching to direct connection")
                    self.use_pgbouncer = False
        
        # Fallback إلى الاتصال المباشر
        try:
            direct_config = settings.DATABASES_DIRECT['default']
            conn = psycopg2.connect(
                host=direct_config['HOST'],
                port=direct_config['PORT'],
                database=direct_config['NAME'],
                user=direct_config['USER'],
                password=direct_config['PASSWORD'],
                connect_timeout=10,
            )
            
            logger.info("Using direct database connection")
            yield conn
            
        except Exception as e:
            logger.error(f"Direct connection also failed: {e}")
            raise
        finally:
            try:
                conn.close()
            except:
                pass
    
    def reset_fallback(self):
        """إعادة تعيين fallback للمحاولة مع PgBouncer مرة أخرى"""
        self.fallback_attempts = 0
        self.use_pgbouncer = True
        logger.info("Fallback reset, will try PgBouncer again")


# إنشاء نسخة عامة
connection_manager = SmartConnectionManager()


class ConnectionPoolMiddleware:
    """
    Middleware لاستخدام connection pool المخصص
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.pool = DatabaseConnectionPool()
    
    def __call__(self, request):
        # إضافة معلومات pool إلى request
        request.db_pool_stats = self.pool.get_stats()
        
        response = self.get_response(request)
        
        # تنظيف دوري كل 100 طلب
        if hasattr(request, 'db_pool_stats'):
            total_requests = (
                request.db_pool_stats.get('pool_hits', 0) + 
                request.db_pool_stats.get('pool_misses', 0)
            )
            
            if total_requests % 100 == 0:
                # فحص صحة pool
                if not self.pool.health_check():
                    logger.warning("Pool health check failed, recreating pool")
                    self.pool.close_all_connections()
                    self.pool._create_pool()
        
        return response


def get_pool_statistics():
    """الحصول على إحصائيات pool للمراقبة"""
    pool = DatabaseConnectionPool()
    return pool.get_stats()


def cleanup_pool():
    """تنظيف pool - للاستخدام في المهام الدورية"""
    pool = DatabaseConnectionPool()
    pool.close_all_connections()
    pool._create_pool()
    logger.info("Connection pool cleaned up and recreated")


# دوال مساعدة للاستخدام في Views
@contextmanager
def get_db_connection():
    """
    دالة مساعدة للحصول على اتصال قاعدة بيانات
    """
    with connection_manager.get_connection() as conn:
        yield conn


def execute_query(query, params=None):
    """
    تنفيذ استعلام مع إدارة تلقائية للاتصال
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchall()
            return cursor.rowcount
