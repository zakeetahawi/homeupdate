"""
Views لتقارير تتبع التعديلات على المسودات
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .wizard_models import DraftOrder, DraftOrderItem
from accounts.models import User


def is_manager(user):
    """التحقق من أن المستخدم مدير"""
    return user.is_general_manager or user.is_region_manager or user.is_branch_manager


@login_required
@user_passes_test(is_manager)
def edit_tracking_report(request):
    """
    تقرير شامل لتتبع التعديلات على المسودات
    """
    # الفترة الزمنية
    period = request.GET.get('period', '30')  # آخر 30 يوم افتراضياً
    try:
        days = int(period)
    except:
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # المسودات التي تم التعديل عليها
    edited_drafts = DraftOrder.objects.filter(
        updated_at__gte=start_date,
        edit_history__isnull=False
    ).exclude(
        edit_history=[]
    ).select_related(
        'created_by',
        'last_modified_by',
        'customer'
    ).prefetch_related(
        'items__added_by',
        'items__modified_by'
    )
    
    # إحصائيات عامة
    total_edited = edited_drafts.count()
    
    # تجميع التعديلات حسب المحرر
    editors_stats = {}
    draft_stats = []
    
    for draft in edited_drafts:
        if not draft.edit_history:
            continue
            
        # معلومات المسودة
        edit_count = len(draft.edit_history)
        editors_set = set()
        
        for edit in draft.edit_history:
            editor_name = edit.get('user_name', 'مستخدم غير معروف')
            editors_set.add(editor_name)
            
            # إحصائيات المحرر
            if editor_name not in editors_stats:
                editors_stats[editor_name] = {
                    'name': editor_name,
                    'edit_count': 0,
                    'drafts_edited': set(),
                    'actions': {
                        'add_item': 0,
                        'remove_item': 0,
                        'other': 0
                    }
                }
            
            editors_stats[editor_name]['edit_count'] += 1
            editors_stats[editor_name]['drafts_edited'].add(draft.id)
            
            action = edit.get('action', 'other')
            if action in editors_stats[editor_name]['actions']:
                editors_stats[editor_name]['actions'][action] += 1
            else:
                editors_stats[editor_name]['actions']['other'] += 1
        
        # إضافة إحصائيات المسودة
        draft_stats.append({
            'draft': draft,
            'edit_count': edit_count,
            'editors': list(editors_set),
            'editors_count': len(editors_set),
            'original_creator': draft.created_by.get_full_name(),
            'last_editor': draft.last_modified_by.get_full_name() if draft.last_modified_by else '-'
        })
    
    # تحويل editors_stats إلى قائمة وحساب عدد المسودات
    editors_list = []
    for editor_name, stats in editors_stats.items():
        stats['drafts_count'] = len(stats['drafts_edited'])
        del stats['drafts_edited']  # حذف المجموعة لأنها غير قابلة للعرض
        editors_list.append(stats)
    
    # ترتيب حسب عدد التعديلات
    editors_list.sort(key=lambda x: x['edit_count'], reverse=True)
    draft_stats.sort(key=lambda x: x['edit_count'], reverse=True)
    
    context = {
        'period_days': days,
        'start_date': start_date,
        'total_edited': total_edited,
        'editors_stats': editors_list,
        'draft_stats': draft_stats[:50],  # أول 50 مسودة
        'total_edits': sum(e['edit_count'] for e in editors_list),
    }
    
    return render(request, 'orders/reports/edit_tracking_report.html', context)


@login_required
@user_passes_test(is_manager)
def draft_edit_detail(request, draft_id):
    """
    تفاصيل تعديلات مسودة معينة
    """
    from django.shortcuts import get_object_or_404
    
    draft = get_object_or_404(
        DraftOrder.objects.select_related(
            'created_by',
            'last_modified_by',
            'customer'
        ).prefetch_related(
            'items__product',
            'items__added_by',
            'items__modified_by'
        ),
        pk=draft_id
    )
    
    # تحليل سجل التعديلات
    timeline = []
    if draft.edit_history:
        for edit in draft.edit_history:
            timeline.append(edit)
    
    # العناصر المضافة/المعدلة من قبل آخرين
    modified_items = []
    for item in draft.items.all():
        if item.added_by and item.added_by != draft.created_by:
            modified_items.append({
                'item': item,
                'action': 'added',
                'by': item.added_by
            })
        elif item.modified_by and item.modified_by != item.added_by:
            modified_items.append({
                'item': item,
                'action': 'modified',
                'by': item.modified_by
            })
    
    context = {
        'draft': draft,
        'timeline': reversed(timeline),  # الأحدث أولاً
        'modified_items': modified_items,
    }
    
    return render(request, 'orders/reports/draft_edit_detail.html', context)
