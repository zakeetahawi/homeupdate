"""
إعدادات إضافية للـ Django Admin لضمان عمل ترتيب الأعمدة بشكل مثالي
"""

from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite


# إعدادات عامة لتحسين admin
def enhance_admin_site():
    """تحسين موقع الإدارة العام"""
    AdminSite.site_header = "نظام إدارة الشركة"
    AdminSite.site_title = "لوحة التحكم"
    AdminSite.index_title = "مرحباً بك في لوحة التحكم"


# دالة لإضافة admin_order_field تلقائياً لجميع الدوال المخصصة
def auto_add_sortable_fields(admin_class):
    """إضافة خاصية الترتيب تلقائياً للدوال المخصصة"""
    if hasattr(admin_class, "list_display"):
        for field_name in admin_class.list_display:
            if hasattr(admin_class, field_name):
                method = getattr(admin_class, field_name)
                if callable(method) and not hasattr(method, "admin_order_field"):
                    # محاولة استنتاج الحقل المناسب للترتيب
                    if field_name.endswith("_display"):
                        base_field = field_name.replace("_display", "")
                        if hasattr(admin_class.model, base_field):
                            method.admin_order_field = base_field
                        elif field_name == "customer_name":
                            method.admin_order_field = "customer__name"
                        elif field_name == "status_display":
                            method.admin_order_field = "status"
                        elif field_name == "order_type_display":
                            method.admin_order_field = "order_type"
                    elif hasattr(admin_class.model, field_name):
                        method.admin_order_field = field_name


# قاموس لتخصيص حقول الترتيب لدوال معينة
CUSTOM_ORDER_FIELDS = {
    "manufacturing_code": "id",
    "customer_name": "order__customer__name",
    "contract_number": "contract_number",
    "exit_permit_display": "delivery_permit_number",
    "order_type_display": "order_type",
    "status_display": "status",
    "rejection_reply_status": "has_rejection_reply",
    "delivery_info": "delivery_date",
    "order_number_display": "order_number",
    "payment_status": "payment_verified",
    "customer_type_display": "customer_type",
    "birth_date_display": "birth_date",
    "customer_code_display": "code",
    "debt_amount_formatted": "debt_amount",
    "order_year": "order_date",
}


def apply_custom_order_fields(admin_class):
    """تطبيق حقول الترتيب المخصصة"""
    if hasattr(admin_class, "list_display"):
        for field_name in admin_class.list_display:
            if hasattr(admin_class, field_name) and field_name in CUSTOM_ORDER_FIELDS:
                method = getattr(admin_class, field_name)
                if callable(method):
                    method.admin_order_field = CUSTOM_ORDER_FIELDS[field_name]


# Middleware لتطبيق التحسينات على جميع admin classes
class AdminSortingMiddleware:
    """Middleware لضمان تطبيق تحسينات الترتيب على جميع admin classes"""

    def __init__(self, get_response):
        self.get_response = get_response
        # تطبيق التحسينات عند بدء التشغيل
        self.enhance_all_admins()

    def enhance_all_admins(self):
        """تحسين جميع admin classes المسجلة"""
        from django.contrib import admin

        # الحصول على جميع النماذج المسجلة
        for model, admin_class in admin.site._registry.items():
            # تطبيق التحسينات
            self.enhance_admin_class(admin_class)

    def enhance_admin_class(self, admin_class):
        """تحسين admin class واحد"""
        # إضافة list_per_page إذا لم يكن موجود
        if (
            not hasattr(admin_class, "list_per_page")
            or admin_class.list_per_page == 100
        ):
            admin_class.list_per_page = 50

        # إضافة list_max_show_all
        if not hasattr(admin_class, "list_max_show_all"):
            admin_class.list_max_show_all = 100

        # تطبيق حقول الترتيب المخصصة
        apply_custom_order_fields(admin_class)

        # إضافة get_sortable_by إذا لم يكن موجود
        if not hasattr(admin_class, "get_sortable_by"):

            def get_sortable_by(self, request):
                if hasattr(self, "list_display"):
                    return self.list_display
                return []

            admin_class.get_sortable_by = get_sortable_by

    def __call__(self, request):
        response = self.get_response(request)
        return response


# دالة لإضافة CSS مخصص للـ admin
def add_admin_css():
    """إضافة CSS مخصص لتحسين مظهر جداول الإدارة"""
    css_content = """
    <style>
    /* تحسين مظهر رؤوس الجداول القابلة للترتيب */
    .admin-changelist table thead th.sortable {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
    }
    
    .admin-changelist table thead th.sortable:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .admin-changelist table thead th.sortable a {
        color: white !important;
        text-decoration: none;
        font-weight: bold;
        display: block;
        padding: 10px 8px;
    }
    
    .admin-changelist table thead th.sorted.ascending a::after {
        content: ' ↑';
        color: #ffeb3b;
        font-weight: bold;
        margin-left: 5px;
    }
    
    .admin-changelist table thead th.sorted.descending a::after {
        content: ' ↓';
        color: #ffeb3b;
        font-weight: bold;
        margin-left: 5px;
    }
    
    /* تحسين hover للصفوف */
    .admin-changelist table tbody tr:hover {
        background-color: #f8f9fa !important;
        transform: scale(1.005);
        transition: all 0.2s ease;
    }
    
    /* إضافة tooltip للتوضيح */
    .admin-changelist table thead th.sortable::before {
        content: 'انقر للترتيب';
        position: absolute;
        top: -25px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 11px;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
        white-space: nowrap;
        z-index: 1000;
    }
    
    .admin-changelist table thead th.sortable:hover::before {
        opacity: 1;
    }
    </style>
    """
    return css_content


# إعدادات JavaScript لتحسين تجربة المستخدم
def add_admin_js():
    """إضافة JavaScript لتحسين تجربة الترتيب"""
    js_content = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // إضافة مؤشر تحميل عند النقر على رؤوس الأعمدة
        const sortableHeaders = document.querySelectorAll('th.sortable a');
        
        sortableHeaders.forEach(function(header) {
            header.addEventListener('click', function(e) {
                // إضافة مؤشر تحميل
                const originalText = this.textContent;
                this.innerHTML = originalText + ' <span style="color: #ffeb3b;">⟳</span>';
                
                // إضافة تأثير visual
                this.closest('th').style.backgroundColor = '#5a6fd8';
                
                // تعطيل النقر المتكرر
                this.style.pointerEvents = 'none';
                
                // إعادة تفعيل النقر بعد ثانيتين (في حالة فشل التحميل)
                setTimeout(() => {
                    this.style.pointerEvents = 'auto';
                }, 2000);
            });
        });
        
        // إضافة أيقونات للأعمدة المختلفة
        const icons = {
            'الحالة': '📊',
            'العميل': '👤',
            'التاريخ': '📅',
            'المبلغ': '💰',
            'الرقم': '🔢',
            'النوع': '📋'
        };
        
        sortableHeaders.forEach(function(header) {
            const text = header.textContent.trim();
            for (const [keyword, icon] of Object.entries(icons)) {
                if (text.includes(keyword)) {
                    header.innerHTML = icon + ' ' + header.innerHTML;
                    break;
                }
            }
        });
    });
    </script>
    """
    return js_content
