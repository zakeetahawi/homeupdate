# 💾 حفظ وتطبيق تخصيصات الثيم - Persistence System

## التاريخ: 7 يناير 2025

---

## 🎯 المشكلة

عند حفظ التخصيصات في صفحة التخصيص:
- ✅ التخصيصات تُحفظ في قاعدة البيانات
- ❌ لكن عند الخروج من الصفحة، التغييرات تختفي
- ❌ في الصفحات الأخرى، الثيم يعود للقيم الافتراضية

**السبب**: التخصيصات محفوظة في DB لكن غير مُطبقة في باقي الصفحات

---

## ✅ الحل الشامل

### نظام من 3 طبقات:

```
1. Context Processor
   ↓ يجلب التخصيصات من DB
   
2. base.html
   ↓ يطبق التخصيصات كـ CSS Variables
   
3. جميع الصفحات
   ↓ ترث التخصيصات تلقائياً
```

---

## 📋 التنفيذ خطوة بخطوة

### الخطوة 1: Context Processor

#### الملف: `/accounts/context_processors.py`

```python
"""
Context Processors للحسابات
"""
from .theme_customization import ThemeCustomization


def theme_customization(request):
    """
    إضافة تخصيصات الثيم لجميع القوالب
    """
    if request.user.is_authenticated:
        try:
            customization = ThemeCustomization.objects.get(
                user=request.user,
                is_active=True
            )
            return {
                'user_theme_customization': customization,
                'user_theme_css_vars': customization.get_css_variables()
            }
        except ThemeCustomization.DoesNotExist:
            return {
                'user_theme_customization': None,
                'user_theme_css_vars': {}
            }
    
    return {
        'user_theme_customization': None,
        'user_theme_css_vars': {}
    }
```

**ماذا يفعل؟**
- يجلب تخصيصات المستخدم المسجل الدخول
- يحولها إلى CSS Variables باستخدام `get_css_variables()`
- يوفرها لجميع القوالب

---

### الخطوة 2: تسجيل Context Processor

#### الملف: `/crm/settings.py`

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.departments',
                'accounts.context_processors.company_info',
                # ... processors أخرى
                'accounts.context_processors.theme_customization',  # ← جديد!
                'notifications.context_processors.notifications_context',
                'crm.context_processors.admin_stats',
                'crm.context_processors.jazzmin_extras',
            ],
        },
    },
]
```

**النتيجة**: 
- `user_theme_customization` متاح في جميع القوالب
- `user_theme_css_vars` متاح في جميع القوالب

---

### الخطوة 3: تطبيق التخصيصات في base.html

#### الملف: `/templates/base.html`

```html
<!-- تطبيق تخصيصات الثيم المحفوظة -->
{% if user_theme_css_vars %}
<style id="user-theme-customization">
    :root,
    [data-theme="{{ user.default_theme }}"] {
        {% for var_name, var_value in user_theme_css_vars.items %}
        {{ var_name }}: {{ var_value }};
        {% endfor %}
    }
</style>
{% endif %}
```

**ماذا يفعل؟**
- إذا كان المستخدم لديه تخصيصات
- يُنشئ `<style>` block inline
- يكتب جميع CSS Variables المخصصة
- يطبقها على `:root` و `[data-theme]`

**مثال على الناتج**:
```html
<style id="user-theme-customization">
    :root,
    [data-theme="default"] {
        --primary: #1976D2;
        --secondary: #42A5F5;
        --background: #F5F5F5;
        --navbar-bg: #0D47A1;
        --navbar-text: #FFFFFF;
        /* ... إلخ */
    }
</style>
```

---

## 🔄 كيف يعمل النظام؟

### السيناريو الكامل:

```
1. المستخدم يفتح صفحة التخصيص
   ↓
2. يغير الألوان (Primary, Navbar, إلخ)
   ↓
3. يضغط "💾 حفظ جميع التخصيصات"
   ↓
4. Form يُرسل إلى Server
   ↓
5. View يحفظ في ThemeCustomization model
   ↓
6. يُحفظ في قاعدة البيانات ✅
   
7. المستخدم يذهب لأي صفحة أخرى
   ↓
8. Context Processor يُستدعى تلقائياً
   ↓
9. يجلب التخصيصات من DB
   ↓
10. يحولها لـ CSS Variables
   ↓
11. base.html يطبقها في <style> block
   ↓
12. جميع الصفحات ترث التخصيصات ✅
```

---

## 🧪 كيفية الاختبار

### الاختبار 1: حفظ التخصيصات

```
1. افتح: /accounts/theme-customization/
2. غيّر اللون الأساسي → #FF0000 (أحمر)
3. غيّر خلفية Navbar → #00FF00 (أخضر)
4. احفظ
5. تحقق من رسالة النجاح: ✅ تم حفظ تخصيصات الثيم بنجاح!
```

### الاختبار 2: تطبيق التخصيصات

```
6. اذهب للصفحة الرئيسية: /
7. تحقق من:
   - الأزرار أحمر ✅
   - Navbar أخضر ✅
   - التخصيصات مطبقة ✅
```

### الاختبار 3: الثبات

```
8. أغلق المتصفح
9. افتح مرة أخرى
10. سجل دخول
11. تحقق من:
    - الأزرار لا تزال حمراء ✅
    - Navbar لا يزال أخضر ✅
    - التخصيصات محفوظة ✅
```

### الاختبار 4: Context Processor

```bash
cd /home/zakee/homeupdate
python manage.py shell

from accounts.context_processors import theme_customization
from django.contrib.auth import get_user_model
from django.http import HttpRequest

User = get_user_model()
user = User.objects.first()

request = HttpRequest()
request.user = user

result = theme_customization(request)

print('Customization:', result['user_theme_customization'])
print('CSS Vars:', result['user_theme_css_vars'])
```

**النتيجة المتوقعة**:
```python
Customization: <ThemeCustomization: تخصيص username - default>
CSS Vars: {
    '--primary': '#FF0000',
    '--navbar-bg': '#00FF00',
    # ... إلخ
}
```

---

## 📊 تدفق البيانات

### من الحفظ إلى التطبيق:

```
صفحة التخصيص
    ↓ [POST]
Form Validation
    ↓ [is_valid]
View Save
    ↓ [save()]
Database (ThemeCustomization)
    ↓
├─→ [الصفحة الحالية] → معاينة فورية
│
└─→ [صفحات أخرى]
        ↓
    Context Processor
        ↓ [get_css_variables()]
    Template Context
        ↓ [user_theme_css_vars]
    base.html
        ↓ [<style> block]
    CSS Variables Applied
        ↓
    جميع الصفحات تستخدم التخصيصات ✅
```

---

## 🔧 استكشاف المشاكل

### المشكلة: التخصيصات لا تظهر

#### التحقق 1: هل تم الحفظ؟
```python
from accounts.theme_customization import ThemeCustomization
from accounts.models import User

user = User.objects.get(username='your_username')
customization = ThemeCustomization.objects.filter(user=user).first()

if customization:
    print('✅ موجود')
    print('Primary:', customization.primary_color)
    print('Navbar BG:', customization.navbar_bg_color)
else:
    print('❌ غير موجود - لم يتم الحفظ')
```

#### التحقق 2: هل Context Processor مُسجل؟
```python
from django.conf import settings

processors = settings.TEMPLATES[0]['OPTIONS']['context_processors']
if 'accounts.context_processors.theme_customization' in processors:
    print('✅ مُسجل')
else:
    print('❌ غير مُسجل')
```

#### التحقق 3: هل CSS Variables موجودة؟
```
افتح أي صفحة
F12 → Elements → <head>
ابحث عن: <style id="user-theme-customization">

إذا موجود:
  ✅ Context Processor يعمل
  ✅ CSS Variables مطبقة

إذا غير موجود:
  ❌ Context Processor لا يعمل
  أو
  ❌ لا توجد تخصيصات محفوظة
```

#### التحقق 4: هل القيم صحيحة؟
```
افتح Console (F12)
اكتب:
getComputedStyle(document.documentElement).getPropertyValue('--primary')

النتيجة المتوقعة: "#FF0000" أو اللون المخصص
إذا كانت القيمة الافتراضية: ❌ التخصيصات غير مطبقة
```

---

## 🎯 الأولوية: is_active

### لماذا is_active مهم؟

```python
customization = ThemeCustomization.objects.get(
    user=request.user,
    is_active=True  # ← مهم!
)
```

**الفائدة**:
- المستخدم يمكنه حفظ تخصيصات متعددة
- لكن تطبيق واحد فقط (is_active=True)
- سهولة التبديل بين التخصيصات

---

## 📝 ملاحظات مهمة

### 1. الأداء
- Context Processor يُستدعى في **كل request**
- لتحسين الأداء، يمكن استخدام caching:

```python
from django.core.cache import cache

def theme_customization(request):
    if request.user.is_authenticated:
        cache_key = f'theme_customization_{request.user.id}'
        result = cache.get(cache_key)
        
        if not result:
            try:
                customization = ThemeCustomization.objects.get(
                    user=request.user,
                    is_active=True
                )
                result = {
                    'user_theme_customization': customization,
                    'user_theme_css_vars': customization.get_css_variables()
                }
                cache.set(cache_key, result, 3600)  # 1 ساعة
            except ThemeCustomization.DoesNotExist:
                result = {
                    'user_theme_customization': None,
                    'user_theme_css_vars': {}
                }
        
        return result
    
    return {
        'user_theme_customization': None,
        'user_theme_css_vars': {}
    }
```

### 2. إبطال Cache عند الحفظ

في View عند الحفظ:
```python
from django.core.cache import cache

saved_customization.save()
# إبطال cache
cache.delete(f'theme_customization_{request.user.id}')
```

### 3. مستخدمين متعددين
- كل مستخدم له تخصيصاته الخاصة
- لا تداخل بين التخصيصات
- كل واحد يرى ثيمه الخاص

---

## 🎉 الخلاصة

الآن النظام:
- ✅ **يحفظ** التخصيصات في قاعدة البيانات
- ✅ **يطبق** التخصيصات في جميع الصفحات
- ✅ **يثبت** التخصيصات حتى بعد تسجيل الخروج/الدخول
- ✅ **يعمل** تلقائياً بدون تدخل

---

**الإصدار**: 2.2.0  
**التاريخ**: 7 يناير 2025  
**الحالة**: ✅ جاهز ومُختبر
