# 🧪 اختبار سريع لنظام التخصيصات

## كيف تتأكد أن كل شيء يعمل؟

### الاختبار السريع (دقيقتين):

#### 1. احفظ تخصيص
```
1. افتح: /accounts/theme-customization/
2. اذهب لتبويب "🌈 الألوان الأساسية"
3. غيّر اللون الأساسي → أي لون (مثلاً أحمر)
4. احفظ
5. يجب أن تظهر: ✅ تم حفظ تخصيصات الثيم بنجاح!
```

#### 2. تحقق من التطبيق
```
6. اذهب للصفحة الرئيسية: /
7. انظر للأزرار - هل تغير لونها؟
   ✅ نعم → يعمل!
   ❌ لا → هناك مشكلة
```

#### 3. تحقق من الثبات
```
8. حدّث الصفحة (F5)
9. هل اللون لا يزال كما هو؟
   ✅ نعم → التخصيصات ثابتة!
   ❌ لا → راجع التوثيق
```

---

## ✅ النتيجة المتوقعة

بعد الحفظ:
- ✅ جميع صفحات النظام تستخدم الألوان الجديدة
- ✅ حتى بعد تحديث الصفحة
- ✅ حتى بعد تسجيل الخروج والدخول مرة أخرى

---

## 🔍 فحص سريع في Console

```javascript
// افتح Console (F12) واكتب:
getComputedStyle(document.documentElement).getPropertyValue('--primary')

// يجب أن يرجع اللون الذي اخترته
// مثال: "#FF0000" أو اللون المخصص
```

---

## 📁 الملفات الرئيسية

1. ✅ `/accounts/context_processors.py` - يجلب التخصيصات
2. ✅ `/crm/settings.py` - مُسجل في TEMPLATES
3. ✅ `/templates/base.html` - يطبق التخصيصات

---

## 💡 إذا لم يعمل

### تحقق من:

1. **هل تم الحفظ؟**
```bash
python manage.py shell
>>> from accounts.models import User
>>> from accounts.theme_customization import ThemeCustomization
>>> user = User.objects.first()
>>> ThemeCustomization.objects.filter(user=user).exists()
True  # ✅ يجب أن يكون True
```

2. **هل Context Processor مُسجل؟**
```bash
python manage.py shell
>>> from django.conf import settings
>>> 'accounts.context_processors.theme_customization' in settings.TEMPLATES[0]['OPTIONS']['context_processors']
True  # ✅ يجب أن يكون True
```

3. **أعد تشغيل Server**
```bash
# أوقف Server (Ctrl+C)
# ثم شغله مرة أخرى
python manage.py runserver
```

---

**جرّب الآن!** 🚀
