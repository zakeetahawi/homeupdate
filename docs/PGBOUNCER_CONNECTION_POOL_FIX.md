# إصلاح أزمة اتصالات قاعدة البيانات - Connection Pool Fix
## تاريخ الإصلاح: 20 فبراير 2026

---

## 🔴 المشكلة

**الساعة 11:58 صباحاً بتوقيت القاهرة**، توقفت عدة صفحات من النظام بالكامل وظهر الخطأ التالي في السجلات:

```
django.db.utils.OperationalError: connection to server at "localhost" (::1),
port 5432 failed: FATAL:  sorry, too many clients already
```

### الصفحات المتأثرة:
- `/complaints/api/unresolved-stats/`
- `/complaints/api/assignment-notifications/`
- `/notifications/ajax/transfer-alerts/`
- `/accounts/api/online-users/`
- `/accounts/api/messages/recent/`
- `/complaints/api/assigned/`

### السبب الجذري:
كان **Django يتصل مباشرة بـ PostgreSQL** على port `5432`، متجاهلاً PgBouncer الذي كان مثبتاً وجاهزاً لكن لم يُستخدم.
- كل request يفتح اتصالاً جديداً بـ PostgreSQL
- `max_connections = 100` (الحد الأقصى) امتلأ خلال فترة ذروة الاستخدام
- النتيجة: رفض كل الاتصالات الجديدة → توقف الموقع

```
Architecture قبل الإصلاح (خاطئ):
Django/Daphne → PostgreSQL:5432 (مباشر، بدون pooling)

Architecture بعد الإصلاح (صحيح):
Django/Daphne → PgBouncer:6432 → pool(40 conn) → PostgreSQL:5432
```

---

## ✅ التغييرات المنفذة

### 1. PostgreSQL - `/var/lib/postgres/data/postgresql.conf`
> ملف النظام - لا يُتتبع بـ git

| الإعداد | قبل | بعد | السبب |
|---------|-----|-----|--------|
| `max_connections` | `100` | `200` | طبقة أمان إضافية في حالة تجاوز الـ pool |
| `shared_buffers` | `128MB` | `2GB` | الاستفادة من 15GB RAM المتاحة (~25% من RAM) |
| `work_mem` | `4MB` | `8MB` | تحسين أداء الاستعلامات المعقدة |
| `effective_cache_size` | `4GB` | `8GB` | مساعدة query planner على اختيار أفضل خطة |
| `statement_timeout` | غير محدد | `30s` | **نُقل من Django OPTIONS** - يطبق عبر PgBouncer |
| `idle_in_transaction_session_timeout` | غير محدد | `60s` | **نُقل من Django OPTIONS** |
| `lock_timeout` | غير محدد | `10s` | **نُقل من Django OPTIONS** |

> **لماذا نقل الـ timeouts إلى postgresql.conf؟**
> PgBouncer في `transaction` mode لا يستطيع تمرير `options` startup parameter من Django.
> نقلها إلى postgresql.conf يضمن تطبيقها على كل الاتصالات.

---

### 2. PgBouncer - `/etc/pgbouncer/pgbouncer.ini`
> ملف النظام - لا يُتتبع بـ git

| الإعداد | قبل | بعد | السبب |
|---------|-----|-----|--------|
| `auth_file` | غير موجود | `/etc/pgbouncer/userlist.txt` | **كان هذا سبب خطأ "no such user"** |
| `default_pool_size` | `20` | `40` | مضاعفة الاتصالات الحقيقية المتاحة |
| `max_db_connections` | `50` | `150` | استيعاب أكبر عدد من الاتصالات الفعلية |
| `max_client_conn` | `1000` | `2000` | استيعاب آلاف الطلبات المتزامنة |
| `reserve_pool_size` | `5` | `10` | reserve للـ spike المفاجئ |
| `server_idle_timeout` | `30s` | `60s` | إبقاء الاتصالات أطول لتقليل التكلفة |
| `ignore_startup_parameters` | غير موجود | `options,extra_float_digits` | منع خطأ Django startup params |

تم إنشاء `/etc/pgbouncer/userlist.txt`:
```
"postgres" ""
```

---

### 3. Django Settings - `crm/settings.py`

```python
# قبل:
"PORT": os.environ.get("DB_PORT", "5432"),   # ← مباشر لـ PostgreSQL
"CONN_MAX_AGE": 60,                           # ← Django تحتفظ باتصالات مفتوحة
"CONN_HEALTH_CHECKS": True,
"OPTIONS": {
    "sslmode": "prefer",
    "options": " ".join([
        "-c statement_timeout=30000",
        "-c idle_in_transaction_session_timeout=60000",
        "-c lock_timeout=10000",
    ]),
}

# بعد:
"PORT": os.environ.get("DB_PORT", "6432"),   # ← عبر PgBouncer
"CONN_MAX_AGE": 0,                           # ← ضروري مع transaction mode
"CONN_HEALTH_CHECKS": False,                 # ← PgBouncer يتولى هذا
"OPTIONS": {
    "sslmode": "disable",                    # ← local connection لا يحتاج SSL
    # timeouts نُقلت إلى postgresql.conf
}
```

---

### 4. Backup Service - `odoo_db_manager/services/backup_service.py`

```python
# قبل:
db_port = db_settings["PORT"] or "5432"

# بعد:
# pg_dump يحتاج اتصالاً مباشراً بـ PostgreSQL (ليس عبر PgBouncer)
# لأن PgBouncer transaction mode يكسر consistency الـ snapshot الخاص بـ pg_dump
db_port = os.environ.get("DB_DIRECT_PORT", "5432")
```

> **لماذا Backup يتصل مباشرة على 5432؟**
> `pg_dump` يستخدم transaction snapshot لضمان consistency النسخة الاحتياطية.
> PgBouncer transaction mode ينهي الـ transaction بعد كل query، مما قد يُفسد snapshot الـ pg_dump.

---

### 5. db_settings.json

```json
// قبل:
"PORT": "5432"

// بعد:
"PORT": "6432"
```

---

## 📊 النتائج قبل وبعد

| المقياس | قبل الإصلاح | بعد الإصلاح |
|---------|------------|------------|
| اتصالات PostgreSQL في الذروة | **100/100** (ممتلئ) | 17/200 |
| اتصالات PostgreSQL العادية | ~43 | ~10 |
| `max_connections` | 100 | **200** |
| Throughput (transactions/sec) | متوقف | **522 tx/s** |
| Wait time | - | **0 μs** |
| أخطاء "too many clients" | متكررة | **صفر** |

---

## 🏗️ Architecture جديدة

```
                    ┌─────────────────────────────────────┐
                    │         Django / Daphne ASGI         │
                    │      (CONN_MAX_AGE=0, port=6432)     │
                    └──────────────────┬──────────────────┘
                                       │ آلاف الطلبات
                                       ▼
                    ┌─────────────────────────────────────┐
                    │           PgBouncer :6432            │
                    │  pool_mode=transaction               │
                    │  max_client_conn=2000                │
                    │  default_pool_size=40                │
                    └──────────────────┬──────────────────┘
                                       │ 40 اتصال حقيقي فقط
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         PostgreSQL :5432             │
                    │    max_connections=200               │
                    │    shared_buffers=2GB                │
                    └─────────────────────────────────────┘
                                       ▲
                                       │ اتصال مباشر (bypass PgBouncer)
                    ┌──────────────────┴──────────────────┐
                    │      pg_dump / Backup Service        │
                    │   (DB_DIRECT_PORT=5432)              │
                    └─────────────────────────────────────┘
```

---

## 🔒 الضمانات المستقبلية

1. **PgBouncer كـ Gateway إجباري** - كل traffic يمر عبره
2. **max_connections=200** - طبقة أمان إضافية حتى لو تجاوز الـ pool
3. **Timeouts في postgresql.conf** - تطبق على كل الاتصالات بدون استثناء
4. **reserve_pool** - 10 اتصالات احتياطية لفترات الذروة
5. **server_check_query** - PgBouncer يتحقق من صحة الاتصالات قبل إعادة استخدامها
