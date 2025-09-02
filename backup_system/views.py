"""
واجهات نظام النسخ الاحتياطي والاستعادة
"""
import os
import json
import uuid
from pathlib import Path
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, FileResponse, Http404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator

from .models import BackupJob, RestoreJob, BackupSchedule
from .services import backup_manager
from .forms import BackupForm, RestoreForm, UploadBackupForm


def is_staff_or_superuser(user):
    """التحقق من أن المستخدم موظف أو مدير"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard(request):
    """لوحة تحكم النسخ الاحتياطي"""
    # إحصائيات عامة
    total_backups = BackupJob.objects.count()
    completed_backups = BackupJob.objects.filter(status='completed').count()
    failed_backups = BackupJob.objects.filter(status='failed').count()
    running_backups = BackupJob.objects.filter(status='running').count()
    
    # آخر النسخ الاحتياطية
    recent_backups = BackupJob.objects.order_by('-created_at')[:5]
    
    # آخر عمليات الاستعادة
    recent_restores = RestoreJob.objects.order_by('-created_at')[:5]
    
    # حساب إجمالي حجم النسخ الاحتياطية
    total_size = sum(
        backup.compressed_size for backup in 
        BackupJob.objects.filter(status='completed')
    )
    
    context = {
        'total_backups': total_backups,
        'completed_backups': completed_backups,
        'failed_backups': failed_backups,
        'running_backups': running_backups,
        'recent_backups': recent_backups,
        'recent_restores': recent_restores,
        'total_size': _format_file_size(total_size),
        'title': 'لو��ة تحكم النسخ الاحتياطي',
    }
    
    return render(request, 'backup_system/dashboard.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def backup_list(request):
    """قائمة النسخ الاحتياطية"""
    backups = BackupJob.objects.order_by('-created_at')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status')
    if status_filter:
        backups = backups.filter(status=status_filter)
    
    # فلترة حسب النوع
    type_filter = request.GET.get('type')
    if type_filter:
        backups = backups.filter(backup_type=type_filter)
    
    # تقسيم الصفحات
    paginator = Paginator(backups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'title': 'قائمة النسخ الاحتياطية',
    }
    
    return render(request, 'backup_system/backup_list.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def backup_create(request):
    """إنشاء نسخة احتياطية جديدة"""
    if request.method == 'POST':
        form = BackupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            backup_type = form.cleaned_data['backup_type']
            
            try:
                if backup_type == 'full':
                    job = backup_manager.create_full_backup(
                        name=name,
                        user=request.user,
                        description=description
                    )
                else:
                    # نسخة جزئية - يمكن تطويرها لاحقاً
                    job = backup_manager.create_full_backup(
                        name=name,
                        user=request.user,
                        description=description
                    )
                
                messages.success(request, f'تم بدء إنشاء النسخة الاحتياطية: {name}')
                return redirect('backup_system:backup_detail', pk=job.id)
                
            except Exception as e:
                error_msg = f'خطأ في إنشاء النسخة الاحتياطية: {str(e)}'
                messages.error(request, error_msg)
                form.add_error(None, error_msg)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = BackupForm()
    
    context = {
        'form': form,
        'title': 'إنشاء نسخة احتياطية جديدة',
    }
    
    return render(request, 'backup_system/backup_create.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def backup_detail(request, pk):
    """تفاصيل النسخة الاحتياطية"""
    backup = get_object_or_404(BackupJob, id=pk)
    
    context = {
        'backup': backup,
        'title': f'تفاصيل النسخة الاحتياطية: {backup.name}',
    }
    
    return render(request, 'backup_system/backup_detail.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def backup_download(request, pk):
    """تحميل النسخة الاحتياطية"""
    backup = get_object_or_404(BackupJob, id=pk)
    
    if backup.status != 'completed' or not backup.file_path:
        raise Http404("النسخة الاحتياطية غير متوفرة للتحميل")
    
    if not os.path.exists(backup.file_path):
        raise Http404("ملف النسخة الاحتياطية غير موجود")
    
    response = FileResponse(
        open(backup.file_path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(backup.file_path)
    )
    
    return response


@login_required
@user_passes_test(is_staff_or_superuser)
def backup_delete(request, pk):
    """حذف النسخة الاحتياطية"""
    backup = get_object_or_404(BackupJob, id=pk)
    
    if request.method == 'POST':
        # حذف الملف
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except Exception as e:
                messages.error(request, f'خطأ في حذف الملف: {str(e)}')
                return redirect('backup_system:backup_detail', pk=backup.id)
        
        # حذف السجل
        backup_name = backup.name
        backup.delete()
        
        messages.success(request, f'تم حذف النسخة الاحتياطية: {backup_name}')
        return redirect('backup_system:backup_list')
    
    context = {
        'backup': backup,
        'title': f'حذف النسخة الاحتياطية: {backup.name}',
    }
    
    return render(request, 'backup_system/backup_delete.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def restore_list(request):
    """قائمة عمليات الاستعادة"""
    restores = RestoreJob.objects.order_by('-created_at')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status')
    if status_filter:
        restores = restores.filter(status=status_filter)
    
    # تقسيم الصفحات
    paginator = Paginator(restores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'title': 'قائمة عمليات الاستعادة',
    }
    
    return render(request, 'backup_system/restore_list.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def restore_upload(request):
    """رفع ملف للاستعادة"""
    if request.method == 'POST':
        form = UploadBackupForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['backup_file']
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            clear_existing = form.cleaned_data['clear_existing_data']
            
            file_path = None
            try:
                # إنشاء مجلد الرفع
                upload_dir = Path(settings.MEDIA_ROOT) / 'uploads'
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                # إنشاء اسم ملف فريد لتجنب التضارب
                unique_filename = f"{uuid.uuid4()}_{uploaded_file.name}"
                file_path = upload_dir / unique_filename
                
                # حفظ الملف
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # التحقق من وجود الملف وحجمه
                if not file_path.exists() or file_path.stat().st_size == 0:
                    raise Exception("فشل في حفظ الملف أو الملف فارغ")
                
                # بدء عملية الاستعادة
                job = backup_manager.restore_backup(
                    file_path=str(file_path),
                    user=request.user,
                    name=name,
                    clear_existing=clear_existing,
                    description=description
                )
                
                messages.success(request, f'تم بدء عملية الاستعادة: {name}')
                return redirect('backup_system:restore_detail', pk=job.id)
                
            except Exception as e:
                # حذف الملف المرفوع في حالة الخطأ
                if file_path and file_path.exists():
                    try:
                        file_path.unlink()
                    except:
                        pass
                
                error_msg = f'خطأ في رفع الملف أو بدء عملية الاستعادة: {str(e)}'
                messages.error(request, error_msg)
                form.add_error(None, error_msg)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = UploadBackupForm()
    
    context = {
        'form': form,
        'title': 'رفع ملف للاستعادة',
    }
    
    return render(request, 'backup_system/restore_upload.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def restore_from_backup(request, backup_pk):
    """استعادة من نسخة احتياطية موجودة"""
    backup = get_object_or_404(BackupJob, id=backup_pk)
    
    if backup.status != 'completed' or not backup.file_path:
        messages.error(request, 'النسخة الاحتياطية غير متوفرة للاستعادة')
        return redirect('backup_system:backup_detail', pk=backup.id)
    
    if request.method == 'POST':
        form = RestoreForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            clear_existing = form.cleaned_data['clear_existing_data']
            
            try:
                # بدء عملية الاستعادة
                job = backup_manager.restore_backup(
                    file_path=backup.file_path,
                    user=request.user,
                    name=name,
                    clear_existing=clear_existing,
                    description=description
                )
                
                messages.success(request, f'تم بدء عملية الاستعادة: {name}')
                return redirect('backup_system:restore_detail', pk=job.id)
                
            except Exception as e:
                error_msg = f'خطأ في بدء عملية الاستعادة: {str(e)}'
                messages.error(request, error_msg)
                form.add_error(None, error_msg)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = RestoreForm(initial={
            'name': f'استعادة {backup.name}',
            'description': f'استعادة من النسخة الاحتياطية: {backup.name}'
        })
    
    context = {
        'form': form,
        'backup': backup,
        'title': f'استعادة من: {backup.name}',
    }
    
    return render(request, 'backup_system/restore_from_backup.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def restore_detail(request, pk):
    """تفاصيل عملية الاستعادة"""
    restore = get_object_or_404(RestoreJob, id=pk)
    
    context = {
        'restore': restore,
        'title': f'تفاصيل الاستعادة: {restore.name}',
    }
    
    return render(request, 'backup_system/restore_detail.html', context)


# API Endpoints للحصول على حالة المهام

@csrf_exempt
@login_required
@user_passes_test(is_staff_or_superuser)
def backup_status_api(request, pk):
    """API للحصول على حالة النسخ الاحتياطي"""
    try:
        status = backup_manager.get_backup_status(pk)
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@user_passes_test(is_staff_or_superuser)
def restore_status_api(request, pk):
    """API للحصول على حالة الاستعادة"""
    try:
        status = backup_manager.get_restore_status(pk)
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# دوال مساعدة

def _format_file_size(size_bytes):
    """تنسيق حجم الملف"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"