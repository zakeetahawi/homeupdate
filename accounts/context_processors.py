from .models import Department, UnifiedSystemSettings, BranchMessage
from .utils import get_user_notifications
from django.utils import timezone
from accounts.models import FooterSettings
from django.core.cache import cache


def departments(request):
    """
    Context processor to add departments to all templates in a hierarchical
    structure.
    """
    # Get all active departments
    all_departments = Department.objects.filter(is_active=True).order_by('order')

    # Create hierarchical structure for parent/child departments
    parent_departments = all_departments.filter(parent__isnull=True)

    # Get user-accessible departments
    user_departments = []
    user_parent_departments = []

    if request.user.is_authenticated:
        if request.user.is_superuser:
            user_departments = all_departments
            user_parent_departments = parent_departments
        else:            # Get user departments with ordering
            user_departments = (
                request.user.departments
                .filter(is_active=True)
                .order_by('order')
            )
            
            # Get unique parent departments
            user_parent_ids = set()
            for dept in user_departments:
                # Add either parent id or own id
                dept_id = dept.parent.id if dept.parent else dept.id
                user_parent_ids.add(dept_id)

            # Get parent departments
            user_parent_departments = (
                Department.objects
                .filter(
                    id__in=user_parent_ids, 
                    is_active=True
                )
                .order_by('order')
            )
            
    return {
        'all_departments': all_departments,
        'parent_departments': parent_departments,
        'user_departments': user_departments,
        'user_parent_departments': user_parent_departments
    }


def notifications(request):
    """
    Context processor to add notifications to all templates.
    """
    unread_notifications = []
    recent_notifications = []
    notifications_count = 0

    if request.user.is_authenticated:
        # Get unread notifications for the user
        unread_notifications = get_user_notifications(request.user, unread_only=True, limit=5)
        notifications_count = unread_notifications.count()

        # Get recent notifications (both read and unread)
        recent_notifications = get_user_notifications(request.user, unread_only=False, limit=5)

    return {
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        'notifications_count': notifications_count,
    }

def company_info(request):
    """توفير معلومات الشركة لجميع القوالب من UnifiedSystemSettings"""
    try:
        # محاولة الحصول على الإعدادات الموجودة فقط، بدون إنشاء جديدة
        company = UnifiedSystemSettings.objects.first()
        if not company:
            # إرجاع كائن افتراضي بدون حفظه في قاعدة البيانات
            company = UnifiedSystemSettings(
                company_name="الخواجة للستائر والمفروشات",
                company_address="العنوان",
                company_phone="01234567890",
                company_email="info@example.com",
                company_logo=None,
            )
    except Exception:
        # fallback default
        company = UnifiedSystemSettings(
            company_name="الخواجة للستائر والمفروشات",
            company_address="العنوان",
            company_phone="01234567890",
            company_email="info@example.com",
            company_logo=None,
        )
    return {'company_info': company}

def footer_settings(request):
    """توفير إعدادات التذييل لجميع القوالب"""
    try:
        footer_settings = FooterSettings.objects.first()
        if not footer_settings:
            footer_settings = FooterSettings.objects.create(
                left_column_title="عن الشركة",
                left_column_text="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
                middle_column_title="روابط سريعة",
                right_column_title="تواصل معنا"
            )
    except Exception:
        # في حالة حدوث أي خطأ، إنشاء كائن بقيم افتراضية
        footer_settings = FooterSettings(
            left_column_title="عن الشركة",
            left_column_text="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
            middle_column_title="روابط سريعة",
            right_column_title="تواصل معنا"
        )

    return {
        'footer_settings': footer_settings,
        'current_year': timezone.now().year
    }

def system_settings(request):
    """
    توفير إعدادات النظام لجميع القوالب من UnifiedSystemSettings
    """
    # محاولة الحصول على الإعدادات من الذاكرة المؤقتة
    settings = cache.get('system_settings')
    if not settings:
        try:
            # محاولة الحصول على الإعدادات الموجودة فقط، بدون إنشاء جديدة
            settings = UnifiedSystemSettings.objects.first()
            if settings:
                cache.set('system_settings', settings, 3600)
            else:
                # إرجاع كائن افتراضي بدون حفظه في قاعدة البيانات
                settings = UnifiedSystemSettings(
                    company_name="الخواجة للستائر والمفروشات",
                    currency="SAR",
                    enable_notifications=True,
                    items_per_page=20,
                    low_stock_threshold=20,
                    enable_analytics=True,
                    default_theme="default",
                    working_hours="9 صباحاً - 5 مساءً",
                    copyright_text="جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi"
                )
        except Exception:
            return {
                'system_settings': None,
                'currency_code': 'SAR',
                'currency_symbol': 'ر.س'
            }
    return {
        'system_settings': settings,
        'currency_code': settings.currency,
        'currency_symbol': settings.currency_symbol
    }

def user_context(request):
    """Context processor to add user-specific context to all templates."""
    context = {}
    if request.user.is_authenticated:
        has_branch = hasattr(request.user, 'branch')
        context['user_branch'] = request.user.branch if has_branch else None
    return context


def branch_messages(request):
    """
    Context processor to add branch messages to templates.
    Only loads messages for the home page.
    """
    if (request.user.is_authenticated and
            hasattr(request.user, 'branch') and
            request.path == '/'):
        messages = BranchMessage.objects.filter(
            branch=request.user.branch,
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).order_by('-created_at')
        return {'branch_messages': messages}
    return {'branch_messages': []}
