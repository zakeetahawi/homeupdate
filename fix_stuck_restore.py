#!/usr/bin/env python3
"""
إصلاح عمليات الاستعادة المعلقة
============================

هذا السكريپت يقوم بـ:
1. تشخيص العمليات المعلقة
2. تنظيف الجلسات القديمة
3. إعادة تشغيل العمليات المتوقفة
4. إصلاح مشاكل قاعدة البيانات
"""

import os
import sys
import django
import json
import threading
import time
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.utils import timezone
from django.db import transaction, connection
from django.core.cache import cache
from odoo_db_manager.models import RestoreProgress, Database
from odoo_db_manager.views import _restore_json_simple_with_progress

class RestoreRecoveryManager:
    """مدير استعادة العمليات المعلقة"""

    def __init__(self):
        self.stuck_threshold_minutes = 10  # العتبة للعمليات المعلقة (دقائق)
        self.cleanup_threshold_hours = 24   # العتبة لتنظيف الجلسات القديمة (ساعات)

    def diagnose_stuck_processes(self):
        """تشخيص العمليات المعلقة"""
        print("🔍 تشخيص العمليات المعلقة...")

        # العمليات التي لم تتحدث لفترة طويلة
        threshold_time = timezone.now() - timedelta(minutes=self.stuck_threshold_minutes)

        stuck_sessions = RestoreProgress.objects.filter(
            status__in=['processing', 'starting'],
            updated_at__lt=threshold_time
        ).order_by('-updated_at')

        if not stuck_sessions.exists():
            print("  ✅ لا توجد عمليات معلقة")
            return []

        print(f"  ⚠️ تم العثور على {stuck_sessions.count()} عملية معلقة:")

        stuck_info = []
        for session in stuck_sessions:
            age_minutes = (timezone.now() - session.updated_at).total_seconds() / 60
            info = {
                'session': session,
                'age_minutes': age_minutes,
                'progress': session.progress_percentage,
                'processed': session.processed_items,
                'total': session.total_items,
                'errors': session.error_count
            }
            stuck_info.append(info)

            print(f"    📋 Session: {session.session_id}")
            print(f"       العمر: {age_minutes:.1f} دقيقة")
            print(f"       التقدم: {session.progress_percentage}%")
            print(f"       معالج: {session.processed_items}/{session.total_items}")
            print(f"       أخطاء: {session.error_count}")
            print(f"       الخطوة: {session.current_step}")
            print()

        return stuck_info

    def cleanup_old_sessions(self):
        """تنظيف الجلسات القديمة"""
        print("🧹 تنظيف الجلسات القديمة...")

        # الجلسات الأقدم من العتبة المحددة
        threshold_time = timezone.now() - timedelta(hours=self.cleanup_threshold_hours)

        old_sessions = RestoreProgress.objects.filter(
            created_at__lt=threshold_time
        )

        if not old_sessions.exists():
            print("  ✅ لا توجد جلسات قديمة للتنظيف")
            return 0

        # عرض تفاصيل الجلسات القديمة
        print(f"  📊 تم العثور على {old_sessions.count()} جلسة قديمة:")
        for session in old_sessions[:5]:  # عرض أول 5 فقط
            age_hours = (timezone.now() - session.created_at).total_seconds() / 3600
            print(f"    - {session.session_id}: {session.status} (عمر: {age_hours:.1f} ساعة)")

        if old_sessions.count() > 5:
            print(f"    ... و {old_sessions.count() - 5} جلسة أخرى")

        # حذف الجلسات القديمة
        deleted_count = old_sessions.delete()[0]
        print(f"  ✅ تم حذف {deleted_count} جلسة قديمة")

        return deleted_count

    def force_complete_stuck_session(self, session_info):
        """إجبار إكمال جلسة معلقة"""
        session = session_info['session']
        print(f"🔧 محاولة إصلاح الجلسة: {session.session_id}")

        try:
            # تحديث الحالة إلى فشل مع رسالة واضحة
            session.status = 'failed'
            session.progress_percentage = 100
            session.current_step = 'تم إيقاف العملية بسبب التعليق'
            session.error_message = f'العملية علقت لمدة {session_info["age_minutes"]:.1f} دقيقة وتم إيقافها تلقائياً'
            session.save()

            # تنظيف الكاش المرتبط
            cache_keys = [
                f'temp_token_{session.session_id}',
                f'session_token_{session.session_id}',
                f'restore_progress_backup_{session.session_id}'
            ]

            for key in cache_keys:
                try:
                    cache.delete(key)
                except:
                    pass

            print(f"  ✅ تم إصلاح الجلسة: {session.session_id}")
            return True

        except Exception as e:
            print(f"  ❌ فشل في إصلاح الجلسة: {str(e)}")
            return False

    def restart_restore_process(self, session_info, backup_file_path=None):
        """إعادة تشغيل عملية الاستعادة"""
        if not backup_file_path:
            print("  ⚠️ مسار ملف النسخة الاحتياطية غير محدد")
            return False

        if not os.path.exists(backup_file_path):
            print(f"  ❌ ملف النسخة الاحتياطية غير موجود: {backup_file_path}")
            return False

        session = session_info['session']
        print(f"🔄 إعادة تشغيل عملية الاستعادة للجلسة: {session.session_id}")

        try:
            # إنشاء جلسة جديدة
            new_session_id = f'restore_recovery_{int(time.time() * 1000)}'

            # إنشاء progress جديد
            new_progress = RestoreProgress.objects.create(
                session_id=new_session_id,
                user=session.user,
                database=session.database,
                status='starting',
                progress_percentage=0,
                current_step='إعادة تشغيل العملية...',
                total_items=0,
                processed_items=0,
                success_count=0,
                error_count=0
            )

            print(f"  ✅ تم إنشاء جلسة جديدة: {new_session_id}")

            # دالة تحديث التقدم
            def update_progress(status=None, progress_percentage=None, current_step=None,
                              total_items=None, processed_items=None, success_count=None,
                              error_count=None, error_message=None, result_data=None):
                try:
                    progress = RestoreProgress.objects.get(session_id=new_session_id)

                    if status is not None:
                        progress.status = status
                    if progress_percentage is not None:
                        progress.progress_percentage = progress_percentage
                    if current_step is not None:
                        progress.current_step = current_step
                    if total_items is not None:
                        progress.total_items = total_items
                    if processed_items is not None:
                        progress.processed_items = processed_items
                    if success_count is not None:
                        progress.success_count = success_count
                    if error_count is not None:
                        progress.error_count = error_count
                    if error_message is not None:
                        progress.error_message = error_message
                    if result_data is not None:
                        progress.result_data = result_data

                    progress.save()
                    print(f"    📊 تقدم: {progress.progress_percentage}% - {progress.current_step}")

                except Exception as e:
                    print(f"    ⚠️ خطأ في تحديث التقدم: {str(e)}")

            # تشغيل الاستعادة في thread منفصل
            def run_restore():
                try:
                    print(f"  🚀 بدء عملية الاستعادة الجديدة...")

                    result = _restore_json_simple_with_progress(
                        backup_file_path,
                        clear_existing=True,  # حذف البيانات القديمة
                        progress_callback=update_progress,
                        session_id=new_session_id
                    )

                    if result:
                        update_progress(
                            status='completed',
                            progress_percentage=100,
                            current_step='اكتملت العملية بنجاح',
                            result_data=result
                        )
                        print(f"  ✅ اكتملت عملية الاستعادة بنجاح")
                    else:
                        update_progress(
                            status='failed',
                            current_step='فشلت العملية',
                            error_message='لم يتم إرجاع نتيجة من عملية الاستعادة'
                        )
                        print(f"  ❌ فشلت عملية الاستعادة")

                except Exception as e:
                    error_msg = str(e)
                    print(f"  ❌ خطأ في عملية الاستعادة: {error_msg}")
                    update_progress(
                        status='failed',
                        current_step='فشلت العملية بسبب خطأ',
                        error_message=error_msg
                    )

            # بدء Thread
            restore_thread = threading.Thread(target=run_restore, daemon=True)
            restore_thread.start()

            print(f"  ✅ تم بدء عملية الاستعادة في الخلفية")
            print(f"  📋 معرف الجلسة الجديدة: {new_session_id}")

            return new_session_id

        except Exception as e:
            print(f"  ❌ فشل في إعادة تشغيل العملية: {str(e)}")
            return False

    def check_database_health(self):
        """فحص صحة قاعدة البيانات"""
        print("🗄️ فحص صحة قاعدة البيانات...")

        try:
            # فحص الاتصال
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            print("  ✅ اتصال قاعدة البيانات يعمل بشكل صحيح")

            # فحص الجداول المهمة
            important_tables = [
                'odoo_db_manager_restoreprogress',
                'customers_customer',
                'orders_order',
                'manufacturing_manufacturingorder'
            ]

            for table in important_tables:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                    print(f"  ✅ {table}: {count} سجل")
                except Exception as e:
                    print(f"  ⚠️ {table}: خطأ - {str(e)}")

            return True

        except Exception as e:
            print(f"  ❌ مشكلة في قاعدة البيانات: {str(e)}")
            return False

    def interactive_recovery(self):
        """وضع الاستعادة التفاعلي"""
        print("\n" + "="*60)
        print("🛠️ وضع الاستعادة التفاعلي")
        print("="*60)

        # تشخيص العمليات المعلقة
        stuck_sessions = self.diagnose_stuck_processes()

        if not stuck_sessions:
            print("\n✅ لا توجد عمليات معلقة تحتاج إصلاح")
            return

        print(f"\n📋 تم العثور على {len(stuck_sessions)} عملية معلقة")
        print("\nاختر الإجراء:")
        print("1. إصلاح جميع العمليات المعلقة (وضع الفشل)")
        print("2. إعادة تشغيل عملية محددة")
        print("3. تنظيف الجلسات القديمة فقط")
        print("4. عرض تفاصيل أكثر")
        print("5. إلغاء")

        try:
            choice = input("\nاختر رقم الخيار (1-5): ").strip()

            if choice == "1":
                print("\n🔧 إصلاح جميع العمليات المعلقة...")
                fixed_count = 0
                for session_info in stuck_sessions:
                    if self.force_complete_stuck_session(session_info):
                        fixed_count += 1
                print(f"\n✅ تم إصلاح {fixed_count} من {len(stuck_sessions)} عملية")

            elif choice == "2":
                print("\n📋 العمليات المعلقة:")
                for i, session_info in enumerate(stuck_sessions, 1):
                    session = session_info['session']
                    print(f"{i}. {session.session_id} - {session_info['progress']}%")

                try:
                    selection = int(input(f"\nاختر رقم العملية (1-{len(stuck_sessions)}): ")) - 1
                    if 0 <= selection < len(stuck_sessions):
                        session_info = stuck_sessions[selection]

                        # طلب مسار ملف النسخة الاحتياطية
                        backup_path = input("أدخل مسار ملف النسخة الاحتياطية (أو اتركه فارغاً للإصلاح فقط): ").strip()

                        if backup_path:
                            new_session = self.restart_restore_process(session_info, backup_path)
                            if new_session:
                                print(f"\n✅ تم بدء عملية جديدة: {new_session}")
                        else:
                            self.force_complete_stuck_session(session_info)
                    else:
                        print("❌ اختيار غير صحيح")
                except ValueError:
                    print("❌ يرجى إدخال رقم صحيح")

            elif choice == "3":
                deleted_count = self.cleanup_old_sessions()
                print(f"\n✅ تم تنظيف {deleted_count} جلسة قديمة")

            elif choice == "4":
                print("\n📊 تفاصيل العمليات المعلقة:")
                for session_info in stuck_sessions:
                    session = session_info['session']
                    print(f"\n🔍 Session: {session.session_id}")
                    print(f"   المستخدم: {session.user.username if session.user else 'غير محدد'}")
                    print(f"   قاعدة البيانات: {session.database.name if session.database else 'غير محدد'}")
                    print(f"   بدأت في: {session.created_at}")
                    print(f"   آخر تحديث: {session.updated_at}")
                    print(f"   رسالة الخطأ: {session.error_message or 'لا توجد'}")

            elif choice == "5":
                print("تم الإلغاء")
                return

            else:
                print("❌ اختيار غير صحيح")

        except KeyboardInterrupt:
            print("\n⏹️ تم إيقاف العملية بواسطة المستخدم")

def main():
    """الدالة الرئيسية"""
    print("🚀 إصلاح عمليات الاستعادة المعلقة")
    print(f"📅 التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # إنشاء مدير الاستعادة
    recovery_manager = RestoreRecoveryManager()

    # فحص صحة قاعدة البيانات أولاً
    if not recovery_manager.check_database_health():
        print("\n❌ مشكلة في قاعدة البيانات. يرجى إصلاحها أولاً")
        return False

    # تشغيل الوضع التفاعلي
    recovery_manager.interactive_recovery()

    print("\n✅ انتهت عملية الإصلاح")
    return True

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف السكريپت بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ عام: {str(e)}")
        sys.exit(1)
