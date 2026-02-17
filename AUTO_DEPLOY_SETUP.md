# 🚀 إعداد النشر التلقائي - Auto Deployment Setup

تم إنشاء سكريبت النشر التلقائي بنجاح! 

## ✅ ما تم إعداده

1. ✓ السكريبت: `/home/zakee/homeupdate/auto_deploy.sh`
2. ✓ ملف صلاحيات sudoers: `/tmp/homeupdate-sudoers`

## 🔧 خطوات الإكمال (على سيرفر الإنتاج)

### 1️⃣ إضافة صلاحيات sudo للخدمات

```bash
# تحقق من صحة ملف sudoers أولاً
sudo visudo -c -f /tmp/homeupdate-sudoers

# إذا كان صحيحاً، انقله
sudo cp /tmp/homeupdate-sudoers /etc/sudoers.d/homeupdate
sudo chmod 440 /etc/sudoers.d/homeupdate

# تأكد من الصلاحيات
sudo -l | grep homeupdate
```

### 2️⃣ إعداد Cron Job للتشغيل التلقائي

```bash
# افتح crontab
crontab -e

# أضف أحد هذه السطور:

# للتشغيل كل يوم الساعة 3:00 صباحاً
0 3 * * * /home/zakee/homeupdate/auto_deploy.sh >> /home/zakee/homeupdate/logs/cron.log 2>&1

# أو كل 6 ساعات
0 */6 * * * /home/zakee/homeupdate/auto_deploy.sh >> /home/zakee/homeupdate/logs/cron.log 2>&1

# أو كل ساعتين (للاختبار)
0 */2 * * * /home/zakee/homeupdate/auto_deploy.sh >> /home/zakee/homeupdate/logs/cron.log 2>&1
```

### 3️⃣ اختبر السكريبت يدوياً أولاً

```bash
# قبل تفعيل cron، جرّب السكريبت يدوياً
/home/zakee/homeupdate/auto_deploy.sh

# راقب الـ log
tail -f /home/zakee/homeupdate/logs/auto_deploy_*.log
```

## 📋 ماذا يفعل السكريبت؟

1. ✓ يفحص وجود تحديثات جديدة على GitHub
2. ✓ إذا لم توجد تحديثات، يخرج مباشرة (لا يعمل شيء)
3. ✓ إذا وجد تحديثات:
   - يسحب التحديثات من `main` branch
   - يثبت/يحدث packages من `requirements.txt`
   - ينفذ migrations على قاعدة البيانات
   - يشغل `setup_accounting_structure`
   - يشغل `create_customer_accounts`
   - يجمع static files
   - يعيد تشغيل جميع الخدمات (Django + Celery + Nginx)
4. ✓ يحفظ logs مفصلة في `logs/auto_deploy_YYYYMMDD_HHMMSS.log`
5. ✓ ينظف logs القديمة (أكثر من 30 يوم)

## 🔄 Rollback تلقائي

السكريبت يحتوي على آلية Rollback:
- إذا فشلت أي خطوة، يرجع تلقائياً للـ commit السابق
- يعيد تشغيل الخدمات
- يسجل الخطأ في الـ log

## 🔔 إضافة إشعارات Telegram (اختياري)

إذا أردت إشعارات Telegram عند كل deployment:

1. أنشئ bot عبر @BotFather واحصل على TOKEN
2. احصل على CHAT_ID من @userinfobot
3. عدّل السكريبت (السطر 23-29) وفك التعليق
4. ضع TOKEN و CHAT_ID

## 📊 مراقبة Cron Jobs

```bash
# عرض cron jobs الحالية
crontab -l

# مشاهدة log الـ cron
tail -f /home/zakee/homeupdate/logs/cron.log

# عرض آخر deployments
ls -lt /home/zakee/homeupdate/logs/auto_deploy_*.log | head -5
```

## 🛠️ استكشاف الأخطاء

### السكريبت لا يعمل من cron؟
```bash
# تأكد من الصلاحيات
ls -la /home/zakee/homeupdate/auto_deploy.sh

# تأكد من PATH في cron
# أضف في أول crontab:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### خطأ في sudo restart؟
```bash
# تحقق من sudoers
sudo cat /etc/sudoers.d/homeupdate

# جرّب يدوياً
sudo systemctl restart homeupdate.service
```

## 📝 ملاحظات مهمة

- السكريبت **لا يعمل** إذا لم تكن هناك تحديثات (موفر للموارد)
- التغييرات المحلية على سيرفر الإنتاج يتم stash لها تلقائياً
- Migrations تُنفذ تلقائياً (تأكد أن migrations جاهزة قبل الـ push)
- Static files يتم جمعها تلقائياً

## ⚠️ تحذير

**على سيرفر الإنتاج فقط!** لا تستخدم هذا على بيئة التطوير.

---

✅ بعد إكمال الخطوات أعلاه، سيعمل النظام تلقائياً!
