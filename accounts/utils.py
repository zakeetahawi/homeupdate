"""
دوال مساعدة لتطبيق إعدادات السنوات في جميع أنحاء النظام
"""
from django.db.models import Q
from django.utils import timezone
from .models import DashboardYearSettings


def apply_default_year_filter(queryset, request, date_field='created_at', exclude_customers=False):
    """
    تطبيق فلتر السنة الافتراضية على أي استعلام
    
    Args:
        queryset: الاستعلام المراد تطبيق الفلتر عليه
        request: كائن الطلب للحصول على المعاملات
        date_field: اسم حقل التاريخ (افتراضي: created_at)
        exclude_customers: استثناء العملاء من فلتر السنة الافتراضية (افتراضي: False)
    
    Returns:
        queryset مفلتر حسب السنة
    """
    # إذا كان المطلوب استثناء العملاء، لا تطبق الفلتر
    if exclude_customers:
        return queryset
    
    # الحصول على السنوات المحددة من المعاملات
    selected_years = request.GET.getlist('years')
    year_filter = request.GET.get('year', '')
    
    # إذا تم تحديد سنوات متعددة
    if selected_years:
        try:
            year_filters = Q()
            for year_str in selected_years:
                if year_str != 'all':
                    year = int(year_str)
                    year_filters |= Q(**{f'{date_field}__year': year})
            
            if year_filters:
                queryset = queryset.filter(year_filters)
        except (ValueError, TypeError):
            pass
    # إذا تم تحديد سنة واحدة فقط
    elif year_filter and year_filter != 'all':
        try:
            year = int(year_filter)
            queryset = queryset.filter(**{f'{date_field}__year': year})
        except (ValueError, TypeError):
            pass
    # إذا لم يتم تحديد أي سنة، استخدم السنة الافتراضية من الإعدادات
    else:
        default_year = DashboardYearSettings.get_default_year()
        queryset = queryset.filter(**{f'{date_field}__year': default_year})
    
    return queryset


def apply_year_filter_for_customers(queryset, request, date_field='created_at'):
    """
    تطبيق فلتر السنة للعملاء (بدون سنة افتراضية)
    
    Args:
        queryset: الاستعلام المراد تطبيق الفلتر عليه
        request: كائن الطلب للحصول على المعاملات
        date_field: اسم حقل التاريخ (افتراضي: created_at)
    
    Returns:
        queryset مفلتر حسب السنة (إذا تم تحديدها)
    """
    # الحصول على السنوات المحددة من المعاملات
    selected_years = request.GET.getlist('years')
    year_filter = request.GET.get('year', '')
    
    # إذا تم تحديد سنوات متعددة
    if selected_years:
        try:
            year_filters = Q()
            for year_str in selected_years:
                if year_str != 'all':
                    year = int(year_str)
                    year_filters |= Q(**{f'{date_field}__year': year})
            
            if year_filters:
                queryset = queryset.filter(year_filters)
        except (ValueError, TypeError):
            pass
    # إذا تم تحديد سنة واحدة فقط
    elif year_filter and year_filter != 'all':
        try:
            year = int(year_filter)
            queryset = queryset.filter(**{f'{date_field}__year': year})
        except (ValueError, TypeError):
            pass
    # إذا لم يتم تحديد أي سنة، لا تطبق أي فلتر (إظهار جميع العملاء)
    
    return queryset


def get_dashboard_year_context(request):
    """
    الحصول على معلومات السنة للسياق
    
    Args:
        request: كائن الطلب
    
    Returns:
        dict: معلومات السنة للسياق
    """
    available_years = DashboardYearSettings.get_available_years()
    default_year = DashboardYearSettings.get_default_year()
    selected_year = request.GET.get('year', '')
    selected_years = request.GET.getlist('years')
    current_year = timezone.now().year
    
    return {
        'available_years': list(available_years),
        'default_year': default_year,
        'selected_year': selected_year,
        'selected_years': selected_years,
        'current_year': current_year,
    }


def get_active_dashboard_years():
    """
    الحصول على السنوات النشطة في الداشبورد
    
    Returns:
        QuerySet: السنوات النشطة
    """
    return DashboardYearSettings.objects.filter(is_active=True).order_by('-year')


def set_default_dashboard_year(year):
    """
    تعيين سنة افتراضية جديدة
    
    Args:
        year: السنة المراد تعيينها كافتراضية
    
    Returns:
        bool: True إذا تم التعيين بنجاح
    """
    try:
        # إلغاء الافتراضية من جميع السنوات
        DashboardYearSettings.objects.update(is_default=False)
        
        # تعيين السنة الجديدة كافتراضية
        year_setting, created = DashboardYearSettings.objects.get_or_create(
            year=year,
            defaults={'is_active': True, 'is_default': True}
        )
        
        if not created:
            year_setting.is_default = True
            year_setting.is_active = True
            year_setting.save()
        
        return True
    except Exception:
        return False


def ensure_current_year_exists():
    """
    التأكد من وجود السنة الحالية في الإعدادات
    """
    current_year = timezone.now().year
    
    # التحقق من وجود السنة الحالية
    if not DashboardYearSettings.objects.filter(year=current_year).exists():
        # إنشاء السنة الحالية
        DashboardYearSettings.objects.create(
            year=current_year,
            is_active=True,
            is_default=True,
            description=f'السنة الحالية {current_year}'
        )
    
    # التأكد من وجود سنة افتراضية
    if not DashboardYearSettings.objects.filter(is_default=True).exists():
        # تعيين السنة الحالية كافتراضية
        year_setting = DashboardYearSettings.objects.filter(year=current_year).first()
        if year_setting:
            year_setting.is_default = True
            year_setting.save()


def get_year_filter_display(request):
    """
    الحصول على نص وصفي للفلتر المطبق حالياً
    
    Args:
        request: كائن الطلب
    
    Returns:
        str: النص الوصفي للفلتر
    """
    selected_years = request.GET.getlist('years')
    year_filter = request.GET.get('year', '')
    
    if selected_years:
        if len(selected_years) == 1:
            return f"السنة: {selected_years[0]}"
        else:
            return f"السنوات: {', '.join(selected_years)}"
    elif year_filter and year_filter != 'all':
        return f"السنة: {year_filter}"
    else:
        default_year = DashboardYearSettings.get_default_year()
        return f"السنة الافتراضية: {default_year}"


