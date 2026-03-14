# دليل إدارة خدمات نظام El-Khawaga ERP

## البنية الحالية للخدمات

```
systemd
├── run-production.service      ← Django + Celery + النسخ الاحتياطي
│     └── start-service.sh
│           ├── daphne (خادم ASGI على منفذ 8000)
│           ├── celery worker
│           └── celery beat
│
└── cloudflared.service         ← نفق Cloudflare (مستقل تماماً)
      └── cloudflared tunnel run
```

> **لماذا مستقلان؟**
> cloudflared يتحدث نفسه تلقائياً ويوقف نفسه عند التحديث.
> بفصله إلى service مستقل، يعيد systemd تشغيله خلال 5 ثوانٍ تلقائياً
> دون أن يؤثر ذلك على Django أو Celery.

---

## أوامر التشغيل اليومية

### عرض حالة جميع الخدمات دفعة واحدة
```bash
sudo systemctl status run-production.service cloudflared.service
```

### إعادة تشغيل كل شيء (بعد تحديث الكود مثلاً)
```bash
sudo systemctl restart run-production.service
sudo systemctl restart cloudflared.service
```

### إعادة تشغيل خدمة واحدة فقط
```bash
# فقط Django/Celery
sudo systemctl restart run-production.service

# فقط النفق
sudo systemctl restart cloudflared.service
```

### إيقاف خدمة
```bash
sudo systemctl stop run-production.service
sudo systemctl stop cloudflared.service
```

### تشغيل خدمة
```bash
sudo systemctl start run-production.service
sudo systemctl start cloudflared.service
```

---

## السجلات (Logs)

| الخدمة | السجل |
|--------|-------|
| بدء التشغيل العام | `logs/startup.log` |
| Django (أخطاء/معلومات) | `logs/django.log` |
| Daphne (طلبات HTTP) | `logs/daphne_access.log` |
| Celery Worker | `logs/celery_worker.log` |
| Celery Beat | `logs/celery_beat.log` |
| Cloudflare Tunnel | `logs/cloudflared.log` |
| أخطاء عامة | `logs/errors.log` |

### مشاهدة السجلات مباشرة (live)
```bash
# سجل Django
tail -f logs/django.log

# سجل النفق
tail -f logs/cloudflared.log

# سجل systemd (أكثر تفصيلاً)
journalctl -u run-production.service -f
journalctl -u cloudflared.service -f
```

---

## إنشاء خدمة systemd جديدة (خطوات عامة)

### 1. إنشاء ملف الـ service
```bash
sudo nano /etc/systemd/system/اسم-الخدمة.service
```

### 2. محتوى الملف الأساسي
```ini
[Unit]
Description=وصف الخدمة
After=network.target

[Service]
Type=simple
User=zakee
WorkingDirectory=/home/zakee/homeupdate
ExecStart=/المسار/الكامل/للأمر
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. تفعيل وتشغيل
```bash
sudo systemctl daemon-reload          # تحديث systemd ليقرأ الملف الجديد
sudo systemctl enable اسم-الخدمة     # تشغيل تلقائي مع الإقلاع
sudo systemctl start اسم-الخدمة      # تشغيل فوري
sudo systemctl status اسم-الخدمة     # التحقق
```

### 4. تعديل service موجود
```bash
sudo nano /etc/systemd/system/اسم-الخدمة.service
# بعد الحفظ:
sudo systemctl daemon-reload
sudo systemctl restart اسم-الخدمة
```

### 5. حذف service
```bash
sudo systemctl stop اسم-الخدمة
sudo systemctl disable اسم-الخدمة
sudo rm /etc/systemd/system/اسم-الخدمة.service
sudo systemctl daemon-reload
```

---

## الخدمات الحالية في النظام

| الملف | الوصف | يبدأ مع الإقلاع؟ |
|-------|-------|-----------------|
| `run-production.service` | Django + Celery | ✅ |
| `cloudflared.service` | نفق Cloudflare | ✅ |
| `redis.service` | Redis/Valkey | ✅ |
| `postgres-healthcheck.service` | مراقبة PostgreSQL | ✅ |
| `crm-production.service` | (قديم - غير مستخدم) | - |

---

## ماذا يحدث عند تحديث cloudflared تلقائياً؟

```
1. cloudflared ينزّل النسخة الجديدة
2. يوقف نفسه (exit code طبيعي)
3. systemd يلاحظ التوقف
4. systemd ينتظر 5 ثوانٍ (RestartSec=5)
5. systemd يشغّل النسخة الجديدة تلقائياً
6. النفق يعود خلال ~10 ثوانٍ
```

Django وCelery يبقيان شغّالَين طوال الوقت ولا يتأثران.

---

## استكشاف الأخطاء

### النفق متوقف
```bash
sudo systemctl status cloudflared.service
tail -50 logs/cloudflared.log
sudo systemctl restart cloudflared.service
```

### Django لا يستجيب
```bash
sudo systemctl status run-production.service
tail -50 logs/startup.log
tail -50 logs/django.log
sudo systemctl restart run-production.service
```

### فحص المنافذ
```bash
ss -tlnp | grep 8000    # Daphne
ss -tlnp | grep 6379    # Redis
```

### بعد أي تعديل على ملفات الـ service
```bash
sudo systemctl daemon-reload
```
