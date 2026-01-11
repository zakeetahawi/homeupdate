"""
عروض محرر الفواتير المتقدم
Advanced Invoice Editor Views
"""

import json
import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .invoice_models import InvoicePrintLog, InvoiceTemplate
from .models import Order

logger = logging.getLogger(__name__)


@staff_member_required
def invoice_editor(request, template_id=None):
    """محرر الفواتير - يفتح محرر البناء الجديد (GrapesJS)"""
    return invoice_builder(request, template_id)


@staff_member_required
def invoice_builder(request, template_id=None):
    """محرر بناء القوالب (GrapesJS) بديل للمحرر البسيط"""
    # جلب إعدادات النظام والشركة
    from accounts.models import CompanyInfo, SystemSettings

    from .models import Order

    system_settings = SystemSettings.get_settings()
    company_info = CompanyInfo.objects.first()

    # التأكد من وجود company_info
    if not company_info:
        company_info = CompanyInfo.objects.create(
            name="الخواجة للستائر والمفروشات",
            description="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
            version="1.0.0",
            release_date="2025-04-30",
            developer="zakee tahawi",
            working_hours="9 صباحاً - 5 مساءً",
            copyright_text="جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi",
        )

    # جلب بيانات الطلب إذا كان في وضع الطباعة
    order = None
    print_mode = request.GET.get("print_mode", False)
    order_id = request.GET.get("order_id")
    auto_print = request.GET.get("auto_print", False)

    if order_id:
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            order = None

    # إذا لم يتم تحديد قالب، استخدام القالب الافتراضي أو إنشاء واحد جديد
    template = None
    if template_id:
        template = get_object_or_404(InvoiceTemplate, id=template_id)
    else:
        # البحث عن القالب الافتراضي أو إنشاء واحد جديد
        template = InvoiceTemplate.objects.filter(is_default=True).first()
        if not template:
            # إنشاء قالب افتراضي بناء على بيانات الشركة
            template = InvoiceTemplate.objects.create(
                name="القالب الافتراضي",
                is_default=True,
                company_name=company_info.name if company_info else "اسم الشركة",
                company_address=company_info.address if company_info else "العنوان",
                company_phone=company_info.phone if company_info else "01234567890",
                company_email=(
                    company_info.email if company_info else "info@example.com"
                ),
                company_website=company_info.website if company_info else "",
                primary_color=company_info.primary_color if company_info else "#0d6efd",
                secondary_color=(
                    company_info.secondary_color if company_info else "#198754"
                ),
                accent_color=company_info.accent_color if company_info else "#ffc107",
            )

    # تجهيز بيانات الحفظ لإرسالها للقالب قبل render
    saved_html_content = ""
    saved_meta_content = {}
    if template:
        try:
            meta = {
                "settings": {
                    "primary_color": template.primary_color,
                    "secondary_color": template.secondary_color,
                    "accent_color": template.accent_color,
                    "font_family": template.font_family,
                    "font_size": template.font_size,
                    "page_size": template.page_size,
                    "page_margins": template.page_margins,
                },
                "company_info": {
                    "name": template.company_name,
                    "address": template.company_address,
                    "phone": template.company_phone,
                    "email": template.company_email,
                    "website": template.company_website,
                },
                "content_settings": {
                    "show_company_logo": template.show_company_logo,
                    "show_order_details": template.show_order_details,
                    "show_customer_details": template.show_customer_details,
                    "show_payment_details": template.show_payment_details,
                    "show_notes": template.show_notes,
                    "show_terms": template.show_terms,
                },
                "advanced_settings": template.advanced_settings or {},
            }
            saved_html_content = template.html_content or ""
            saved_meta_content = meta
        except Exception:
            saved_html_content = ""
            saved_meta_content = {}

    context = {
        "template": template,
        "template_id": template.id if template else None,
        "page_title": "مُنشئ قالب الفاتورة",
        "system_settings": system_settings,
        "company_info": company_info,
        "currency_symbol": (
            system_settings.currency_symbol if system_settings else "ج.م"
        ),
        "order": order,
        "print_mode": print_mode,
        "auto_print": auto_print,
        "saved_html_content": saved_html_content,
        "saved_meta_content": saved_meta_content,
    }
    return render(request, "orders/invoice_builder.html", context)


@staff_member_required
def template_list(request):
    """قائمة قوالب الفواتير"""
    templates = InvoiceTemplate.objects.all().order_by("-is_default", "-updated_at")

    # البحث
    search_query = request.GET.get("search", "")
    if search_query:
        templates = templates.filter(name__icontains=search_query)

    # التصفية حسب النوع
    template_type = request.GET.get("type", "")
    if template_type:
        templates = templates.filter(template_type=template_type)

    # التصفية حسب الحالة
    is_active = request.GET.get("active", "")
    if is_active == "1":
        templates = templates.filter(is_active=True)
    elif is_active == "0":
        templates = templates.filter(is_active=False)

    # التقسيم إلى صفحات
    paginator = Paginator(templates, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "template_type": template_type,
        "is_active": is_active,
        "template_types": InvoiceTemplate.TEMPLATE_TYPES,
        "page_title": "قوالب الفواتير",
    }

    return render(request, "orders/template_list.html", context)


@staff_member_required
def save_template(request):
    """حفظ قالب الفاتورة - محمي بـ CSRF"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة غير مسموحة"})

    try:
        data = json.loads(request.body)

        template_id = data.get("template_id")
        template_data = data.get("template_data", {})

        if template_id:
            # تحديث قالب موجود
            template = get_object_or_404(InvoiceTemplate, id=template_id)
            logger.info(f"تحديث القالب: {template.name}")
        else:
            # إنشاء قالب جديد
            template = InvoiceTemplate()
            template.created_by = request.user
            logger.info("إنشاء قالب جديد")

        # تحديث البيانات
        template.name = template_data.get("name", "قالب جديد")
        template.template_type = template_data.get("template_type", "custom")
        template.html_content = template_data.get("html_content", "")
        template.css_styles = template_data.get("css_styles", "")

        # إعدادات التصميم
        settings = template_data.get("settings", {})
        template.primary_color = settings.get("primary_color", "#0d6efd")
        template.secondary_color = settings.get("secondary_color", "#198754")
        template.accent_color = settings.get("accent_color", "#ffc107")
        template.font_family = settings.get("font_family", "Cairo, Arial, sans-serif")
        template.font_size = int(settings.get("font_size", 14))
        template.page_size = settings.get("page_size", "A4")
        template.page_margins = int(settings.get("page_margins", 20))

        # إعدادات الشركة - استخدام إعدادات النظام كافتراضية
        from accounts.models import CompanyInfo, SystemSettings

        system_settings = SystemSettings.get_settings()
        company_info_db = CompanyInfo.objects.first()

        company_info = template_data.get("company_info", {})
        template.company_name = company_info.get("name") or (
            company_info_db.name if company_info_db else "اسم الشركة"
        )
        template.company_address = company_info.get("address") or (
            company_info_db.address if company_info_db else "المملكة العربية السعودية"
        )
        template.company_phone = company_info.get("phone") or (
            company_info_db.phone if company_info_db else ""
        )
        template.company_email = company_info.get("email") or (
            company_info_db.email if company_info_db else ""
        )
        template.company_website = company_info.get("website") or (
            company_info_db.website if company_info_db else ""
        )

        # إعدادات المحتوى
        content_settings = template_data.get("content_settings", {})
        template.show_company_logo = content_settings.get("show_company_logo", True)
        template.show_order_details = content_settings.get("show_order_details", True)
        template.show_customer_details = content_settings.get(
            "show_customer_details", True
        )
        template.show_payment_details = content_settings.get(
            "show_payment_details", True
        )
        template.show_notes = content_settings.get("show_notes", True)
        template.show_terms = content_settings.get("show_terms", True)

        # نصوص مخصصة
        custom_texts = template_data.get("custom_texts", {})
        template.header_text = custom_texts.get("header_text", "")
        template.footer_text = custom_texts.get("footer_text", "")
        template.terms_text = custom_texts.get("terms_text", "شكراً لتعاملكم معنا.")

        # إعدادات متقدمة
        template.advanced_settings = template_data.get("advanced_settings", {})

        # حالة القالب
        template.is_active = template_data.get("is_active", True)

        # جعل القالب افتراضياً إذا لم يكن هناك قالب افتراضي
        if template_data.get("is_default", True):
            # إزالة الافتراضي من القوالب الأخرى
            InvoiceTemplate.objects.filter(is_default=True).update(is_default=False)
            template.is_default = True
        else:
            template.is_default = False

        template.save()

        return JsonResponse(
            {
                "success": True,
                "message": "تم حفظ القالب بنجاح",
                "template_id": template.id,
                "template_name": template.name,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "بيانات غير صحيحة"})
    except Exception as e:
        logger.error(f"خطأ في حفظ القالب: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في الحفظ: {str(e)}"})


@staff_member_required
def load_template(request, template_id):
    """تحميل قالب الفاتورة"""
    try:
        template = get_object_or_404(InvoiceTemplate, id=template_id)

        # جلب إعدادات النظام الحالية
        from accounts.models import CompanyInfo, SystemSettings

        system_settings = SystemSettings.get_settings()
        company_info_db = CompanyInfo.objects.first()

        template_data = {
            "id": template.id,
            "name": template.name,
            "template_type": template.template_type,
            "html_content": template.html_content,
            "css_styles": template.css_styles,
            "settings": {
                "primary_color": template.primary_color,
                "secondary_color": template.secondary_color,
                "accent_color": template.accent_color,
                "font_family": template.font_family,
                "font_size": template.font_size,
                "page_size": template.page_size,
                "page_margins": template.page_margins,
            },
            "company_info": {
                "name": template.company_name
                or (company_info_db.name if company_info_db else "اسم الشركة"),
                "address": template.company_address
                or (
                    company_info_db.address
                    if company_info_db
                    else "المملكة العربية السعودية"
                ),
                "phone": template.company_phone
                or (company_info_db.phone if company_info_db else ""),
                "email": template.company_email
                or (company_info_db.email if company_info_db else ""),
                "website": template.company_website
                or (company_info_db.website if company_info_db else ""),
            },
            "system_info": {
                "currency_code": system_settings.currency if system_settings else "EGP",
                "currency_symbol": (
                    system_settings.currency_symbol if system_settings else "ج.م"
                ),
                "system_name": (
                    system_settings.name if system_settings else "نظام الخواجه"
                ),
            },
            "content_settings": {
                "show_company_logo": template.show_company_logo,
                "show_order_details": template.show_order_details,
                "show_customer_details": template.show_customer_details,
                "show_payment_details": template.show_payment_details,
                "show_notes": template.show_notes,
                "show_terms": template.show_terms,
            },
            "custom_texts": {
                "header_text": template.header_text,
                "footer_text": template.footer_text,
                "terms_text": template.terms_text,
            },
            "advanced_settings": template.advanced_settings,
            "is_active": template.is_active,
            "is_default": template.is_default,
            "usage_count": template.usage_count,
            "last_used": template.last_used.isoformat() if template.last_used else None,
        }

        return JsonResponse({"success": True, "template": template_data})

    except Exception as e:
        logger.error(f"خطأ في تحميل القالب: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في التحميل: {str(e)}"})


@staff_member_required
def clone_template(request, template_id):
    """نسخ قالب الفاتورة"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة غير مسموحة"})

    try:
        original_template = get_object_or_404(InvoiceTemplate, id=template_id)

        # الحصول على الاسم الجديد
        data = json.loads(request.body)
        new_name = data.get("name", f"{original_template.name} - نسخة")

        # إنشاء النسخة
        cloned_template = original_template.clone_template(new_name)
        cloned_template.created_by = request.user
        cloned_template.is_default = False  # النسخة ليست افتراضية
        cloned_template.save()

        logger.info(f"تم نسخ القالب: {original_template.name} -> {new_name}")

        return JsonResponse(
            {
                "success": True,
                "message": "تم نسخ القالب بنجاح",
                "template_id": cloned_template.id,
                "template_name": cloned_template.name,
            }
        )

    except Exception as e:
        logger.error(f"خطأ في نسخ القالب: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في النسخ: {str(e)}"})


@staff_member_required
def delete_template(request, template_id):
    """حذف قالب الفاتورة"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة غير مسموحة"})

    try:
        template = get_object_or_404(InvoiceTemplate, id=template_id)

        # منع حذف القالب الافتراضي إذا كان الوحيد
        if template.is_default:
            active_templates_count = InvoiceTemplate.objects.filter(
                is_active=True
            ).count()
            if active_templates_count <= 1:
                return JsonResponse(
                    {"success": False, "error": "لا يمكن حذف القالب الافتراضي الوحيد"}
                )

        template_name = template.name
        template.delete()

        logger.info(f"تم حذف القالب: {template_name}")

        return JsonResponse(
            {"success": True, "message": f'تم حذف القالب "{template_name}" بنجاح'}
        )

    except Exception as e:
        logger.error(f"خطأ في حذف القالب: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في الحذف: {str(e)}"})


@staff_member_required
def set_default_template(request, template_id):
    """تعيين قالب افتراضي"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة غير مسموحة"})

    try:
        template = get_object_or_404(InvoiceTemplate, id=template_id)

        # إزالة الافتراضية من القوالب الأخرى
        InvoiceTemplate.objects.filter(is_default=True).update(is_default=False)

        # تعيين القالب الجديد كافتراضي
        template.is_default = True
        template.is_active = True  # تأكد من أنه نشط
        template.save()

        logger.info(f"تم تعيين القالب الافتراضي: {template.name}")

        return JsonResponse(
            {"success": True, "message": f'تم تعيين "{template.name}" كقالب افتراضي'}
        )

    except Exception as e:
        logger.error(f"خطأ في تعيين القالب الافتراضي: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في التعيين: {str(e)}"})


@login_required
def preview_invoice(request, order_id, template_id=None):
    """توحيد المعاينة: إعادة توجيه إلى صفحة الطباعة الموحدة المعتمدة على محتوى المحرر"""
    try:
        order = get_object_or_404(Order, id=order_id)
        # نستخدم القالب الافتراضي دائماً، والمعاينة تتم عبر نفس مسار الطباعة بدون طباعة تلقائية
        logger.info(
            f"معاينة موحدة لفاتورة الطلب {order.order_number} باستخدام القالب الافتراضي (المحرر البسيط)"
        )
        return redirect("orders:invoice_print", order_number=order.order_number)
    except Exception as e:
        logger.error(f"خطأ في معاينة الفاتورة: {str(e)}")
        messages.error(request, f"خطأ في المعاينة: {str(e)}")
        return redirect("orders:order_detail", pk=order_id)


@login_required
def print_invoice_with_template(request, order_id, template_id=None):
    """توحيد الطباعة: إعادة توجيه إلى صفحة الطباعة الموحدة المعتمدة على محتوى المحرر"""
    try:
        order = get_object_or_404(Order, id=order_id)
        logger.info(
            f"طباعة موحدة لفاتورة الطلب {order.order_number} باستخدام القالب الافتراضي (المحرر البسيط)"
        )
        # استخدام الطباعة التلقائية
        return redirect(f"/orders/order/{order.order_number}/invoice/?auto_print=1")
    except Exception as e:
        logger.error(f"خطأ في طباعة الفاتورة: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في الطباعة: {str(e)}"})


@staff_member_required
def template_analytics(request):
    """إحصائيات استخدام القوالب"""
    templates = InvoiceTemplate.objects.all().order_by("-usage_count")

    # إحصائيات عامة
    total_templates = templates.count()
    active_templates = templates.filter(is_active=True).count()
    total_usage = sum(template.usage_count for template in templates)

    # أكثر القوالب استخداماً
    most_used = templates.filter(usage_count__gt=0)[:5]

    # القوالب حسب النوع
    type_stats = {}
    for template_type, name in InvoiceTemplate.TEMPLATE_TYPES:
        count = templates.filter(template_type=template_type).count()
        usage = sum(
            t.usage_count for t in templates.filter(template_type=template_type)
        )
        type_stats[name] = {"count": count, "usage": usage}

    # سجلات الطباعة الأخيرة
    recent_prints = InvoicePrintLog.objects.select_related(
        "order", "template", "printed_by"
    ).order_by("-printed_at")[:10]

    context = {
        "templates": templates,
        "total_templates": total_templates,
        "active_templates": active_templates,
        "total_usage": total_usage,
        "most_used": most_used,
        "type_stats": type_stats,
        "recent_prints": recent_prints,
        "page_title": "إحصائيات قوالب الفواتير",
    }

    return render(request, "orders/template_analytics.html", context)


@staff_member_required
def export_template(request, template_id):
    """تصدير قالب الفاتورة"""
    try:
        template = get_object_or_404(InvoiceTemplate, id=template_id)

        # إعداد البيانات للتصدير
        export_data = {
            "name": template.name,
            "template_type": template.template_type,
            "html_content": template.html_content,
            "css_styles": template.css_styles,
            "settings": {
                "primary_color": template.primary_color,
                "secondary_color": template.secondary_color,
                "accent_color": template.accent_color,
                "font_family": template.font_family,
                "font_size": template.font_size,
                "page_size": template.page_size,
                "page_margins": template.page_margins,
            },
            "company_info": {
                "name": template.company_name,
                "address": template.company_address,
                "phone": template.company_phone,
                "email": template.company_email,
                "website": template.company_website,
            },
            "content_settings": {
                "show_company_logo": template.show_company_logo,
                "show_order_details": template.show_order_details,
                "show_customer_details": template.show_customer_details,
                "show_payment_details": template.show_payment_details,
                "show_notes": template.show_notes,
                "show_terms": template.show_terms,
            },
            "custom_texts": {
                "header_text": template.header_text,
                "footer_text": template.footer_text,
                "terms_text": template.terms_text,
            },
            "advanced_settings": template.advanced_settings,
            "export_info": {
                "exported_at": timezone.now().isoformat(),
                "exported_by": request.user.username,
                "version": "1.0",
            },
        }

        # إنشاء الاستجابة
        response = HttpResponse(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{template.name}_template.json"'
        )

        logger.info(f"تصدير القالب: {template.name}")

        return response

    except Exception as e:
        logger.error(f"خطأ في تصدير القالب: {str(e)}")
        messages.error(request, f"خطأ في التصدير: {str(e)}")
        return redirect("orders:template_list")


@staff_member_required
def import_template(request):
    """استيراد قالب الفاتورة - محمي بـ CSRF"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة غير مسموحة"})

    try:
        # قراءة الملف المرفوع
        uploaded_file = request.FILES.get("template_file")
        if not uploaded_file:
            return JsonResponse({"success": False, "error": "لم يتم اختيار ملف"})

        # قراءة محتوى الملف
        file_content = uploaded_file.read().decode("utf-8")
        template_data = json.loads(file_content)

        # التحقق من صحة البيانات
        if not template_data.get("name"):
            return JsonResponse({"success": False, "error": "ملف القالب غير صحيح"})

        # إنشاء القالب الجديد
        template = InvoiceTemplate()
        template.name = template_data["name"] + " (مستورد)"
        template.template_type = template_data.get("template_type", "custom")
        template.html_content = template_data.get("html_content", "")
        template.css_styles = template_data.get("css_styles", "")

        # إعدادات التصميم
        settings = template_data.get("settings", {})
        template.primary_color = settings.get("primary_color", "#0d6efd")
        template.secondary_color = settings.get("secondary_color", "#198754")
        template.accent_color = settings.get("accent_color", "#ffc107")
        template.font_family = settings.get("font_family", "Cairo, Arial, sans-serif")
        template.font_size = settings.get("font_size", 14)
        template.page_size = settings.get("page_size", "A4")
        template.page_margins = settings.get("page_margins", 20)

        # معلومات الشركة
        company_info = template_data.get("company_info", {})
        template.company_name = company_info.get("name") or (
            company_info_db.name if company_info_db else "اسم الشركة"
        )
        template.company_address = company_info.get(
            "address", "المملكة العربية السعودية"
        )
        template.company_phone = company_info.get("phone", "")
        template.company_email = company_info.get("email", "")
        template.company_website = company_info.get("website", "")

        # إعدادات المحتوى
        content_settings = template_data.get("content_settings", {})
        template.show_company_logo = content_settings.get("show_company_logo", True)
        template.show_order_details = content_settings.get("show_order_details", True)
        template.show_customer_details = content_settings.get(
            "show_customer_details", True
        )
        template.show_payment_details = content_settings.get(
            "show_payment_details", True
        )
        template.show_notes = content_settings.get("show_notes", True)
        template.show_terms = content_settings.get("show_terms", True)

        # نصوص مخصصة
        custom_texts = template_data.get("custom_texts", {})
        template.header_text = custom_texts.get("header_text", "")
        template.footer_text = custom_texts.get("footer_text", "")
        template.terms_text = custom_texts.get("terms_text", "شكراً لتعاملكم معنا.")

        # إعدادات متقدمة
        template.advanced_settings = template_data.get("advanced_settings", {})

        # معلومات النظام
        template.created_by = request.user
        template.is_active = True
        template.is_default = False

        template.save()

        logger.info(f"تم استيراد القالب: {template.name}")

        return JsonResponse(
            {
                "success": True,
                "message": f'تم استيراد القالب "{template.name}" بنجاح',
                "template_id": template.id,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "ملف JSON غير صحيح"})
    except Exception as e:
        logger.error(f"خطأ في استيراد القالب: {str(e)}")
        return JsonResponse({"success": False, "error": f"خطأ في الاستيراد: {str(e)}"})
