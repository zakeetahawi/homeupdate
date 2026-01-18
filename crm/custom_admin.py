"""
لوحة تحكم Admin مخصصة مع تجميع منطقي للتطبيقات
"""

from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _


class CustomAdminSite(AdminSite):
    """
    موقع إدارة مخصص مع تجميع منطقي للتطبيقات
    """

    site_header = _("لوحة تحكم النظام المتكامل")
    site_title = _("إدارة الشركة")
    index_title = _("مرحباً بك في لوحة التحكم")

    # تعريف المجموعات المنطقية
    APP_GROUPS = {
        "إدارة العملاء والمبيعات": {
            "apps": ["customers", "orders"],
            "icon": "📊",
            "order": 1,
        },
        "إدارة المخزون والإنتاج": {
            "apps": ["inventory", "cutting", "manufacturing"],
            "icon": "🏭",
            "order": 2,
        },
        "الحسابات والمالية": {
            "apps": ["accounting", "factory_accounting", "reports"],
            "icon": "💼",
            "order": 3,
        },
        "العمليات والخدمات": {
            "apps": ["inspections", "installations", "complaints"],
            "icon": "🔧",
            "order": 4,
        },
        "النظام والإدارة": {
            "apps": [
                "accounts",
                "core",
                "backup_system",
                "notifications",
                "user_activity",
            ],
            "icon": "⚙️",
            "order": 5,
        },
        "التكاملات الخارجية": {
            "apps": ["whatsapp", "odoo_db_manager", "public"],
            "icon": "🔗",
            "order": 6,
        },
    }

    def get_app_list(self, request, app_label=None):
        """
        تخصيص قائمة التطبيقات مع التجميع المنطقي
        """
        # الحصول على القائمة الافتراضية
        app_dict = self._build_app_dict(request, app_label)

        if app_label:
            # إذا كان هناك app_label محدد، استخدم السلوك الافتراضي
            return super().get_app_list(request, app_label)

        # إنشاء قائمة مجمعة
        grouped_apps = {}
        ungrouped_apps = []

        # تجميع التطبيقات
        for app_name, app_data in app_dict.items():
            grouped = False

            # البحث عن المجموعة المناسبة
            for group_name, group_config in self.APP_GROUPS.items():
                if app_name in group_config["apps"]:
                    if group_name not in grouped_apps:
                        grouped_apps[group_name] = {
                            "name": f"{group_config['icon']} {group_name}",
                            "app_label": group_name,
                            "models": [],
                            "order": group_config["order"],
                        }

                    # إضافة النماذج إلى المجموعة
                    grouped_apps[group_name]["models"].extend(app_data["models"])
                    grouped = True
                    break

            # إذا لم يتم تجميع التطبيق، أضفه للقائمة غير المجمعة
            if not grouped:
                ungrouped_apps.append(app_data)

        # ترتيب المجموعات حسب الأولوية
        app_list = sorted(grouped_apps.values(), key=lambda x: x["order"])

        # إضافة التطبيقات غير المجمعة في النهاية
        app_list.extend(ungrouped_apps)

        return app_list

    def index(self, request, extra_context=None):
        """
        إضافة إحصائيات سريعة في الصفحة الرئيسية
        """
        extra_context = extra_context or {}

        try:
            # إحصائيات العملاء والطلبات
            from customers.models import Customer
            from orders.models import Order

            extra_context["total_customers"] = Customer.objects.count()
            extra_context["total_orders"] = Order.objects.count()
            extra_context["pending_orders"] = Order.objects.filter(
                status__in=["pending", "in_progress"]
            ).count()

            # إحصائيات المخزون
            from inventory.models import Product

            extra_context["total_products"] = Product.objects.count()
            extra_context["low_stock_products"] = Product.objects.filter(
                quantity__lt=10
            ).count()

        except Exception as e:
            # في حالة وجود خطأ، لا نريد أن يتعطل Admin
            pass

        return super().index(request, extra_context)


# إنشاء instance من الـ AdminSite المخصص
# استخدام name='admin' للحفاظ على التوافق مع URLs الموجودة
custom_admin_site = CustomAdminSite(name="admin")
