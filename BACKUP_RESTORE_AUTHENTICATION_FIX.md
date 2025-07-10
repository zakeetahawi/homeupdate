# إصلاح مشكلة التوثيق في تتبع تقدم استعادة النسخ الاحتياطية

## المشكلة 🔍
كانت هناك مشكلة في تتبع تقدم عملية استعادة النسخ الاحتياطية حيث كان المستخدم يحصل على خطأ 401 (Unauthorized) عند محاولة الوصول إلى نقطة النهاية لمراقبة التقدم.

### الأخطاء المسجلة:
```
"GET /odoo-db-manager/restore-progress/restore_1752146893951_kare4uvx2/status/ HTTP/1.1" 401 130
Unauthorized: /odoo-db-manager/restore-progress/restore_1752146893951_kare4uvx2/status/
```

## السبب الجذري 🔧
الدالة `restore_progress_status` في `odoo_db_manager/views.py` لم تكن تحتوي على ديكوريتر التوثيق المطلوب:
- `@login_required`
- `@user_passes_test(is_staff_or_superuser)`

## الحل المطبق ✅

### 1. إضافة ديكوريتر التوثيق
```python
@login_required
@user_passes_test(is_staff_or_superuser)
def restore_progress_status(request, session_id):
    """API endpoint للحصول على حالة التقدم الحالية"""
    try:
        # تحديث الجلسة لمنع انتهاء صلاحيتها
        request.session.modified = True
        request.session.set_expiry(3600)  # ساعة إضافية
        
        progress = RestoreProgress.objects.filter(session_id=session_id).first()
        
        if not progress:
            return JsonResponse({'error': 'الجلسة غير موجودة'}, status=404)
        
        # التحقق من أن المستخدم يملك هذه الجلسة
        if progress.user != request.user:
            return JsonResponse({'error': 'ليس لديك صلاحية للوصول لهذه الجلسة'}, status=403)
        
        # ... باقي الكود
```

### 2. تحسين معالجة الأخطاء في الواجهة
```javascript
// دالة لتتبع التقدم
function checkProgress(sessionId) {
    return fetch(`/odoo-db-manager/restore-progress/${sessionId}/status/`, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else if (response.status === 401) {
            // إذا كان هناك خطأ في التوثيق، نعيد تحميل الصفحة
            console.warn('⚠️ [DEBUG] Authentication error - reloading page');
            window.location.reload();
            throw new Error('Authentication error');
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    })
    // ... باقي الكود
}
```

### 3. إضافة آلية إعادة المحاولة
```javascript
function startProgressTracking(sessionId) {
    let errorCount = 0;
    const maxErrors = 5;
    
    progressInterval = setInterval(() => {
        checkProgress(sessionId)
        .then(data => {
            errorCount = 0; // إعادة تعيين عداد الأخطاء عند النجاح
            updateProgressDisplay(data);
        })
        .catch(error => {
            errorCount++;
            if (errorCount >= maxErrors) {
                // إيقاف التتبع وإظهار رسالة خطأ
                clearInterval(progressInterval);
                Swal.fire({
                    icon: 'error',
                    title: 'خطأ في تتبع التقدم',
                    text: 'حدث خطأ في تتبع التقدم. يرجى إعادة تحميل الصفحة.',
                    confirmButtonText: 'إعادة تحميل',
                    allowOutsideClick: false
                }).then(() => {
                    window.location.reload();
                });
            }
        });
    }, 1000);
}
```

## النتيجة 🎉
- ✅ تم إصلاح مشكلة التوثيق 401
- ✅ تتبع التقدم يعمل بشكل صحيح
- ✅ معالجة أفضل للأخطاء
- ✅ إعادة تحميل تلقائية عند انتهاء الجلسة
- ✅ آلية إعادة المحاولة عند الأخطاء المؤقتة

## الملفات المعدلة 📝
1. `odoo_db_manager/views.py` - إضافة ديكوريتر التوثيق
2. `odoo_db_manager/templates/odoo_db_manager/backup_upload.html` - تحسين معالجة الأخطاء

## طريقة الاختبار 🧪
1. قم بتسجيل الدخول كمستخدم إداري
2. انتقل إلى صفحة رفع النسخة الاحتياطية
3. ارفع ملف نسخة احتياطية
4. راقب شريط التقدم - يجب أن يعمل بدون أخطاء 401

## ملاحظات مهمة ⚠️
- تأكد من أن المستخدم مسجل دخول قبل بدء عملية الاستعادة
- الجلسة تتجدد تلقائياً كل ثانية أثناء التتبع
- في حالة انتهاء الجلسة، ستتم إعادة تحميل الصفحة تلقائياً
- الحد الأقصى للأخطاء هو 5 أخطاء متتالية قبل إيقاف التتبع 