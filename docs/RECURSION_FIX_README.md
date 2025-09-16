# إصلاح مشكلة الحلقة اللانهائية في تحديث حالة التركيب

## المشكلة
كان هناك خطأ "maximum recursion depth exceeded" عند تحديث حالة التركيب للطلب 5-0094-0001. المشكلة كانت بسبب حلقة لانهائية في signals.

## سبب المشكلة
كان هناك signal مكرر في ملفين مختلفين:
1. `orders/models.py` - السطر 1127
2. `orders/signals.py` - السطر 221

كلاهما يستمع لتغييرات `InstallationSchedule` ويقوم بتحديث حالة الطلب، مما يسبب حلقة لانهائية.

## الحل المطبق

### 1. إصلاح signal في orders/models.py
```python
@receiver(post_save, sender='installations.InstallationSchedule')
def update_order_installation_status(sender, instance, **kwargs):
    """تحديث حالة الطلب عند تغيير حالة التركيب"""
    try:
        if instance.order:
            # تحديث حالة التركيب في الطلب فقط إذا تغيرت
            if instance.order.installation_status != instance.status:
                instance.order.installation_status = instance.status
                instance.order.save(update_fields=['installation_status'])
                
                # تحديث إشارة الإكمال
                instance.order.update_completion_status()
    except Exception as e:
        print(f"خطأ في تحديث حالة الطلب من التركيب: {e}")
        pass
```

### 2. إزالة signal المكرر من orders/signals.py
تم إزالة signal التركيب من ملف `orders/signals.py` لتجنب التكرار.

### 3. تحسين method update_completion_status
```python
def update_completion_status(self):
    """تحديث إشارة الإكمال بناءً على جميع المراحل"""
    is_completed = True
    
    # التحقق من حالة التصنيع
    if 'installation' in self.get_selected_types_list() or 'tailoring' in self.get_selected_types_list():
        if self.order_status not in ['completed', 'delivered']:
            is_completed = False
    
    # التحقق من حالة التركيب
    if 'installation' in self.get_selected_types_list():
        if self.installation_status != 'completed':
            is_completed = False
    
    # التحقق من حالة المعاينة
    if 'inspection' in self.get_selected_types_list():
        if self.inspection_status != 'completed':
            is_completed = False
    
    # تحديث الحقل فقط إذا تغيرت القيمة
    if self.is_fully_completed != is_completed:
        self.is_fully_completed = is_completed
        self.save(update_fields=['is_fully_completed'])
```

## التحسينات المطبقة

### 1. فحص التغيير قبل التحديث
- إضافة فحص `if instance.order.installation_status != instance.status` لتجنب التحديثات غير الضرورية

### 2. تحديث الحقول المحددة فقط
- استخدام `update_fields=['installation_status']` لتحديث الحقل المطلوب فقط
- استخدام `update_fields=['is_fully_completed']` لتحديث إشارة الإكمال فقط

### 3. إزالة التكرار
- إزالة signal المكرر من `orders/signals.py`
- الاحتفاظ بـ signal واحد فقط في `orders/models.py`

## النتائج المتوقعة

1. **عدم حدوث حلقة لانهائية**: لن يحدث خطأ "maximum recursion depth exceeded" مرة أخرى
2. **تحديث الحالة بشكل صحيح**: سيتم تحديث حالة الطلب عند تغيير حالة التركيب
3. **تحسين الأداء**: تقليل عدد عمليات الحفظ غير الضرورية
4. **استقرار النظام**: عدم حدوث أخطاء عند تحديث الحالات

## كيفية الاختبار

1. انتقل إلى قسم التركيبات
2. اختر طلب تركيب
3. جرب تحديث الحالة (مثل "بدء التركيب")
4. تأكد من عدم حدوث خطأ
5. تحقق من تحديث حالة الطلب في قسم الطلبات

## ملاحظات تقنية

- تم الحفاظ على جميع الوظائف الموجودة
- تم تحسين الأداء بتقليل عمليات الحفظ
- تم إضافة فحوصات إضافية لتجنب التحديثات غير الضرورية
- تم توثيق التغييرات بشكل واضح 