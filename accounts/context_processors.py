from .models import Department, CompanyInfo, BranchMessage
from accounts.models import SystemSettings as AccountsSystemSettings
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




def company_info(request):
    """توفير معلومات الشركة لجميع القوالب"""
    try:
        company = CompanyInfo.objects.first()
        if not company:
            # إنشاء كائن بقيم افتراضية إذا لم يكن موجوداً
            company = CompanyInfo.objects.create(
                name="الخواجة للستائر والمفروشات",
                description="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
                version="1.0.0",
                release_date="2025-04-30",
                developer="zakee tahawi",
                working_hours="9 صباحاً - 5 مساءً",
                copyright_text="جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi"
            )
    except Exception:
        # في حالة حدوث أي خطأ، إنشاء كائن بقيم افتراضية
        company = CompanyInfo(
            name="الخواجة للستائر والمفروشات",
            description="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
            version="1.0.0",
            release_date="2025-04-30",
            developer="zakee tahawi",
            working_hours="9 صباحاً - 5 مساءً",
            copyright_text="جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi"
        )
    
    # التأكد من أن اللوغو موجود قبل إرجاعه
    if hasattr(company, 'logo') and company.logo:
        try:
            # اختبار الوصول إلى URL للتأكد من وجود الملف
            company.logo.url
        except (ValueError, FileNotFoundError):
            # إذا لم يكن الملف موجود، تعيين اللوغو كـ None
            company.logo = None
    
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
    توفير إعدادات النظام لجميع القوالب
    """
    # محاولة الحصول على الإعدادات من الذاكرة المؤقتة
    settings = cache.get('system_settings')

    if not settings:
        try:
            # الحصول على الإعدادات أو إنشاؤها إذا لم تكن موجودة
            settings, created = AccountsSystemSettings.objects.get_or_create(pk=1)
            # تخزين في الذاكرة المؤقتة لمدة ساعة
            cache.set('accounts_system_settings', settings, 3600)
        except Exception:
            # إرجاع قيم افتراضية في حالة حدوث خطأ
            return {
                'system_settings': None,
                'currency_code': 'SAR',
                'currency_symbol': 'ر.س'
            }

    # تم إلغاء السنة الافتراضية

    return {
        'system_settings': settings,
        'currency_code': settings.currency,
        'currency_symbol': settings.CURRENCY_SYMBOLS.get(settings.currency, settings.currency),
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
    if request.user.is_authenticated and request.path == '/':
        from django.db.models import Q
        
        messages_query = Q(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        
        # إضافة الرسائل العامة
        messages_query &= Q(is_for_all_branches=True)
        
        # إضافة رسائل الفرع المحدد إذا كان للمستخدم فرع
        if hasattr(request.user, 'branch') and request.user.branch:
            messages_query |= Q(
                branch=request.user.branch,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
        
        messages = BranchMessage.objects.filter(messages_query).order_by('-created_at')
        return {'branch_messages': messages}
    return {'branch_messages': []}


def notifications_context(request):
    """إضافة عدادات الإشعارات إلى السياق"""
    context = {}

    if request.user.is_authenticated:
        # الإشعارات - تم إزالتها
        simple_unread = 0
        total_unread = 0
        
        # عدد الرسائل الداخلية غير المقروءة
        from .models import InternalMessage
        internal_messages_unread = InternalMessage.get_unread_count(request.user)

        context.update({
            'simple_notifications_unread': simple_unread,
            'total_notifications_unread': total_unread,
            'internal_messages_unread': internal_messages_unread,
        })

    return context


def admin_notifications_context(request):
    """إضافة عدادات الإشعارات لـ admin panel"""
    context = {}

    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        # الإشعارات - تم إزالتها
        total_simple = 0
        unread_simple = 0
        urgent_simple = 0

        context.update({
            'admin_simple_total': total_simple,
            'admin_simple_unread': unread_simple,
            'admin_simple_urgent': urgent_simple,
            'admin_total_unread': unread_simple,
        })

    return context
