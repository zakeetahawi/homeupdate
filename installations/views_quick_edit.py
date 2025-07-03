"""
عروض التعديل السريع للتركيبات
"""
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime

from .models_new import InstallationNew, InstallationTeamNew
from accounts.mixins import DepartmentRequiredMixin


@login_required
def quick_edit_table_view(request):
    """عرض جدول التعديل السريع"""
    
    # الحصول على المرشحات
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    branch_filter = request.GET.get('branch', '')
    date_filter = request.GET.get('date', '')
    
    # بناء الاستعلام
    installations = InstallationNew.objects.all().select_related('team', 'order')
    
    # تطبيق المرشحات
    if search:
        installations = installations.filter(
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search) |
            Q(id__icontains=search)
        )
    
    if status_filter:
        installations = installations.filter(status=status_filter)
    
    if priority_filter:
        installations = installations.filter(priority=priority_filter)
    
    if branch_filter:
        installations = installations.filter(branch_name=branch_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            installations = installations.filter(scheduled_date=filter_date)
        except ValueError:
            pass
    
    # ترتيب النتائج
    installations = installations.order_by('-created_at')
    
    # التصفح
    paginator = Paginator(installations, 50)  # 50 تركيب في الصفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # الحصول على الفرق المتاحة
    teams = InstallationTeamNew.objects.filter(is_active=True).order_by('name')
    
    # الحصول على قائمة الفروع
    branches = InstallationNew.objects.values_list('branch_name', flat=True).distinct()
    
    # حساب الإحصائيات
    stats = {
        'pending': installations.filter(status='pending').count(),
        'ready': installations.filter(status='ready').count(),
        'scheduled': installations.filter(status='scheduled').count(),
        'in_progress': installations.filter(status='in_progress').count(),
        'completed': installations.filter(status='completed').count(),
        'cancelled': installations.filter(status='cancelled').count(),
    }
    
    context = {
        'installations': page_obj,
        'teams': teams,
        'branches': branches,
        'stats': stats,
        'search': search,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'branch_filter': branch_filter,
        'date_filter': date_filter,
    }
    
    return render(request, 'installations/quick_edit_table.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def quick_update_installation(request, installation_id):
    """تحديث سريع لتركيب واحد"""
    
    try:
        installation = get_object_or_404(InstallationNew, id=installation_id)
        
        # التحقق من الصلاحيات
        if not request.user.has_perm('installations.change_installation'):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية لتعديل التركيبات'
            })
        
        # قراءة البيانات
        data = json.loads(request.body)
        
        # تحديث الحقول
        if 'windows_count' in data:
            installation.windows_count = max(1, int(data['windows_count']))
        
        if 'status' in data:
            installation.status = data['status']
        
        if 'priority' in data:
            installation.priority = data['priority']
        
        if 'team' in data and data['team']:
            try:
                team = InstallationTeamNew.objects.get(id=data['team'])
                installation.team = team
            except InstallationTeamNew.DoesNotExist:
                pass
        elif 'team' in data and not data['team']:
            installation.team = None
        
        if 'scheduled_date' in data and data['scheduled_date']:
            try:
                installation.scheduled_date = datetime.strptime(
                    data['scheduled_date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                pass
        
        if 'scheduled_time_start' in data and data['scheduled_time_start']:
            try:
                installation.scheduled_time_start = datetime.strptime(
                    data['scheduled_time_start'], '%H:%M'
                ).time()
            except ValueError:
                pass
        
        if 'scheduled_time_end' in data and data['scheduled_time_end']:
            try:
                installation.scheduled_time_end = datetime.strptime(
                    data['scheduled_time_end'], '%H:%M'
                ).time()
            except ValueError:
                pass
        
        if 'is_ready_for_installation' in data:
            installation.is_ready_for_installation = bool(data['is_ready_for_installation'])
        
        # تحديث معلومات التعديل
        installation.updated_by = request.user
        
        # حفظ التغييرات
        installation.save()
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديث التركيب بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def bulk_update_installations(request):
    """تحديث مجمع للتركيبات"""
    
    try:
        # التحقق من الصلاحيات
        if not request.user.has_perm('installations.change_installation'):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية لتعديل التركيبات'
            })
        
        # قراءة البيانات
        data = json.loads(request.body)
        installations_data = data.get('installations', [])
        
        updated_count = 0
        
        for inst_data in installations_data:
            try:
                installation = InstallationNew.objects.get(id=inst_data['id'])
                
                # تحديث الحقول (نفس المنطق من quick_update_installation)
                if 'windows_count' in inst_data:
                    installation.windows_count = max(1, int(inst_data['windows_count']))
                
                if 'status' in inst_data:
                    installation.status = inst_data['status']
                
                if 'priority' in inst_data:
                    installation.priority = inst_data['priority']
                
                if 'team' in inst_data and inst_data['team']:
                    try:
                        team = InstallationTeamNew.objects.get(id=inst_data['team'])
                        installation.team = team
                    except InstallationTeamNew.DoesNotExist:
                        pass
                elif 'team' in inst_data and not inst_data['team']:
                    installation.team = None
                
                if 'scheduled_date' in inst_data and inst_data['scheduled_date']:
                    try:
                        installation.scheduled_date = datetime.strptime(
                            inst_data['scheduled_date'], '%Y-%m-%d'
                        ).date()
                    except ValueError:
                        pass
                
                if 'scheduled_time_start' in inst_data and inst_data['scheduled_time_start']:
                    try:
                        installation.scheduled_time_start = datetime.strptime(
                            inst_data['scheduled_time_start'], '%H:%M'
                        ).time()
                    except ValueError:
                        pass
                
                if 'scheduled_time_end' in inst_data and inst_data['scheduled_time_end']:
                    try:
                        installation.scheduled_time_end = datetime.strptime(
                            inst_data['scheduled_time_end'], '%H:%M'
                        ).time()
                    except ValueError:
                        pass
                
                if 'is_ready_for_installation' in inst_data:
                    installation.is_ready_for_installation = bool(inst_data['is_ready_for_installation'])
                
                # تحديث معلومات التعديل
                installation.updated_by = request.user
                
                # حفظ التغييرات
                installation.save()
                updated_count += 1
                
            except InstallationNew.DoesNotExist:
                continue
            except Exception as e:
                continue
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'تم تحديث {updated_count} تركيب بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def bulk_action_installations(request):
    """تطبيق إجراء مجمع على التركيبات"""
    
    try:
        # التحقق من الصلاحيات
        if not request.user.has_perm('installations.change_installation'):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية لتعديل التركيبات'
            })
        
        # قراءة البيانات
        data = json.loads(request.body)
        action = data.get('action')
        value = data.get('value')
        ids = data.get('ids', [])
        
        if not action or not ids:
            return JsonResponse({
                'success': False,
                'error': 'بيانات غير مكتملة'
            })
        
        # الحصول على التركيبات
        installations = InstallationNew.objects.filter(id__in=ids)
        updated_count = 0
        
        for installation in installations:
            try:
                if action == 'update_status':
                    installation.status = value
                elif action == 'update_priority':
                    installation.priority = value
                elif action == 'assign_team':
                    if value:
                        try:
                            team = InstallationTeamNew.objects.get(id=value)
                            installation.team = team
                        except InstallationTeamNew.DoesNotExist:
                            continue
                    else:
                        installation.team = None
                elif action == 'schedule_date':
                    try:
                        installation.scheduled_date = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                
                # تحديث معلومات التعديل
                installation.updated_by = request.user
                installation.save()
                updated_count += 1
                
            except Exception as e:
                continue
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'تم تطبيق الإجراء على {updated_count} تركيب'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
