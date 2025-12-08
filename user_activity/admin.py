"""
إدارة نماذج نشاط المستخدمين
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import UserSession, UserActivityLog, OnlineUser, UserLoginHistory


@admin.register(OnlineUser)
class OnlineUserAdmin(admin.ModelAdmin):
    """إدارة المستخدمين المتصلين"""
    list_display = [
        'user', 'last_seen', 'current_page_title', 'online_duration_display',
        'pages_visited', 'actions_performed', 'ip_address'
    ]
    list_filter = ['last_seen']
    search_fields = ['user__username', 'user__email', 'current_page', 'ip_address']
    readonly_fields = [
        'user', 'last_seen', 'current_page', 'current_page_title',
        'ip_address', 'session_key', 'device_info', 'pages_visited',
        'actions_performed', 'login_time', 'online_duration_display'
    ]
    ordering = ['-last_seen']

    def online_duration_display(self, obj):
        """عرض مدة الاتصال"""
        return obj.online_duration_formatted

    online_duration_display.short_description = 'مدة الاتصال'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """إدارة سجلات نشاط المستخدمين"""
    list_display = [
        'user', 'action_type_display', 'entity_type', 'description_short',
        'timestamp', 'success', 'ip_address'
    ]
    list_filter = [
        'action_type', 'entity_type', 'success', 'timestamp',
        ('user', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'user__username', 'user__email', 'description', 'url_path', 'ip_address'
    ]
    readonly_fields = [
        'user', 'session', 'action_type', 'entity_type', 'entity_id',
        'entity_name', 'description', 'url_path', 'http_method',
        'ip_address', 'user_agent', 'extra_data', 'timestamp',
        'success', 'error_message'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    list_per_page = 50
    actions = ['bulk_delete_selected', 'delete_old_logs_30_days', 'delete_old_logs_60_days', 'delete_old_logs_90_days']

    def action_type_display(self, obj):
        """عرض نوع العملية مع الأيقونة"""
        return format_html(
            '<span title="{}">{} {}</span>',
            obj.get_action_type_display(),
            obj.get_icon(),
            obj.get_action_type_display()
        )

    action_type_display.short_description = 'نوع العملية'

    def description_short(self, obj):
        """عرض وصف مختصر"""
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description

    description_short.short_description = 'الوصف'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def bulk_delete_selected(self, request, queryset):
        """حذف مجمّع سريع بدون تنفيذ signals"""
        count = queryset.count()
        
        if count > 0:
            # الحذف المباشر من قاعدة البيانات (أسرع بكثير)
            queryset._raw_delete(queryset.db)
            
            self.message_user(
                request,
                f'تم حذف {count} سجل بنجاح بطريقة سريعة!',
                level='success'
            )
        else:
            self.message_user(request, 'لم يتم تحديد أي سجلات للحذف', level='warning')
    
    bulk_delete_selected.short_description = '🗑️ حذف سريع للسجلات المحددة'

    def delete_old_logs_30_days(self, request, queryset):
        """حذف السجلات الأقدم من 30 يوم"""
        cutoff_date = timezone.now() - timedelta(days=30)
        old_logs = UserActivityLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count > 0:
            old_logs._raw_delete(old_logs.db)
            self.message_user(
                request,
                f'تم حذف {count} سجل أقدم من 30 يوم',
                level='success'
            )
        else:
            self.message_user(request, 'لا توجد سجلات أقدم من 30 يوم', level='info')
    
    delete_old_logs_30_days.short_description = '🗑️ حذف سجلات أقدم من 30 يوم'

    def delete_old_logs_60_days(self, request, queryset):
        """حذف السجلات الأقدم من 60 يوم"""
        cutoff_date = timezone.now() - timedelta(days=60)
        old_logs = UserActivityLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count > 0:
            old_logs._raw_delete(old_logs.db)
            self.message_user(
                request,
                f'تم حذف {count} سجل أقدم من 60 يوم',
                level='success'
            )
        else:
            self.message_user(request, 'لا توجد سجلات أقدم من 60 يوم', level='info')
    
    delete_old_logs_60_days.short_description = '🗑️ حذف سجلات أقدم من 60 يوم'

    def delete_old_logs_90_days(self, request, queryset):
        """حذف السجلات الأقدم من 90 يوم"""
        cutoff_date = timezone.now() - timedelta(days=90)
        old_logs = UserActivityLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count > 0:
            old_logs._raw_delete(old_logs.db)
            self.message_user(
                request,
                f'تم حذف {count} سجل أقدم من 90 يوم',
                level='success'
            )
        else:
            self.message_user(request, 'لا توجد سجلات أقدم من 90 يوم', level='info')
    
    delete_old_logs_90_days.short_description = '🗑️ حذف سجلات أقدم من 90 يوم'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """إدارة جلسات المستخدمين"""
    list_display = [
        'user', 'ip_address', 'device_type', 'browser',
        'login_time', 'last_activity', 'is_active', 'duration_display'
    ]
    list_filter = [
        'is_active', 'device_type', 'login_time', 'last_activity'
    ]
    search_fields = ['user__username', 'user__email', 'ip_address', 'browser']
    readonly_fields = [
        'session_key', 'login_time', 'last_activity', 'duration_display'
    ]
    date_hierarchy = 'login_time'
    ordering = ['-last_activity']
    actions = [
        'bulk_delete_selected', 
        'delete_inactive_sessions',
        'delete_old_sessions_1day',
        'delete_old_sessions_7days',
        'delete_old_sessions_30days',
        'delete_all_sessions_keep_superusers',
    ]
    list_per_page = 50  # تقليل عدد الصفوف لتسريع التحميل
    
    def changelist_view(self, request, extra_context=None):
        """إضافة رابط للحذف السريع"""
        extra_context = extra_context or {}
        extra_context['quick_cleanup_url'] = 'quick-cleanup/'
        return super().changelist_view(request, extra_context)
    
    def get_urls(self):
        """إضافة URL للحذف السريع"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('quick-cleanup/', self.admin_site.admin_view(self.quick_cleanup_view), name='usersession_quick_cleanup'),
        ]
        return custom_urls + urls
    
    def quick_cleanup_view(self, request):
        """صفحة الحذف السريع بدون تحميل القائمة"""
        from django.shortcuts import render
        from django.db import connection
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from django.utils import timezone
        from datetime import timedelta
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            with connection.cursor() as cursor:
                if action == 'inactive':
                    # حذف الجلسات غير النشطة
                    cursor.execute("DELETE FROM user_activity_useractivitylog WHERE session_id IN (SELECT id FROM user_activity_usersession WHERE is_active = false)")
                    cursor.execute("DELETE FROM user_activity_usersession WHERE is_active = false")
                    count = cursor.rowcount
                    # حذف جلسات Django غير النشطة
                    cursor.execute("DELETE FROM django_session WHERE expire_date < NOW()")
                    django_count = cursor.rowcount
                    messages.success(request, f'✅ تم حذف {count} جلسة تتبع + {django_count} جلسة Django منتهية')
                    
                elif action == '1day':
                    cutoff = timezone.now() - timedelta(days=1)
                    # جمع session_keys المراد حذفها
                    cursor.execute("SELECT session_key FROM user_activity_usersession WHERE last_activity < %s", [cutoff])
                    session_keys = [row[0] for row in cursor.fetchall()]
                    
                    # حذف من user_activity
                    cursor.execute("DELETE FROM user_activity_useractivitylog WHERE session_id IN (SELECT id FROM user_activity_usersession WHERE last_activity < %s)", [cutoff])
                    cursor.execute("DELETE FROM user_activity_usersession WHERE last_activity < %s", [cutoff])
                    count = cursor.rowcount
                    
                    # حذف من django_session
                    if session_keys:
                        placeholders = ','.join(['%s'] * len(session_keys))
                        cursor.execute(f"DELETE FROM django_session WHERE session_key IN ({placeholders})", session_keys)
                        django_count = cursor.rowcount
                    else:
                        django_count = 0
                    
                    messages.success(request, f'✅ تم حذف {count} جلسة تتبع + {django_count} جلسة Django (أقدم من يوم). تم إخراج المستخدمين!')
                    
                elif action == '7days':
                    cutoff = timezone.now() - timedelta(days=7)
                    # جمع session_keys
                    cursor.execute("SELECT session_key FROM user_activity_usersession WHERE last_activity < %s", [cutoff])
                    session_keys = [row[0] for row in cursor.fetchall()]
                    
                    cursor.execute("DELETE FROM user_activity_useractivitylog WHERE session_id IN (SELECT id FROM user_activity_usersession WHERE last_activity < %s)", [cutoff])
                    cursor.execute("DELETE FROM user_activity_usersession WHERE last_activity < %s", [cutoff])
                    count = cursor.rowcount
                    
                    if session_keys:
                        placeholders = ','.join(['%s'] * len(session_keys))
                        cursor.execute(f"DELETE FROM django_session WHERE session_key IN ({placeholders})", session_keys)
                        django_count = cursor.rowcount
                    else:
                        django_count = 0
                    
                    messages.success(request, f'✅ تم حذف {count} جلسة تتبع + {django_count} جلسة Django (أقدم من أسبوع). تم إخراج المستخدمين!')
                    
                elif action == '30days':
                    cutoff = timezone.now() - timedelta(days=30)
                    cursor.execute("SELECT session_key FROM user_activity_usersession WHERE last_activity < %s", [cutoff])
                    session_keys = [row[0] for row in cursor.fetchall()]
                    
                    cursor.execute("DELETE FROM user_activity_useractivitylog WHERE session_id IN (SELECT id FROM user_activity_usersession WHERE last_activity < %s)", [cutoff])
                    cursor.execute("DELETE FROM user_activity_usersession WHERE last_activity < %s", [cutoff])
                    count = cursor.rowcount
                    
                    if session_keys:
                        placeholders = ','.join(['%s'] * len(session_keys))
                        cursor.execute(f"DELETE FROM django_session WHERE session_key IN ({placeholders})", session_keys)
                        django_count = cursor.rowcount
                    else:
                        django_count = 0
                    
                    messages.success(request, f'✅ تم حذف {count} جلسة تتبع + {django_count} جلسة Django (أقدم من شهر). تم إخراج المستخدمين!')
                    
                elif action == 'all_except_super':
                    # جمع session_keys للمستخدمين العاديين
                    cursor.execute("SELECT session_key FROM user_activity_usersession WHERE user_id IN (SELECT id FROM accounts_user WHERE is_superuser = false)")
                    session_keys = [row[0] for row in cursor.fetchall()]
                    
                    cursor.execute("DELETE FROM user_activity_useractivitylog WHERE session_id IN (SELECT id FROM user_activity_usersession WHERE user_id IN (SELECT id FROM accounts_user WHERE is_superuser = false))")
                    cursor.execute("DELETE FROM user_activity_usersession WHERE user_id IN (SELECT id FROM accounts_user WHERE is_superuser = false)")
                    count = cursor.rowcount
                    
                    if session_keys:
                        placeholders = ','.join(['%s'] * len(session_keys))
                        cursor.execute(f"DELETE FROM django_session WHERE session_key IN ({placeholders})", session_keys)
                        django_count = cursor.rowcount
                    else:
                        django_count = 0
                    
                    messages.warning(request, f'🔴 تم حذف {count} جلسة تتبع + {django_count} جلسة Django. تم إخراج جميع المستخدمين (ماعدا السوبر يوزر)!')
                    
                elif action == 'all_data':
                    # حذف كل شيء
                    cursor.execute("SELECT session_key FROM user_activity_usersession")
                    session_keys = [row[0] for row in cursor.fetchall()]
                    
                    cursor.execute("DELETE FROM user_activity_useractivitylog WHERE session_id IS NOT NULL")
                    cursor.execute("DELETE FROM user_activity_usersession")
                    count = cursor.rowcount
                    
                    if session_keys:
                        placeholders = ','.join(['%s'] * len(session_keys))
                        cursor.execute(f"DELETE FROM django_session WHERE session_key IN ({placeholders})", session_keys)
                        django_count = cursor.rowcount
                    else:
                        django_count = 0
                    
                    messages.error(request, f'🔴🔴 تم حذف {count} جلسة تتبع + {django_count} جلسة Django. تم إخراج الجميع!')
            
            return HttpResponseRedirect(request.path)
        
        # حساب الإحصائيات
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM user_activity_usersession")
            total_sessions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_activity_usersession WHERE is_active = false")
            inactive_sessions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_activity_usersession WHERE last_activity < %s", [timezone.now() - timedelta(days=1)])
            old_1day = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_activity_usersession WHERE last_activity < %s", [timezone.now() - timedelta(days=7)])
            old_7days = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_activity_usersession WHERE last_activity < %s", [timezone.now() - timedelta(days=30)])
            old_30days = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_activity_useractivitylog")
            total_logs = cursor.fetchone()[0]
        
        context = {
            'title': 'حذف الجلسات السريع',
            'total_sessions': total_sessions,
            'inactive_sessions': inactive_sessions,
            'old_1day': old_1day,
            'old_7days': old_7days,
            'old_30days': old_30days,
            'total_logs': total_logs,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        
        return render(request, 'admin/user_activity/quick_cleanup.html', context)

    def duration_display(self, obj):
        """عرض مدة الجلسة"""
        duration = obj.duration
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if duration.days > 0:
            return f"{duration.days} يوم و {hours} ساعة"
        elif hours > 0:
            return f"{hours} ساعة و {minutes} دقيقة"
        else:
            return f"{minutes} دقيقة"

    duration_display.short_description = 'مدة الجلسة'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def bulk_delete_selected(self, request, queryset):
        """حذف مجمّع سريع"""
        count = queryset.count()
        if count > 0:
            queryset._raw_delete(queryset.db)
            self.message_user(request, f'تم حذف {count} جلسة بنجاح', level='success')
        else:
            self.message_user(request, 'لم يتم تحديد أي جلسات للحذف', level='warning')
    
    bulk_delete_selected.short_description = '🗑️ حذف سريع للجلسات المحددة'

    def delete_inactive_sessions(self, request, queryset):
        """حذف الجلسات غير النشطة"""
        from django.db import connection
        with connection.cursor() as cursor:
            # حذف السجلات المرتبطة أولاً
            cursor.execute("""
                DELETE FROM user_activity_useractivitylog 
                WHERE session_id IN (
                    SELECT id FROM user_activity_usersession WHERE is_active = false
                )
            """)
            logs_count = cursor.rowcount
            
            # حذف الجلسات
            cursor.execute("DELETE FROM user_activity_usersession WHERE is_active = false")
            sessions_count = cursor.rowcount
            
        self.message_user(
            request, 
            f'✅ تم حذف {sessions_count} جلسة غير نشطة و {logs_count} سجل نشاط', 
            level='success'
        )
    
    delete_inactive_sessions.short_description = '🗑️ حذف الجلسات غير النشطة (سريع)'
    
    def delete_old_sessions_1day(self, request, queryset):
        """حذف الجلسات الأقدم من يوم"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db import connection
        
        cutoff = timezone.now() - timedelta(days=1)
        with connection.cursor() as cursor:
            # حذف السجلات المرتبطة أولاً
            cursor.execute("""
                DELETE FROM user_activity_useractivitylog 
                WHERE session_id IN (
                    SELECT id FROM user_activity_usersession WHERE last_activity < %s
                )
            """, [cutoff])
            logs_count = cursor.rowcount
            
            # حذف الجلسات
            cursor.execute(
                "DELETE FROM user_activity_usersession WHERE last_activity < %s",
                [cutoff]
            )
            sessions_count = cursor.rowcount
            
        self.message_user(
            request, 
            f'✅ تم حذف {sessions_count} جلسة و {logs_count} سجل (أقدم من يوم واحد)', 
            level='success'
        )
    
    delete_old_sessions_1day.short_description = '⏰ حذف الجلسات (أقدم من يوم)'
    
    def delete_old_sessions_7days(self, request, queryset):
        """حذف الجلسات الأقدم من 7 أيام"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db import connection
        
        cutoff = timezone.now() - timedelta(days=7)
        with connection.cursor() as cursor:
            # حذف السجلات المرتبطة أولاً
            cursor.execute("""
                DELETE FROM user_activity_useractivitylog 
                WHERE session_id IN (
                    SELECT id FROM user_activity_usersession WHERE last_activity < %s
                )
            """, [cutoff])
            logs_count = cursor.rowcount
            
            # حذف الجلسات
            cursor.execute(
                "DELETE FROM user_activity_usersession WHERE last_activity < %s",
                [cutoff]
            )
            sessions_count = cursor.rowcount
            
        self.message_user(
            request, 
            f'✅ تم حذف {sessions_count} جلسة و {logs_count} سجل (أقدم من 7 أيام)', 
            level='success'
        )
    
    delete_old_sessions_7days.short_description = '⏰ حذف الجلسات (أقدم من أسبوع)'
    
    def delete_old_sessions_30days(self, request, queryset):
        """حذف الجلسات الأقدم من 30 يوم"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db import connection
        
        cutoff = timezone.now() - timedelta(days=30)
        with connection.cursor() as cursor:
            # حذف السجلات المرتبطة أولاً
            cursor.execute("""
                DELETE FROM user_activity_useractivitylog 
                WHERE session_id IN (
                    SELECT id FROM user_activity_usersession WHERE last_activity < %s
                )
            """, [cutoff])
            logs_count = cursor.rowcount
            
            # حذف الجلسات
            cursor.execute(
                "DELETE FROM user_activity_usersession WHERE last_activity < %s",
                [cutoff]
            )
            sessions_count = cursor.rowcount
            
        self.message_user(
            request, 
            f'✅ تم حذف {sessions_count} جلسة و {logs_count} سجل (أقدم من 30 يوم)', 
            level='success'
        )
    
    delete_old_sessions_30days.short_description = '⏰ حذف الجلسات (أقدم من شهر)'
    
    def delete_all_sessions_keep_superusers(self, request, queryset):
        """حذف جميع الجلسات ماعدا السوبر يوزر"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            # حذف السجلات المرتبطة أولاً
            cursor.execute("""
                DELETE FROM user_activity_useractivitylog 
                WHERE session_id IN (
                    SELECT id FROM user_activity_usersession 
                    WHERE user_id IN (
                        SELECT id FROM accounts_user WHERE is_superuser = false
                    )
                )
            """)
            logs_count = cursor.rowcount
            
            # حذف جلسات المستخدمين الذين ليسوا superuser
            cursor.execute("""
                DELETE FROM user_activity_usersession 
                WHERE user_id IN (
                    SELECT id FROM accounts_user WHERE is_superuser = false
                )
            """)
            sessions_count = cursor.rowcount
            
        self.message_user(
            request, 
            f'🔴 تم حذف {sessions_count} جلسة و {logs_count} سجل. تم الاحتفاظ بجلسات السوبر يوزر فقط.', 
            level='warning'
        )
    
    delete_all_sessions_keep_superusers.short_description = '🔴 حذف الجميع (ماعدا السوبر يوزر)'


@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    """إدارة سجلات تسجيل الدخول"""
    list_display = [
        'user_display', 'login_time', 'logout_time', 'session_duration_display',
        'device_type', 'browser', 'ip_address', 'is_successful_login'
    ]
    list_filter = [
        'is_successful_login', 'device_type', 'logout_reason',
        ('user', admin.RelatedOnlyFieldListFilter),
        'login_time', 'logout_time'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name', 'user__email', 
        'ip_address', 'browser', 'operating_system', 'device_type'
    ]
    readonly_fields = [
        'user', 'login_time', 'logout_time', 'ip_address', 'user_agent',
        'session_key', 'browser', 'operating_system', 'device_type',
        'pages_visited', 'actions_performed', 'is_successful_login',
        'logout_reason', 'session_duration_display'
    ]
    date_hierarchy = 'login_time'
    ordering = ['-login_time']
    list_per_page = 50
    actions = ['bulk_delete_selected', 'delete_old_history_30_days', 'delete_old_history_60_days']

    def user_display(self, obj):
        """عرض اسم المستخدم مع رابط"""
        if obj.user:
            full_name = obj.user.get_full_name() or obj.user.username
            return format_html(
                '<a href="{}" target="_blank">{}</a><br/><small style="color: #666;">{}</small>',
                reverse('admin:accounts_user_change', args=[obj.user.pk]),
                full_name,
                obj.user.username
            )
        return '-'
    user_display.short_description = 'المستخدم'
    user_display.admin_order_field = 'user__username'

    def session_duration_display(self, obj):
        """عرض مدة الجلسة"""
        return obj.session_duration_formatted

    session_duration_display.short_description = 'مدة الجلسة'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def bulk_delete_selected(self, request, queryset):
        """حذف مجمّع سريع"""
        count = queryset.count()
        if count > 0:
            queryset._raw_delete(queryset.db)
            self.message_user(request, f'تم حذف {count} سجل تسجيل دخول', level='success')
        else:
            self.message_user(request, 'لم يتم تحديد أي سجلات للحذف', level='warning')
    
    bulk_delete_selected.short_description = '🗑️ حذف سريع للسجلات المحددة'

    def delete_old_history_30_days(self, request, queryset):
        """حذف سجلات تسجيل الدخول الأقدم من 30 يوم"""
        cutoff_date = timezone.now() - timedelta(days=30)
        old_records = UserLoginHistory.objects.filter(login_time__lt=cutoff_date)
        count = old_records.count()
        if count > 0:
            old_records._raw_delete(old_records.db)
            self.message_user(request, f'تم حذف {count} سجل أقدم من 30 يوم', level='success')
        else:
            self.message_user(request, 'لا توجد سجلات أقدم من 30 يوم', level='info')
    
    delete_old_history_30_days.short_description = '🗑️ حذف سجلات أقدم من 30 يوم'

    def delete_old_history_60_days(self, request, queryset):
        """حذف سجلات تسجيل الدخول الأقدم من 60 يوم"""
        cutoff_date = timezone.now() - timedelta(days=60)
        old_records = UserLoginHistory.objects.filter(login_time__lt=cutoff_date)
        count = old_records.count()
        if count > 0:
            old_records._raw_delete(old_records.db)
            self.message_user(request, f'تم حذف {count} سجل أقدم من 60 يوم', level='success')
        else:
            self.message_user(request, 'لا توجد سجلات أقدم من 60 يوم', level='info')
    
    delete_old_history_60_days.short_description = '🗑️ حذف سجلات أقدم من 60 يوم'
