# تقرير إصلاح مشكلة جدولة التركيب

## المشكلة الأصلية
كانت هناك مشكلة في جدولة التركيب حيث يظهر خطأ:
```
null value in column: جدول التركيب
"scheduled_date" of relation "installations_installationschedule" violates not-null constraint
```

## سبب المشكلة
1. **الحقول المطلوبة**: نموذج `InstallationSchedule` يتطلب حقول `scheduled_date` و `scheduled_time` ولا يمكن أن تكون فارغة
2. **دالة API خاطئة**: دالة `receive_completed_order` كانت تنشئ تركيب بدون تحديد التاريخ والوقت
3. **عدم وجود نموذج مناسب**: لم يكن هناك نموذج مناسب للجدولة السريعة

## الإصلاحات المطبقة

### 1. إصلاح دالة API
```python
# في installations/views.py
@csrf_exempt
@require_http_methods(["POST"])
def receive_completed_order(request):
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        from orders.models import Order
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من عدم وجود جدولة سابقة
        if InstallationSchedule.objects.filter(order=order).exists():
            return JsonResponse({
                'success': False,
                'error': 'يوجد جدولة تركيب سابقة لهذا الطلب'
            }, status=400)
        
        # إنشاء جدولة تركيب جديدة مع تاريخ افتراضي
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        default_time = timezone.datetime.strptime('09:00', '%H:%M').time()
        
        installation = InstallationSchedule.objects.create(
            order=order,
            scheduled_date=tomorrow,
            scheduled_time=default_time,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'installation_id': installation.id,
            'message': 'تم استقبال الطلب بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
```

### 2. إنشاء نموذج جديد للجدولة السريعة
```python
# في installations/forms.py
class QuickScheduleForm(forms.ModelForm):
    """نموذج جدولة سريعة للتركيب"""
    scheduled_date = forms.DateField(
        label=_('تاريخ التركيب'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text=_('اختر تاريخ التركيب')
    )
    scheduled_time = forms.TimeField(
        label=_('موعد التركيب'),
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=True,
        help_text=_('اختر موعد التركيب')
    )

    class Meta:
        model = InstallationSchedule
        fields = ['team', 'scheduled_date', 'scheduled_time', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'أضف ملاحظات هنا...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')

        if not scheduled_date:
            raise ValidationError(_('تاريخ التركيب مطلوب'))

        if not scheduled_time:
            raise ValidationError(_('موعد التركيب مطلوب'))

        if scheduled_date and scheduled_date < timezone.now().date():
            raise ValidationError(_('لا يمكن جدولة تركيب في تاريخ ماضي'))

        if scheduled_date and scheduled_time:
            scheduled_datetime = timezone.make_aware(
                timezone.datetime.combine(scheduled_date, scheduled_time)
            )
            if scheduled_datetime < timezone.now():
                raise ValidationError(_('لا يمكن جدولة تركيب في وقت ماضي'))

        return cleaned_data
```

### 3. إنشاء view جديد للجدولة السريعة
```python
# في installations/views.py
@login_required
def quick_schedule_installation(request, order_id):
    """جدولة سريعة للتركيب من الطلب"""
    from orders.models import Order
    order = get_object_or_404(Order, id=order_id)
    
    # التحقق من عدم وجود جدولة سابقة
    if InstallationSchedule.objects.filter(order=order).exists():
        messages.warning(request, _('يوجد جدولة تركيب سابقة لهذا الطلب'))
        return redirect('installations:dashboard')
    
    if request.method == 'POST':
        form = QuickScheduleForm(request.POST)
        if form.is_valid():
            installation = form.save(commit=False)
            installation.order = order
            installation.status = 'scheduled'
            installation.save()
            messages.success(request, _('تم جدولة التركيب بنجاح'))
            return redirect('installations:dashboard')
    else:
        # تعيين قيم افتراضية
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        default_time = timezone.datetime.strptime('09:00', '%H:%M').time()
        form = QuickScheduleForm(initial={
            'scheduled_date': tomorrow,
            'scheduled_time': default_time
        })
    
    context = {
        'form': form,
        'order': order,
    }
    
    return render(request, 'installations/quick_schedule_installation.html', context)
```

### 4. إضافة URL جديد
```python
# في installations/urls.py
path('quick-schedule/<int:order_id>/', views.quick_schedule_installation, name='quick_schedule_installation'),
```

### 5. إنشاء template جديد للجدولة السريعة
تم إنشاء `installations/templates/installations/quick_schedule_installation.html` مع:
- عرض معلومات الطلب
- نموذج جدولة مع حقول التاريخ والوقت المطلوبة
- تصميم جميل ومتجاوب
- رسائل خطأ واضحة

### 6. تحديث JavaScript
```javascript
// وظيفة جدولة التركيب
function scheduleInstallation(orderId) {
    if (confirm('هل تريد جدولة تركيب لهذا الطلب؟')) {
        // الانتقال إلى صفحة الجدولة السريعة
        window.location.href = `{% url 'installations:quick_schedule_installation' 0 %}`.replace('0', orderId);
    }
}

// وظيفة جدولة التركيب من الـ modal
function scheduleInstallationFromModal(orderId, buttonElement) {
    if (confirm('هل تريد جدولة تركيب لهذا الطلب؟')) {
        // الانتقال إلى صفحة الجدولة السريعة
        window.location.href = `{% url 'installations:quick_schedule_installation' 0 %}`.replace('0', orderId);
    }
}
```

## المميزات الجديدة

### 1. الجدولة السريعة
- صفحة مخصصة لجدولة التركيب
- نموذج سهل الاستخدام مع حقول التاريخ والوقت
- قيم افتراضية ذكية (غداً في الساعة 9:00 صباحاً)

### 2. التحقق من الأخطاء
- التحقق من عدم وجود جدولة سابقة
- التحقق من صحة التاريخ والوقت
- رسائل خطأ واضحة باللغة العربية

### 3. تجربة مستخدم محسنة
- تصميم جميل ومتجاوب
- ألوان وأيقونات واضحة
- رسائل نجاح وخطأ واضحة

### 4. التكامل مع النظام
- تكامل كامل مع قسم الطلبات
- تحديث تلقائي للإحصائيات
- إعادة توجيه ذكية

## كيفية الاستخدام

### 1. من لوحة التحكم
1. انتقل إلى قسم التركيبات
2. اضغط على "جدولة تركيب" في أي طلب
3. ستنتقل إلى صفحة الجدولة السريعة
4. اختر التاريخ والوقت والفريق
5. اضغط "جدولة التركيب"

### 2. من القوائم الديناميكية
1. اضغط على أي بطاقة في لوحة التحكم
2. ستفتح نافذة مع قائمة الطلبات
3. اضغط "جدولة تركيب" بجانب أي طلب
4. ستنتقل إلى صفحة الجدولة السريعة

## النتائج المتوقعة

### 1. إصلاح الخطأ
- لن تظهر رسالة الخطأ مرة أخرى
- جميع الحقول المطلوبة ستكون مملوءة

### 2. تحسين تجربة المستخدم
- جدولة أسرع وأسهل
- رسائل واضحة
- تصميم جميل

### 3. تكامل أفضل
- تكامل كامل مع النظام
- تحديث تلقائي للبيانات
- إحصائيات دقيقة

## الاختبار

### 1. اختبار الجدولة السريعة
- انتقل إلى قسم التركيبات
- اضغط على "جدولة تركيب" لأي طلب
- تأكد من أن الصفحة تفتح بشكل صحيح
- جرب ملء النموذج وحفظه

### 2. اختبار التحقق من الأخطاء
- جرب جدولة طلب مجدول مسبقاً
- جرب جدولة بتاريخ ماضي
- تأكد من ظهور رسائل الخطأ المناسبة

### 3. اختبار التكامل
- تأكد من تحديث الإحصائيات
- تأكد من ظهور الطلب في القوائم المناسبة
- تأكد من عمل الروابط بشكل صحيح

## الخلاصة

تم إصلاح مشكلة جدولة التركيب بنجاح من خلال:
1. إصلاح دالة API لتشمل الحقول المطلوبة
2. إنشاء نظام جدولة سريع ومتطور
3. تحسين تجربة المستخدم
4. ضمان التكامل الكامل مع النظام

الآن يمكن جدولة التركيبات بسهولة وسرعة دون أي أخطاء. 