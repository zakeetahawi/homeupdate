"""
خدمة تصدير التقارير والطباعة
"""
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from datetime import datetime, date
from typing import Dict, List, Optional
import io
import os

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .calendar_service import CalendarService
from .technician_analytics import TechnicianAnalyticsService
from ..models_new import InstallationNew, InstallationTeamNew


class PDFExportService:
    """خدمة تصدير PDF والطباعة"""
    
    @classmethod
    def export_daily_schedule(cls, target_date: date, 
                            branch_name: str = None) -> HttpResponse:
        """تصدير جدول التركيبات اليومي كـ PDF"""
        
        if not REPORTLAB_AVAILABLE:
            raise ImportError("مكتبة ReportLab غير متاحة. يرجى تثبيتها أولاً")
        
        # الحصول على بيانات اليوم
        daily_data = CalendarService.get_daily_schedule(target_date, branch_name)
        
        # إنشاء PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # إعداد الأنماط
        styles = cls._get_arabic_styles()
        story = []
        
        # العنوان الرئيسي
        title = f"جدول التركيبات اليومي - {target_date.strftime('%Y/%m/%d')}"
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 12))
        
        # معلومات إضافية
        info_text = f"""
        التاريخ: {target_date.strftime('%Y/%m/%d')} ({daily_data['day_name']})
        الفرع: {branch_name or 'جميع الفروع'}
        تاريخ الإنشاء: {timezone.now().strftime('%Y/%m/%d %H:%M')}
        """
        story.append(Paragraph(info_text, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # إحصائيات سريعة
        stats = daily_data['statistics']
        stats_data = [
            ['إجمالي التركيبات', str(stats['total_installations'])],
            ['إجمالي الشبابيك', str(stats['total_windows'])],
            ['عدد الفرق', str(stats['teams_count'])],
            ['حالة اليوم', 'مزدحم' if stats['is_overloaded'] else 'عادي'],
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 1*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # جدول التركيبات
        if daily_data['installations_list']:
            story.append(Paragraph("قائمة التركيبات:", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # رؤوس الجدول
            table_data = [
                ['الوقت', 'اسم العميل', 'الهاتف', 'الشبابيك', 'الفريق', 'الحالة', 'الأولوية']
            ]
            
            # بيانات التركيبات
            for installation in daily_data['installations_list']:
                time_str = installation.get('scheduled_time_start', 'غير محدد')
                if time_str and time_str != 'غير محدد':
                    time_str = time_str.strftime('%H:%M') if hasattr(time_str, 'strftime') else str(time_str)
                
                row = [
                    time_str,
                    installation.get('customer_name', ''),
                    installation.get('customer_phone', ''),
                    str(installation.get('windows_count', 0)),
                    installation.get('team_name', 'غير محدد'),
                    cls._get_status_text(installation.get('status', '')),
                    cls._get_priority_text(installation.get('priority', ''))
                ]
                table_data.append(row)
            
            # إنشاء الجدول
            installations_table = Table(table_data, colWidths=[
                0.8*inch, 1.5*inch, 1*inch, 0.7*inch, 1*inch, 0.8*inch, 0.7*inch
            ])
            
            installations_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(installations_table)
        else:
            story.append(Paragraph("لا توجد تركيبات مجدولة في هذا اليوم", styles['Normal']))
        
        # إنشاء PDF
        doc.build(story)
        
        # إعداد الاستجابة
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"daily_schedule_{target_date.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @classmethod
    def export_technician_report(cls, technician_id: int, 
                               start_date: date, end_date: date) -> HttpResponse:
        """تصدير تقرير أداء فني"""
        
        if not REPORTLAB_AVAILABLE:
            raise ImportError("مكتبة ReportLab غير متاحة")
        
        # الحصول على بيانات الفني
        monthly_stats = TechnicianAnalyticsService.get_technician_monthly_stats(
            technician_id, start_date.year, start_date.month
        )
        
        if 'error' in monthly_stats:
            raise ValueError(monthly_stats['error'])
        
        # إنشاء PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = cls._get_arabic_styles()
        story = []
        
        # العنوان
        technician_name = monthly_stats['technician']['name']
        title = f"تقرير أداء الفني - {technician_name}"
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 12))
        
        # معلومات الفني
        tech_info = f"""
        اسم الفني: {technician_name}
        رقم الموظف: {monthly_stats['technician']['employee_id']}
        سنوات الخبرة: {monthly_stats['technician']['experience_years']} سنة
        الفترة: {monthly_stats['period']['month_name']} {monthly_stats['period']['year']}
        """
        story.append(Paragraph(tech_info, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # إحصائيات الأداء
        summary = monthly_stats['summary']
        performance_data = [
            ['المؤشر', 'القيمة'],
            ['إجمالي التركيبات', str(summary['total_installations'])],
            ['إجمالي الشبابيك', str(summary['total_windows'])],
            ['متوسط الشبابيك اليومي', f"{summary['avg_daily_windows']:.1f}"],
            ['استغلال السعة', f"{summary['monthly_capacity_utilization']:.1f}%"],
            ['تقييم الأداء', summary['performance_rating']['rating']],
        ]
        
        performance_table = Table(performance_data, colWidths=[2*inch, 1.5*inch])
        performance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(performance_table)
        
        # إنشاء PDF
        doc.build(story)
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"technician_report_{technician_id}_{start_date.strftime('%Y%m')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @classmethod
    def export_monthly_summary(cls, year: int, month: int, 
                             branch_name: str = None) -> HttpResponse:
        """تصدير ملخص شهري للتركيبات"""
        
        if not REPORTLAB_AVAILABLE:
            raise ImportError("مكتبة ReportLab غير متاحة")
        
        # الحصول على بيانات الشهر
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timezone.timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timezone.timedelta(days=1)
        
        # استعلام التركيبات
        installations = InstallationNew.objects.filter(
            scheduled_date__range=[start_date, end_date]
        )
        
        if branch_name:
            installations = installations.filter(branch_name=branch_name)
        
        # إنشاء PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = cls._get_arabic_styles()
        story = []
        
        # العنوان
        import calendar
        month_name = calendar.month_name[month]
        title = f"التقرير الشهري للتركيبات - {month_name} {year}"
        story.append(Paragraph(title, styles['Title']))
        story.append(Spacer(1, 12))
        
        # الإحصائيات العامة
        total_installations = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        completed_installations = installations.filter(status='completed').count()
        
        summary_data = [
            ['المؤشر', 'القيمة'],
            ['إجمالي التركيبات', str(total_installations)],
            ['إجمالي الشبابيك', str(total_windows)],
            ['التركيبات المكتملة', str(completed_installations)],
            ['معدل الإكمال', f"{(completed_installations/total_installations*100):.1f}%" if total_installations > 0 else "0%"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        
        # إنشاء PDF
        doc.build(story)
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"monthly_summary_{year}_{month:02d}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @classmethod
    def _get_arabic_styles(cls):
        """الحصول على أنماط النص العربي"""
        styles = getSampleStyleSheet()
        
        # إضافة خط عربي إذا كان متاحاً
        try:
            # يمكن إضافة خط عربي هنا
            pass
        except:
            pass
        
        # تخصيص الأنماط
        styles.add(ParagraphStyle(
            name='ArabicTitle',
            parent=styles['Title'],
            alignment=1,  # وسط
            fontSize=18,
            spaceAfter=12
        ))
        
        return styles
    
    @classmethod
    def _get_status_text(cls, status: str) -> str:
        """تحويل حالة التركيب إلى نص عربي"""
        status_map = {
            'pending': 'قيد الانتظار',
            'ready': 'جاهز',
            'scheduled': 'مجدول',
            'in_progress': 'جاري التنفيذ',
            'completed': 'مكتمل',
            'cancelled': 'ملغي',
        }
        return status_map.get(status, status)
    
    @classmethod
    def _get_priority_text(cls, priority: str) -> str:
        """تحويل أولوية التركيب إلى نص عربي"""
        priority_map = {
            'urgent': 'عاجل',
            'high': 'عالية',
            'normal': 'عادية',
            'low': 'منخفضة',
        }
        return priority_map.get(priority, priority)


class PrintService:
    """خدمة الطباعة"""
    
    @classmethod
    def generate_printable_html(cls, target_date: date, 
                              branch_name: str = None) -> str:
        """إنشاء HTML قابل للطباعة"""
        
        # الحصول على بيانات اليوم
        daily_data = CalendarService.get_printable_schedule(target_date, branch_name)
        
        # قالب HTML للطباعة
        html_template = """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>جدول التركيبات اليومي</title>
            <style>
                @media print {
                    body { margin: 0; }
                    .no-print { display: none; }
                }
                
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    direction: rtl;
                }
                
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 15px;
                }
                
                .header h1 {
                    margin: 0;
                    color: #333;
                }
                
                .info {
                    margin-bottom: 20px;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                }
                
                .stats {
                    display: flex;
                    justify-content: space-around;
                    margin-bottom: 20px;
                    background: #e9ecef;
                    padding: 15px;
                    border-radius: 5px;
                }
                
                .stat-item {
                    text-align: center;
                }
                
                .stat-number {
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #007bff;
                }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }
                
                th {
                    background-color: #f8f9fa;
                    font-weight: bold;
                }
                
                .priority-urgent { color: #dc3545; font-weight: bold; }
                .priority-high { color: #fd7e14; font-weight: bold; }
                .priority-normal { color: #28a745; }
                .priority-low { color: #6c757d; }
                
                .footer {
                    margin-top: 30px;
                    text-align: center;
                    font-size: 0.9em;
                    color: #6c757d;
                    border-top: 1px solid #ddd;
                    padding-top: 15px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ title }}</h1>
                <p>{{ day_name }} - {{ branch }}</p>
            </div>
            
            <div class="info">
                <strong>تاريخ الإنشاء:</strong> {{ generated_at }}
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number">{{ total_installations }}</div>
                    <div>إجمالي التركيبات</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ total_windows }}</div>
                    <div>إجمالي الشبابيك</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{{ teams_count }}</div>
                    <div>عدد الفرق</div>
                </div>
            </div>
            
            {% if installations %}
            <table>
                <thead>
                    <tr>
                        <th>الوقت</th>
                        <th>اسم العميل</th>
                        <th>رقم الهاتف</th>
                        <th>العنوان</th>
                        <th>الشبابيك</th>
                        <th>الفريق</th>
                        <th>الفنيين</th>
                        <th>الحالة</th>
                        <th>الأولوية</th>
                        <th>ملاحظات</th>
                    </tr>
                </thead>
                <tbody>
                    {% for installation in installations %}
                    <tr>
                        <td>{{ installation.time }}</td>
                        <td>{{ installation.customer_name }}</td>
                        <td>{{ installation.phone }}</td>
                        <td>{{ installation.address }}</td>
                        <td>{{ installation.windows }}</td>
                        <td>{{ installation.team }}</td>
                        <td>{{ installation.technicians }}</td>
                        <td>{{ installation.status }}</td>
                        <td class="priority-{{ installation.priority }}">{{ installation.priority }}</td>
                        <td>{{ installation.notes }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div style="text-align: center; padding: 50px; color: #6c757d;">
                <h3>لا توجد تركيبات مجدولة في هذا اليوم</h3>
            </div>
            {% endif %}
            
            <div class="footer">
                تم إنشاء هذا التقرير بواسطة نظام إدارة التركيبات
            </div>
        </body>
        </html>
        """
        
        # استبدال المتغيرات في القالب
        from django.template import Template, Context
        template = Template(html_template)
        context = Context(daily_data)
        
        return template.render(context)
