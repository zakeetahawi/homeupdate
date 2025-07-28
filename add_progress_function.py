#!/usr/bin/env python
"""
إضافة دالة تتبع التقدم إلى ملف views.py
"""

# قراءة الملف الحالي
with open('/home/zakee/homeupdate/odoo_db_manager/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# إضافة الدالة في النهاية
additional_code = '''

@csrf_exempt
def restore_progress_status(request, session_id):
    """API endpoint للحصول على حالة التقدم الحالية"""
    print(f"🔍 [DEBUG] restore_progress_status called for session: {session_id}")
    
    try:
        # البحث عن سجل التقدم
        try:
            progress = RestoreProgress.objects.get(session_id=session_id)
            print(f"✅ [DEBUG] Progress found for session: {session_id}")
        except RestoreProgress.DoesNotExist:
            print(f"❌ [DEBUG] Progress not found for session: {session_id}")
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        # إنشاء البيانات للإرسال
        response_data = {
            'status': progress.status,
            'progress_percentage': progress.progress_percentage,
            'current_step': progress.current_step,
            'total_items': progress.total_items,
            'processed_items': progress.processed_items,
            'success_count': progress.success_count,
            'error_count': progress.error_count,
            'error_message': progress.error_message or '',
            'result_data': progress.result_data,
            'created_at': progress.created_at.isoformat() if progress.created_at else None,
            'updated_at': progress.updated_at.isoformat() if progress.updated_at else None,
        }
        
        print(f"✅ [DEBUG] Progress status: {progress.status} - {progress.progress_percentage}%")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ [DEBUG] Error in restore_progress_status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _apply_migrations_to_database(database):
    """تطبيق migrations على قاعدة بيانات محددة"""
    # هذه دالة مساعدة - يمكن تنفيذها لاحقاً
    return False


def _create_default_user(database):
    """إنشاء مستخدم افتراضي في قاعدة البيانات"""
    # هذه دالة مساعدة - يمكن تنفيذها لاحقاً
    return False
'''

# التحقق من وجود الدالة مسبقاً
if 'def restore_progress_status(' not in content:
    # إضافة الكود الجديد
    content += additional_code
    
    # كتابة الملف المحدث
    with open('/home/zakee/homeupdate/odoo_db_manager/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ تم إضافة دالة restore_progress_status بنجاح")
else:
    print("⚠️ دالة restore_progress_status موجودة مسبقاً")