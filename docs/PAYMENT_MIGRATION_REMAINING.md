# خطوات إكمال إزالة نظام العربونات

## ما تم إنجازه ✅
1. ✅ حذف CustomerAdvance و AdvanceUsage models
2. ✅ تعديل Payment ليكون عام (order اختياري)
3. ✅ إنشاء PaymentAllocation model
4. ✅ إضافة آلية FIFO للتخصيص التلقائي
5. ✅ حذف signals و admin classes
6. ✅ حذف forms

## المتبقي للإتمام ⚠️

### 1. تنظيف Views (accounting/views.py)
يجب حذف/تعطيل هذه الـ views:
- `customer_advances()` - line ~701
- `customer_advance_detail()` - line ~550
- `use_advance()` - line ~577  
- `register_customer_advance()` - line ~823
- `advances_list()` - line ~1176

**الحل المؤقت**: علّق على هذه الdefs بالكامل أو احذفها

### 2. تنظيف URLs (accounting/urls.py)
يجب حذف/تعطيل مسارات العربونات:
```python
# path('customer/<int:customer_id>/advances/', views.customer_advances, name='customer_advances'),
# path('advance/<int:pk>/', views.customer_advance_detail, name='customer_advance_detail'),
# path('advance/<int:pk>/use/', views.use_advance, name='use_advance'),
# path('customer/<int:customer_id>/register-advance/', views.register_customer_advance, name='register_customer_advance'),
# path('advances/', views.advances_list, name='advances_list'),
```

### 3. إنشاء Migrations

```bash
python manage.py makemigrations orders accounting --name="remove_advances_add_payment_allocation"
python manage.py migrate
```

### 4. تنظيف AccountingSettings
في [accounting/models.py](accounting/models.py) - `AccountingSettings`:
```python
# حذف أو تعليق:
#  default_advances_account = models.ForeignKey(...)
```

### 5. إضافة Admin لـ PaymentAllocation
في [orders/admin.py](orders/admin.py):
```python
from orders.models import PaymentAllocation

@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ['payment', 'order', 'allocated_amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['payment__customer__name', 'order__order_number']
    readonly_fields = ['created_at', 'created_by']
```

### 6. اختبار النظام الجديد
```bash
# إنشاء دفعة عامة
python manage.py shell
>>> from orders.models import Payment
>>> from customers.models import Customer
>>> customer = Customer.objects.first()
>>> payment = Payment.objects.create(
...     customer=customer,
...     amount=5000,
...     payment_type='general',
...     payment_method='cash'
... )
# سيتم التخصيص تلقائياً FIFO!
>>> payment.allocations.all()  # عرض التخصيصات
```

## الأوامر السريعة للإكمال

```bash
# 1. تعطيل views مؤقتاً
sed -i 's/^def customer_advances/def _disabled_customer_advances/g' accounting/views.py
sed -i 's/^def use_advance/def _disabled_use_advance/g' accounting/views.py  
sed -i 's/^def register_customer_advance/def _disabled_register_customer_advance/g' accounting/views.py

# 2. إنشاء migrations
python manage.py makemigrations accounting orders
python manage.py migrate

# 3. حذف العربونات الموجودة
python manage.py shell -c "from accounting.models import CustomerAdvance, AdvanceUsage; CustomerAdvance.objects.all().delete(); AdvanceUsage.objects.all().delete()"
```

## ملاحظات مهمة
- ⚠️ الدفعات الزائدة تبقى برصيد  العميل (حسب متطلباتك)
- ✅ FIFO يعمل تلقائياً عند إنشاء دفعة عامة
- ✅ النظام المحاسبي يسجل كل دفعة (قيد محاسبي)
- ℹ️ العربونات الموجودة ستُحذف - احفظها قبل Migration إذا أردت

