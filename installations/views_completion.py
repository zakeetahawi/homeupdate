"""
عروض إكمال التركيبات
"""
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime

from .models_new import InstallationNew
from .services.order_completion import OrderCompletionService


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def complete_installation(request, installation_id):
    """إكمال التركيب"""
    
    try:
        # قراءة البيانات
        data = json.loads(request.body)
        
        # بيانات الإكمال
        completion_data = {
            'quality_rating': data.get('quality_rating'),
            'customer_satisfaction': data.get('customer_satisfaction'),
            'completion_notes': data.get('completion_notes', ''),
            'issues_encountered': data.get('issues_encountered', ''),
            'customer_feedback': data.get('customer_feedback', ''),
            'photos_taken': data.get('photos_taken', False),
            'warranty_explained': data.get('warranty_explained', False),
            'cleanup_completed': data.get('cleanup_completed', False),
        }
        
        # إكمال التركيب
        result = OrderCompletionService.complete_installation(
            installation_id=installation_id,
            completed_by=request.user,
            completion_data=completion_data
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات JSON غير صحيحة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def cancel_installation(request, installation_id):
    """إلغاء التركيب"""
    
    try:
        data = json.loads(request.body)
        cancellation_reason = data.get('reason', '')
        
        result = OrderCompletionService.cancel_installation(
            installation_id=installation_id,
            cancelled_by=request.user,
            cancellation_reason=cancellation_reason
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات JSON غير صحيحة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def reschedule_installation(request, installation_id):
    """إعادة جدولة التركيب"""
    
    try:
        data = json.loads(request.body)
        
        # تحويل التاريخ والوقت
        new_date_str = data.get('new_date')
        new_time_start_str = data.get('new_time_start')
        new_time_end_str = data.get('new_time_end')
        reason = data.get('reason', '')
        
        if not new_date_str:
            return JsonResponse({
                'success': False,
                'error': 'التاريخ الجديد مطلوب'
            })
        
        try:
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'تنسيق التاريخ غير صحيح'
            })
        
        new_time_start = None
        new_time_end = None
        
        if new_time_start_str:
            try:
                new_time_start = datetime.strptime(new_time_start_str, '%H:%M').time()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'تنسيق وقت البدء غير صحيح'
                })
        
        if new_time_end_str:
            try:
                new_time_end = datetime.strptime(new_time_end_str, '%H:%M').time()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'تنسيق وقت الانتهاء غير صحيح'
                })
        
        result = OrderCompletionService.reschedule_installation(
            installation_id=installation_id,
            new_date=new_date,
            new_time_start=new_time_start,
            new_time_end=new_time_end,
            rescheduled_by=request.user,
            reason=reason
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات JSON غير صحيحة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["GET"])
def installation_completion_form(request, installation_id):
    """نموذج إكمال التركيب"""
    
    try:
        installation = get_object_or_404(InstallationNew, id=installation_id)
        
        # التحقق من إمكانية الإكمال
        if installation.status not in ['scheduled', 'in_progress']:
            return render(request, 'installations/error.html', {
                'error_message': f'لا يمكن إكمال التركيب في الحالة الحالية: {installation.get_status_display()}'
            })
        
        context = {
            'installation': installation,
            'quality_choices': InstallationNew.QUALITY_CHOICES,
        }
        
        return render(request, 'installations/completion_form.html', context)
        
    except Exception as e:
        return render(request, 'installations/error.html', {
            'error_message': str(e)
        })


@login_required
@require_http_methods(["GET"])
def installation_completion_summary(request):
    """ملخص الإكمالات"""
    
    try:
        # الحصول على المعاملات
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        date_range = None
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                date_range = (start_date, end_date)
            except ValueError:
                pass
        
        # الحصول على ملخص الإكمالات
        summary = OrderCompletionService.get_completion_summary(date_range)
        
        return JsonResponse({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def bulk_complete_installations(request):
    """إكمال مجمع للتركيبات"""
    
    try:
        data = json.loads(request.body)
        installation_ids = data.get('installation_ids', [])
        completion_data = data.get('completion_data', {})
        
        if not installation_ids:
            return JsonResponse({
                'success': False,
                'error': 'لا توجد تركيبات محددة'
            })
        
        results = []
        success_count = 0
        
        for installation_id in installation_ids:
            try:
                result = OrderCompletionService.complete_installation(
                    installation_id=installation_id,
                    completed_by=request.user,
                    completion_data=completion_data
                )
                
                results.append({
                    'installation_id': installation_id,
                    'success': result['success'],
                    'message': result.get('message', result.get('error', ''))
                })
                
                if result['success']:
                    success_count += 1
                    
            except Exception as e:
                results.append({
                    'installation_id': installation_id,
                    'success': False,
                    'message': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'message': f'تم إكمال {success_count} من أصل {len(installation_ids)} تركيب',
            'success_count': success_count,
            'total_count': len(installation_ids),
            'results': results
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات JSON غير صحيحة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["GET"])
def installation_status_history(request, installation_id):
    """تاريخ حالات التركيب"""
    
    try:
        installation = get_object_or_404(InstallationNew, id=installation_id)
        
        # يمكن إضافة نموذج لتتبع تاريخ التغييرات
        # هنا نعرض المعلومات الأساسية
        
        history = [
            {
                'status': 'pending',
                'date': installation.created_at,
                'user': installation.created_by.get_full_name() if installation.created_by else 'النظام',
                'notes': 'تم إنشاء التركيب'
            }
        ]
        
        if installation.scheduled_date:
            history.append({
                'status': 'scheduled',
                'date': installation.updated_at,
                'user': installation.updated_by.get_full_name() if installation.updated_by else 'النظام',
                'notes': f'تم جدولة التركيب لتاريخ {installation.scheduled_date}'
            })
        
        if installation.actual_start_date:
            history.append({
                'status': 'in_progress',
                'date': installation.actual_start_date,
                'user': 'الفريق',
                'notes': 'تم بدء التركيب'
            })
        
        if installation.status == 'completed' and installation.actual_end_date:
            history.append({
                'status': 'completed',
                'date': installation.actual_end_date,
                'user': 'الفريق',
                'notes': 'تم إكمال التركيب'
            })
        
        return JsonResponse({
            'success': True,
            'installation_id': installation_id,
            'customer_name': installation.customer_name,
            'current_status': installation.status,
            'history': history
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["GET"])
def pending_completions(request):
    """التركيبات المعلقة للإكمال"""
    
    try:
        # التركيبات التي يمكن إكمالها
        pending_installations = InstallationNew.objects.filter(
            status__in=['scheduled', 'in_progress']
        ).select_related('team', 'order').order_by('scheduled_date', 'scheduled_time_start')
        
        # فلترة حسب الفرع إذا كان المستخدم مقيد
        branch_filter = request.GET.get('branch')
        if branch_filter:
            pending_installations = pending_installations.filter(branch_name=branch_filter)
        
        # فلترة حسب التاريخ
        date_filter = request.GET.get('date')
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                pending_installations = pending_installations.filter(scheduled_date=filter_date)
            except ValueError:
                pass
        
        installations_data = []
        for installation in pending_installations:
            installations_data.append({
                'id': installation.id,
                'customer_name': installation.customer_name,
                'customer_phone': installation.customer_phone,
                'windows_count': installation.windows_count,
                'scheduled_date': installation.scheduled_date.strftime('%Y-%m-%d') if installation.scheduled_date else None,
                'scheduled_time_start': installation.scheduled_time_start.strftime('%H:%M') if installation.scheduled_time_start else None,
                'scheduled_time_end': installation.scheduled_time_end.strftime('%H:%M') if installation.scheduled_time_end else None,
                'team_name': installation.team.name if installation.team else 'غير محدد',
                'status': installation.status,
                'priority': installation.priority,
                'branch_name': installation.branch_name,
                'is_overdue': installation.is_overdue,
            })
        
        return JsonResponse({
            'success': True,
            'count': len(installations_data),
            'installations': installations_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
