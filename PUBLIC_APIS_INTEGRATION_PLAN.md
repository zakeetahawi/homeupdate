# خطة تكامل Public APIs في مشروع ERP/CRM

**المصدر**: https://github.com/public-apis/public-apis  
**تاريخ التقرير**: 9 مارس 2026  
**الأولوية**: مرتّبة من الأعلى تأثيراً

---

## الأولوية الأولى - تكامل عاجل

### 1. ExchangeRate-API — أسعار الصرف
- **الموقع**: https://www.exchangerate-api.com
- **الفائدة**: تحويل العملات تلقائياً في الفواتير (ريال / دولار / يورو)
- **المصادقة**: API Key مجاني (1500 طلب/شهر)
- **HTTPS**: نعم | **CORS**: نعم
- **التكامل المقترح**: `accounting/` — عند إنشاء فاتورة أو قيد محاسبي بعملة أجنبية
- **ملاحظات التطبيق**:
  ```python
  # في accounting/models.py أو accounting/views.py
  import requests
  
  def get_exchange_rate(from_currency='USD', to_currency='SAR'):
      url = f"https://v6.exchangerate-api.com/v6/YOUR_API_KEY/pair/{from_currency}/{to_currency}"
      response = requests.get(url)
      return response.json().get('conversion_rate', 1.0)
  ```

---

### 2. OpenWeatherMap — بيانات الطقس
- **الموقع**: https://openweathermap.org/api
- **الفائدة**: جدولة مواعيد التركيب بناءً على حالة الطقس، تنبيه الفنيين
- **المصادقة**: API Key مجاني (60 طلب/دقيقة)
- **HTTPS**: نعم | **CORS**: نعم
- **التكامل المقترح**: `installations/` — عند حجز موعد تركيب جديد
- **ملاحظات التطبيق**:
  ```python
  # في installations/views.py أو installations/models.py
  import requests
  
  def check_weather_for_installation(city, date):
      url = f"https://api.openweathermap.org/data/2.5/forecast"
      params = {'q': city, 'appid': 'YOUR_API_KEY', 'lang': 'ar', 'units': 'metric'}
      response = requests.get(url, params=params)
      return response.json()
  ```

---

### 3. Geocoding — تحديد المواقع الجغرافية
- **الخيار المجاني**: Nominatim (OpenStreetMap) — https://nominatim.org
- **الخيار المدفوع**: Google Maps Geocoding API
- **الفائدة**: تحديد مواقع العملاء والتركيب، حساب مسافات الفنيين
- **المصادقة**: بدون مصادقة (Nominatim) | API Key (Google)
- **التكامل المقترح**: `customers/` و `installations/`
- **ملاحظات التطبيق**:
  ```python
  # استخدام Nominatim المجاني
  import requests
  
  def geocode_address(address):
      url = "https://nominatim.openstreetmap.org/search"
      params = {'q': address, 'format': 'json', 'limit': 1}
      headers = {'User-Agent': 'ElKhawagaERP/1.0'}
      response = requests.get(url, params=params, headers=headers)
      results = response.json()
      if results:
          return {'lat': results[0]['lat'], 'lon': results[0]['lon']}
      return None
  ```

---

### 4. SMS API (Vonage / Twilio) — الرسائل النصية
- **Vonage**: https://developer.vonage.com
- **Twilio**: https://www.twilio.com
- **الفائدة**: إشعار العملاء بـ: تأكيد الطلب، موعد التركيب، حالة الشكوى
- **المصادقة**: API Key + Secret
- **التكامل المقترح**: `notifications/` — ربط مع نظام الإشعارات الحالي
- **ملاحظات التطبيق**:
  ```python
  # في notifications/ أو orders/signals.py
  import vonage
  
  def send_sms_notification(phone_number, message):
      client = vonage.Client(key='YOUR_KEY', secret='YOUR_SECRET')
      sms = vonage.Sms(client)
      response = sms.send_message({
          'from': 'ElKhawaga',
          'to': phone_number,
          'text': message,
      })
      return response
  
  # مثال الاستخدام في signals.py عند تأكيد الطلب
  # send_sms_notification(order.customer.phone, f"تم تأكيد طلبك رقم {order.id}")
  ```

---

## الأولوية الثانية - تحسينات مفيدة

### 5. Abstract API — التحقق من البيانات
- **الموقع**: https://www.abstractapi.com
- **الفائدة**: التحقق من صحة البريد الإلكتروني وأرقام الهواتف عند إضافة عميل جديد
- **المصادقة**: API Key (مجاني محدود)
- **التكامل المقترح**: `customers/forms.py` — التحقق عند إنشاء عميل
- **ملاحظات التطبيق**:
  ```python
  # في customers/forms.py
  def validate_phone(phone):
      url = f"https://phonevalidation.abstractapi.com/v1/?api_key=YOUR_KEY&phone={phone}"
      response = requests.get(url)
      data = response.json()
      return data.get('valid', False)
  ```

---

### 6. OCR.Space — مسح الفواتير الورقية
- **الموقع**: https://ocr.space
- **الفائدة**: مسح الفواتير الورقية وإدخالها تلقائياً في `accounting/`
- **المصادقة**: API Key مجاني (500 طلب/شهر)
- **HTTPS**: نعم
- **التكامل المقترح**: `accounting/` — رفع صورة فاتورة واستخراج البيانات
- **ملاحظات التطبيق**:
  ```python
  import requests
  
  def extract_text_from_invoice(image_path):
      url = "https://api.ocr.space/parse/image"
      with open(image_path, 'rb') as f:
          response = requests.post(url, files={'file': f}, data={
              'apikey': 'YOUR_API_KEY',
              'language': 'ara',  # العربية
              'isOverlayRequired': False,
          })
      return response.json()
  ```

---

### 7. LibreTranslate — الترجمة
- **الموقع**: https://libretranslate.com
- **الفائدة**: ترجمة التقارير والمستندات من عربي إلى إنجليزي والعكس
- **المصادقة**: API Key (نسخة مجانية محدودة / self-hosted مجاني)
- **التكامل المقترح**: `reports/` — تصدير التقارير بلغتين
- **ملاحظات التطبيق**:
  ```python
  import requests
  
  def translate_text(text, source='ar', target='en'):
      url = "https://libretranslate.com/translate"
      response = requests.post(url, json={
          'q': text,
          'source': source,
          'target': target,
          'api_key': 'YOUR_API_KEY'
      })
      return response.json().get('translatedText', text)
  ```

---

### 8. Barcode Lookup — معلومات المنتجات
- **الموقع**: https://www.barcodelookup.com/api
- **الفائدة**: قراءة باركود المواد الخام وإضافة معلوماتها تلقائياً في `inventory/`
- **المصادقة**: API Key
- **التكامل المقترح**: `inventory/` — عند إضافة صنف جديد بمسح الباركود

---

## متطلبات التطبيق

### إعدادات Django المطلوبة (في `crm/settings.py`)

```python
# ==========================================
# إعدادات APIs الخارجية
# ==========================================

# أسعار الصرف
EXCHANGE_RATE_API_KEY = env('EXCHANGE_RATE_API_KEY', default='')

# الطقس
OPENWEATHER_API_KEY = env('OPENWEATHER_API_KEY', default='')

# SMS
VONAGE_API_KEY = env('VONAGE_API_KEY', default='')
VONAGE_API_SECRET = env('VONAGE_API_SECRET', default='')

# التحقق من البيانات
ABSTRACT_API_KEY = env('ABSTRACT_API_KEY', default='')

# OCR
OCR_SPACE_API_KEY = env('OCR_SPACE_API_KEY', default='')

# LibreTranslate
LIBRETRANSLATE_API_KEY = env('LIBRETRANSLATE_API_KEY', default='')
```

### متغيرات البيئة (`.env` أو ملف الإعدادات)

```env
EXCHANGE_RATE_API_KEY=your_key_here
OPENWEATHER_API_KEY=your_key_here
VONAGE_API_KEY=your_key_here
VONAGE_API_SECRET=your_secret_here
ABSTRACT_API_KEY=your_key_here
OCR_SPACE_API_KEY=your_key_here
LIBRETRANSLATE_API_KEY=your_key_here
```

### المكتبات المطلوبة (إضافة لـ `requirements.txt`)

```
requests>=2.31.0
vonage>=3.0.0
```

---

## خطوات التنفيذ المقترحة

| الخطوة | المهمة | الملف المستهدف | الأولوية |
|--------|---------|----------------|---------|
| 1 | إضافة API Keys في settings.py | `crm/settings.py` | عاجل |
| 2 | إنشاء `core/utils/external_apis.py` | ملف جديد | عاجل |
| 3 | ربط أسعار الصرف بالمحاسبة | `accounting/models.py` | عاجل |
| 4 | إضافة الطقس لجدولة التركيب | `installations/views.py` | متوسط |
| 5 | إضافة Geocoding للعملاء | `customers/models.py` | متوسط |
| 6 | ربط SMS بنظام الإشعارات | `notifications/` | متوسط |
| 7 | إضافة OCR للفواتير | `accounting/views.py` | منخفض |
| 8 | إضافة الترجمة للتقارير | `reports/views.py` | منخفض |

---

## ملاحظات أمنية مهمة

1. **لا تضع API Keys مباشرة في الكود** — استخدم متغيرات البيئة دائماً
2. **معدل الطلبات (Rate Limiting)** — استخدم Celery tasks للطلبات الثقيلة
3. **التخزين المؤقت** — استخدم `cacheops` لتخزين نتائج APIs (أسعار الصرف مثلاً)
4. **Timeout** — دائماً حدد `timeout=10` في `requests.get()` لتجنب تعليق الطلبات
5. **SSRF Protection** — تحقق من عناوين URL قبل أي طلب خارجي

```python
# مثال آمن مع timeout وcaching
from django.core.cache import cache
import requests

def get_exchange_rate_cached(from_currency, to_currency):
    cache_key = f"exchange_rate_{from_currency}_{to_currency}"
    rate = cache.get(cache_key)
    if rate is None:
        try:
            response = requests.get(
                f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGE_RATE_API_KEY}/pair/{from_currency}/{to_currency}",
                timeout=10
            )
            response.raise_for_status()
            rate = response.json().get('conversion_rate', 1.0)
            cache.set(cache_key, rate, timeout=3600)  # كاش لمدة ساعة
        except requests.RequestException:
            rate = 1.0  # قيمة افتراضية عند الفشل
    return rate
```

---

*لتفعيل أي من هذه التكاملات، راجع هذا الملف وابدأ بالأولوية الأولى.*
