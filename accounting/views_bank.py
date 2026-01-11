"""
Views للحسابات البنكية و QR System
Bank Accounts Views & QR System
"""

import base64
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import BankAccount


def bank_qr_view(request, unique_code):
    """
    عرض صفحة QR للحساب البنكي (للاختبار المحلي)
    """
    bank = get_object_or_404(BankAccount, unique_code=unique_code, is_active=True)

    context = {
        "bank": bank,
        "site_name": getattr(settings, "SITE_NAME", "الخواجة"),
        "main_site_url": getattr(settings, "MAIN_SITE_URL", "https://elkhawaga.com"),
    }

    return render(request, "accounting/bank_qr.html", context)


def all_banks_qr_view(request):
    """
    عرض جميع الحسابات البنكية النشطة
    """
    banks = BankAccount.objects.filter(is_active=True, show_in_qr=True).order_by(
        "display_order", "bank_name"
    )

    context = {
        "banks": banks,
        "count": banks.count(),
        "site_name": getattr(settings, "SITE_NAME", "الخواجة"),
        "main_site_url": getattr(settings, "MAIN_SITE_URL", "https://elkhawaga.com"),
    }

    return render(request, "accounting/all_banks_qr.html", context)


def export_bank_qr_pdf(request):
    """
    تصدير QR Codes للحسابات البنكية كـ PDF
    """
    # الحصول على الحسابات المطلوبة
    codes = request.GET.get("codes", "").split(",")

    if codes and codes[0]:
        banks = BankAccount.objects.filter(unique_code__in=codes, is_active=True)
    else:
        banks = BankAccount.objects.filter(is_active=True).order_by("display_order")

    if not banks.exists():
        return HttpResponse("لا توجد حسابات بنكية لتصديرها", status=404)

    # إنشاء PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # تسجيل خط عربي
    try:
        font_path = settings.BASE_DIR / "static" / "fonts" / "DejaVuSans.ttf"
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("Arabic", str(font_path)))
            pdf.setFont("Arabic", 12)
        else:
            pdf.setFont("Helvetica", 12)
    except:
        pdf.setFont("Helvetica", 12)

    y_position = height - 2 * cm
    page_number = 1

    for bank in banks:
        # التأكد من وجود QR
        if not bank.qr_code_base64:
            bank.generate_qr_code()

        # عنوان الصفحة
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(3 * cm, y_position, f"Bank Account QR - {bank.bank_name_en}")
        y_position -= 1 * cm

        # معلومات البنك
        try:
            pdf.setFont("Arabic", 12)
        except:
            pdf.setFont("Helvetica", 12)

        pdf.drawString(3 * cm, y_position, f"Bank: {bank.bank_name}")
        y_position -= 0.7 * cm

        pdf.drawString(3 * cm, y_position, f"Account Number: {bank.account_number}")
        y_position -= 0.7 * cm

        if bank.iban:
            pdf.drawString(3 * cm, y_position, f"IBAN: {bank.iban}")
            y_position -= 0.7 * cm

        if bank.swift_code:
            pdf.drawString(3 * cm, y_position, f"SWIFT: {bank.swift_code}")
            y_position -= 0.7 * cm

        y_position -= 0.5 * cm

        # QR Code
        if bank.qr_code_base64:
            try:
                # استخراج base64 من data URL
                qr_data = bank.qr_code_base64.split(",")[1]
                qr_image = BytesIO(base64.b64decode(qr_data))

                # رسم QR Code
                qr_size = 6 * cm
                x_center = (width - qr_size) / 2
                pdf.drawImage(
                    qr_image,
                    x_center,
                    y_position - qr_size,
                    width=qr_size,
                    height=qr_size,
                )
                y_position -= qr_size + 1 * cm
            except Exception as e:
                pdf.drawString(3 * cm, y_position, f"Error loading QR: {str(e)}")
                y_position -= 1 * cm

        # رابط QR
        pdf.setFont("Helvetica", 10)
        qr_url = bank.get_qr_url()
        pdf.drawString(3 * cm, y_position, f"QR URL: {qr_url}")
        y_position -= 1.5 * cm

        # خط فاصل
        pdf.line(2 * cm, y_position, width - 2 * cm, y_position)
        y_position -= 1 * cm

        # صفحة جديدة إذا لزم الأمر
        if y_position < 5 * cm and bank != banks.last():
            pdf.showPage()
            page_number += 1
            y_position = height - 2 * cm
            try:
                pdf.setFont("Arabic", 12)
            except:
                pdf.setFont("Helvetica", 12)

    # إنهاء PDF
    pdf.save()
    buffer.seek(0)

    # إرجاع الملف
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    filename = f'bank_accounts_qr_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


def bank_accounts_api(request):
    """
    API للحصول على جميع الحسابات البنكية النشطة
    """
    banks = BankAccount.objects.filter(is_active=True).order_by("display_order")

    data = {
        "success": True,
        "count": banks.count(),
        "accounts": [
            {
                "code": bank.unique_code,
                "bank_name": bank.bank_name,
                "bank_name_en": bank.bank_name_en,
                "account_number": bank.account_number,
                "iban": bank.iban,
                "swift_code": bank.swift_code,
                "branch": bank.branch,
                "account_holder": bank.account_holder,
                "currency": bank.currency,
                "is_primary": bank.is_primary,
                "qr_url": bank.get_qr_url(),
            }
            for bank in banks
        ],
    }

    return JsonResponse(data)
