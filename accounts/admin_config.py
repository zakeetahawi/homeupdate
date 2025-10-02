"""
إعدادات إضافية لتحسين تنظيم لوحة إدارة Django
"""

from django.contrib import admin
from django.utils.html import format_html


class UserActivityAdminConfig:
    """إعدادات تخصيص لوحة إدارة نشاط المستخدمين"""

    @staticmethod
    def customize_admin_site():
        """تخصيص موقع الإدارة الرئيسي"""
        # تخصيص العناوين
        admin.site.site_header = "📊 نظام إدارة الخواجة - لوحة التحكم"
        admin.site.site_title = "إدارة النظام"
        admin.site.index_title = "مرحباً بك في لوحة التحكم"

        # إضافة CSS مخصص
        admin.site.enable_nav_sidebar = True

    @staticmethod
    def get_admin_css():
        """CSS مخصص للوحة الإدارة"""
        return """
        <style>
        /* تحسين عرض نماذج نشاط المستخدمين */
        .model-useractivitylog .addlink,
        .model-usersession .addlink,
        .model-onlineuser .addlink,
        .model-userloginhistory .addlink {
            display: none !important;
        }
        
        /* تجميع نماذج النشاط */
        .app-accounts .model-onlineuser,
        .app-accounts .model-useractivitylog,
        .app-accounts .model-usersession,
        .app-accounts .model-userloginhistory {
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            margin: 2px 0;
            padding: 5px;
            border-radius: 4px;
        }
        
        /* أيقونات مخصصة */
        .model-onlineuser .addlink::before {
            content: "🟢 ";
        }
        
        .model-useractivitylog .addlink::before {
            content: "📋 ";
        }
        
        .model-usersession .addlink::before {
            content: "💻 ";
        }
        
        .model-userloginhistory .addlink::before {
            content: "🔐 ";
        }
        
        /* تحسين عرض الجداول */
        .admin-object-tools {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 20px;
        }
        
        .admin-object-tools a {
            color: white !important;
            text-decoration: none;
        }
        
        .admin-object-tools a:hover {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            padding: 5px 10px;
        }
        
        /* تحسين عرض الفلاتر */
        #changelist-filter {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
        }
        
        #changelist-filter h2 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px;
            border-radius: 6px;
            margin: -15px -15px 15px -15px;
        }
        
        /* تحسين عرض النتائج */
        .results {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .results th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
        }
        
        .results tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .results tr:hover {
            background: #e3f2fd;
        }
        
        /* تحسين عرض التفاصيل */
        .form-row {
            background: white;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .form-row label {
            font-weight: bold;
            color: #333;
        }
        
        /* تحسين عرض الأزرار */
        .default, .deletelink, .addlink {
            border-radius: 6px;
            padding: 8px 16px;
            text-decoration: none;
            display: inline-block;
            margin: 2px;
            transition: all 0.3s ease;
        }
        
        .default:hover, .deletelink:hover, .addlink:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        /* تحسين عرض الرسائل */
        .messagelist {
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .messagelist .success {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            color: white;
        }
        
        .messagelist .error {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            color: white;
        }
        
        .messagelist .warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        </style>
        """


class UserActivityAdminMixin:
    """Mixin لتحسين عرض نماذج نشاط المستخدمين"""

    def changelist_view(self, request, extra_context=None):
        """تخصيص عرض قائمة التغييرات"""
        extra_context = extra_context or {}
        extra_context["custom_css"] = UserActivityAdminConfig.get_admin_css()
        extra_context["title"] = f"📊 {self.model._meta.verbose_name_plural}"
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """تخصيص عرض التفاصيل"""
        extra_context = extra_context or {}
        extra_context["custom_css"] = UserActivityAdminConfig.get_admin_css()
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        """تخصيص عرض الإضافة"""
        extra_context = extra_context or {}
        extra_context["custom_css"] = UserActivityAdminConfig.get_admin_css()
        return super().add_view(request, form_url, extra_context)


def get_activity_summary_html():
    """إنشاء ملخص HTML لنشاط المستخدمين"""
    try:
        from django.utils import timezone

        from user_activity.models import OnlineUser, UserActivityLog, UserLoginHistory

        today = timezone.now().date()

        # إحصائيات سريعة
        online_count = OnlineUser.get_online_users().count()
        today_logins = UserLoginHistory.objects.filter(login_time__date=today).count()
        today_activities = UserActivityLog.objects.filter(timestamp__date=today).count()

        return format_html(
            """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="margin: 0 0 15px 0;">📊 ملخص نشاط المستخدمين</h3>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem; font-weight: bold;">{}</div>
                        <div style="font-size: 0.9rem;">متصلون الآن</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2rem; font-weight: bold;">{}</div>
                        <div style="font-size: 0.9rem;">تسجيلات دخول اليوم</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2rem; font-weight: bold;">{}</div>
                        <div style="font-size: 0.9rem;">أنشطة اليوم</div>
                    </div>
                </div>
                <div style="margin-top: 15px; text-align: center;">
                    <a href="/accounts/activity/dashboard/" 
                       style="background: rgba(255,255,255,0.2); color: white; 
                              padding: 8px 16px; border-radius: 6px; text-decoration: none;">
                        🔗 عرض لوحة التحكم الكاملة
                    </a>
                </div>
            </div>
            """,
            online_count,
            today_logins,
            today_activities,
        )
    except Exception:
        return format_html(
            """
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>📊 نشاط المستخدمين</h3>
                <p>جاري تحميل الإحصائيات...</p>
            </div>
            """
        )


# تطبيق التخصيصات عند استيراد الملف
UserActivityAdminConfig.customize_admin_site()
