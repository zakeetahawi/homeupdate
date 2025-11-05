# 🔧 تفاصيل التغييرات في الكود

## 📂 الملف الأول: `orders/permissions.py`

### الإضافات في البداية (السطور 1-8):

```python
# الـ Imports الجديدة:
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from functools import wraps
```

### الـ Decorator الأول (السطور 377-395):

```python
def order_create_permission_required(view_func):
    """
    Decorator مخصص للتحقق من صلاحية إنشاء الطلبات
    يستخدم نظام الصلاحيات المتقدم بدلاً من الـ permission_required البسيط
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        if not can_user_create_order_type(request.user, 'product'):
            raise PermissionDenied('ليس لديك صلاحية لإنشاء طلبات')
        return view_func(request, *args, **kwargs)
    return wrapper
```

### الـ Decorator الثاني (السطور 398-444):

```python
def order_edit_permission_required(view_func):
    """
    Decorator مخصص للتحقق من صلاحية تعديل الطلبات
    يدعم معاملات مختلفة: pk, order_id, order_number, order_code
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # البحث عن الطلب من المعاملات المختلفة
        order = None
        if 'pk' in kwargs:
            order = get_object_or_404(Order, pk=kwargs['pk'])
        elif 'order_id' in kwargs:
            order = get_object_or_404(Order, id=kwargs['order_id'])
        elif 'order_number' in kwargs:
            order = get_object_or_404(Order, order_number=kwargs['order_number'])
        elif 'order_code' in kwargs:
            order = get_object_or_404(Order, order_code=kwargs['order_code'])
        
        if order and not can_user_edit_order(request.user, order):
            raise PermissionDenied('ليس لديك صلاحية لتعديل هذا الطلب')
        
        return view_func(request, *args, **kwargs)
    return wrapper
```

### الـ Decorator الثالث (السطور 447-493):

```python
def order_delete_permission_required(view_func):
    """
    Decorator مخصص للتحقق من صلاحية حذف الطلبات
    يدعم معاملات مختلفة: pk, order_id, order_number, order_code
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # البحث عن الطلب من المعاملات المختلفة
        order = None
        if 'pk' in kwargs:
            order = get_object_or_404(Order, pk=kwargs['pk'])
        elif 'order_id' in kwargs:
            order = get_object_or_404(Order, id=kwargs['order_id'])
        elif 'order_number' in kwargs:
            order = get_object_or_404(Order, order_number=kwargs['order_number'])
        elif 'order_code' in kwargs:
            order = get_object_or_404(Order, order_code=kwargs['order_code'])
        
        if order and not can_user_delete_order(request.user, order):
            raise PermissionDenied('ليس لديك صلاحية لحذف هذا الطلب')
        
        return view_func(request, *args, **kwargs)
    return wrapper
```

---

## 📂 الملف الثاني: `orders/views.py`

### التغيير 1: الـ Imports (السطور 1-23)

**قبل:**
```python
from django.contrib.auth.decorators import login_required, permission_required
```

**بعد:**
```python
from django.contrib.auth.decorators import login_required

from .permissions import (
    get_user_orders_queryset,
    can_user_view_order,
    can_user_edit_order,
    can_user_delete_order,
    order_create_permission_required,
    order_edit_permission_required,
    order_delete_permission_required
)
```

### التغيير 2: `order_create` (السطر 324)

**قبل:**
```python
@permission_required('orders.add_order')
def order_create(request):
```

**بعد:**
```python
@order_create_permission_required
def order_create(request):
```

### التغيير 3: `order_update` (السطر 573)

**قبل:**
```python
@permission_required('orders.change_order')
def order_update(request, pk):
```

**بعد:**
```python
@order_edit_permission_required
def order_update(request, pk):
```

### التغيير 4: `order_delete` (السطر 807)

**قبل:**
```python
@permission_required('orders.delete_order')
def order_delete(request, pk):
```

**بعد:**
```python
@order_delete_permission_required
def order_delete(request, pk):
```

### التغيير 5: `update_order_status` (السطر 954)

**قبل:**
```python
@permission_required('orders.change_order')
def update_order_status(request, pk):
```

**بعد:**
```python
@order_edit_permission_required
def update_order_status(request, pk):
```

### التغيير 6: `order_update_by_number` (السطر 1248)

**قبل:**
```python
@login_required
def order_update_by_number(request, order_number):
```

**بعد:**
```python
@order_edit_permission_required
def order_update_by_number(request, order_number):
```

### التغيير 7: `order_delete_by_number` (السطر 1477)

**قبل:**
```python
@login_required
def order_delete_by_number(request, order_number):
```

**بعد:**
```python
@order_delete_permission_required
def order_delete_by_number(request, order_number):
```

---

## 📊 ملخص التغييرات

| الملف | النوع | العدد | الوصف |
|------|-------|-------|--------|
| `permissions.py` | إضافة | 3 | decorators جديدة |
| `permissions.py` | إضافة | 3 | imports جديدة |
| `views.py` | تحديث | 6 | decorators محدثة |
| `views.py` | تحديث | 1 | imports محدثة |
| `views.py` | حذف | 1 | permission_required |

---

## ✅ التحقق من الصحة

- ✅ لا توجد أخطاء في الكود
- ✅ جميع الـ decorators مطبقة بشكل صحيح
- ✅ جميع الـ imports محدثة
- ✅ جميع الـ views محدثة
- ✅ الأمان محفوظ

---

## 🎯 النتيجة

البائعون الآن يستطيعون:
- ✅ إنشاء طلبات جديدة
- ✅ إضافة عناصر يدويًا
- ✅ إضافة عناصر من الباركود
- ✅ حفظ الطلبات بنجاح
- ✅ تعديل طلباتهم
- ✅ حذف طلباتهم

مع الحفاظ على الأمان والحماية! 🔒

