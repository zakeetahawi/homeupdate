"""
API views for complaints system integration
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import json

from .models import Complaint, ComplaintType, ComplaintUpdate, ComplaintEscalation, ComplaintNotification, ResolutionMethod
from .services.notification_service import notification_service
from accounts.models import User


@method_decorator(login_required, name='dispatch')
class ComplaintStatusUpdateView(View):
    """
    API endpoint for updating complaint status via AJAX
    """
    
    def post(self, request, complaint_id):
        try:
            complaint = get_object_or_404(Complaint, pk=complaint_id)
            
            # Check permissions
            if not self.has_permission(request.user, complaint):
                return JsonResponse({
                    'success': False,
                    'error': 'ليس لديك صلاحية لتحديث هذه الشكوى'
                }, status=403)
            
            data = json.loads(request.body)
            new_status = data.get('status')
            resolution_method_id = data.get('resolutionMethod')
            resolution_notes = data.get('notes', '')

            if new_status not in dict(Complaint.STATUS_CHOICES):
                return JsonResponse({
                    'success': False,
                    'error': 'حالة غير صحيحة'
                }, status=400)

            # Check if resolution method is required for resolved status
            if new_status == 'resolved' and not resolution_method_id:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب اختيار طريقة الحل عند حل الشكوى'
                }, status=400)

            old_status = complaint.status
            old_status_display = complaint.get_status_display()

            complaint.status = new_status

            # Set resolution method if resolving
            if new_status == 'resolved' and resolution_method_id:
                try:
                    resolution_method = ResolutionMethod.objects.get(id=resolution_method_id, is_active=True)
                    complaint.resolution_method = resolution_method
                except ResolutionMethod.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'طريقة الحل المحددة غير صحيحة'
                    }, status=400)

            complaint._changed_by = request.user  # للاستخدام في الإشعارات
            complaint.save()

            new_status_display = complaint.get_status_display()

            # إنشاء تحديث
            update_description = f'تم تغيير الحالة من {old_status_display} إلى {new_status_display}'
            if new_status == 'resolved' and complaint.resolution_method:
                update_description += f'\nطريقة الحل: {complaint.resolution_method.name}'
            if resolution_notes:
                update_description += f'\nملاحظات: {resolution_notes}'

            update = ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='resolution' if new_status == 'resolved' else 'status_change',
                title=f'تغيير الحالة إلى {new_status_display}',
                description=update_description,
                old_status=old_status,
                new_status=new_status,
                resolution_method=complaint.resolution_method if new_status == 'resolved' else None,
                created_by=request.user,
                is_visible_to_customer=True
            )
            
            return JsonResponse({
                'success': True,
                'message': 'تم تحديث حالة الشكوى بنجاح',
                'new_status': new_status,
                'new_status_display': dict(Complaint.STATUS_CHOICES)[new_status]
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات غير صحيحة'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=500)
    
    def has_permission(self, user, complaint):
        """
        Check if user has permission to update complaint status
        Enhanced to use the new permission system
        """
        # Get the new status from request data
        try:
            data = json.loads(self.request.body)
            new_status = data.get('status')
        except:
            new_status = None

        # Check user's complaint permissions
        try:
            permissions = user.complaint_permissions
            if not permissions.is_active:
                return False
        except:
            # If no permissions record, fall back to group-based permissions
            permissions = None

        # Check specific status change permissions
        if new_status == 'resolved':
            if permissions and not permissions.can_resolve_complaints:
                return False
        elif new_status == 'closed':
            if permissions and not permissions.can_close_complaints:
                return False

        # Check general status change permission
        if permissions and not permissions.can_change_complaint_status:
            return False

        # Only original complaint creator can close or resolve complaints (unless admin)
        if new_status in ['resolved', 'closed']:
            if complaint.created_by == user:
                return True
            # Check if user has admin permissions
            if permissions and permissions.can_edit_all_complaints:
                return True
            # Supervisors and managers can also close/resolve
            if user.groups.filter(name__in=['Complaints_Supervisors', 'Managers']).exists():
                return True
            return False

        # For other status changes, check regular permissions
        # المسؤول المعين يمكنه التحديث
        if complaint.assigned_to == user:
            return True

        # منشئ الشكوى يمكنه التحديث (ما عدا الإغلاق والحل)
        if complaint.created_by == user:
            return True

        # Check if user can edit all complaints
        if permissions and permissions.can_edit_all_complaints:
            return True

        # مدير القسم يمكنه التحديث
        if (complaint.assigned_department and
            complaint.assigned_department.manager == user):
            return True

        # المشرفون يمكنهم التحديث
        if user.groups.filter(name='Complaints_Supervisors').exists():
            return True

        # المدراء يمكنهم التحديث
        if user.groups.filter(name='Managers').exists():
            return True

        return False


@method_decorator(login_required, name='dispatch')
class ComplaintEscalationView(View):
    """
    API endpoint for escalating complaints via AJAX
    """

    def post(self, request, complaint_id):
        try:
            complaint = get_object_or_404(Complaint, pk=complaint_id)

            # Check permissions
            if not self.has_permission(request.user, complaint):
                return JsonResponse({
                    'success': False,
                    'error': 'ليس لديك صلاحية لتصعيد هذه الشكوى'
                }, status=403)

            data = json.loads(request.body)
            escalated_to_id = data.get('escalated_to')
            reason = data.get('reason', '')
            description = data.get('description', '')

            if not escalated_to_id:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب تحديد الشخص المراد التصعيد إليه'
                }, status=400)

            try:
                escalated_to = User.objects.get(pk=escalated_to_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'المستخدم المحدد غير موجود'
                }, status=400)

            # Save old status
            old_status = complaint.status

            # Create escalation record
            from .models import ComplaintEscalation
            escalation = ComplaintEscalation.objects.create(
                complaint=complaint,
                reason=reason,
                description=description,
                escalated_from=complaint.assigned_to,
                escalated_to=escalated_to,
                escalated_by=request.user
            )

            # Update complaint status
            complaint.status = 'escalated'
            complaint.save()

            # Create update log
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='escalation',
                title='تصعيد الشكوى',
                description=f'تم تصعيد الشكوى إلى {escalated_to.get_full_name()}\nسبب التصعيد: {reason}\n{description}',
                old_status=old_status,
                new_status='escalated',
                created_by=request.user,
                is_visible_to_customer=True
            )

            # Create escalation notification for real-time alerts
            ComplaintNotification.objects.create(
                complaint=complaint,
                recipient=escalated_to,
                notification_type='escalation',
                title=f'تصعيد شكوى عاجل - {complaint.complaint_number}',
                message=f'تم تصعيد الشكوى إليك من {request.user.get_full_name()}\nسبب التصعيد: {reason}',
                is_read=False
            )

            # Also create assignment notification for the escalated user
            ComplaintNotification.objects.create(
                complaint=complaint,
                recipient=escalated_to,
                notification_type='assignment',
                title=f'تعيين شكوى مصعدة - {complaint.complaint_number}',
                message=f'تم تعيين شكوى مصعدة إليك\nالعميل: {complaint.customer.name}\nالأولوية: {complaint.get_priority_display()}',
                is_read=False
            )

            return JsonResponse({
                'success': True,
                'message': 'تم تصعيد الشكوى بنجاح وإرسال إشعار فوري',
                'escalated_to': escalated_to.get_full_name(),
                'notification_sent': True
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات غير صحيحة'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=500)

    def has_permission(self, user, complaint):
        """
        Check if user has permission to escalate complaint
        Enhanced to use the new permission system
        """
        # 1. التحقق من كون المستخدم مشرف النظام
        if user.is_superuser:
            return True
        
        # 2. التحقق من المجموعات
        if user.groups.filter(name__in=[
            'Complaints_Managers',
            'Complaints_Supervisors', 
            'Managers',
            'Department_Managers'
        ]).exists():
            return True
        
        # 3. التحقق من الصلاحيات المباشرة
        if user.has_perm('complaints.escalate_complaint'):
            return True
        
        # 4. التحقق من سجل الصلاحيات المخصص (إذا كان موجوداً)
        try:
            if hasattr(user, 'complaint_permissions'):
                permissions = user.complaint_permissions
                if permissions.is_active and permissions.can_escalate_complaints:
                    return True
        except:
            pass
        
        # 5. المسؤول المعين يمكنه التصعيد
        if complaint.assigned_to == user:
            return True

        # 6. منشئ الشكوى يمكنه التصعيد
        if complaint.created_by == user:
            return True

        # 7. مدير القسم يمكنه التصعيد
        if (complaint.assigned_department and
            hasattr(complaint.assigned_department, 'manager') and
            complaint.assigned_department.manager == user):
            return True

        return False


@method_decorator(login_required, name='dispatch')
class ComplaintAssignmentView(View):
    """
    API endpoint for assigning complaints via AJAX
    """

    def post(self, request, complaint_id):
        try:
            complaint = get_object_or_404(Complaint, pk=complaint_id)

            # Check permissions
            if not self.has_permission(request.user, complaint):
                return JsonResponse({
                    'success': False,
                    'error': 'ليس لديك صلاحية لتعيين هذه الشكوى'
                }, status=403)

            data = json.loads(request.body)
            assigned_to_id = data.get('assigned_to')
            assigned_department = data.get('assigned_department', '')
            assignment_notes = data.get('assignment_notes', '')
            urgent_notification = data.get('urgent_notification', False)

            if not assigned_to_id:
                return JsonResponse({
                    'success': False,
                    'error': 'يجب تحديد المستخدم المراد التعيين إليه'
                }, status=400)

            try:
                assigned_to = User.objects.get(pk=assigned_to_id, is_active=True)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'المستخدم المحدد غير موجود أو غير نشط'
                }, status=400)

            # Store old assignment for logging
            old_assigned_to = complaint.assigned_to
            old_assigned_to_name = old_assigned_to.get_full_name() or old_assigned_to.username if old_assigned_to else None

            # Update assignment
            complaint.assigned_to = assigned_to
            if assigned_department:
                # Update assigned department if provided
                try:
                    from accounts.models import Department
                    department = Department.objects.get(name=assigned_department)
                    complaint.assigned_department = department
                except Department.DoesNotExist:
                    pass  # Keep existing department if new one not found

            complaint._changed_by = request.user  # للاستخدام في الإشعارات
            complaint.save()  # هذا سيستدعي signals تلقائياً

            # Create update log
            assigned_to_name = assigned_to.get_full_name() or assigned_to.username
            if old_assigned_to:
                title = f'تغيير تعيين الشكوى من {old_assigned_to_name} إلى {assigned_to_name}'
            else:
                title = f'تعيين الشكوى إلى {assigned_to_name}'

            description = title
            if assigned_department:
                description += f'\nالقسم: {assigned_department}'
            if assignment_notes:
                description += f'\nملاحظات: {assignment_notes}'

            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='assignment',
                title=title,
                description=description,
                old_assignee=old_assigned_to,
                new_assignee=assigned_to,
                created_by=request.user,
                is_visible_to_customer=True
            )

            # الإشعارات ستُرسل تلقائياً عبر signals عند حفظ الشكوى
            return JsonResponse({
                'success': True,
                'message': 'تم تعيين الشكوى بنجاح',
                'assigned_to': assigned_to_name,
                'notification_sent': True  # signals ستتولى الإشعارات
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات JSON غير صحيحة'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=500)

    def has_permission(self, user, complaint):
        """
        Check if user has permission to assign complaint
        Enhanced to use the new permission system
        """
        # Check user's complaint permissions
        try:
            permissions = user.complaint_permissions
            if not permissions.is_active:
                return False
            # Check if user has assignment permission
            if not permissions.can_assign_complaints:
                # If user doesn't have assignment permission, check if they can at least assign their own
                if complaint.assigned_to != user and complaint.created_by != user:
                    return False
        except:
            # If no permissions record, fall back to group-based permissions
            pass

        # المسؤول المعين يمكنه التعيين
        if complaint.assigned_to == user:
            return True

        # منشئ الشكوى يمكنه التعيين
        if complaint.created_by == user:
            return True

        # Check if user can assign all complaints
        try:
            if user.complaint_permissions.can_assign_complaints:
                return True
        except:
            pass

        # المشرفون يمكنهم التعيين
        if user.groups.filter(name='Complaints_Supervisors').exists():
            return True

        # المدراء يمكنهم التعيين
        if user.groups.filter(name='Managers').exists():
            return True

        return False


@method_decorator(login_required, name='dispatch')
class ComplaintNoteView(View):
    """
    API endpoint for adding notes to complaints via AJAX
    """

    def post(self, request, complaint_id):
        try:
            complaint = get_object_or_404(Complaint, pk=complaint_id)

            # Check permissions
            if not self.has_permission(request.user, complaint):
                return JsonResponse({
                    'success': False,
                    'error': 'ليس لديك صلاحية لإضافة ملاحظات لهذه الشكوى'
                }, status=403)

            data = json.loads(request.body)
            title = data.get('title', '')
            content = data.get('content', '')
            is_visible_to_customer = data.get('is_visible_to_customer', False)

            if not title.strip():
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال عنوان الملاحظة'
                }, status=400)

            if not content.strip():
                return JsonResponse({
                    'success': False,
                    'error': 'يجب إدخال محتوى الملاحظة'
                }, status=400)

            # Create update log
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='note',
                title=title,
                description=content,
                created_by=request.user,
                is_visible_to_customer=is_visible_to_customer
            )

            return JsonResponse({
                'success': True,
                'message': 'تم إضافة الملاحظة بنجاح'
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات JSON غير صحيحة'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=500)

    def has_permission(self, user, complaint):
        """
        Check if user has permission to add notes to complaint
        """
        # المسؤول المعين يمكنه إضافة ملاحظات
        if complaint.assigned_to == user:
            return True

        # منشئ الشكوى يمكنه إضافة ملاحظات
        if complaint.created_by == user:
            return True

        # المشرفون يمكنهم إضافة ملاحظات
        if user.groups.filter(name='Complaints_Supervisors').exists():
            return True

        # المدراء يمكنهم إضافة ملاحظات
        if user.groups.filter(name='Managers').exists():
            return True

        return False


@login_required
@require_http_methods(["POST"])
def mark_complaint_notification_read(request, notification_id):
    """
    API endpoint لتحديد إشعار شكوى كمقروء
    """
    try:
        from .models import ComplaintNotification
        from django.utils import timezone

        notification = get_object_or_404(
            ComplaintNotification,
            pk=notification_id,
            recipient=request.user
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()

        return JsonResponse({
            'success': True,
            'message': 'تم تحديد الإشعار كمقروء'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def complaints_notifications_api(request):
    """
    API endpoint لإشعارات الشكاوى - يعرض فقط الشكاوى غير المحلولة
    """
    try:
        from .models import ComplaintNotification

        # الحصول على المعاملات
        limit = int(request.GET.get('limit', 10))

        # الحصول على الإشعارات غير المقروءة فقط للشكاوى النشطة
        notifications_queryset = ComplaintNotification.objects.filter(
            recipient=request.user,
            is_read=False,  # فقط الإشعارات غير المقروءة
            complaint__status__in=['new', 'in_progress', 'escalated']  # فقط الشكاوى التي تحتاج إجراء
        ).select_related('complaint', 'complaint__customer').order_by('-created_at')[:limit]

        notifications = []
        for notification in notifications_queryset:
            notifications.append({
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'complaint_number': notification.complaint.complaint_number,
                'complaint_id': notification.complaint.id,
                'created_at': notification.created_at.isoformat(),
                'url': notification.url,
                'is_read': notification.is_read
            })

        # حساب عدد الإشعارات غير المقروءة (فقط للشكاوى غير المحلولة)
        unread_count = ComplaintNotification.objects.filter(
            recipient=request.user,
            is_read=False,
            complaint__status__in=['new', 'in_progress', 'escalated']
        ).count()

        return JsonResponse({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count,
            'total_count': len(notifications)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def clear_complaints_notifications(request):
    """
    API endpoint لمسح جميع إشعارات الشكاوى للمستخدم الحالي
    """
    try:
        from .models import ComplaintNotification

        # تحديد إشعارات الشكاوى غير المحلولة فقط كمقروءة (نفس منطق العداد)
        updated_count = ComplaintNotification.objects.filter(
            recipient=request.user,
            is_read=False,
            complaint__status__in=['new', 'in_progress', 'escalated']
        ).update(is_read=True)

        return JsonResponse({
            'success': True,
            'message': f'تم تحديد {updated_count} إشعار كمقروء',
            'updated_count': updated_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)





@login_required
@require_http_methods(["GET"])
def assigned_complaints_api(request):
    """
    API endpoint للشكاوى المسندة للمستخدم الحالي
    """
    try:
        # الحصول على الشكاوى المسندة للمستخدم والتي لم يتم حلها بعد (استبعاد المحلولة والمغلقة)
        assigned_complaints = Complaint.objects.filter(
            assigned_to=request.user,
            status__in=['new', 'in_progress', 'overdue', 'escalated']
        ).exclude(
            status__in=['resolved', 'closed', 'pending_evaluation']
        ).select_related('customer', 'complaint_type').order_by('-created_at')[:5]

        complaints_data = []
        for complaint in assigned_complaints:
            complaints_data.append({
                'id': complaint.id,
                'complaint_number': complaint.complaint_number,
                'title': complaint.title,
                'customer_name': complaint.customer.name,
                'priority': complaint.priority,
                'status': complaint.status,
                'created_at': complaint.created_at.isoformat(),
                'deadline': complaint.deadline.isoformat() if complaint.deadline else None,
                'url': f'/complaints/{complaint.id}/'
            })

        return JsonResponse({
            'success': True,
            'complaints': complaints_data,
            'count': len(complaints_data)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def escalated_complaints_api(request):
    """
    API endpoint للشكاوى المصعدة للمستخدم الحالي فقط
    """
    try:
        # الحصول على الشكاوى المصعدة إلى المستخدم الحالي (آخر تصعيد فقط)
        from .models import ComplaintEscalation
        from django.db.models import Max

        # الحصول على آخر تصعيد لكل شكوى
        latest_escalations = ComplaintEscalation.objects.filter(
            complaint__status='escalated'
        ).values('complaint_id').annotate(
            latest_escalation_date=Max('escalated_at')
        )

        # الحصول على IDs الشكاوى التي آخر تصعيد لها هو للمستخدم الحالي
        escalated_complaint_ids = []
        for escalation_info in latest_escalations:
            latest_escalation = ComplaintEscalation.objects.filter(
                complaint_id=escalation_info['complaint_id'],
                escalated_at=escalation_info['latest_escalation_date']
            ).first()

            if latest_escalation and latest_escalation.escalated_to == request.user:
                escalated_complaint_ids.append(escalation_info['complaint_id'])

        escalated_complaints = Complaint.objects.filter(
            id__in=escalated_complaint_ids,
            status='escalated'
        ).select_related('customer', 'complaint_type', 'assigned_to').prefetch_related('escalations').order_by('-created_at')[:10]

        complaints_data = []
        for complaint in escalated_complaints:
            # الحصول على آخر تصعيد للشكوى
            latest_escalation = complaint.escalations.order_by('-escalated_at').first()
            escalation_reason = 'سبب غير محدد'
            escalation_description = ''

            if latest_escalation:
                escalation_reason = latest_escalation.get_reason_display()
                escalation_description = latest_escalation.description

            complaints_data.append({
                'id': complaint.id,
                'complaint_number': complaint.complaint_number,
                'title': complaint.title,
                'customer_name': complaint.customer.name,
                'priority': complaint.priority,
                'assigned_to': complaint.assigned_to.get_full_name() if complaint.assigned_to else 'غير مسند',
                'created_at': complaint.created_at.isoformat(),
                'deadline': complaint.deadline.isoformat() if complaint.deadline else None,
                'url': f'/complaints/{complaint.id}/',
                'escalation_reason': escalation_reason,
                'escalation_description': escalation_description
            })

        return JsonResponse({
            'success': True,
            'complaints': complaints_data,
            'count': len(complaints_data),
            'urgent': True  # إشارة أن هذه شكاوى عاجلة
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@method_decorator(login_required, name='dispatch')
class ComplaintAssignmentUpdateView(View):
    """
    API endpoint for updating complaint assignment via AJAX
    """
    
    def post(self, request, complaint_id):
        try:
            complaint = get_object_or_404(Complaint, pk=complaint_id)
            
            # Check permissions
            if not self.has_permission(request.user, complaint):
                return JsonResponse({
                    'success': False,
                    'error': 'ليس لديك صلاحية لتحديث هذه الشكوى'
                }, status=403)
            
            data = json.loads(request.body)
            new_assignee_id = data.get('assigned_to')
            
            old_assignee = complaint.assigned_to
            
            if new_assignee_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                new_assignee = get_object_or_404(User, pk=new_assignee_id)
                complaint.assigned_to = new_assignee
            else:
                complaint.assigned_to = None
                new_assignee = None
            
            complaint._changed_by = request.user
            complaint.save()
            
            # إنشاء تحديث
            if new_assignee:
                description = f'تم إسناد الشكوى إلى {new_assignee.get_full_name()}'
            else:
                description = 'تم إلغاء إسناد الشكوى'
                
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='assignment',
                description=description,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'تم تحديث إسناد الشكوى بنجاح',
                'assigned_to': new_assignee.get_full_name() if new_assignee else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=500)
    
    def has_permission(self, user, complaint):
        """
        Check if user has permission to update complaint assignment
        """
        # مدير القسم يمكنه التحديث
        if (complaint.assigned_department and 
            complaint.assigned_department.manager == user):
            return True
        
        # المشرفون يمكنهم التحديث
        if user.groups.filter(name='Complaints_Supervisors').exists():
            return True
        
        # المدراء يمكنهم التحديث
        if user.groups.filter(name='Managers').exists():
            return True
        
        return False


@login_required
@require_http_methods(["GET"])
def complaint_search_api(request):
    """
    API endpoint for searching complaints
    """
    try:
        query = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        priority = request.GET.get('priority', '')
        assigned_to = request.GET.get('assigned_to', '')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        complaints = Complaint.objects.select_related(
            'customer', 'complaint_type', 'assigned_to', 'assigned_department'
        )
        
        # Apply filters
        if query:
            complaints = complaints.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(complaint_number__icontains=query) |
                Q(customer__name__icontains=query)
            )
        
        if status:
            complaints = complaints.filter(status=status)
        
        if priority:
            complaints = complaints.filter(priority=priority)
        
        if assigned_to:
            complaints = complaints.filter(assigned_to_id=assigned_to)
        
        # Pagination
        paginator = Paginator(complaints, per_page)
        page_obj = paginator.get_page(page)
        
        # Serialize data
        results = []
        for complaint in page_obj:
            results.append({
                'id': complaint.id,
                'complaint_number': complaint.complaint_number,
                'title': complaint.title,
                'customer_name': complaint.customer.name,
                'status': complaint.status,
                'status_display': complaint.get_status_display(),
                'priority': complaint.priority,
                'priority_display': complaint.get_priority_display(),
                'assigned_to': complaint.assigned_to.get_full_name() if complaint.assigned_to else None,
                'created_at': complaint.created_at.strftime('%Y-%m-%d %H:%M'),
                'url': f'/complaints/{complaint.id}/'
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ في البحث: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def complaint_stats_api(request):
    """
    API endpoint for getting complaint statistics
    """
    try:
        # Get filter parameters
        days = int(request.GET.get('days', 30))
        department_id = request.GET.get('department_id', '')
        
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        complaints = Complaint.objects.filter(created_at__gte=start_date)
        
        if department_id:
            complaints = complaints.filter(assigned_department_id=department_id)
        
        # Calculate statistics
        stats = complaints.aggregate(
            total=Count('id'),
            new=Count('id', filter=Q(status='new')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            resolved=Count('id', filter=Q(status='resolved')),
            overdue=Count('id', filter=Q(status='overdue')),
            high_priority=Count('id', filter=Q(priority='high')),
            urgent_priority=Count('id', filter=Q(priority='urgent'))
        )
        
        # Calculate resolution rate
        resolved_count = stats['resolved']
        total_count = stats['total']
        resolution_rate = (resolved_count / total_count * 100) if total_count > 0 else 0
        
        return JsonResponse({
            'success': True,
            'stats': {
                **stats,
                'resolution_rate': round(resolution_rate, 2)
            },
            'period_days': days
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ في جلب الإحصائيات: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def user_notifications_api(request):
    """
    API endpoint for getting user notifications
    """
    try:
        from .models import ComplaintNotification
        
        notifications = ComplaintNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).select_related('complaint').order_by('-created_at')[:10]
        
        results = []
        for notification in notifications:
            results.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'url': notification.url,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
                'complaint_number': notification.complaint.complaint_number if notification.complaint else None
            })
        
        return JsonResponse({
            'success': True,
            'notifications': results,
            'unread_count': notifications.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ في جلب الإشعارات: {str(e)}'
        }, status=500)


@method_decorator(login_required, name='dispatch')
class AssignmentNotificationsView(View):
    """
    API endpoint for getting assignment notifications for dashboard
    """

    def get(self, request):
        """Get assignment notifications for current user"""
        try:
            # Get assignment notifications for current user (only unread and for active complaints)
            assignment_notifications = ComplaintNotification.objects.filter(
                recipient=request.user,
                notification_type__in=['assignment', 'new_complaint'],
                is_read=False,
                complaint__status__in=['new', 'in_progress', 'escalated']  # فقط الشكاوى النشطة
            ).select_related('complaint', 'complaint__customer').order_by('-created_at')[:5]

            notifications_data = []

            # Add assignment notifications
            for notification in assignment_notifications:
                notifications_data.append({
                    'id': notification.id,
                    'type': 'assignment',
                    'title': notification.title,
                    'message': notification.message,
                    'complaint_id': notification.complaint.id,
                    'complaint_number': notification.complaint.complaint_number,
                    'customer_name': notification.complaint.customer.name,
                    'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
                    'url': notification.url or f'/complaints/{notification.complaint.id}/',
                    'is_read': notification.is_read
                })

            return JsonResponse({
                'success': True,
                'notifications': notifications_data[:5],  # Limit to 5
                'unread_assignments': assignment_notifications.count()
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ في جلب إشعارات التعيين: {str(e)}'
            }, status=500)


@login_required
@require_http_methods(["POST"])
def mark_assignment_notification_read(request, notification_id):
    """Mark assignment notification as read"""
    try:
        notification = get_object_or_404(
            ComplaintNotification,
            id=notification_id,
            recipient=request.user,
            notification_type='assignment'
        )

        notification.mark_as_read()

        return JsonResponse({
            'success': True,
            'message': 'تم تحديد الإشعار كمقروء'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ في تحديث الإشعار: {str(e)}'
        }, status=500)


@method_decorator(login_required, name='dispatch')
class ResolutionMethodsView(View):
    """
    API endpoint for fetching active resolution methods
    """

    def get(self, request):
        try:
            methods = ResolutionMethod.objects.filter(is_active=True).order_by('order', 'name')

            methods_data = []
            for method in methods:
                methods_data.append({
                    'id': method.id,
                    'name': method.name,
                    'description': method.description
                })

            return JsonResponse(methods_data, safe=False)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ في جلب طرق الحل: {str(e)}'
            }, status=500)


@method_decorator(login_required, name='dispatch')
class UsersForEscalationView(View):
    """
    API endpoint to fetch users available for escalation
    """

    def get(self, request):
        try:
            # Get users who can receive escalated complaints
            escalation_users = User.objects.filter(
                is_active=True,
                complaint_permissions__can_receive_escalations=True,
                complaint_permissions__is_active=True
            ).exclude(
                id=request.user.id  # Exclude current user
            ).prefetch_related('departments', 'groups', 'complaint_permissions').order_by('first_name', 'last_name')

            users_data = []
            for user in escalation_users:
                # Get user's department if available
                department = None
                if user.departments.exists():
                    department = user.departments.first().name
                elif hasattr(user, 'branch') and user.branch:
                    department = f"فرع {user.branch.name}"

                users_data.append({
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'username': user.username,
                    'department': department,
                    'is_supervisor': user.groups.filter(name='Complaints_Supervisors').exists(),
                    'is_manager': user.groups.filter(name='Managers').exists()
                })

            return JsonResponse(users_data, safe=False)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ في جلب المستخدمين: {str(e)}'
            }, status=500)


@method_decorator(login_required, name='dispatch')
class UsersForAssignmentView(View):
    """
    API endpoint to fetch all users available for assignment
    """

    def get(self, request):
        try:
            # Get users who can be assigned complaints
            assignment_users = User.objects.filter(
                is_active=True,
                complaint_permissions__can_be_assigned_complaints=True,
                complaint_permissions__is_active=True
            ).prefetch_related('departments', 'groups', 'complaint_permissions').order_by('first_name', 'last_name')

            users_data = []
            for user in assignment_users:
                # Get user's department if available
                department = None
                if user.departments.exists():
                    department = user.departments.first().name
                elif hasattr(user, 'branch') and user.branch:
                    department = f"فرع {user.branch.name}"

                users_data.append({
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'username': user.username,
                    'department': department,
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'is_supervisor': user.groups.filter(name='Complaints_Supervisors').exists(),
                    'is_manager': user.groups.filter(name='Managers').exists()
                })

            return JsonResponse(users_data, safe=False)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ في جلب المستخدمين: {str(e)}'
            }, status=500)


@method_decorator(login_required, name='dispatch')
class UnresolvedComplaintsStatsView(View):
    """
    API endpoint to fetch unresolved complaints statistics
    """

    def get(self, request):
        try:
            # Get unresolved complaints (not resolved or closed)
            unresolved_complaints = Complaint.objects.exclude(
                status__in=['resolved', 'closed']
            )

            # Calculate statistics
            total_unresolved = unresolved_complaints.count()
            urgent_count = unresolved_complaints.filter(priority='urgent').count()
            overdue_count = unresolved_complaints.filter(deadline__lt=timezone.now()).count()
            escalated_count = unresolved_complaints.filter(status='escalated').count()
            unassigned_count = unresolved_complaints.filter(assigned_to__isnull=True).count()

            # Get user-specific counts if not admin
            user_assigned_count = 0
            user_created_count = 0

            if not (request.user.is_superuser or
                    request.user.groups.filter(name__in=[
                        'Complaints_Managers', 'Complaints_Supervisors', 'Managers'
                    ]).exists()):
                user_assigned_count = unresolved_complaints.filter(assigned_to=request.user).count()
                user_created_count = unresolved_complaints.filter(created_by=request.user).count()

            return JsonResponse({
                'success': True,
                'unresolved_count': total_unresolved,
                'urgent_count': urgent_count,
                'overdue_count': overdue_count,
                'escalated_count': escalated_count,
                'unassigned_count': unassigned_count,
                'user_assigned_count': user_assigned_count,
                'user_created_count': user_created_count,
                'is_admin': (request.user.is_superuser or
                           request.user.groups.filter(name__in=[
                               'Complaints_Managers', 'Complaints_Supervisors', 'Managers'
                           ]).exists())
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ في جلب إحصائيات الشكاوى: {str(e)}'
            }, status=500)


@login_required
@require_http_methods(["GET"])
def get_complaint_type_responsible_staff(request, complaint_type_id):
    """
    API endpoint to get responsible staff for a specific complaint type
    """
    try:
        complaint_type = get_object_or_404(ComplaintType, pk=complaint_type_id)

        # Get responsible staff for this complaint type
        responsible_staff = complaint_type.responsible_staff.filter(is_active=True)

        # If no specific responsible staff, get all active staff
        if not responsible_staff.exists():
            responsible_staff = User.objects.filter(is_active=True)

        staff_data = []
        for staff in responsible_staff.order_by('first_name', 'last_name'):
            full_name = staff.get_full_name() or staff.username
            staff_data.append({
                'id': staff.id,
                'name': full_name,
                'username': staff.username
            })

        return JsonResponse({
            'success': True,
            'staff': staff_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ في جلب الموظفين المسؤولين: {str(e)}'
        }, status=500)
