"""
Views لإدارة أكواد الخصم الترويجية
Promo Code Management Views
"""

import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import PromoCode

logger = logging.getLogger(__name__)


def promo_code_required(view_func):
    """ديكوريتر للتحقق من صلاحية إصدار أكواد الخصم"""

    def wrapper(request, *args, **kwargs):
        if not request.user.can_issue_promo_code and not request.user.is_superuser:
            messages.error(request, "ليس لديك صلاحية إدارة أكواد الخصم")
            return redirect("orders:orders_dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


def _get_filtered_promo_codes(request):
    """
    فلترة أكواد الخصم بناءً على معاملات الطلب.
    تُستخدم في القائمة والتصدير.
    """
    from accounts.models import User

    qs = PromoCode.objects.select_related(
        "issued_by",
        "used_by",
        "used_for_customer",
        "used_in_order",
        "sent_to_customer",
    ).all()

    params = request.GET
    status_filter = params.get("status", "")
    search = params.get("q", "").strip()
    issued_by_filter = params.get("issued_by", "")
    discount_filter = params.get("discount", "")
    date_from = params.get("date_from", "")
    date_to = params.get("date_to", "")

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search:
        qs = qs.filter(
            Q(code__icontains=search)
            | Q(issued_by__first_name__icontains=search)
            | Q(issued_by__last_name__icontains=search)
            | Q(used_for_customer__name__icontains=search)
            | Q(issue_notes__icontains=search)
        )

    if issued_by_filter:
        qs = qs.filter(issued_by_id=issued_by_filter)

    if discount_filter:
        qs = qs.filter(discount_percentage=discount_filter)

    if date_from:
        qs = qs.filter(issued_at__date__gte=date_from)

    if date_to:
        qs = qs.filter(issued_at__date__lte=date_to)

    # قائمة المُصدرين للفلتر
    issuer_ids = PromoCode.objects.values_list("issued_by", flat=True).distinct()
    issuers = User.objects.filter(pk__in=issuer_ids).values("id", "first_name", "last_name")

    filter_context = {
        "status_filter": status_filter,
        "search_query": search,
        "issued_by_filter": issued_by_filter,
        "discount_filter": discount_filter,
        "date_from": date_from,
        "date_to": date_to,
        "issuers": issuers,
    }

    return qs, filter_context


@login_required
@promo_code_required
def promo_code_list(request):
    """صفحة عرض جميع أكواد الخصم"""
    # تحديث الأكواد المنتهية تلقائياً
    now = timezone.now()
    PromoCode.objects.filter(
        status="active", expires_at__lt=now
    ).update(status="expired")

    promo_codes, filter_context = _get_filtered_promo_codes(request)

    # إحصائيات
    stats = {
        "total": PromoCode.objects.count(),
        "active": PromoCode.objects.filter(status="active", expires_at__gt=now).count(),
        "used": PromoCode.objects.filter(status="used").count(),
        "expired": PromoCode.objects.filter(
            Q(status="expired") | Q(status="active", expires_at__lt=now)
        ).count(),
        "cancelled": PromoCode.objects.filter(status="cancelled").count(),
    }

    context = {
        "promo_codes": promo_codes[:100],
        "stats": stats,
        "filtered_count": promo_codes.count(),
        "discount_range": range(1, 16),
        **filter_context,
    }
    return render(request, "orders/promo_codes/list.html", context)


@login_required
@promo_code_required
def promo_code_export(request):
    """تصدير أكواد الخصم إلى Excel بناءً على الفلاتر الحالية"""
    from accounting.export_utils import export_to_excel

    promo_codes, _ = _get_filtered_promo_codes(request)

    STATUS_MAP = {"active": "فعّال", "used": "مُستخدم", "expired": "منتهي", "cancelled": "ملغي"}

    columns = [
        {"header": "الكود", "key": "code", "width": 14},
        {"header": "نسبة الخصم %", "key": "discount", "width": 14},
        {"header": "الحالة", "key": "status", "width": 12},
        {"header": "صادر من", "key": "issued_by", "width": 20},
        {"header": "تاريخ الإصدار", "key": "issued_at", "width": 18},
        {"header": "ينتهي في", "key": "expires_at", "width": 16},
        {"header": "ملاحظات", "key": "notes", "width": 25},
        {"header": "أُرسل للعميل", "key": "sent_to", "width": 20},
        {"header": "تاريخ الإرسال", "key": "sent_at", "width": 16},
        {"header": "استُخدم للعميل", "key": "used_for", "width": 20},
        {"header": "استُخدم بواسطة", "key": "used_by", "width": 18},
        {"header": "تاريخ الاستخدام", "key": "used_at", "width": 16},
        {"header": "رقم الطلب", "key": "order_number", "width": 14},
    ]

    data = []
    for p in promo_codes:
        data.append({
            "code": p.code,
            "discount": p.discount_percentage,
            "status": STATUS_MAP.get(p.status, p.status),
            "issued_by": p.issued_by.get_full_name() if p.issued_by else "—",
            "issued_at": p.issued_at.strftime("%Y-%m-%d %H:%M") if p.issued_at else "",
            "expires_at": p.expires_at.strftime("%Y-%m-%d") if p.expires_at else "",
            "notes": p.issue_notes or "",
            "sent_to": p.sent_to_customer.name if p.sent_to_customer else "",
            "sent_at": p.sent_at.strftime("%Y-%m-%d %H:%M") if p.sent_at else "",
            "used_for": p.used_for_customer.name if p.used_for_customer else "",
            "used_by": p.used_by.get_full_name() if p.used_by else "",
            "used_at": p.used_at.strftime("%Y-%m-%d %H:%M") if p.used_at else "",
            "order_number": p.used_in_order.order_number if p.used_in_order else "",
        })

    return export_to_excel(data, columns, filename="أكواد_الخصم", sheet_name="أكواد الخصم")


@login_required
@promo_code_required
def promo_code_issue(request):
    """إصدار كود خصم جديد"""
    from accounts.models import InternalMessage, User

    if request.method == "POST":
        discount_percentage = request.POST.get("discount_percentage")
        issue_notes = request.POST.get("issue_notes", "").strip()
        expires_days = request.POST.get("expires_days")
        send_to_user_id = request.POST.get("send_to_user", "").strip()

        if not discount_percentage or not expires_days:
            messages.error(request, "يجب تحديد نسبة الخصم ومدة الصلاحية")
            return redirect("orders:promo_code_issue")

        try:
            discount_percentage = int(discount_percentage)
            expires_days = int(expires_days)

            if not 1 <= discount_percentage <= 15:
                messages.error(request, "نسبة الخصم يجب أن تكون بين 1% و 15%")
                return redirect("orders:promo_code_issue")

            if expires_days < 1:
                messages.error(request, "مدة الصلاحية يجب أن تكون يوم واحد على الأقل")
                return redirect("orders:promo_code_issue")

            code = PromoCode.generate_code()
            promo = PromoCode.objects.create(
                code=code,
                discount_percentage=discount_percentage,
                issued_by=request.user,
                issue_notes=issue_notes,
                expires_at=timezone.now() + timedelta(days=expires_days),
            )

            # إرسال رسالة داخلية للمستخدم المختار (اختياري)
            if send_to_user_id:
                try:
                    recipient = User.objects.get(pk=send_to_user_id, is_active=True)
                    expires_date = promo.expires_at.strftime("%Y-%m-%d")
                    InternalMessage.objects.create(
                        sender=request.user,
                        recipient=recipient,
                        subject=f"كود خصم جديد: {promo.code}",
                        body=(
                            f"تم إصدار كود خصم جديد لك:\n\n"
                            f"الكود: {promo.code}\n"
                            f"نسبة الخصم: {promo.discount_percentage}%\n"
                            f"صالح حتى: {expires_date}\n"
                            f"{('ملاحظات: ' + issue_notes) if issue_notes else ''}\n\n"
                            f"يُستخدم الكود مرة واحدة فقط عند إنشاء طلب جديد."
                        ),
                        is_important=True,
                    )
                    messages.success(
                        request,
                        f"تم إصدار كود الخصم: {promo.code} ({promo.discount_percentage}%) وإرسال رسالة لـ {recipient.get_full_name()}",
                    )
                except User.DoesNotExist:
                    messages.success(
                        request,
                        f"تم إصدار كود الخصم بنجاح: {promo.code} ({promo.discount_percentage}%)",
                    )
            else:
                messages.success(
                    request,
                    f"تم إصدار كود الخصم بنجاح: {promo.code} ({promo.discount_percentage}%)",
                )
            return redirect("orders:promo_code_list")

        except (ValueError, TypeError):
            messages.error(request, "قيم غير صالحة")
            return redirect("orders:promo_code_issue")

    # المستخدمون النشطون (ما عدا الحالي)
    active_users = (
        User.objects.filter(is_active=True)
        .exclude(pk=request.user.pk)
        .order_by("first_name", "last_name")
    )

    context = {
        "discount_range": range(1, 16),
        "active_users": active_users,
    }
    return render(request, "orders/promo_codes/issue.html", context)


@login_required
@promo_code_required
@require_http_methods(["POST"])
def promo_code_cancel(request, code_id):
    """إلغاء كود خصم فعّال"""
    promo = get_object_or_404(PromoCode, pk=code_id)

    if promo.status != "active":
        messages.error(request, "لا يمكن إلغاء كود غير فعّال")
        return redirect("orders:promo_code_list")

    promo.status = "cancelled"
    promo.save(update_fields=["status"])
    messages.success(request, f"تم إلغاء كود الخصم: {promo.code}")
    return redirect("orders:promo_code_list")


@login_required
@promo_code_required
@require_http_methods(["POST"])
def promo_code_send(request, code_id):
    """إرسال كود الخصم لعميل عبر WhatsApp"""
    promo = get_object_or_404(PromoCode, pk=code_id, status="active")

    customer_id = request.POST.get("customer_id")
    if not customer_id:
        return JsonResponse({"success": False, "message": "يجب اختيار العميل"})

    from customers.models import Customer

    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return JsonResponse({"success": False, "message": "العميل غير موجود"})

    if not customer.phone:
        return JsonResponse(
            {"success": False, "message": "العميل ليس لديه رقم هاتف"}
        )

    # تسجيل الإرسال
    promo.sent_to_customer = customer
    promo.sent_at = timezone.now()
    promo.sent_by = request.user
    promo.save(update_fields=["sent_to_customer", "sent_at", "sent_by"])

    # إرسال WhatsApp (إذا كان مفعّلاً)
    try:
        from whatsapp.tasks import send_whatsapp_message

        message = (
            f"🎉 مبروك! حصلت على كود خصم خاص\n\n"
            f"📋 *الكود:* {promo.code}\n"
            f"💰 *الخصم:* {promo.discount_percentage}%\n"
            f"📅 *صالح حتى:* {promo.expires_at.strftime('%Y-%m-%d')}\n\n"
            f"⚠️ الكود صالح للاستخدام مرة واحدة فقط"
        )
        send_whatsapp_message.delay(customer.phone, message)
        logger.info(
            f"WhatsApp promo code sent: {promo.code} to {customer.name} ({customer.phone})"
        )
    except Exception as e:
        logger.warning(f"Failed to send WhatsApp for promo code: {e}")

    return JsonResponse(
        {
            "success": True,
            "message": f"تم إرسال كود الخصم {promo.code} للعميل {customer.name}",
        }
    )


@login_required
@require_http_methods(["POST"])
def promo_code_verify(request):
    """التحقق من كود خصم في الويزارد (AJAX)"""
    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip().upper()
        draft_id = request.session.get("wizard_draft_id")

        if not code:
            return JsonResponse({"success": False, "message": "أدخل كود الخصم"})

        try:
            promo = PromoCode.objects.select_related("issued_by").get(code=code)
        except PromoCode.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "كود الخصم غير صحيح"}
            )

        # تحقق من الحالة
        if promo.status == "used":
            return JsonResponse(
                {"success": False, "message": "كود الخصم مُستخدم مسبقاً"}
            )
        if promo.status == "cancelled":
            return JsonResponse(
                {"success": False, "message": "كود الخصم ملغي"}
            )
        if promo.status == "expired":
            return JsonResponse(
                {"success": False, "message": "كود الخصم منتهي الصلاحية"}
            )

        # تحقق من تاريخ الانتهاء
        if promo.expires_at and timezone.now() > promo.expires_at:
            promo.status = "expired"
            promo.save(update_fields=["status"])
            return JsonResponse(
                {"success": False, "message": "كود الخصم منتهي الصلاحية"}
            )

        return JsonResponse(
            {
                "success": True,
                "code": promo.code,
                "discount_percentage": promo.discount_percentage,
                "issued_by": promo.issued_by.get_full_name()
                if promo.issued_by
                else "غير معروف",
                "expires_at": promo.expires_at.strftime("%Y-%m-%d %H:%M")
                if promo.expires_at
                else None,
                "message": f"كود صالح - خصم {promo.discount_percentage}%",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "طلب غير صالح"}, status=400
        )
    except Exception as e:
        logger.error(f"Error verifying promo code: {e}")
        return JsonResponse(
            {"success": False, "message": "حدث خطأ في التحقق"}, status=500
        )


@login_required
@require_http_methods(["POST"])
def promo_code_apply(request):
    """تطبيق كود خصم على مسودة الطلب (AJAX)"""
    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip().upper()

        from .wizard_models import DraftOrder

        draft_id = request.session.get("wizard_draft_id")
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = (
                DraftOrder.objects.filter(
                    created_by=request.user, is_completed=False
                )
                .order_by("-updated_at")
                .first()
            )

        if not draft:
            return JsonResponse(
                {"success": False, "message": "لم يتم العثور على مسودة نشطة"},
                status=404,
            )

        try:
            promo = PromoCode.objects.get(code=code, status="active")
        except PromoCode.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "كود الخصم غير صالح"}
            )

        if not promo.is_valid:
            return JsonResponse(
                {"success": False, "message": "كود الخصم منتهي الصلاحية أو غير فعّال"}
            )

        # ربط الكود بالمسودة
        draft.promo_code = promo
        draft.save(update_fields=["promo_code"])

        return JsonResponse(
            {
                "success": True,
                "code": promo.code,
                "discount_percentage": promo.discount_percentage,
                "message": f"تم تطبيق كود الخصم - {promo.discount_percentage}%",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "طلب غير صالح"}, status=400
        )
    except Exception as e:
        logger.error(f"Error applying promo code: {e}")
        return JsonResponse(
            {"success": False, "message": "حدث خطأ"}, status=500
        )


@login_required
@require_http_methods(["POST"])
def promo_code_remove(request):
    """إزالة كود الخصم من مسودة الطلب (AJAX)"""
    try:
        from .wizard_models import DraftOrder

        draft_id = request.session.get("wizard_draft_id")
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = (
                DraftOrder.objects.filter(
                    created_by=request.user, is_completed=False
                )
                .order_by("-updated_at")
                .first()
            )

        if not draft:
            return JsonResponse(
                {"success": False, "message": "لم يتم العثور على مسودة نشطة"},
                status=404,
            )

        draft.promo_code = None
        draft.promo_discount_amount = 0
        draft.save(update_fields=["promo_code", "promo_discount_amount"])

        return JsonResponse(
            {"success": True, "message": "تم إزالة كود الخصم"}
        )

    except Exception as e:
        logger.error(f"Error removing promo code: {e}")
        return JsonResponse(
            {"success": False, "message": "حدث خطأ"}, status=500
        )


@login_required
@require_http_methods(["GET"])
def customer_search_api(request):
    """بحث عن عملاء (AJAX) - للاستخدام في إرسال البرومو كود"""
    q = request.GET.get("q", "").strip()
    if len(q) < 3:
        return JsonResponse({"results": []})

    from customers.models import Customer

    customers = Customer.objects.filter(
        Q(name__icontains=q) | Q(phone__icontains=q) | Q(customer_id__icontains=q)
    ).values("id", "name", "phone", "customer_id")[:15]

    return JsonResponse(
        {
            "results": [
                {
                    "id": c["id"],
                    "text": f"{c['name']} ({c['phone'] or 'بدون رقم'})",
                    "name": c["name"],
                    "phone": c["phone"] or "",
                }
                for c in customers
            ]
        }
    )
