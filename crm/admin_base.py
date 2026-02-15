"""
ملف الإعدادات الأساسية لجميع admin classes
لتطبيق إعدادات موحدة لجميع جداول لوحة التحكم
"""

from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    """فئة أساسية لجميع ModelAdmin مع إعدادات محسنة"""

    # إعدادات عامة لتحسين الأداء
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_max_show_all = 100  # السماح بعرض حتى 100 صف عند اختيار "عرض الكل"
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء

    # إعدادات عامة للواجهة
    save_on_top = True  # إضافة أزرار الحفظ في الأعلى أيضاً
    preserve_filters = True  # الحفاظ على الفلاتر بعد الحفظ

    # إعدادات البحث والفلترة
    search_help_text = "يمكنك البحث في جميع الحقول المدرجة أعلاه"

    def get_search_fields(self, request):
        """تحسين حقول البحث بناءً على نوع المستخدم"""
        search_fields = getattr(self, "search_fields", [])
        # يمكن إضافة منطق هنا لتخصيص البحث حسب صلاحيات المستخدم
        return search_fields

    def get_list_filter(self, request):
        """تحسين الفلاتر بناءً على نوع المستخدم"""
        list_filter = getattr(self, "list_filter", [])
        # يمكن إضافة منطق هنا لتخصيص الفلاتر حسب صلاحيات المستخدم
        return list_filter

    def get_queryset(self, request):
        """استعلام محسن أساسي"""
        qs = super().get_queryset(request)

        # إضافة select_related للحقول الشائعة
        if hasattr(self.model, "created_by"):
            qs = qs.select_related("created_by")
        if hasattr(self.model, "updated_by"):
            qs = qs.select_related("updated_by")

        return qs

    class Media:
        """إضافة CSS وJS مخصص لجميع admin pages"""

        css = {"all": ("admin/css/custom_admin.css",)}  # ملف CSS مخصص
        js = ("admin/js/custom_admin.js",)  # ملف JS مخصص


class BaseSortableModelAdmin(BaseModelAdmin):
    """فئة أساسية مع إمكانيات ترتيب محسنة"""

    def get_sortable_by(self, request):
        """تمكين الترتيب لجميع الحقول الممكنة"""
        sortable_fields = []

        # إضافة جميع حقول list_display
        for field_name in self.list_display:
            # إذا كان اسم دالة، نحاول الحصول على admin_order_field منها
            if hasattr(self, field_name):
                method = getattr(self, field_name)
                if hasattr(method, "admin_order_field"):
                    sortable_fields.append(field_name)
                else:
                    # محاولة إضافة الحقل مباشرة إذا كان موجود في النموذج
                    try:
                        if hasattr(self.model, field_name):
                            sortable_fields.append(field_name)
                    except Exception:
                        pass
            else:
                # إضافة الحقل مباشرة إذا كان موجود في النموذج
                try:
                    if hasattr(self.model, field_name):
                        sortable_fields.append(field_name)
                except Exception:
                    pass

        # الحصول على جميع حقول النموذج
        for field in self.model._meta.fields:
            if not field.many_to_many and not field.one_to_many:
                sortable_fields.append(field.name)

        # إضافة حقول العلاقات المباشرة
        for field in self.model._meta.fields:
            if field.related_model and hasattr(field, "related_name"):
                sortable_fields.append(f"{field.name}__name")  # افتراض وجود حقل name
                sortable_fields.append(f"{field.name}__id")

        # دمج مع sortable_by المحدد يدوياً
        manual_sortable = getattr(self, "sortable_by", [])

        # إزالة التكرارات وإرجاع القائمة
        all_sortable = list(set(sortable_fields + manual_sortable))

        return all_sortable

    def get_list_display_links(self, request, list_display):
        """تحديد الحقول القابلة للنقر للوصول لصفحة التحرير"""
        # الحقل الأول دائماً قابل للنقر
        if list_display:
            return [list_display[0]]
        return super().get_list_display_links(request, list_display)

    def __init__(self, *args, **kwargs):
        """تلقائياً إضافة admin_order_field للدوال المخصصة"""
        super().__init__(*args, **kwargs)

        # إضافة admin_order_field تلقائياً للدوال التي لا تحتوي عليه
        for field_name in self.list_display:
            if hasattr(self, field_name):
                method = getattr(self, field_name)
                if callable(method) and not hasattr(method, "admin_order_field"):
                    # محاولة استنتاج الحقل المناسب للترتيب
                    if field_name.endswith("_display"):
                        base_field = field_name.replace("_display", "")
                        if hasattr(self.model, base_field):
                            method.admin_order_field = base_field
                    elif hasattr(self.model, field_name):
                        method.admin_order_field = field_name


def apply_sortable_to_admin_method(method_name, order_field):
    """دالة مساعدة لإضافة admin_order_field لأي method"""

    def decorator(func):
        func.admin_order_field = order_field
        return func

    return decorator


# دالات مساعدة لإنشاء display methods محسنة
def create_foreign_key_display(field_name, display_name, order_field=None):
    """إنشاء display method للحقول المرتبطة"""

    def display_method(self, obj):
        try:
            related_obj = getattr(obj, field_name)
            if related_obj:
                return str(related_obj)
            return "-"
        except Exception:
            return "-"

    display_method.short_description = display_name
    if order_field:
        display_method.admin_order_field = order_field

    return display_method


def create_choice_display(field_name, display_name, choices_dict=None):
    """إنشاء display method للحقول ذات الخيارات"""

    def display_method(self, obj):
        value = getattr(obj, field_name)
        if choices_dict and value in choices_dict:
            return choices_dict[value]
        return getattr(obj, f"get_{field_name}_display", lambda: value)()

    display_method.short_description = display_name
    display_method.admin_order_field = field_name

    return display_method


def create_date_display(field_name, display_name, date_format="%Y-%m-%d"):
    """إنشاء display method للحقول التاريخية"""

    def display_method(self, obj):
        date_value = getattr(obj, field_name)
        if date_value:
            return date_value.strftime(date_format)
        return "-"

    display_method.short_description = display_name
    display_method.admin_order_field = field_name

    return display_method


def create_boolean_display(field_name, display_name, true_text="نعم", false_text="لا"):
    """إنشاء display method للحقول المنطقية"""

    def display_method(self, obj):
        value = getattr(obj, field_name)
        return true_text if value else false_text

    display_method.short_description = display_name
    display_method.admin_order_field = field_name

    return display_method
