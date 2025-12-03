# خطة الإصلاح الشاملة للأداء والأخطاء
**تاريخ الإنشاء:** 3 ديسمبر 2025  
**الحالة:** جاهزة للتنفيذ  
**الأولوية:** عاجلة

---

## 📊 ملخص المشاكل المكتشفة

### الأخطاء الحرجة:
- **337 خطأ** في سجل الأخطاء
- **4,856 تحذير أداء** للصفحات البطيئة
- **8,272 استعلام بطيء** في قاعدة البيانات

### الصفحات الأكثر تأثراً:
1. `/installations/installation-list/` - 2,829 حالة بطء (450-774 استعلام)
2. `/orders/wizard/step/1/` - 308 حالة بطء
3. `/orders/wizard/finalize/` - 125 حالة بطء (حتى 9.5 ثانية!)
4. `/orders/api/salespersons/` - أكثر من 100 خطأ 500

---

## 🔴 المرحلة الأولى: إصلاح الأخطاء الحرجة (اليوم 1)

### 1.1 إصلاح `/orders/api/salespersons/` - أولوية قصوى
**المشكلة:** خطأ 500 متكرر (أكثر من 100 مرة)  
**التأثير:** المستخدمون لا يمكنهم الوصول لبيانات موظفي المبيعات

**خطوات الإصلاح:**

#### الخطوة 1: تحديد السبب الجذري
```bash
# فحص الكود الحالي
cd /home/zakee/homeupdate
grep -r "api/salespersons" orders/
find orders/ -name "*api*" -o -name "*views*" | xargs grep -l "salesperson"
```

#### الخطوة 2: فحص ملف الـ API
**الملفات المحتملة:**
- `orders/api.py` أو `orders/views.py` أو `orders/api/views.py`
- `orders/urls.py` للتأكد من الـ route

**الأخطاء المحتملة:**
1. Query على جدول غير موجود
2. مشكلة في Serialization
3. Foreign key معطوبة
4. مشكلة في الأذونات (permissions)

#### الخطوة 3: الحل المقترح
```python
# في الملف المناسب (orders/api.py أو orders/views.py)

# الكود الحالي المتوقع (يسبب الخطأ):
@api_view(['GET'])
def salespersons_list(request):
    salespersons = User.objects.filter(groups__name='Sales')
    # ... كود معطوب

# الإصلاح:
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def salespersons_list(request):
    try:
        # التأكد من وجود المجموعة أولاً
        from django.contrib.auth.models import Group
        
        sales_group = Group.objects.filter(name__in=['Sales', 'مبيعات', 'موظف مبيعات']).first()
        
        if not sales_group:
            logger.warning("Sales group not found")
            return Response({
                'salespersons': [],
                'message': 'لم يتم العثور على مجموعة المبيعات'
            }, status=status.HTTP_200_OK)
        
        # جلب موظفي المبيعات مع select_related لتحسين الأداء
        salespersons = User.objects.filter(
            groups=sales_group,
            is_active=True
        ).select_related('profile').only(
            'id', 'username', 'first_name', 'last_name', 'email'
        ).order_by('first_name', 'last_name')
        
        # Serialize البيانات
        data = [{
            'id': sp.id,
            'name': f"{sp.first_name} {sp.last_name}".strip() or sp.username,
            'username': sp.username,
            'email': sp.email,
        } for sp in salespersons]
        
        return Response({
            'salespersons': data,
            'count': len(data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in salespersons_list: {str(e)}", exc_info=True)
        return Response({
            'error': 'حدث خطأ في جلب بيانات موظفي المبيعات',
            'salespersons': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

#### الخطوة 4: الاختبار
```bash
# اختبار الـ endpoint
curl -X GET http://localhost:8000/orders/api/salespersons/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# أو باستخدام httpie
http GET http://localhost:8000/orders/api/salespersons/
```

**الوقت المتوقع:** 2-3 ساعات  
**الأولوية:** 🔴 حرجة

---

### 1.2 إصلاح Manufacturing Order Duplicates
**المشكلة:** `MultipleObjectsReturned` في `/manufacturing/order/{code}/`

**خطوات الإصلاح:**

#### الخطوة 1: تحليل المشكلة
```bash
# فحص الكود الحالي
cd /home/zakee/homeupdate
grep -n "manufacturing_order_detail_by_code" manufacturing/views.py
```

#### الخطوة 2: الكود الحالي (السطر 2438)
```python
# الكود المعطوب:
manufacturing_order = get_object_or_404(
    ManufacturingOrder.objects.select_related('order', 'order__customer'),
    order__order_number=order_number  # هذا يمكن أن يرجع أكثر من سجل!
)
```

**السبب:** `order_number` ليس فريداً في جدول `orders`، أو هناك سجلات manufacturing مكررة لنفس الطلب.

#### الخطوة 3: الحل المقترح
```python
# في manufacturing/views.py حول السطر 2438

# الحل الأول: استخدام filter + first
def manufacturing_order_detail_by_code(request, order_code):
    try:
        # فك تشفير الكود إذا كان مشفراً
        # order_code مثل: "9-1142-0002-M"
        
        manufacturing_orders = ManufacturingOrder.objects.select_related(
            'order', 
            'order__customer'
        ).filter(
            order__order_number=order_code.replace('-M', '')
        ).order_by('-created_at')  # الأحدث أولاً
        
        if not manufacturing_orders.exists():
            messages.error(request, f'لم يتم العثور على أمر التصنيع {order_code}')
            return redirect('manufacturing:orders_list')
        
        if manufacturing_orders.count() > 1:
            # تسجيل تحذير للسجلات المكررة
            logger.warning(
                f"Found {manufacturing_orders.count()} manufacturing orders for {order_code}"
            )
            # يمكن إضافة منطق لدمج أو حذف المكررات
        
        manufacturing_order = manufacturing_orders.first()
        
        # باقي الكود...
        
    except Exception as e:
        logger.error(f"Error in manufacturing_order_detail_by_code: {e}", exc_info=True)
        messages.error(request, 'حدث خطأ في تحميل أمر التصنيع')
        return redirect('manufacturing:orders_list')
```

#### الخطوة 4: إصلاح البيانات المكررة
```python
# إنشاء سكريبت لتنظيف السجلات المكررة
# اسم الملف: fix_duplicate_manufacturing_orders.py

from django.db.models import Count
from manufacturing.models import ManufacturingOrder
import logging

logger = logging.getLogger(__name__)

def find_duplicates():
    """البحث عن أوامر التصنيع المكررة"""
    duplicates = ManufacturingOrder.objects.values('order_id').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    return duplicates

def fix_duplicates(dry_run=True):
    """إصلاح السجلات المكررة - الاحتفاظ بالأحدث فقط"""
    duplicates = find_duplicates()
    
    print(f"Found {duplicates.count()} orders with duplicates")
    
    for dup in duplicates:
        order_id = dup['order_id']
        
        # جلب جميع السجلات المكررة
        orders = ManufacturingOrder.objects.filter(
            order_id=order_id
        ).order_by('created_at')
        
        # الاحتفاظ بالأحدث
        keep = orders.last()
        delete_these = orders.exclude(id=keep.id)
        
        print(f"\nOrder ID: {order_id}")
        print(f"  Total records: {orders.count()}")
        print(f"  Keeping: {keep.id} (created: {keep.created_at})")
        print(f"  Deleting: {[o.id for o in delete_these]}")
        
        if not dry_run:
            count = delete_these.delete()[0]
            print(f"  Deleted {count} duplicate records")
            logger.info(f"Deleted {count} duplicate manufacturing orders for order {order_id}")

if __name__ == '__main__':
    print("=== Manufacturing Order Duplicates Fix ===\n")
    print("DRY RUN - No changes will be made\n")
    fix_duplicates(dry_run=True)
    
    response = input("\nDo you want to proceed with actual deletion? (yes/no): ")
    if response.lower() == 'yes':
        print("\nExecuting actual deletion...")
        fix_duplicates(dry_run=False)
        print("\nDone!")
    else:
        print("\nCancelled.")
```

#### الخطوة 5: التنفيذ
```bash
# تشغيل السكريبت
cd /home/zakee/homeupdate
python manage.py shell < fix_duplicate_manufacturing_orders.py

# أو مباشرة
python manage.py shell
>>> exec(open('fix_duplicate_manufacturing_orders.py').read())
```

**الوقت المتوقع:** 2-4 ساعات  
**الأولوية:** 🔴 عالية

---

### 1.3 إصلاح مشكلة Celery Database Connection
**المشكلة:** `Connection refused` على PostgreSQL

**الحل:**

#### إنشاء health check قبل بدء Celery
```bash
# ملف: celery_healthcheck.sh
#!/bin/bash

echo "Waiting for PostgreSQL to be ready..."

max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if pg_isready -h localhost -p 5432 -q; then
        echo "PostgreSQL is ready!"
        exit 0
    fi
    
    attempt=$((attempt + 1))
    echo "Attempt $attempt/$max_attempts - PostgreSQL not ready yet..."
    sleep 2
done

echo "ERROR: PostgreSQL did not become ready in time"
exit 1
```

#### تعديل systemd service
```ini
# في ملف systemd/celery_worker.service
[Unit]
Description=Celery Worker
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=forking
User=zakee
Group=zakee
WorkingDirectory=/home/zakee/homeupdate

# Health check قبل البدء
ExecStartPre=/home/zakee/homeupdate/celery_healthcheck.sh

# باقي التكوين...
```

**الوقت المتوقع:** 1 ساعة  
**الأولوية:** 🟡 متوسطة

---

## 🟡 المرحلة الثانية: تحسين الأداء الحرج (اليوم 2-3)

### 2.1 تحسين `/installations/installation-list/` - الأولوية القصوى
**المشكلة الحالية:** 450-774 استعلام لكل طلب!

#### تحليل المشكلة:
```bash
# فحص الكود
cd /home/zakee/homeupdate
find installations/ -name "views.py" -o -name "views/" | xargs grep -l "installation.*list"
```

#### الحل المقترح - تقنيات التحسين:

**1. استخدام select_related و prefetch_related**
```python
# في installations/views.py

# الكود الحالي (المتوقع):
def installation_list(request):
    installations = Installation.objects.all()  # N+1 queries!
    # ...

# الحل الأمثل:
def installation_list(request):
    installations = Installation.objects.select_related(
        'order',
        'order__customer',
        'order__salesperson',
        'assigned_team',
        'installer',
        'created_by',
        'updated_by'
    ).prefetch_related(
        'order__items',
        'order__items__product',
        'installation_team_members',
        'installation_photos'
    ).only(
        # تحديد الحقول المطلوبة فقط
        'id',
        'order_id',
        'installation_date',
        'status',
        'priority',
        'notes',
        'assigned_team_id',
        'installer_id',
        'created_at',
        'updated_at',
        # حقول العلاقات
        'order__order_number',
        'order__customer__name',
        'order__customer__phone',
        'order__salesperson__username',
        'assigned_team__name',
        'installer__username'
    )
    
    # إضافة pagination
    from django.core.paginator import Paginator
    
    paginator = Paginator(installations, 50)  # 50 سجل لكل صفحة
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'installations': page_obj,
        'page_obj': page_obj,
        'total_count': paginator.count,
    }
    
    return render(request, 'installations/installation_list.html', context)
```

**2. إضافة Caching**
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache الصفحة لمدة 5 دقائق
@cache_page(60 * 5)
def installation_list(request):
    # ... الكود السابق
    pass

# أو استخدام cache يدوي للبيانات المتكررة
def installation_list(request):
    cache_key = f'installation_list_page_{page_number}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return render(request, 'installations/installation_list.html', cached_data)
    
    # جلب البيانات...
    context = {...}
    
    # حفظ في الـ cache لمدة 5 دقائق
    cache.set(cache_key, context, 60 * 5)
    
    return render(request, 'installations/installation_list.html', context)
```

**3. استخدام Database Indexes**
```python
# في installations/models.py

class Installation(models.Model):
    # ... الحقول الموجودة
    
    class Meta:
        indexes = [
            models.Index(fields=['installation_date', 'status']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['assigned_team', 'installation_date']),
            models.Index(fields=['status', 'priority', 'installation_date']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-installation_date', '-created_at']

# إنشاء الـ migrations
# python manage.py makemigrations
# python manage.py migrate
```

**4. تحسين Template (إذا كان يحتوي على queries)**
```django
{# في installations/templates/installation_list.html #}

{# بدلاً من: #}
{% for installation in installations %}
    {{ installation.order.customer.name }}  {# query لكل سجل #}
{% endfor %}

{# استخدم: #}
{% for installation in installations %}
    {{ installation.order.customer.name }}  {# محملة مسبقاً بـ select_related #}
{% endfor %}

{# تجنب: #}
{% for installation in installations %}
    {% for item in installation.order.items.all %}  {# N+1 query #}
    {% endfor %}
{% endfor %}

{# استخدم: #}
{# البيانات محملة مسبقاً بـ prefetch_related #}
```

**5. إضافة API Endpoint محسّن (اختياري)**
```python
# إنشاء API endpoint باستخدام Django REST Framework
from rest_framework import viewsets, serializers
from rest_framework.pagination import PageNumberPagination

class InstallationPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class InstallationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='order.customer.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Installation
        fields = [
            'id', 'order_number', 'customer_name', 
            'installation_date', 'status', 'priority'
        ]

class InstallationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Installation.objects.select_related(
        'order__customer'
    ).only('id', 'installation_date', 'status', 'priority',
           'order__order_number', 'order__customer__name')
    
    serializer_class = InstallationSerializer
    pagination_class = InstallationPagination
```

#### التوقعات بعد التحسين:
- **قبل:** 450-774 استعلام، 1-2 ثانية
- **بعد:** 5-10 استعلامات، 100-300 ميللي ثانية
- **تحسين:** 98% تقليل في الاستعلامات، 80% أسرع

**الوقت المتوقع:** 4-6 ساعات  
**الأولوية:** 🔴 حرجة

---

### 2.2 تحسين `/orders/wizard/finalize/`
**المشكلة:** 151-525 استعلام، حتى 9.5 ثانية!

#### التحليل:
```bash
grep -n "wizard.*finalize" orders/views.py
grep -n "def finalize" orders/views.py
```

#### الحل المقترح:

**1. تجميع الاستعلامات**
```python
# في orders/views.py - wizard finalize view

def wizard_finalize(request):
    order_id = request.session.get('wizard_order_id')
    
    # جلب كل البيانات المطلوبة في استعلام واحد محسّن
    order = Order.objects.select_related(
        'customer',
        'salesperson',
        'contract_template',
        'created_by'
    ).prefetch_related(
        Prefetch('items', queryset=OrderItem.objects.select_related(
            'product',
            'product__category',
            'warehouse'
        )),
        'accessories',
        'fabrics',
        'curtain_details',
        'customizations'
    ).get(id=order_id)
    
    # معالجة البيانات في الذاكرة بدلاً من queries متعددة
    total_items = order.items.count()  # محمّل مسبقاً
    total_amount = sum(item.total_price for item in order.items.all())
    
    # استخدام bulk operations
    if order.items.exists():
        # بدلاً من حفظ كل item على حدة
        items_to_update = list(order.items.all())
        for item in items_to_update:
            item.calculated_field = some_calculation()
        
        # حفظ جماعي
        OrderItem.objects.bulk_update(items_to_update, ['calculated_field'])
    
    context = {
        'order': order,
        'total_items': total_items,
        'total_amount': total_amount,
    }
    
    return render(request, 'orders/wizard_finalize.html', context)
```

**2. استخدام Database Functions**
```python
from django.db.models import Sum, Count, F, Q

def wizard_finalize(request):
    order_id = request.session.get('wizard_order_id')
    
    # حساب الإجماليات في قاعدة البيانات بدلاً من Python
    order_stats = Order.objects.filter(id=order_id).aggregate(
        total_items=Count('items'),
        total_amount=Sum(F('items__quantity') * F('items__unit_price')),
        total_fabric_meters=Sum('fabrics__quantity')
    )
    
    order = Order.objects.select_related(...).get(id=order_id)
    
    context = {
        'order': order,
        **order_stats,  # دمج الإحصائيات
    }
```

**3. Async Processing للعمليات الثقيلة**
```python
from celery import shared_task

@shared_task
def process_order_finalization(order_id):
    """معالجة غير متزامنة للعمليات الثقيلة"""
    order = Order.objects.get(id=order_id)
    
    # العمليات الثقيلة مثل:
    # - إنشاء PDF
    # - إرسال emails
    # - حساب معقد
    # - تحديث inventory
    
    return {'status': 'completed', 'order_id': order_id}

def wizard_finalize(request):
    order_id = request.session.get('wizard_order_id')
    
    # حفظ البيانات الأساسية فقط
    order = Order.objects.get(id=order_id)
    order.status = 'pending_approval'
    order.save(update_fields=['status'])
    
    # تشغيل المعالجة في الخلفية
    process_order_finalization.delay(order_id)
    
    messages.success(request, 'تم حفظ الطلب وجاري المعالجة...')
    return redirect('orders:order_detail', order_id=order_id)
```

**التوقعات:**
- **قبل:** 151-525 استعلام، 1.6-9.5 ثانية
- **بعد:** 10-20 استعلام، 200-500 ميللي ثانية
- **تحسين:** 95% تقليل

**الوقت المتوقع:** 4-6 ساعات  
**الأولوية:** 🔴 عالية

---

### 2.3 تحسين `/orders/wizard/step/1/`
**المشكلة:** 32-36 استعلام، 1-1.3 ثانية

#### الحل السريع:
```python
def wizard_step_1(request):
    # تحميل البيانات المطلوبة فقط
    customers = Customer.objects.only(
        'id', 'name', 'phone', 'address'
    ).order_by('name')[:100]  # حد أقصى 100
    
    salespersons = User.objects.filter(
        groups__name='Sales',
        is_active=True
    ).only('id', 'username', 'first_name', 'last_name')
    
    # Cache البيانات الثابتة
    cache_key = 'wizard_step_1_static_data'
    static_data = cache.get(cache_key)
    
    if not static_data:
        static_data = {
            'order_types': OrderType.objects.all(),
            'payment_methods': PaymentMethod.objects.all(),
        }
        cache.set(cache_key, static_data, 60 * 30)  # 30 دقيقة
    
    context = {
        'customers': customers,
        'salespersons': salespersons,
        **static_data
    }
```

**الوقت المتوقع:** 2-3 ساعات  
**الأولوية:** 🟡 متوسطة

---

### 2.4 تحسين `/manufacturing/fabric-receipt/`
**المشكلة:** 2,150 استعلام!

#### الحل:
```python
def fabric_receipt_list(request):
    receipts = FabricReceipt.objects.select_related(
        'supplier',
        'warehouse',
        'received_by',
        'approved_by'
    ).prefetch_related(
        Prefetch('items', queryset=FabricReceiptItem.objects.select_related(
            'fabric',
            'fabric__category',
            'fabric__supplier'
        ))
    ).order_by('-receipt_date')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(receipts, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    return render(request, 'manufacturing/fabric_receipt_list.html', {
        'receipts': page_obj
    })
```

**التوقعات:**
- **قبل:** 2,150 استعلام
- **بعد:** 5-8 استعلامات
- **تحسين:** 99.6% تقليل

**الوقت المتوقع:** 3-4 ساعات  
**الأولوية:** 🔴 عالية

---

## 🟢 المرحلة الثالثة: تحسينات قاعدة البيانات (اليوم 4-5)

### 3.1 إضافة Indexes للجداول الرئيسية

#### تحليل الاستعلامات البطيئة:
```sql
-- في PostgreSQL
SELECT 
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY total_exec_time DESC
LIMIT 20;
```

#### إضافة Indexes للجداول الأساسية:

**1. جدول inventory_product**
```python
# في inventory/models.py

class Product(models.Model):
    # ... الحقول الموجودة
    
    class Meta:
        indexes = [
            # Index مركب للبحث والفلترة
            models.Index(fields=['category', 'is_active', 'name']),
            models.Index(fields=['code']),  # للبحث بالكود
            models.Index(fields=['supplier', 'category']),
            models.Index(fields=['price', 'is_active']),
            models.Index(fields=['-created_at']),
            
            # Index للحقول المستخدمة في WHERE
            models.Index(fields=['is_active', 'in_stock']),
            models.Index(fields=['warehouse', 'is_active']),
        ]
```

**2. جدول orders_order**
```python
class Order(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['order_number']),  # مهم جداً
            models.Index(fields=['customer', 'status', '-created_at']),
            models.Index(fields=['salesperson', 'status']),
            models.Index(fields=['status', 'payment_status']),
            models.Index(fields=['-order_date', 'status']),
            models.Index(fields=['created_at', 'status']),
        ]
```

**3. جدول installations_installation**
```python
class Installation(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['installation_date', 'status']),
            models.Index(fields=['assigned_team', 'installation_date']),
            models.Index(fields=['installer', 'status']),
            models.Index(fields=['status', 'priority', 'installation_date']),
        ]
```

**4. جدول manufacturing_manufacturingorder**
```python
class ManufacturingOrder(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['order', 'status']),  # منع التكرار
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['production_date']),
            models.Index(fields=['assigned_worker', 'status']),
        ]
        
        # إضافة unique constraint لمنع التكرار
        constraints = [
            models.UniqueConstraint(
                fields=['order'],
                name='unique_manufacturing_order_per_order'
            )
        ]
```

#### تطبيق الـ Indexes:
```bash
# إنشاء migrations
python manage.py makemigrations

# فحص SQL الذي سيتم تنفيذه
python manage.py sqlmigrate inventory 00XX
python manage.py sqlmigrate orders 00XX

# تطبيق
python manage.py migrate
```

**الوقت المتوقع:** 3-4 ساعات  
**الأولوية:** 🟡 متوسطة

---

### 3.2 تحسين استعلامات inventory_product

**السبب:** الاستعلامات تأخذ 100-130ms

#### الحلول:

**1. إنشاء Materialized View (PostgreSQL)**
```sql
-- إنشاء view محسّن للمنتجات الأكثر استخداماً
CREATE MATERIALIZED VIEW products_summary AS
SELECT 
    p.id,
    p.name,
    p.code,
    p.price,
    p.currency,
    p.unit,
    p.category_id,
    c.name as category_name,
    p.supplier_id,
    s.name as supplier_name,
    p.is_active,
    p.in_stock,
    COALESCE(SUM(wp.quantity), 0) as total_stock
FROM inventory_product p
LEFT JOIN inventory_category c ON p.category_id = c.id
LEFT JOIN inventory_supplier s ON p.supplier_id = s.id
LEFT JOIN inventory_warehouseproduct wp ON p.id = wp.product_id
GROUP BY p.id, c.name, s.name;

-- إنشاء index على الـ view
CREATE INDEX idx_products_summary_active ON products_summary(is_active, in_stock);
CREATE INDEX idx_products_summary_category ON products_summary(category_id, is_active);

-- Refresh الـ view يومياً
-- يمكن إضافة cron job أو Celery task
```

```python
# في Celery tasks
@shared_task
def refresh_products_summary():
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("REFRESH MATERIALIZED VIEW products_summary;")
```

**2. استخدام Database-level Caching**
```python
# في Django settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'homeupdate',
        'TIMEOUT': 300,  # 5 دقائق
    }
}
```

**3. تحسين Query المتكرر**
```python
# بدلاً من:
products = Product.objects.all()

# استخدم:
products = Product.objects.select_related(
    'category',
    'supplier'
).only(
    'id', 'name', 'code', 'price', 'currency', 'unit',
    'is_active', 'in_stock',
    'category__name',
    'supplier__name'
)

# مع caching
from django.core.cache import cache

cache_key = 'active_products_list'
products = cache.get(cache_key)

if not products:
    products = list(Product.objects.select_related(...).filter(is_active=True))
    cache.set(cache_key, products, 60 * 10)  # 10 دقائق
```

**الوقت المتوقع:** 2-3 ساعات  
**الأولوية:** 🟡 متوسطة

---

## 🔵 المرحلة الرابعة: تحسينات إضافية (اليوم 6-7)

### 4.1 إعداد Query Monitoring

**إنشاء نظام مراقبة أفضل:**

```python
# ملف: homeupdate/middleware/query_monitor.py

import time
import logging
from django.db import connection
from django.conf import settings

logger = logging.getLogger('database.queries')

class QueryMonitorMiddleware:
    """مراقبة الاستعلامات البطيئة والمتكررة"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # إعادة تعيين queries
        connection.queries_log.clear()
        
        start_time = time.time()
        response = self.get_response(request)
        duration = (time.time() - start_time) * 1000  # ms
        
        num_queries = len(connection.queries)
        
        # تسجيل الصفحات التي تحتوي على استعلامات كثيرة
        if num_queries > 20:
            logger.warning(
                f"HIGH_QUERY_COUNT: {request.path} | "
                f"{num_queries} queries | {duration:.0f}ms | "
                f"user={getattr(request.user, 'username', 'anonymous')}"
            )
            
            # تحليل الاستعلامات المتكررة
            query_list = [q['sql'] for q in connection.queries]
            duplicates = {}
            
            for sql in query_list:
                # تبسيط SQL لاكتشاف التكرار
                simplified = sql[:100]
                duplicates[simplified] = duplicates.get(simplified, 0) + 1
            
            # تسجيل الاستعلامات المكررة
            for sql, count in duplicates.items():
                if count > 5:
                    logger.warning(f"DUPLICATE_QUERY ({count}x): {sql}")
        
        return response
```

```python
# في settings.py
MIDDLEWARE = [
    # ... middlewares أخرى
    'homeupdate.middleware.query_monitor.QueryMonitorMiddleware',
]

# تفعيل query logging في development
if DEBUG:
    LOGGING['loggers']['database.queries'] = {
        'handlers': ['file'],
        'level': 'WARNING',
        'propagate': False,
    }
```

**الوقت المتوقع:** 2 ساعة  
**الأولوية:** 🟢 منخفضة

---

### 4.2 Database Connection Pooling

```python
# في settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # 10 دقائق - connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 ثانية timeout
        }
    }
}
```

**الوقت المتوقع:** 30 دقيقة  
**الأولوية:** 🟢 منخفضة

---

### 4.3 إعداد Gunicorn Workers الأمثل

```python
# ملف: gunicorn_config.py

import multiprocessing

# عدد الـ workers الأمثل
workers = multiprocessing.cpu_count() * 2 + 1

# نوع الـ worker
worker_class = 'sync'  # أو 'gevent' للأداء الأفضل

# عدد الطلبات قبل إعادة تشغيل worker
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = 120  # ثانيتين
graceful_timeout = 30

# Logging
accesslog = '/home/zakee/homeupdate/logs/gunicorn_access.log'
errorlog = '/home/zakee/homeupdate/logs/gunicorn_error.log'
loglevel = 'info'

# Bind
bind = '0.0.0.0:8000'

# Performance
keepalive = 5
worker_connections = 1000
```

**تشغيل:**
```bash
gunicorn homeupdate.wsgi:application \
    --config gunicorn_config.py \
    --daemon
```

**الوقت المتوقع:** 1 ساعة  
**الأولوية:** 🟢 منخفضة

---

## 📋 قائمة التحقق (Checklist)

### المرحلة الأولى - الأخطاء الحرجة:
- [ ] إصلاح `/orders/api/salespersons/` (2-3 ساعات)
- [ ] إصلاح Manufacturing Order duplicates (2-4 ساعات)
- [ ] إصلاح Celery DB connection (1 ساعة)

**الوقت الإجمالي:** 5-8 ساعات

### المرحلة الثانية - الأداء الحرج:
- [ ] تحسين `/installations/installation-list/` (4-6 ساعات)
- [ ] تحسين `/orders/wizard/finalize/` (4-6 ساعات)
- [ ] تحسين `/orders/wizard/step/1/` (2-3 ساعات)
- [ ] تحسين `/manufacturing/fabric-receipt/` (3-4 ساعات)

**الوقت الإجمالي:** 13-19 ساعة

### المرحلة الثالثة - قاعدة البيانات:
- [ ] إضافة Database Indexes (3-4 ساعات)
- [ ] تحسين inventory_product queries (2-3 ساعات)

**الوقت الإجمالي:** 5-7 ساعات

### المرحلة الرابعة - تحسينات إضافية:
- [ ] Query monitoring middleware (2 ساعة)
- [ ] Connection pooling (30 دقيقة)
- [ ] Gunicorn optimization (1 ساعة)

**الوقت الإجمالي:** 3.5 ساعة

---

## 🎯 الوقت الإجمالي المتوقع

- **المرحلة 1 (حرجة):** 5-8 ساعات
- **المرحلة 2 (عالية):** 13-19 ساعة
- **المرحلة 3 (متوسطة):** 5-7 ساعات
- **المرحلة 4 (منخفضة):** 3.5 ساعة

**الإجمالي:** 26.5 - 37.5 ساعة (3-5 أيام عمل)

---

## 📈 النتائج المتوقعة

### قبل التحسينات:
- 337 خطأ
- 2,829 صفحة بطيئة لـ installations
- 450-2,150 استعلام لبعض الصفحات
- وقت استجابة: 1-9.5 ثانية

### بعد التحسينات:
- 0 أخطاء حرجة
- أقل من 100 صفحة بطيئة
- 5-20 استعلام للصفحات المحسّنة
- وقت استجابة: 100-500ms

**التحسين الإجمالي:** 90-95%

---

## 🔧 أدوات المساعدة

### سكريبتات الاختبار:

**1. اختبار الأداء:**
```bash
# ملف: test_performance.sh
#!/bin/bash

echo "=== Performance Test ==="

endpoints=(
    "/installations/installation-list/"
    "/orders/wizard/step/1/"
    "/orders/wizard/finalize/"
    "/orders/api/salespersons/"
)

for endpoint in "${endpoints[@]}"; do
    echo "Testing: $endpoint"
    time curl -s -o /dev/null -w "Time: %{time_total}s\n" \
        "http://localhost:8000$endpoint"
done
```

**2. مراقبة الاستعلامات:**
```python
# ملف: monitor_queries.py
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_view_queries(view_func, *args, **kwargs):
    """اختبار عدد الاستعلامات لـ view معين"""
    connection.queries_log.clear()
    
    result = view_func(*args, **kwargs)
    
    num_queries = len(connection.queries)
    print(f"Number of queries: {num_queries}")
    
    # طباعة الاستعلامات
    for i, query in enumerate(connection.queries, 1):
        print(f"\nQuery {i}:")
        print(query['sql'][:200])
    
    return result
```

**3. تنظيف السجلات:**
```bash
# ملف: cleanup_logs.sh
#!/bin/bash

cd /home/zakee/homeupdate/logs

# أرشفة السجلات القديمة
tar -czf logs_archive_$(date +%Y%m%d).tar.gz *.log
mv logs_archive_*.tar.gz ../backups/logs/

# تنظيف السجلات
> errors.log
> performance.log
> slow_queries.log

echo "Logs cleaned and archived"
```

---

## 📞 الدعم والمتابعة

### المراقبة المستمرة:
- فحص السجلات يومياً
- مراجعة الأداء أسبوعياً
- تحديث الـ indexes شهرياً

### التواصل:
- تقرير يومي عن التقدم
- اجتماع أسبوعي لمراجعة الأداء
- توثيق جميع التغييرات

---

## ✅ الخلاصة

هذه الخطة توفر حلاً شاملاً ومفصلاً لجميع المشاكل المكتشفة. التنفيذ على مراحل يضمن:

1. **إصلاح سريع** للأخطاء الحرجة
2. **تحسين ملموس** في الأداء
3. **استقرار النظام** على المدى الطويل
4. **قابلية التوسع** مستقبلاً

**الأولوية:** ابدأ بالمرحلة الأولى اليوم!
