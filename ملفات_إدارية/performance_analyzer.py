#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 أداة تحليل الأداء الشامل - Performance Analyzer
تحليل Frontend + Backend + Admin Panel + Database

الهدف: تحديد نقاط البطء وتقديم حلول لتسريع 1000x
"""

import os
import sys
import re
import json
import time
from pathlib import Path
from collections import defaultdict

# إضافة المشروع للـ path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

from django.conf import settings


def print_header(title):
    """طباعة عنوان"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_section(title):
    """طباعة قسم"""
    print(f"\n📊 {title}")
    print("-" * 50)


def analyze_database():
    """تحليل أداء قاعدة البيانات"""
    print_header("🗄️ تحليل قاعدة البيانات")
    
    from django.db import connection
    
    issues = []
    optimizations = []
    
    # 1. فحص الفهارس
    print_section("فحص الفهارس")
    with connection.cursor() as cursor:
        # عدد الفهارس
        cursor.execute("""
            SELECT count(*) FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        index_count = cursor.fetchone()[0]
        print(f"  ✅ عدد الفهارس: {index_count}")
        
        # الجداول بدون فهارس
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT IN (
                SELECT tablename FROM pg_indexes WHERE schemaname = 'public'
            )
        """)
        tables_no_index = cursor.fetchall()
        if tables_no_index:
            issues.append(f"⚠️ {len(tables_no_index)} جداول بدون فهارس")
        
        # حجم الجداول
        cursor.execute("""
            SELECT relname, n_live_tup, pg_size_pretty(pg_total_relation_size(relid))
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
            LIMIT 10
        """)
        large_tables = cursor.fetchall()
        print(f"\n  📈 أكبر 10 جداول:")
        for table, rows, size in large_tables:
            print(f"     - {table}: {rows:,} صف ({size})")
    
    # 2. فحص الاستعلامات البطيئة
    print_section("إعدادات قاعدة البيانات")
    db_settings = settings.DATABASES['default']
    conn_max_age = db_settings.get('CONN_MAX_AGE', 0)
    print(f"  ✅ CONN_MAX_AGE: {conn_max_age} ثانية")
    
    if conn_max_age == 0:
        issues.append("⚠️ CONN_MAX_AGE = 0 (اتصالات جديدة لكل طلب)")
        optimizations.append("💡 زيادة CONN_MAX_AGE إلى 300-600")
    
    return issues, optimizations


def analyze_cache():
    """تحليل نظام التخزين المؤقت"""
    print_header("💾 تحليل Cache")
    
    issues = []
    optimizations = []
    
    cache_backend = settings.CACHES.get('default', {}).get('BACKEND', '')
    
    print_section("إعدادات Cache الحالية")
    if 'redis' in cache_backend.lower():
        print("  ✅ Redis Cache مفعّل")
        
        # فحص اتصال Redis
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
            info = redis.info()
            print(f"  ✅ Redis متصل - الذاكرة: {info.get('used_memory_human', 'N/A')}")
            print(f"  ✅ عدد المفاتيح: {info.get('db1', {}).get('keys', 0)}")
        except Exception as e:
            issues.append(f"⚠️ Redis غير متصل: {e}")
            optimizations.append("💡 تأكد من تشغيل Redis: systemctl start redis")
    else:
        issues.append("⚠️ Cache بدون Redis")
        optimizations.append("💡 استخدم Redis للـ Cache")
    
    # فحص Session Cache
    session_engine = settings.SESSION_ENGINE
    print(f"\n  📦 Session Engine: {session_engine}")
    
    if 'cache' not in session_engine:
        optimizations.append("💡 استخدم cache للـ sessions: SESSION_ENGINE = 'django.contrib.sessions.backends.cache'")
    
    return issues, optimizations


def analyze_static_files():
    """تحليل الملفات الثابتة"""
    print_header("📁 تحليل الملفات الثابتة (Frontend)")
    
    issues = []
    optimizations = []
    
    static_dir = Path(settings.BASE_DIR) / 'static'
    
    # حساب الأحجام
    css_size = 0
    js_size = 0
    css_files = []
    js_files = []
    
    for f in static_dir.rglob('*.css'):
        size = f.stat().st_size
        css_size += size
        if size > 50000:  # > 50KB
            css_files.append((f.name, size))
    
    for f in static_dir.rglob('*.js'):
        size = f.stat().st_size
        js_size += size
        if size > 100000:  # > 100KB
            js_files.append((f.name, size))
    
    print_section("حجم الملفات")
    print(f"  📄 CSS الكلي: {css_size / 1024:.1f} KB")
    print(f"  📜 JS الكلي: {js_size / 1024:.1f} KB")
    
    if css_files:
        print(f"\n  ⚠️ ملفات CSS كبيرة:")
        for name, size in sorted(css_files, key=lambda x: -x[1])[:5]:
            print(f"     - {name}: {size/1024:.1f} KB")
        optimizations.append("💡 ضغط ملفات CSS باستخدام cssnano")
    
    if js_files:
        print(f"\n  ⚠️ ملفات JS كبيرة:")
        for name, size in sorted(js_files, key=lambda x: -x[1])[:5]:
            print(f"     - {name}: {size/1024:.1f} KB")
        optimizations.append("💡 ضغط ملفات JS باستخدام terser")
    
    # فحص WhiteNoise
    print_section("إعدادات الملفات الثابتة")
    storage = settings.STATICFILES_STORAGE
    if 'whitenoise' in storage.lower():
        print("  ✅ WhiteNoise مفعّل مع ضغط")
    else:
        issues.append("⚠️ WhiteNoise غير مفعّل")
        optimizations.append("💡 استخدم WhiteNoise لضغط وتخزين الملفات")
    
    return issues, optimizations


def analyze_templates():
    """تحليل القوالب"""
    print_header("📝 تحليل القوالب (Templates)")
    
    issues = []
    optimizations = []
    
    templates_dir = Path(settings.BASE_DIR) / 'templates'
    
    total_templates = 0
    large_templates = []
    templates_with_loops = []
    external_cdn = []
    
    for template in templates_dir.rglob('*.html'):
        total_templates += 1
        content = template.read_text(encoding='utf-8', errors='ignore')
        size = len(content)
        
        # ملفات كبيرة
        if size > 50000:
            large_templates.append((template.name, size))
        
        # حلقات كثيرة
        loop_count = len(re.findall(r'{%\s*for\s+', content))
        if loop_count > 5:
            templates_with_loops.append((template.name, loop_count))
        
        # CDN خارجي
        cdn_matches = re.findall(r'(https?://cdn\.[^\s"\']+)', content)
        if cdn_matches:
            for cdn in cdn_matches:
                external_cdn.append((template.name, cdn))
    
    print_section("إحصائيات القوالب")
    print(f"  📄 عدد القوالب: {total_templates}")
    
    if large_templates:
        print(f"\n  ⚠️ قوالب كبيرة (>50KB):")
        for name, size in sorted(large_templates, key=lambda x: -x[1])[:5]:
            print(f"     - {name}: {size/1024:.1f} KB")
        optimizations.append("💡 تقسيم القوالب الكبيرة باستخدام {% include %}")
    
    if templates_with_loops:
        print(f"\n  ⚠️ قوالب بحلقات كثيرة:")
        for name, count in sorted(templates_with_loops, key=lambda x: -x[1])[:5]:
            print(f"     - {name}: {count} حلقات")
        optimizations.append("💡 استخدم pagination للقوائم الكبيرة")
    
    if external_cdn:
        print(f"\n  ⚠️ استخدام CDN خارجي ({len(external_cdn)} ملف):")
        issues.append(f"⚠️ {len(external_cdn)} ملف يستخدم CDN خارجي (بطء)")
        optimizations.append("💡 استضف المكتبات محلياً لتقليل الـ latency")
    
    return issues, optimizations


def analyze_middleware():
    """تحليل Middleware"""
    print_header("🔧 تحليل Middleware")
    
    issues = []
    optimizations = []
    
    middleware_list = settings.MIDDLEWARE
    
    print_section("قائمة Middleware")
    print(f"  📦 عدد الـ Middleware: {len(middleware_list)}")
    
    for i, mw in enumerate(middleware_list, 1):
        name = mw.split('.')[-1]
        print(f"  {i}. {name}")
    
    if len(middleware_list) > 15:
        issues.append(f"⚠️ عدد كبير من Middleware: {len(middleware_list)}")
        optimizations.append("💡 راجع الـ Middleware وأزل غير الضروري")
    
    return issues, optimizations


def analyze_context_processors():
    """تحليل Context Processors"""
    print_header("⚙️ تحليل Context Processors")
    
    issues = []
    optimizations = []
    
    templates_config = settings.TEMPLATES[0]
    context_processors = templates_config.get('OPTIONS', {}).get('context_processors', [])
    
    print_section("قائمة Context Processors")
    print(f"  📦 العدد: {len(context_processors)}")
    
    custom_processors = [cp for cp in context_processors if not cp.startswith('django.')]
    
    if custom_processors:
        print(f"\n  ⚙️ Context Processors مخصصة ({len(custom_processors)}):")
        for cp in custom_processors:
            print(f"     - {cp.split('.')[-1]}")
        
        if len(custom_processors) > 5:
            issues.append(f"⚠️ عدد كبير من Context Processors: {len(custom_processors)}")
            optimizations.append("💡 دمج Context Processors أو استخدم caching")
    
    return issues, optimizations


def analyze_admin_panel():
    """تحليل لوحة التحكم"""
    print_header("🎛️ تحليل لوحة التحكم (Admin)")
    
    issues = []
    optimizations = []
    
    from django.contrib.admin.sites import all_sites
    from django.apps import apps
    
    print_section("النماذج المسجلة")
    
    # حساب النماذج
    total_models = 0
    models_without_optimization = []
    
    for admin_site in all_sites:
        for model, model_admin in admin_site._registry.items():
            total_models += 1
            
            # فحص select_related/prefetch_related
            has_optimization = False
            if hasattr(model_admin, 'list_select_related') and model_admin.list_select_related:
                has_optimization = True
            if hasattr(model_admin, 'get_queryset'):
                import inspect
                source = inspect.getsource(model_admin.get_queryset)
                if 'select_related' in source or 'prefetch_related' in source:
                    has_optimization = True
            
            if not has_optimization:
                models_without_optimization.append(model.__name__)
    
    print(f"  📦 عدد النماذج المسجلة: {total_models}")
    
    if models_without_optimization:
        print(f"\n  ⚠️ نماذج بدون تحسين ({len(models_without_optimization)}):")
        for name in models_without_optimization[:10]:
            print(f"     - {name}")
        if len(models_without_optimization) > 10:
            print(f"     ... و {len(models_without_optimization) - 10} أخرى")
        issues.append(f"⚠️ {len(models_without_optimization)} نموذج بدون select_related/prefetch_related")
        optimizations.append("💡 أضف select_related/prefetch_related في get_queryset")
    
    return issues, optimizations


def analyze_queries():
    """تحليل الاستعلامات"""
    print_header("🔍 تحليل الاستعلامات (N+1 Problem)")
    
    issues = []
    optimizations = []
    
    # البحث عن استعلامات بدون تحسين
    project_dir = Path(settings.BASE_DIR)
    
    problematic_patterns = [
        (r'\.objects\.all\(\)', 'استخدام all() بدون filter/select_related'),
        (r'\.objects\.filter\([^)]+\)(?!\.select)', 'filter بدون select_related'),
        (r'for\s+\w+\s+in\s+\w+\.objects', 'حلقة مباشرة على objects'),
    ]
    
    findings = defaultdict(list)
    
    for py_file in project_dir.rglob('*.py'):
        if 'venv' in str(py_file) or 'migration' in str(py_file):
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            
            # عدّ الأنماط الخطرة
            for pattern, desc in problematic_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    findings[desc].append(py_file.name)
        except:
            pass
    
    print_section("أنماط قد تسبب N+1")
    for desc, files in findings.items():
        if len(files) > 3:
            print(f"  ⚠️ {desc}:")
            print(f"     في {len(files)} ملف")
    
    return issues, optimizations


def generate_optimization_script():
    """إنشاء سكريبت التحسين"""
    print_header("🚀 توصيات التحسين لتسريع 1000x")
    
    recommendations = """
╔══════════════════════════════════════════════════════════════════════════╗
║                    🚀 خطة التسريع 1000x                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ⚡ المستوى 1: تحسينات فورية (10x أسرع)                                   ║
║  ────────────────────────────────────────                                ║
║  ✓ تفعيل Redis Cache للجلسات والاستعلامات                               ║
║  ✓ CONN_MAX_AGE = 600 (إعادة استخدام الاتصالات)                          ║
║  ✓ إضافة فهارس للجداول الكبيرة                                          ║
║  ✓ تفعيل WhiteNoise للملفات الثابتة                                     ║
║                                                                          ║
║  ⚡ المستوى 2: تحسينات متوسطة (100x أسرع)                                 ║
║  ────────────────────────────────────────                                ║
║  ✓ select_related/prefetch_related في كل الاستعلامات                     ║
║  ✓ Pagination للقوائم الكبيرة (max 25 عنصر)                              ║
║  ✓ Lazy Loading للصور والمحتوى                                          ║
║  ✓ استضافة المكتبات محلياً (بدون CDN)                                   ║
║  ✓ ضغط CSS/JS (minify)                                                  ║
║                                                                          ║
║  ⚡ المستوى 3: تحسينات متقدمة (1000x أسرع)                                ║
║  ────────────────────────────────────────                                ║
║  ✓ تخزين النتائج في Redis (@cache_page)                                 ║
║  ✓ Async views للعمليات الطويلة                                         ║
║  ✓ Database read replicas                                               ║
║  ✓ Celery للمهام الخلفية                                                ║
║  ✓ HTTP/2 + Brotli compression                                          ║
║  ✓ CDN (Cloudflare) للملفات الثابتة                                     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    print(recommendations)


def main():
    """التحليل الشامل"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  🚀 أداة تحليل الأداء الشامل - Performance Analyzer                      ║
║  تحليل: Frontend + Backend + Admin + Database                           ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    all_issues = []
    all_optimizations = []
    
    # التحليلات
    analyzers = [
        analyze_database,
        analyze_cache,
        analyze_static_files,
        analyze_templates,
        analyze_middleware,
        analyze_context_processors,
        analyze_admin_panel,
        analyze_queries,
    ]
    
    for analyzer in analyzers:
        try:
            issues, opts = analyzer()
            all_issues.extend(issues)
            all_optimizations.extend(opts)
        except Exception as e:
            print(f"  ⚠️ خطأ في {analyzer.__name__}: {e}")
    
    # الملخص
    print_header("📋 ملخص التحليل")
    
    print(f"\n❌ المشاكل المكتشفة ({len(all_issues)}):")
    for issue in all_issues:
        print(f"  {issue}")
    
    print(f"\n💡 التحسينات المقترحة ({len(all_optimizations)}):")
    for opt in list(set(all_optimizations)):
        print(f"  {opt}")
    
    # توليد خطة التحسين
    generate_optimization_script()
    
    # حفظ التقرير
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'issues_count': len(all_issues),
        'issues': all_issues,
        'optimizations': list(set(all_optimizations)),
    }
    
    report_path = Path(__file__).parent / 'performance_analysis_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم حفظ التقرير في: {report_path}")


if __name__ == '__main__':
    main()
