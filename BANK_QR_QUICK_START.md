# 🚀 خطوات تشغيل نظام QR للحسابات البنكية

## ✅ **1. تطبيق التغييرات على قاعدة البيانات**

```bash
cd /home/zakee/homeupdate

# تطبيق Migration
python manage.py migrate accounting

# أو التحقق أولاً
python manage.py showmigrations accounting
```

---

## ✅ **2. إضافة بيانات حساب البنك (من الصورة المرفقة)**

### **من Django Shell:**

```bash
python manage.py shell
```

ثم نفذ:

```python
from accounting.models import BankAccount

# إضافة بنك CIB بناءً على الصورة المرفقة
bank_cib = BankAccount.objects.create(
    bank_name="بنك CIB شركات",
    bank_name_en="CIB Corporate Bank",
    account_number="100054913731",
    iban="",  # أضف IBAN إن وجد
    swift_code="CIBEEGCX",  # افتراضي لـ CIB
    branch="",  # أضف الفرع إن وجد
    account_holder="الخواجة",
    account_holder_en="Elkhawaga",
    currency="EGP",
    is_primary=True,
    is_active=True,
    show_in_qr=True,
    display_order=1,
)

print(f"✅ تم إنشاء الحساب: {bank_cib.unique_code}")
```

### **من Django Admin (الأسهل):**

1. افتح: `http://localhost:8000/admin/`
2. اذهب إلى: **Accounting → Bank Accounts → Add**
3. أدخل البيانات:
   - **اسم البنك:** بنك CIB شركات
   - **Bank Name (EN):** CIB Corporate Bank
   - **رقم الحساب:** 100054913731
   - **صاحب الحساب:** الخواجة
   - **العملة:** EGP
   - ✅ **حساب رئيسي**
   - ✅ **نشط**
   - ✅ **عرض في QR**
4. احفظ

---

## ✅ **3. توليد QR Code**

```bash
# توليد QR لجميع الحسابات
python manage.py generate_bank_qr

# أو من Admin:
# حدد الحساب → Actions → "🔲 توليد QR Codes" → Go
```

---

## ✅ **4. اختبار محلي (قبل Cloudflare)**

افتح المتصفح:

```
# صفحة الحساب
http://localhost:8000/accounting/bank-qr/CIB001/

# جميع الحسابات
http://localhost:8000/accounting/bank-qr-all/
```

---

## ✅ **5. إعداد Cloudflare (للنشر النهائي)**

### **أ) تحديث `.env`:**

```bash
nano .env
```

أضف أو عدّل:

```env
# Cloudflare Settings
CLOUDFLARE_WORKER_URL=https://qr.elkhawaga.uk
CLOUDFLARE_ACCOUNT_ID=your-cloudflare-account-id
CLOUDFLARE_SYNC_API_KEY=your-api-token
CLOUDFLARE_KV_NAMESPACE_ID=your-kv-namespace-id
CLOUDFLARE_SYNC_ENABLED=True

# Site Settings
SITE_NAME=الخواجة
MAIN_SITE_URL=https://elkhawaga.com
```

### **ب) نشر Worker:**

```bash
cd cloudflare-worker

# تسجيل الدخول (إذا لم تكن مسجلاً)
wrangler login

# نشر
wrangler deploy
```

### **ج) مزامنة البيانات:**

```bash
cd /home/zakee/homeupdate

# مزامنة جميع الحسابات
python manage.py sync_bank_accounts

# أو من Admin:
# حدد الحساب → Actions → "☁️ مزامنة مع Cloudflare" → Go
```

---

## ✅ **6. اختبار النهائي على Cloudflare**

افتح المتصفح:

```
# صفحة حساب CIB
https://qr.elkhawaga.uk/bank/CIB001

# جميع الحسابات
https://qr.elkhawaga.uk/bank/all
```

---

## ✅ **7. طباعة QR Code**

### **من Admin:**

1. حدد الحساب(ات) المطلوبة
2. اختر: **"📄 تصدير PDF"**
3. انقر "Go"
4. سيتم تنزيل PDF جاهز للطباعة

---

## 🎯 **اختبار سريع للنظام الكامل**

```bash
# 1. Migration
python manage.py migrate accounting

# 2. إضافة حساب تجريبي
python manage.py shell -c "
from accounting.models import BankAccount
bank = BankAccount.objects.create(
    bank_name='بنك CIB شركات',
    bank_name_en='CIB Corporate',
    account_number='100054913731',
    account_holder='الخواجة',
    account_holder_en='Elkhawaga',
    currency='EGP',
    is_primary=True,
    is_active=True,
)
print(f'✅ تم إنشاء: {bank.unique_code}')
"

# 3. توليد QR
python manage.py generate_bank_qr

# 4. عرض النتيجة
echo "افتح: http://localhost:8000/admin/accounting/bankaccount/"
```

---

## 📝 **ملاحظات مهمة**

1. **الكود الفريد** يتم توليده تلقائياً من أول 3 أحرف من اسم البنك بالإنجليزية + رقم تسلسلي
   - مثال: `CIB` → `CIB001`, `CIB002`, ...
   - مثال: `NBE` → `NBE001`, `NBE002`, ...

2. **حساب رئيسي واحد فقط:**
   - عند تحديد حساب كـ "رئيسي"، يتم إلغاء تفعيل الخاصية من الحسابات الأخرى تلقائياً

3. **QR URL:**
   - محلي: `http://localhost:8000/accounting/bank-qr/<CODE>/`
   - Cloudflare: `https://qr.elkhawaga.uk/bank/<CODE>`

4. **صفحة "All":**
   - تعرض جميع الحسابات التي `show_in_qr=True`
   - مرتبة حسب `display_order`

---

## 🔧 **استكشاف الأخطاء**

### **خطأ: Migration لا يعمل**

```bash
# حذف Migration وإعادة إنشائه
rm accounting/migrations/0023_add_bank_accounts.py
python manage.py makemigrations accounting
python manage.py migrate accounting
```

### **خطأ: QR لا يظهر**

```bash
# إعادة توليد QR
python manage.py generate_bank_qr --force
```

### **خطأ: Cloudflare لا يعرض البيانات**

```bash
# إعادة المزامنة
python manage.py sync_bank_accounts --active-only
```

---

## ✨ **جاهز للاستخدام!**

بعد تنفيذ الخطوات أعلاه، سيكون لديك:

- ✅ نظام كامل لإدارة الحسابات البنكية
- ✅ QR Codes جاهزة للطباعة
- ✅ صفحات ثابتة على Cloudflare
- ✅ لوحة تحكم احترافية

---

**للمساعدة، راجع:** [BANK_QR_SYSTEM_GUIDE.md](./BANK_QR_SYSTEM_GUIDE.md)
