import csv
from datetime import datetime
from io import BytesIO

import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone

from ..models import Complaint


def export_complaints_to_csv(queryset=None, selected_ids=None):
    """تصدير الشكاوى إلى ملف CSV"""
    if selected_ids:
        queryset = Complaint.objects.filter(id__in=selected_ids)
    elif queryset is None:
        queryset = Complaint.objects.all()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="complaints-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv"'
    )

    # إضافة BOM لدعم الحروف العربية
    response.write("\ufeff")

    writer = csv.writer(response)
    headers = [
        "رقم الشكوى",
        "العميل",
        "نوع الشكوى",
        "الموضوع",
        "الحالة",
        "الأولوية",
        "المسؤول",
        "القسم",
        "تاريخ الإنشاء",
        "الموعد النهائي",
        "تاريخ الحل",
        "تقييم العميل",
        "تعليق العميل",
        "الطلب المرتبط",
        "الفرع",
    ]
    writer.writerow(headers)

    for complaint in queryset.select_related(
        "customer",
        "complaint_type",
        "assigned_to",
        "assigned_department",
        "related_order",
        "branch",
    ):
        row = [
            complaint.complaint_number,
            complaint.customer.name,
            complaint.complaint_type.name,
            complaint.title,
            complaint.get_status_display(),
            complaint.get_priority_display(),
            (
                complaint.assigned_to.get_full_name()
                if complaint.assigned_to
                else "غير معين"
            ),
            (
                complaint.assigned_department.name
                if complaint.assigned_department
                else "غير محدد"
            ),
            timezone.localtime(complaint.created_at).strftime("%Y-%m-%d %H:%M"),
            timezone.localtime(complaint.deadline).strftime("%Y-%m-%d %H:%M"),
            (
                timezone.localtime(complaint.resolved_at).strftime("%Y-%m-%d %H:%M")
                if complaint.resolved_at
                else "لم يتم الحل"
            ),
            (
                complaint.get_customer_rating_display()
                if complaint.customer_rating
                else "لم يتم التقييم"
            ),
            complaint.customer_feedback or "",
            (
                complaint.related_order.order_number
                if complaint.related_order
                else "لا يوجد"
            ),
            complaint.branch.name if complaint.branch else "غير محدد",
        ]
        writer.writerow(row)

    return response


def export_complaints_to_excel(queryset=None, selected_ids=None):
    """تصدير الشكاوى إلى ملف Excel"""
    if selected_ids:
        queryset = Complaint.objects.filter(id__in=selected_ids)
    elif queryset is None:
        queryset = Complaint.objects.all()

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("الشكاوى")

    # تنسيق العناوين
    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#4B0082",
            "font_color": "white",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        }
    )

    # تنسيق البيانات
    data_format = workbook.add_format(
        {"align": "center", "valign": "vcenter", "text_wrap": True, "border": 1}
    )

    # تنسيق التواريخ
    date_format = workbook.add_format(
        {
            "num_format": "yyyy-mm-dd hh:mm",
            "align": "center",
            "valign": "vcenter",
            "border": 1,
        }
    )

    # العناوين
    headers = [
        "رقم الشكوى",
        "العميل",
        "نوع الشكوى",
        "الموضوع",
        "الوصف",
        "الحالة",
        "الأولوية",
        "المسؤول",
        "القسم",
        "تاريخ الإنشاء",
        "الموعد النهائي",
        "تاريخ الحل",
        "مدة الحل (ساعات)",
        "تقييم العميل",
        "تعليق العميل",
        "الطلب المرتبط",
        "الفرع",
    ]

    # كتابة العناوين
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    # ضبط عرض الأعمدة
    worksheet.set_column("A:A", 15)  # رقم الشكوى
    worksheet.set_column("B:B", 20)  # العميل
    worksheet.set_column("C:C", 20)  # نوع الشكوى
    worksheet.set_column("D:D", 30)  # الموضوع
    worksheet.set_column("E:E", 40)  # الوصف
    worksheet.set_column("F:H", 15)  # الحالة، الأولوية، المسؤول
    worksheet.set_column("I:I", 20)  # القسم
    worksheet.set_column("J:L", 20)  # التواريخ
    worksheet.set_column("M:M", 15)  # مدة الحل
    worksheet.set_column("N:O", 25)  # تقييم وتعليق العميل
    worksheet.set_column("P:Q", 15)  # الطلب والفرع

    # كتابة البيانات
    for row, complaint in enumerate(
        queryset.select_related(
            "customer",
            "complaint_type",
            "assigned_to",
            "assigned_department",
            "related_order",
            "branch",
        ),
        start=1,
    ):
        resolution_time = None
        if complaint.resolved_at and complaint.created_at:
            delta = complaint.resolved_at - complaint.created_at
            resolution_time = delta.total_seconds() / 3600  # تحويل إلى ساعات

        data = [
            complaint.complaint_number,
            complaint.customer.name,
            complaint.complaint_type.name,
            complaint.title,
            complaint.description,
            complaint.get_status_display(),
            complaint.get_priority_display(),
            (
                complaint.assigned_to.get_full_name()
                if complaint.assigned_to
                else "غير معين"
            ),
            (
                complaint.assigned_department.name
                if complaint.assigned_department
                else "غير محدد"
            ),
            complaint.created_at,
            complaint.deadline,
            complaint.resolved_at if complaint.resolved_at else None,
            round(resolution_time, 2) if resolution_time else None,
            (
                complaint.get_customer_rating_display()
                if complaint.customer_rating
                else "لم يتم التقييم"
            ),
            complaint.customer_feedback or "",
            (
                complaint.related_order.order_number
                if complaint.related_order
                else "لا يوجد"
            ),
            complaint.branch.name if complaint.branch else "غير محدد",
        ]

        for col, value in enumerate(data):
            if isinstance(value, datetime):
                worksheet.write_datetime(row, col, value, date_format)
            else:
                worksheet.write(row, col, value, data_format)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="complaints-{timezone.now().strftime("%Y%m%d-%H%M%S")}.xlsx"'
    )

    return response
