"""
Views للتعامل مع عمليات الاستيراد من Google Sheets
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from .forms import ImportSelectionForm
from .import_service import ImportService
from .models import ImportLog

def is_staff_or_superuser(user):
    """التحقق من أن المستخدم موظف أو مشرف"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_staff_or_superuser)
def import_dashboard(request):
    """الصفحة الرئيسية للاستيراد"""
    try:
        import_service = ImportService()
        available_sheets = import_service.get_available_sheets()

        context = {
            'title': 'استيراد البيانات',
            'available_sheets': available_sheets,
        }

    except Exception as e:
        messages.error(request, f'خطأ في تحميل البيانات: {str(e)}')
        context = {
            'title': 'استيراد البيانات',
            'available_sheets': [],
        }

    return render(request, 'odoo_db_manager/import_dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def import_select(request):
    """اختيار البيانات للاستيراد"""
    if request.method == 'POST':
        form = ImportSelectionForm(request.POST)
        if form.is_valid():
            # حفظ الاختيارات في الجلسة
            request.session['import_selection'] = {
                'sheet_name': form.cleaned_data['sheet_name'],
                'import_all': form.cleaned_data['import_all'],
                'page_start': form.cleaned_data.get('page_start'),
                'page_end': form.cleaned_data.get('page_end'),
                'clear_existing': form.cleaned_data['clear_existing'],
            }
            return redirect('odoo_db_manager:import_preview')
    else:
        # تعيين الجدول المحدد من الصفحة الرئيسية
        initial = {}
        if 'sheet' in request.GET:
            initial['sheet_name'] = request.GET['sheet']
        form = ImportSelectionForm(initial=initial)

    context = {
        'title': 'اختيار البيانات للاستيراد',
        'form': form,
    }

    return render(request, 'odoo_db_manager/import_select.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def import_preview(request):
    """معاينة البيانات قبل الاستيراد"""
    # التحقق من وجود اختيارات في الجلسة
    if 'import_selection' not in request.session:
        messages.error(request, 'يجب اختيار البيانات أولاً')
        return redirect('odoo_db_manager:import_select')

    selection = request.session['import_selection']
    import_service = ImportService()

    try:
        # جلب عينة من البيانات للمعاينة
        page_range = None
        if not selection['import_all']:
            page_range = {
                'start': selection['page_start'],
                'end': min(selection['page_start'] + 10, selection['page_end'])
            }

        preview_data = import_service.get_sheet_data(
            selection['sheet_name'],
            page_range=page_range
        )

        if not preview_data:
            messages.warning(request, 'لا توجد بيانات للمعاينة')
            return redirect('odoo_db_manager:import_select')

        context = {
            'title': 'معاينة البيانات',
            'sheet_name': selection['sheet_name'],
            'headers': list(preview_data[0].keys()) if preview_data else [],
            'preview_data': [list(row.values()) for row in preview_data],
            'total_records': len(preview_data),
            'page_range': {
                'start': selection['page_start'],
                'end': selection['page_end']
            } if not selection['import_all'] else None,
            'clear_existing': selection['clear_existing'],
        }

        return render(request, 'odoo_db_manager/import_preview.html', context)

    except Exception as e:
        messages.error(request, f'خطأ في معاينة البيانات: {str(e)}')
        return redirect('odoo_db_manager:import_select')

@login_required
@user_passes_test(is_staff_or_superuser)
def import_execute(request):
    """تنفيذ عملية الاستيراد"""
    if request.method != 'POST':
        return redirect('odoo_db_manager:import_select')

    # التحقق من وجود اختيارات في الجلسة
    if 'import_selection' not in request.session:
        messages.error(request, 'يجب اختيار البيانات أولاً')
        return redirect('odoo_db_manager:import_select')

    selection = request.session['import_selection']
    import_service = ImportService()

    try:
        # جلب البيانات
        page_range = None
        if not selection['import_all']:
            page_range = {
                'start': selection['page_start'],
                'end': selection['page_end']
            }

        data = import_service.get_sheet_data(
            selection['sheet_name'],
            page_range=page_range
        )

        if not data:
            raise ValueError('لا توجد بيانات للاستيراد')

        # تنفيذ الاستيراد
        result = import_service.import_data(
            selection['sheet_name'],
            data,
            selection['clear_existing']
        )

        # إنشاء سجل الاستيراد
        import_log = ImportLog.objects.create(
            user=request.user,
            sheet_name=selection['sheet_name'],
            total_records=len(data),
            imported_records=result['imported'],
            updated_records=result['updated'],
            failed_records=result['failed'],
            clear_existing=selection['clear_existing'],
            status='failed' if result['failed'] > 0 else 'success',
            error_details='\n'.join(result['errors']) if result['errors'] else ''
        )

        # حذف الاختيارات من الجلسة
        del request.session['import_selection']

        # إعادة التوجيه إلى صفحة النتائج
        return redirect('odoo_db_manager:import_result', log_id=import_log.id)

    except Exception as e:
        messages.error(request, f'خطأ في تنفيذ الاستيراد: {str(e)}')
        return redirect('odoo_db_manager:import_select')

@login_required
@user_passes_test(is_staff_or_superuser)
def import_result(request, log_id):
    """عرض نتائج الاستيراد"""
    try:
        import_log = ImportLog.objects.get(id=log_id)
        context = {
            'title': 'نتائج الاستيراد',
            'log': import_log,
        }
        return render(request, 'odoo_db_manager/import_result.html', context)

    except ImportLog.DoesNotExist:
        messages.error(request, 'سجل الاستيراد غير موجود')
        return redirect('odoo_db_manager:import_dashboard')

@login_required
@user_passes_test(is_staff_or_superuser)
def import_progress(request):
    """تحديث مؤشر التقدم"""
    if request.is_ajax():
        if 'import_progress' in request.session:
            progress = request.session['import_progress']
            return JsonResponse({'progress': progress})
    return JsonResponse({'progress': 0})
