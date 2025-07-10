# 🔍 دليل تشخيص مشكلة توقف الواجهة

## المشكلة الحالية
الواجهة تتوقف عند "بدء العملية..." ولا تُرسل النموذج إلى الخادم.

## التشخيص الأولي
من الرسائل المرفقة:
- ✅ الخادم يعمل بشكل صحيح
- ✅ المستخدم مسجل دخول (`zakee.tahawi`)
- ✅ صفحة الاستعادة تحمل بشكل صحيح
- ❌ **لا توجد رسائل POST في الطرفية** - هذا يعني أن النموذج لا يُرسل!

## خطوات التشخيص

### 1. فحص الواجهة الأمامية
```bash
# تشغيل الخادم
python manage.py runserver

# في متصفح آخر، افتح:
http://localhost:8000/odoo-db-manager/backups/upload/

# افتح أدوات المطور (F12) وانتقل لتبويب Console
```

### 2. رسائل التشخيص المتوقعة في Console
يجب أن تظهر هذه الرسائل عند تحميل الصفحة:
```
🚀 [DEBUG] JavaScript script starting...
🚀 [DEBUG] SweetAlert2 loaded: true
🚀 [DEBUG] Document ready state: complete
✅ [DEBUG] Document already loaded, initializing immediately
🔍 [DEBUG] Initializing restore system...
🔍 [DEBUG] Variables initialized
🔍 [DEBUG] Script loaded, checking form elements...
🔍 [DEBUG] Form element: <form id="restoreForm">
🔍 [DEBUG] Button element: <button id="restoreBtn">
✅ [DEBUG] Form found, adding event listener
✅ [DEBUG] Button found, adding click listener
```

### 3. إذا لم تظهر الرسائل
**المشكلة:** JavaScript لا يتم تحميله أو تنفيذه

**الحلول:**
1. تحقق من أن الصفحة تحتوي على JavaScript
2. تحقق من عدم وجود أخطاء في Console
3. تحقق من تحميل SweetAlert2

### 4. إذا ظهرت الرسائل لكن النموذج لا يُرسل
**المشكلة:** مشكلة في معالج إرسال النموذج

**التشخيص:**
```javascript
// في Console، اختبر:
document.getElementById('restoreForm')
document.getElementById('restoreBtn') 
document.getElementById('backup_file')
document.getElementById('database_id')
```

### 5. عند الضغط على زر الاستعادة
يجب أن تظهر هذه الرسائل:
```
🔍 [DEBUG] Button clicked, preventing default and triggering form submit
✅ [DEBUG] Form is valid, triggering submit event
🔍 [DEBUG] Form submission started
🔍 [DEBUG] Event object: SubmitEvent
🔍 [DEBUG] File input: <input type="file">
🔍 [DEBUG] Database select: <select>
🔍 [DEBUG] Selected file: filename.json (1234 bytes)
🔍 [DEBUG] Selected database: 1
🔍 [DEBUG] Generated session ID: restore_1234567890_abc123
🔍 [DEBUG] Showing initial progress bar
🔍 [DEBUG] Starting operation
🔍 [DEBUG] Form data prepared
🔍 [DEBUG] About to make fetch request...
```

### 6. إذا توقفت الرسائل عند "About to make fetch request"
**المشكلة:** مشكلة في إرسال fetch request

**الحلول:**
1. تحقق من CSRF token
2. تحقق من اتصال الشبكة
3. تحقق من إعدادات CORS

### 7. في الطرفية (Terminal)
عند إرسال النموذج بنجاح، يجب أن تظهر:
```
🔍 [DEBUG] POST request received
🔍 [DEBUG] POST data keys: ['csrfmiddlewaretoken', 'database_id', 'backup_type', 'clear_data', 'session_id']
🔍 [DEBUG] FILES keys: ['backup_file']
🔍 [DEBUG] Uploaded file: filename.json, size: 1234
🔍 [DEBUG] Creating RestoreProgress for session: restore_1234567890_abc123
✅ [DEBUG] RestoreProgress created: 1
🚀 [DEBUG] Starting restore process...
```

## الحلول المحتملة

### الحل 1: إعادة تحميل الصفحة
```javascript
// في Console:
location.reload();
```

### الحل 2: تشغيل JavaScript يدوياً
```javascript
// في Console:
initializeRestoreSystem();
```

### الحل 3: إرسال النموذج يدوياً
```javascript
// في Console:
const form = document.getElementById('restoreForm');
if (form) {
    form.dispatchEvent(new Event('submit', { cancelable: true }));
}
```

### الحل 4: تحقق من العناصر
```javascript
// في Console:
console.log('Form:', document.getElementById('restoreForm'));
console.log('Button:', document.getElementById('restoreBtn'));
console.log('File input:', document.getElementById('backup_file'));
console.log('Database select:', document.getElementById('database_id'));
```

### الحل 5: إرسال مباشر باستخدام fetch
```javascript
// في Console (بعد اختيار الملف وقاعدة البيانات):
const form = document.getElementById('restoreForm');
const formData = new FormData(form);
formData.append('session_id', 'manual_' + Date.now());

fetch('/odoo-db-manager/backups/upload/', {
    method: 'POST',
    body: formData,
    headers: {
        'X-Requested-With': 'XMLHttpRequest'
    }
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('Error:', error));
```

## الأدوات المساعدة

### 1. صفحة تشخيصية
```bash
# افتح في المتصفح:
file:///path/to/debug_form.html
```

### 2. سكريبت اختبار الواجهة
```bash
python test_frontend_simple.py
```

### 3. سكريپت اختبار إرسال النموذج
```bash
python test_form_submission.py
```

## خطوات الحل المقترحة

1. **افتح أدوات المطور** (F12)
2. **انتقل لتبويب Console**
3. **حمّل صفحة الاستعادة**
4. **تحقق من رسائل التشخيص**
5. **اختر ملف وقاعدة بيانات**
6. **اضغط زر الاستعادة**
7. **راقب الرسائل في Console والطرفية**
8. **إذا لم تظهر رسائل POST في الطرفية، المشكلة في الواجهة الأمامية**

## معلومات إضافية

- **الملفات المهمة:** `odoo_db_manager/templates/odoo_db_manager/backup_upload.html`
- **الدالة المهمة:** `backup_upload` في `odoo_db_manager/views.py`
- **نموذج التقدم:** `RestoreProgress` في `odoo_db_manager/models.py`

## الاتصال بالمطور
إذا استمرت المشكلة، أرسل:
1. رسائل Console كاملة
2. رسائل الطرفية
3. لقطة شاشة من صفحة الاستعادة
4. معلومات المتصفح والنظام 