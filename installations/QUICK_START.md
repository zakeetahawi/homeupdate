# 🚀 دليل التشغيل السريع - نظام التركيبات المتقدم

## 📋 المتطلبات الأساسية

```bash
# المكتبات المطلوبة
pip install reportlab openpyxl
```

## ⚡ التشغيل السريع (3 خطوات)

### 1️⃣ إعداد النظام
```bash
# تشغيل سكريبت الإعداد التلقائي
python installations/setup_new_system.py
```

### 2️⃣ تشغيل الخادم
```bash
# تشغيل خادم Django
python manage.py runserver
```

### 3️⃣ الوصول للنظام
- **لوحة التحكم**: http://localhost:8000/installations/
- **المدير**: admin / admin123

---

## 🎯 الميزات الرئيسية

### 📊 لوحة التحكم
- إحصائيات شاملة
- إنذارات فورية
- نظرة عامة على الأداء

### 📅 التقويم الذكي
- جدولة ديناميكية
- فحص التعارضات
- توزيع الأحمال

### 👥 إدارة الفنيين
- تتبع الأداء
- تحليل الإنتاجية
- إدارة السعة

### 🏭 واجهة المصنع
- تحديث حالة الإنتاج
- إدارة الأولويات
- تتبع الجاهزية

### 📈 التحليلات
- تقارير شاملة
- تحليلات تنبؤية
- مقارنة الأداء

### 📄 التصدير والطباعة
- تصدير PDF
- تصدير Excel
- طباعة الجداول

---

## 🔧 الأوامر المفيدة

### فحص الإنذارات
```bash
python manage.py check_alerts
```

### إنشاء تقرير يومي
```bash
python manage.py generate_daily_report
```

### تنظيف البيانات القديمة
```bash
python manage.py cleanup_old_data
```

### تشغيل الاختبارات
```bash
# جميع الاختبارات
python installations/run_tests.py all

# اختبارات الأداء
python installations/run_tests.py performance

# اختبار محدد
python installations/run_tests.py InstallationModelTests
```

---

## 📱 الواجهات الرئيسية

| الواجهة | الرابط | الوصف |
|---------|--------|-------|
| لوحة التحكم | `/installations/` | الصفحة الرئيسية |
| قائمة التركيبات | `/installations/list/` | إدارة التركيبات |
| التقويم الذكي | `/installations/calendar/` | الجدولة |
| تحليل الفنيين | `/installations/technician-analytics/` | الأداء |
| واجهة المصنع | `/installations/factory/` | الإنتاج |
| التعديل السريع | `/installations/quick-edit/` | التحديث |

---

## 🎨 الحسابات التجريبية

### المدير
- **المستخدم**: admin
- **كلمة المرور**: admin123
- **الصلاحيات**: كاملة

### الفنيين
- **فني 1**: technician1 / tech123
- **فني 2**: technician2 / tech123  
- **فني 3**: technician3 / tech123

---

## 🚨 نظام الإنذارات

### أنواع الإنذارات
- **حرج**: تجاوز 13 تركيب/يوم
- **عالي**: تجاوز 20 شباك/فني
- **متوسط**: تأخير في التركيبات
- **منخفض**: إكمال التركيبات

### إعدادات الإنذارات
```python
# في settings.py
INSTALLATION_SETTINGS = {
    'MAX_DAILY_INSTALLATIONS': 13,
    'MAX_TECHNICIAN_WINDOWS': 20,
    'ALERT_SETTINGS': {
        'ENABLE_EMAIL_ALERTS': True,
        'SEND_DAILY_SUMMARY': True,
    }
}
```

---

## 📊 البيانات التجريبية

النظام يأتي مع:
- ✅ 3 فرق تركيب
- ✅ 3 فنيين متخصصين
- ✅ 20 تركيب تجريبي
- ✅ إنذارات تلقائية
- ✅ تقارير جاهزة

---

## 🔍 استكشاف الأخطاء

### مشاكل شائعة

#### خطأ في الهجرة
```bash
# حذف ملفات الهجرة وإعادة إنشائها
rm installations/migrations/0*.py
python manage.py makemigrations installations
python manage.py migrate
```

#### خطأ في المكتبات
```bash
# تثبيت المكتبات المطلوبة
pip install reportlab openpyxl
```

#### خطأ في الصلاحيات
```bash
# إنشاء مستخدم إداري جديد
python manage.py createsuperuser
```

### سجلات النظام
```bash
# عرض سجلات التركيبات
tail -f logs/installations.log

# عرض سجلات الأخطاء
tail -f logs/installations_errors.log
```

---

## 📞 الدعم والمساعدة

### الملفات المرجعية
- **الدليل الشامل**: `README_NEW_SYSTEM.md`
- **الاختبارات**: `tests_new.py`
- **الإعدادات**: `settings_new.py`

### الأوامر المساعدة
```bash
# عرض مساعدة الأوامر
python manage.py help check_alerts
python manage.py help generate_daily_report
python manage.py help cleanup_old_data
```

### فحص حالة النظام
```bash
# فحص شامل للنظام
python manage.py check
python manage.py check --deploy
```

---

## 🎉 مبروك!

النظام الآن جاهز للاستخدام. استمتع بالميزات المتقدمة لإدارة التركيبات!

### الخطوات التالية:
1. 🔐 تغيير كلمات المرور الافتراضية
2. ⚙️ تخصيص الإعدادات حسب احتياجاتك
3. 📧 إعداد البريد الإلكتروني للإنذارات
4. 👥 إضافة المستخدمين الحقيقيين
5. 📊 بدء استخدام النظام

---

**💡 نصيحة**: ابدأ بتجربة البيانات التجريبية لفهم النظام، ثم احذفها وأضف بياناتك الحقيقية.
