import json
import os
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.utils import send_notification
from django.db.models.signals import post_save
from django.dispatch import receiver
from model_utils import FieldTracker


def validate_pdf_file(value):
    """التحقق من أن الملف المرفوع هو PDF"""
    if value:
        ext = os.path.splitext(value.name)[1]
        if ext.lower() != '.pdf':
            raise ValidationError('يجب أن يكون الملف من نوع PDF فقط')

        # التحقق من حجم الملف (أقل من 10 ميجابايت)
        if value.size > 10 * 1024 * 1024:
            raise ValidationError('حجم الملف يجب أن يكون أقل من 10 ميجابايت')


class Order(models.Model):
    STATUS_CHOICES = [
        ('normal', 'عادي'),
        ('vip', 'VIP'),
    ]
    ORDER_TYPES = [
        ('accessory', 'إكسسوار'),
        ('installation', 'تركيب'),
        ('inspection', 'معاينة'),
        ('tailoring', 'تسليم'),
    ]
    TRACKING_STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('processing', 'قيد المعالجة'),
        ('warehouse', 'في المستودع'),
        ('factory', 'في المصنع'),
        ('cutting', 'قيد القص'),
        ('ready', 'جاهز للتسليم'),
        ('delivered', 'تم التسليم'),
    ]
    
    # حالات الطلب المستمدة من التصنيع
    ORDER_STATUS_CHOICES = [
        ('pending_approval', 'قيد الموافقة'),
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التصنيع'),
        ('ready_install', 'جاهز للتركيب'),
        ('completed', 'مكتمل'),
        ('delivered', 'تم التسليم'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
        ('manufacturing_deleted', 'أمر تصنيع محذوف'),
    ]
    DELIVERY_TYPE_CHOICES = [
        ('home', 'توصيل للمنزل'),
        ('branch', 'استلام من الفرع'),
    ]
    ITEM_TYPE_CHOICES = [
        ('fabric', 'قماش'),
        ('accessory', 'إكسسوار'),
    ]
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='customer_orders',
        verbose_name='العميل'
    )
    salesperson = models.ForeignKey(
        'accounts.Salesperson',
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='البائع',
        null=True,
        blank=True
    )
    salesperson_name_raw = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='اسم البائع من الجدول (إذا لم يوجد في النظام)',
        help_text='اسم البائع كما هو في الجدول إذا لم يوجد في النظام'
    )
    delivery_type = models.CharField(
        max_length=10,
        choices=DELIVERY_TYPE_CHOICES,
        default='branch',
        verbose_name='نوع التسليم'
    )
    delivery_address = models.TextField(
        blank=True,
        null=True,
        verbose_name='عنوان التسليم'
    )
    location_type = models.CharField(
        max_length=20,
        choices=[
            ('open', 'مفتوح'),
            ('compound', 'كومبوند'),
        ],
        blank=True,
        null=True,
        verbose_name='نوع المكان',
        help_text='نوع المكان (مفتوح أو كومبوند)'
    )
    location_address = models.TextField(
        blank=True,
        null=True,
        verbose_name='عنوان التركيب',
        help_text='عنوان التركيب بالتفصيل'
    )
    delivery_recipient_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='اسم المستلم',
        help_text='اسم الشخص الذي استلم الطلب'
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='رقم الطلب'
    )
    order_date = models.DateTimeField(default=timezone.now, editable=True, verbose_name='تاريخ الطلب')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='normal',
        verbose_name='وضع الطلب'
    )
    
    # حالة الطلب المستمدة من التصنيع
    order_status = models.CharField(
        max_length=30,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        verbose_name='حالة الطلب'
    )
    
    # حالة التركيب (مزامنة مع قسم التركيبات)
    installation_status = models.CharField(
        max_length=30,
        choices=[
            ('needs_scheduling', 'بحاجة جدولة'),
            ('scheduled', 'مجدول'),
            ('in_installation', 'قيد التركيب'),
            ('completed', 'مكتمل'),
            ('cancelled', 'ملغي'),
            ('modification_required', 'يحتاج تعديل'),
            ('modification_in_progress', 'التعديل قيد التنفيذ'),
            ('modification_completed', 'التعديل مكتمل'),
        ],
        default='needs_scheduling',
        verbose_name='حالة التركيب'
    )
    
    # حالة المعاينة (مزامنة مع قسم المعاينات)
    inspection_status = models.CharField(
        max_length=30,
        choices=[
            ('not_scheduled', 'غير مجدولة'),
            ('pending', 'في الانتظار'),
            ('scheduled', 'مجدولة'),
            ('in_progress', 'قيد التنفيذ'),
            ('completed', 'مكتملة'),
            ('cancelled', 'ملغية'),
        ],
        default='not_scheduled',
        verbose_name='حالة المعاينة'
    )
    
    # إشارة إكمال جميع المراحل
    is_fully_completed = models.BooleanField(
        default=False,
        verbose_name='مكتمل بالكامل',
        help_text='إشارة خضراء عند اكتمال جميع مراحل الطلب'
    )
    
    # Order type fields
    selected_types = models.JSONField(
        default=list,
        verbose_name='أنواع الطلب المختارة'
    )
    # Keep old fields for backward compatibility
    order_type = models.CharField(
        max_length=10,
        choices=[('product', 'منتج'), ('service', 'خدمة')],
        null=True,
        blank=True
    )
    service_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name='أنواع الخدمات'
    )
    tracking_status = models.CharField(
        max_length=20,
        choices=TRACKING_STATUS_CHOICES,
        default='pending',
        verbose_name='حالة التتبع'
    )
    last_notification_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ آخر إشعار'
    )
    invoice_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم الفاتورة'
    )
    invoice_number_2 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم الفاتورة الإضافي 2'
    )
    invoice_number_3 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم الفاتورة الإضافي 3'
    )
    contract_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم العقد'
    )
    contract_number_2 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم العقد الإضافي 2'
    )
    contract_number_3 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم العقد الإضافي 3'
    )
    contract_file = models.FileField(
        upload_to='contracts/',
        null=True,
        blank=True,
        validators=[validate_pdf_file],
        verbose_name='ملف العقد',
        help_text='يجب أن يكون الملف من نوع PDF وأقل من 10 ميجابايت'
    )
    payment_verified = models.BooleanField(
        default=False,
        verbose_name='تم التحقق من السداد'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='المبلغ الإجمالي'
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='المبلغ المدفوع'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='تم الإنشاء بواسطة'
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='الفرع',
        null=True
    )
    created_at = models.DateTimeField(default=timezone.now, editable=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="السعر النهائي"
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ التسليم المتوقع"
    )
    # حقول Google Drive للعقد
    contract_google_drive_file_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='معرف ملف العقد في Google Drive'
    )
    contract_google_drive_file_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='رابط ملف العقد في Google Drive'
    )
    contract_google_drive_file_name = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='اسم ملف العقد في Google Drive'
    )
    is_contract_uploaded_to_drive = models.BooleanField(
        default=False,
        verbose_name='تم رفع العقد إلى Google Drive'
    )
    
    # المعاينة المرتبطة بالطلب
    related_inspection = models.ForeignKey(
        'inspections.Inspection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='معاينة مرتبطة',
        help_text='المعاينة المرتبطة بهذا الطلب',
        related_name='related_orders'
    )
    
    # نوع المعاينة المرتبطة
    related_inspection_type = models.CharField(
        max_length=20,
        choices=[
            ('inspection', 'معاينة فعلية'),
            ('customer_side', 'طرف العميل'),
        ],
        blank=True,
        null=True,
        verbose_name='نوع المعاينة المرتبطة',
        help_text='نوع المعاينة المرتبطة بالطلب'
    )
    
    modified_at = models.DateTimeField(auto_now=True, help_text='آخر تحديث للطلب')
    tracker = FieldTracker(fields=['tracking_status', 'status'])
    class Meta:
        verbose_name = 'طلب'
        verbose_name_plural = 'الطلبات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer'], name='order_customer_idx'),
            models.Index(fields=['salesperson'], name='order_salesperson_idx'),
            models.Index(fields=['tracking_status'], name='order_tracking_status_idx'),
            models.Index(fields=['order_date'], name='order_date_idx'),
            models.Index(fields=['branch', 'tracking_status'], name='order_branch_status_idx'),
            models.Index(fields=['payment_verified'], name='order_payment_verified_idx'),
            models.Index(fields=['created_at'], name='order_created_at_idx'),
        ]
    def calculate_final_price(self):
        """حساب السعر النهائي للطلب"""
        # حساب السعر الأساسي من عناصر الطلب باستخدام استعلام أكثر كفاءة
        from django.db.models import F, Sum, ExpressionWrapper, DecimalField
        # استخدام استعلام مُحسّن لحساب السعر النهائي
        total = self.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('unit_price'),
                    output_field=DecimalField()
                )
            )
        )['total'] or 0
        self.final_price = total
        return self.final_price
    def save(self, *args, **kwargs):
        try:
            # تحقق مما إذا كان هذا كائن جديد (ليس له مفتاح أساسي)
            # is_new = self.pk is None <- تم الحذف
            # تحقق من وجود العميل
            if not self.customer:
                raise models.ValidationError('يجب اختيار العميل')
            # تحقق من وجود رقم طلب
            if not self.order_number:
                self.order_number = self.generate_unique_order_number()
            
            # Validate selected types
            selected_types = self.selected_types or []
            if isinstance(selected_types, str):
                try:
                    selected_types = json.loads(selected_types)
                except json.JSONDecodeError:
                    selected_types = [
                        st.strip() for st in selected_types.split(',') if st.strip()
                    ]
            if not selected_types:
                selected_types = ['inspection']  # Default to inspection if no types are selected
                self.selected_types = selected_types
            
            # Contract number validation
            if 'tailoring' in selected_types and not self.contract_number:
                raise ValidationError('رقم العقد مطلوب لخدمة التسليم')
            
            # Invoice number validation - required for all types except inspection alone
            if not (len(selected_types) == 1 and selected_types[0] == 'inspection'):
                if not self.invoice_number:
                    raise ValidationError('رقم الفاتورة مطلوب')
            
            # Set legacy fields for backward compatibility
            has_products = any(t in ['fabric', 'accessory'] for t in selected_types)
            has_services = any(
                t in ['installation', 'inspection', 'transport', 'tailoring']
                for t in selected_types
            )
            if has_products:
                self.order_type = 'product'
            if has_services:
                self.order_type = 'service'
                self.service_types = [
                    t for t in selected_types if t in [
                        'installation', 'inspection', 'transport', 'tailoring'
                    ]
                ]
            
            # Validate delivery address for home delivery
            if self.delivery_type == 'home' and not self.delivery_address:
                raise models.ValidationError(
                    'عنوان التسليم مطلوب لخدمة التوصيل للمنزل'
                )

            # حساب تاريخ التسليم المتوقع إذا لم يكن محدداً
            if not self.expected_delivery_date:
                self.expected_delivery_date = self.calculate_expected_delivery_date()

            # حفظ الطلب أولاً للحصول على مفتاح أساسي
            super().save(*args, **kwargs)
            # التأكد من أن الطلب تم حفظه بنجاح
            if not self.pk:
                raise models.ValidationError('فشل في حفظ الطلب: لم يتم إنشاء مفتاح أساسي')

            # تم إزالة التحقق من Google Drive بناءً على طلب المستخدم
            # رفع ملف العقد إلى Google Drive إذا كان موجوداً ولم يتم رفعه مسبقاً
            # if self.contract_file and not self.is_contract_uploaded_to_drive:
            #     try:
            #         success, message = self.upload_contract_to_google_drive()
            #         if success:
            #             pass
            #         else:
            #             pass
            #     except Exception as e:
            #         pass
            # حساب السعر النهائي بعد الحفظ (بعد وجود pk)
            try:
                final_price = self.calculate_final_price()
                if self.final_price != final_price:
                    self.final_price = final_price
                    # حفظ التغيير في السعر النهائي فقط إذا تغير
                    super().save(update_fields=['final_price'])
                    # تحديث المبلغ الإجمالي ليطابق السعر النهائي
                    self.total_amount = self.final_price
                    super().save(update_fields=['total_amount'])
            except Exception as e:
                pass
                self.final_price = 0
                super().save(update_fields=['final_price'])
        except Exception as e:
            # تسجيل الخطأ
            pass
            raise
    def notify_status_change(self, old_status, new_status, changed_by=None, notes=''):
        """إرسال إشعار عند تغيير حالة تتبع الطلب"""
        status_messages = {
            'pending': _('الطلب في قائمة الانتظار'),
            'processing': _('جاري معالجة الطلب'),
            'warehouse': _('الطلب في المستودع'),
            'factory': _('الطلب في المصنع'),
            'cutting': _('جاري قص القماش'),
            'ready': _('الطلب جاهز للتسليم'),
            'delivered': _('تم تسليم الطلب'),
        }
        title = _('تحديث حالة الطلب #{}'.format(self.order_number))
        message = _('{}\nتم تغيير الحالة من {} إلى {}'.format(
            status_messages.get(new_status, ''),
            self.get_tracking_status_display(),
            dict(self.TRACKING_STATUS_CHOICES)[new_status]
        ))
        if notes:
            message += f'\nملاحظات: {notes}'
        # إنشاء سجل لتغيير الحالة
        OrderStatusLog.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes
        )
        # إرسال إشعار للعميل
        send_notification(
            title=title,
            message=message,
            sender=changed_by or self.created_by,
            sender_department_code='orders',
            target_department_code='customers',
            target_branch=self.branch,
            priority='high' if new_status in ['ready', 'delivered'] else 'medium',
            related_object=self
        )
    def send_status_notification(self):
        """إرسال إشعار عند تغيير حالة الطلب"""
        status_messages = {
            'pending': _('تم إنشاء طلب جديد وهو قيد الانتظار'),
            'processing': _('تم بدء العمل على الطلب'),
            'completed': _('تم إكمال الطلب بنجاح'),
            'cancelled': _('تم إلغاء الطلب')
        }
        title = _('تحديث حالة الطلب #{}'.format(self.order_number))
        message = status_messages.get(self.status, _('تم تحديث حالة الطلب'))
        # إرسال إشعار للعميل
        send_notification(
            title=title,
            message=message,
            sender=self.created_by,  # استخدام created_by فقط لأن last_modified_by غير موجود
            sender_department_code='orders',
            target_department_code='customers',
            target_branch=self.branch,
            priority='high' if self.status in ['completed', 'cancelled'] else 'medium',
            related_object=self
        )

    def calculate_expected_delivery_date(self):
        """حساب تاريخ التسليم المتوقع بناءً على وضع الطلب ونوع الطلب"""
        if not self.order_date:
            return None

        # تحديد نوع الطلب للحصول على عدد الأيام المناسب
        order_type = 'vip' if self.status == 'vip' else 'normal'
        
        # التحقق من وجود معاينة في الطلب
        if 'inspection' in self.get_selected_types_list():
            order_type = 'inspection'
        
        # الحصول على عدد الأيام من الإعدادات
        days_to_add = DeliveryTimeSettings.get_delivery_days(order_type)

        # حساب التاريخ المتوقع
        expected_date = self.order_date + timedelta(days=days_to_add)
        return expected_date

    def generate_unique_order_number(self):
        """توليد رقم طلب فريد للعميل"""
        if not self.customer:
            import uuid
            return f"ORD-{str(uuid.uuid4())[:8]}"
        
        try:
            customer_code = self.customer.code if hasattr(self.customer, 'code') and self.customer.code else "UNKNOWN"
            
            # البحث عن آخر رقم طلب لهذا العميل
            last_order = Order.objects.filter(
                customer=self.customer,
                order_number__startswith=customer_code
            ).exclude(pk=self.pk).order_by('-order_number').first()
            
            if last_order:
                # Extract the number part and increment it
                try:
                    last_num = int(last_order.order_number.split('-')[-1])
                    next_num = last_num + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
            
            # التأكد من عدم تكرار رقم الطلب
            max_attempts = 100
            for attempt in range(max_attempts):
                potential_order_number = f"{customer_code}-{next_num:04d}"
                
                # التحقق من عدم وجود رقم مكرر (باستثناء الطلب الحالي)
                if not Order.objects.filter(order_number=potential_order_number).exclude(pk=self.pk).exists():
                    return potential_order_number
                
                next_num += 1
            
            # إذا فشل في العثور على رقم فريد، استخدم UUID
            import uuid
            return f"{customer_code}-{str(uuid.uuid4())[:8]}"
            
        except Exception as e:
            print(f"Error generating order number: {e}")
            # Use a fallback order number if we can't generate one
            import uuid
            return f"ORD-{str(uuid.uuid4())[:8]}"

    def upload_contract_to_google_drive(self):
        """رفع ملف العقد إلى Google Drive"""
        try:
            if not self.contract_file:
                return False, "لا يوجد ملف عقد للرفع"

            if self.is_contract_uploaded_to_drive:
                return False, "تم رفع ملف العقد مسبقاً"

            from orders.services.google_drive_service import get_contract_google_drive_service

            drive_service = get_contract_google_drive_service()
            if not drive_service:
                return False, "خدمة Google Drive غير متوفرة"

            # رفع الملف
            result = drive_service.upload_contract_file(
                self.contract_file.path,
                self
            )

            # تحديث بيانات الطلب
            self.contract_google_drive_file_id = result['file_id']
            self.contract_google_drive_file_url = result['view_url']
            self.contract_google_drive_file_name = result['filename']
            self.is_contract_uploaded_to_drive = True
            self.save(update_fields=[
                'contract_google_drive_file_id',
                'contract_google_drive_file_url',
                'contract_google_drive_file_name',
                'is_contract_uploaded_to_drive'
            ])

            return True, "تم رفع ملف العقد بنجاح"

        except Exception as e:
            return False, f"خطأ في رفع ملف العقد: {str(e)}"

    def __str__(self):
        return f'{self.order_number} - {self.customer.name}'

    def get_absolute_url(self):
        """إرجاع رابط تفاصيل الطلب باستخدام رقم الطلب"""
        from django.urls import reverse
        return reverse('orders:order_detail_by_code', args=[self.order_number])

    def get_selected_types_list(self):
        """Convert selected_types JSON to list"""
        if not self.selected_types:
            return []
        try:
            import json
            # Handle both string and already parsed data
            if isinstance(self.selected_types, str):
                parsed = json.loads(self.selected_types)

                # Handle double-encoded JSON like '["[\"inspection\"]"]'
                if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str):
                    try:
                        # Try to parse the inner JSON
                        inner_parsed = json.loads(parsed[0])
                        if isinstance(inner_parsed, list):
                            return inner_parsed
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Handle normal JSON
                if isinstance(parsed, list):
                    return parsed
                else:
                    return [parsed]  # Single value
            elif isinstance(self.selected_types, list):
                return self.selected_types
            else:
                return []
        except (json.JSONDecodeError, TypeError):
            # Fallback: try to extract from string representation
            if isinstance(self.selected_types, str):
                # Handle cases like "['inspection']" or '["inspection"]'
                import re
                matches = re.findall(r"'(\w+)'|\"(\w+)\"", self.selected_types)
                result = [match[0] or match[1] for match in matches]
                return result if result else []
            return []

    def get_selected_type_display(self):
        """Get display name for the first selected type"""
        types_list = self.get_selected_types_list()
        if not types_list:
            return "غير محدد"

        type_map = {
            'inspection': 'معاينة',
            'installation': 'تركيب',
            'accessory': 'إكسسوار',
            'tailoring': 'تسليم'
        }

        return type_map.get(types_list[0], types_list[0])

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        return self.total_amount - self.paid_amount
    @property
    def is_fully_paid(self):
        """التحقق من سداد الطلب بالكامل"""
        return self.remaining_amount <= 0

    def get_smart_delivery_date(self):
        """إرجاع التاريخ المناسب حسب حالة الطلب"""
        # إذا كان الطلب يحتوي على معاينة، اعرض تاريخ المعاينة
        if 'inspection' in self.get_selected_types_list():
            try:
                from inspections.models import Inspection
                inspection = self.inspections.first()
                if inspection:
                    # إذا كانت المعاينة مجدولة أو مكتملة، اعرض التاريخ المناسب
                    if inspection.status == 'scheduled' and inspection.scheduled_date:
                        return inspection.scheduled_date
                    elif inspection.status == 'completed' and inspection.completed_at:
                        return inspection.completed_at.date()
                    elif inspection.scheduled_date:
                        return inspection.scheduled_date
            except:
                pass
        
        # إذا كان الطلب يحتوي على تركيب، اعرض التاريخ المحدث م�� التركيب
        if 'installation' in self.get_selected_types_list():
            try:
                from installations.models import InstallationSchedule
                installation = InstallationSchedule.objects.filter(order=self).first()
                if installation:
                    # استخدام دالة get_installation_date التي تعطي الأولوية لتاريخ الإكمال الفعلي
                    installation_date = installation.get_installation_date()
                    if installation_date:
                        return installation_date
            except:
                pass
        
        # إذا كان الطلب مكتمل أو جاهز للتركيب أو تم التسليم
        if self.order_status in ['completed', 'ready_install', 'delivered']:
            # التحقق من وجود أمر تصنيع وتاريخ إكمال
            if hasattr(self, 'manufacturing_order') and self.manufacturing_order.completion_date:
                return self.manufacturing_order.completion_date.date()
            # إذا كان تم التسليم، التحقق من تاريخ التسليم الفعلي
            elif self.order_status == 'delivered' and hasattr(self, 'manufacturing_order') and self.manufacturing_order.delivery_date:
                return self.manufacturing_order.delivery_date.date()
        
        # في جميع الحالات الأخرى، إرجاع التاريخ المتوقع المحدث
        return self.expected_delivery_date

    def get_installation_date(self):
        """إرجاع تاريخ التركيب المناسب"""
        # البحث عن جدولة التركيب المرتبطة بالطلب
        try:
            from installations.models import InstallationSchedule
            installation = InstallationSchedule.objects.filter(order=self).first()
            if installation:
                return installation.get_installation_date()
        except:
            pass
        return None

    def get_installation_date_label(self):
        """إرجاع تسمية تاريخ التركيب المناسبة"""
        try:
            from installations.models import InstallationSchedule
            installation = InstallationSchedule.objects.filter(order=self).first()
            if installation:
                return installation.get_installation_date_label()
        except:
            pass
        return "تاريخ التركيب المتوقع"

    def get_expected_installation_date(self):
        """إرجاع تاريخ التركيب المتوقع"""
        # البحث عن جدولة التركيب المرتبطة بالطلب
        try:
            from installations.models import InstallationSchedule
            installation = InstallationSchedule.objects.filter(order=self).first()
            if installation:
                return installation.get_expected_installation_date()
        except:
            pass
        # إذا لم توجد جدولة، إرجاع تاريخ التسليم المتوقع
        return self.expected_delivery_date
    
    def update_installation_status(self):
        """تحديث حالة التركيب بناءً على قسم التركيبات"""
        if getattr(self, '_updating_installation_status', False):
            return
        setattr(self, '_updating_installation_status', True)
        try:
            from installations.models import InstallationSchedule
            installation = InstallationSchedule.objects.filter(order=self).first()
            
            if installation:
                # تحديث حالة التركيب من قسم التركيبات
                old_status = self.installation_status
                self.installation_status = installation.status
                
                # حفظ التغيير فقط إذا كان مختلفاً
                if old_status != self.installation_status:
                    self.save(update_fields=['installation_status'])
            else:
                # إذا لم توجد جدولة، تأكد من أن الحالة صحيحة
                if self.installation_status != 'needs_scheduling':
                    self.installation_status = 'needs_scheduling'
                    self.save(update_fields=['installation_status'])
        except Exception as e:
            # تسجيل الخطأ بدون إيقاف العملية
            print(f"خطأ في تحديث حالة التركيب للطلب {self.order_number}: {e}")
            pass
        setattr(self, '_updating_installation_status', False)
    
    def update_inspection_status(self):
        """تحديث حالة المعاينة بناءً على قسم المعاينات"""
        try:
            from inspections.models import Inspection
            inspection = Inspection.objects.filter(order=self).first()
            
            if inspection:
                self.inspection_status = inspection.status
            else:
                self.inspection_status = 'not_scheduled'
            
            self.save(update_fields=['inspection_status'])
        except Exception:
            pass
    
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
            
            # إرسال إشعار عند اكتمال الطلب
            if is_completed and self.created_by:
                try:
                    send_notification(
                        title="تم إكمال الطلب",
                        message=f"تم إكمال الطلب {self.order_number} بنجاح",
                        sender=self.created_by,
                        sender_department_code='orders',
                        target_department_code='customers',
                        target_branch=self.branch,
                        priority='high',
                        related_object=self
                    )
                except Exception as e:
                    print(f"خطأ في إرسال إشعار إكمال الطلب: {e}")
    
    def update_all_statuses(self):
        """تحديث جميع الحالات"""
        # تعيين علامة لتجنب الحلقة اللانهائية
        setattr(self, '_updating_statuses', True)
        try:
            self.update_installation_status()
            self.update_inspection_status()
            self.update_completion_status()
        finally:
            # إزالة العلامة بعد الانتهاء
            setattr(self, '_updating_statuses', False)

    def get_delivery_date_label(self):
        """إرجاع تسمية التاريخ المناسبة حسب حا��ة الطلب"""
        # إذا كان الطلب يحتوي على معاينة، اعرض تسمية المعاينة
        if 'inspection' in self.get_selected_types_list():
            try:
                from inspections.models import Inspection
                inspection = self.inspections.first()
                if inspection:
                    if inspection.status == 'scheduled':
                        return "تاريخ جدولة المعاينة"
                    elif inspection.status == 'completed':
                        return "تاريخ إتمام المعاينة"
                    else:
                        return "تاريخ المعاينة المتوقع"
            except:
                pass
            return "تاريخ المعاينة المتوقع"
        
        # إذا كان الطلب يحتوي على تركيب، اعرض التسمية المناسبة
        if 'installation' in self.get_selected_types_list():
            try:
                from installations.models import InstallationSchedule
                installation = InstallationSchedule.objects.filter(order=self).first()
                if installation:
                    return installation.get_installation_date_label()
            except:
                pass
        
        if self.order_status in ['completed', 'ready_install']:
            return "تاريخ الإكمال"
        elif self.order_status == 'delivered':
            return "تاريخ التسليم"
        else:
            return "تاريخ التسليم المتوقع"
    
    def get_display_status(self):
        """إرجاع الحالة المعروضة بناءً على منطق العرض الجديد"""
        # إذا كان الطلب من نوع معاينة
        if 'inspection' in self.get_selected_types_list():
            # البحث عن المعاينة المرتبطة بالطلب
            inspection = self.inspections.first()
            if inspection:
                # إذا كانت المعاينة مكتملة، اعرض "مكتمل"
                if inspection.status == 'completed':
                    return {
                        'status': 'completed',
                        'source': 'inspection',
                        'manufacturing_status': None
                    }
                else:
                    # اعرض حالة المعاينة
                    return {
                        'status': inspection.status,
                        'source': 'inspection',
                        'manufacturing_status': None
                    }
            else:
                # لا توجد معاينة، اعرض حالة الطلب الأساسية
                return {
                    'status': self.order_status,
                    'source': 'order',
                    'manufacturing_status': None
                }
        
        # إذا كان الطلب يحتوي على تركيب
        elif 'installation' in self.get_selected_types_list():
            # التحقق من وجود أمر تصنيع
            if hasattr(self, 'manufacturing_order') and self.manufacturing_order:
                manufacturing_status = self.manufacturing_order.status
                
                # إذا كانت حالة المصنع "جاهز للتركيب" أو ما بعدها، اعرض حالة التركيب
                if manufacturing_status in ['ready_install', 'completed', 'delivered']:
                    # تحديث حالة التركيب من قسم التركيبات
                    self.update_installation_status()
                    return {
                        'status': self.installation_status,
                        'source': 'installation',
                        'manufacturing_status': manufacturing_status
                    }
                else:
                    # قبل "جاهز للتركيب"، اعرض حالة المصنع
                    return {
                        'status': manufacturing_status,
                        'source': 'manufacturing',
                        'manufacturing_status': manufacturing_status
                    }
            else:
                # لا يوجد أمر تصنيع، اعرض حالة الطلب الأساسية
                return {
                    'status': self.order_status,
                    'source': 'order',
                    'manufacturing_status': None
                }
        else:
            # الطلب لا يحتوي على تركيب، اعرض حالة الطلب الأساسية
            return {
                'status': self.order_status,
                'source': 'order',
                'manufacturing_status': None
            }
    
    def get_display_status_badge_class(self):
        """إرجاع فئة البادج المناسبة للحالة المعروضة"""
        display_info = self.get_display_status()
        status = display_info['status']
        source = display_info['source']
        
        # فئات البادج حسب المصدر والحالة - ألوان موحدة
        if source == 'inspection':
            inspection_badges = {
                'not_scheduled': 'bg-secondary',  # فضي
                'pending': 'bg-warning text-dark',  # برتقالي
                'scheduled': 'bg-info',  # أزرق فاتح
                'in_progress': 'bg-primary',  # أزرق
                'completed': 'bg-success',  # أخضر
                'cancelled': 'bg-danger',  # أحمر
            }
            return inspection_badges.get(status, 'bg-secondary')
        
        elif source == 'installation':
            installation_badges = {
                'needs_scheduling': 'bg-secondary',  # فضي
                'scheduled': 'bg-info',  # أزرق فاتح
                'in_installation': 'bg-warning text-dark',  # برتقالي
                'completed': 'bg-success',  # أخضر
                'cancelled': 'bg-danger',  # أحمر
                'modification_required': 'bg-warning text-dark',  # برتقالي
                'modification_in_progress': 'bg-info',  # أزرق فاتح
                'modification_completed': 'bg-success',  # أخضر
            }
            return installation_badges.get(status, 'bg-secondary')
        
        elif source == 'manufacturing':
            manufacturing_badges = {
                'pending_approval': 'bg-warning text-dark',  # برتقالي
                'pending': 'bg-warning text-dark',  # برتقالي
                'in_progress': 'bg-primary',  # أزرق
                'ready_install': 'bg-success',  # أخضر
                'completed': 'bg-success',  # أخضر
                'delivered': 'bg-success',  # أخضر
                'rejected': 'bg-danger',  # أحمر
                'cancelled': 'bg-danger',  # أحمر
            }
            return manufacturing_badges.get(status, 'bg-secondary')
        
        else:  # source == 'order'
            order_badges = {
                'pending_approval': 'bg-warning text-dark',  # برتقالي
                'pending': 'bg-warning text-dark',  # برتقالي
                'in_progress': 'bg-primary',  # أزرق
                'ready_install': 'bg-success',  # أخضر
                'completed': 'bg-success',  # أخضر
                'delivered': 'bg-success',  # أخضر
                'rejected': 'bg-danger',  # أحمر
                'cancelled': 'bg-danger',  # أحمر
                'manufacturing_deleted': 'bg-secondary',  # فضي
            }
            return order_badges.get(status, 'bg-secondary')
    
    def get_display_status_icon(self):
        """إرجاع الأيقونة المناسبة للحالة المعروضة"""
        display_info = self.get_display_status()
        status = display_info['status']
        source = display_info['source']
        
        # أيقونات حسب المصدر والحالة
        if source == 'inspection':
            inspection_icons = {
                'not_scheduled': 'fas fa-clock',
                'pending': 'fas fa-hourglass-half',
                'scheduled': 'fas fa-calendar',
                'in_progress': 'fas fa-search',
                'completed': 'fas fa-check',
                'cancelled': 'fas fa-times',
            }
            return inspection_icons.get(status, 'fas fa-question')
        
        elif source == 'installation':
            installation_icons = {
                'needs_scheduling': 'fas fa-clock',
                'scheduled': 'fas fa-calendar',
                'in_installation': 'fas fa-tools',
                'completed': 'fas fa-check',
                'cancelled': 'fas fa-times',
                'modification_required': 'fas fa-exclamation-triangle',
                'modification_in_progress': 'fas fa-wrench',
                'modification_completed': 'fas fa-check-double',
            }
            return installation_icons.get(status, 'fas fa-question')
        
        elif source == 'manufacturing':
            manufacturing_icons = {
                'pending_approval': 'fas fa-clock',
                'pending': 'fas fa-hourglass-half',
                'in_progress': 'fas fa-cogs',
                'ready_install': 'fas fa-tools',
                'completed': 'fas fa-check',
                'delivered': 'fas fa-truck',
                'rejected': 'fas fa-times',
                'cancelled': 'fas fa-ban',
            }
            return manufacturing_icons.get(status, 'fas fa-question')
        
        else:  # source == 'order'
            order_icons = {
                'pending_approval': 'fas fa-clock',
                'pending': 'fas fa-hourglass-half',
                'in_progress': 'fas fa-cogs',
                'ready_install': 'fas fa-tools',
                'completed': 'fas fa-check',
                'delivered': 'fas fa-truck',
                'rejected': 'fas fa-times',
                'cancelled': 'fas fa-ban',
                'manufacturing_deleted': 'fas fa-trash-alt',
            }
            return order_icons.get(status, 'fas fa-question')
    
    def get_display_status_text(self):
        """إرجاع النص المناسب للحالة المعروضة"""
        display_info = self.get_display_status()
        status = display_info['status']
        source = display_info['source']
        
        # نصوص الحالات حسب المصدر
        if source == 'inspection':
            inspection_texts = {
                'not_scheduled': 'غير مجدولة',
                'pending': 'في الانتظار',
                'scheduled': 'مجدولة',
                'in_progress': 'قيد التنفيذ',
                'completed': 'مكتمل',
                'cancelled': 'ملغية',
            }
            return inspection_texts.get(status, status)
        
        elif source == 'installation':
            installation_texts = {
                'needs_scheduling': 'بحاجة جدولة',
                'scheduled': 'مجدول',
                'in_installation': 'قيد التركيب',
                'completed': 'مكتمل',
                'cancelled': 'ملغي',
                'modification_required': 'يحتاج تعديل',
                'modification_in_progress': 'التعديل قيد التنفيذ',
                'modification_completed': 'التعديل مكتمل',
            }
            return installation_texts.get(status, status)
        
        elif source == 'manufacturing':
            manufacturing_texts = {
                'pending_approval': 'قيد الموافقة',
                'pending': 'قيد الانتظار',
                'in_progress': 'قيد التصنيع',
                'ready_install': 'جاهز للتركيب',
                'completed': 'مكتمل',
                'delivered': 'تم التسليم',
                'rejected': 'مرفوض',
                'cancelled': 'ملغي',
            }
            return manufacturing_texts.get(status, status)
        
        else:  # source == 'order'
            order_texts = {
                'pending_approval': 'قيد الموافقة',
                'pending': 'قيد الانتظار',
                'in_progress': 'قيد التصنيع',
                'ready_install': 'جاهز للتركيب',
                'completed': 'مكتمل',
                'delivered': 'تم التسليم',
                'rejected': 'مرفوض',
                'cancelled': 'ملغي',
                'manufacturing_deleted': 'أمر تصنيع محذوف',
            }
            return order_texts.get(status, status)
    
    @property
    def is_manufacturing_order(self):
        """التحقق من وجود أمر تصنيع مرتبط بالطلب"""
        return hasattr(self, 'manufacturing_order') and self.manufacturing_order is not None
    
    @property
    def is_delivered_manufacturing_order(self):
        """التحقق من أن أمر التصنيع تم تسليمه"""
        if self.is_manufacturing_order:
            return self.manufacturing_order.status == 'delivered'
        return False

    def get_display_inspection_status(self):
        """
        إرجاع حالة المعاينة حسب نوع الطلب:
        1. طلب معاينة: يعرض حالة المعاينة التلقائية المنشأة
        2. طلب تفصيل/تركيب: يعرض زر تفاصيل المعاينة أو طرف العميل
        """
        # إذا كان طلب معاينة - يجب أن تكون هناك معاينة تلقائية
        if 'inspection' in self.get_selected_types_list():
            # البحث عن المعاينة المرتبطة بالطلب
            inspection = self.inspections.first()
            if inspection:
                return {
                    'status': inspection.status,
                    'text': inspection.get_status_display(),
                    'badge_class': inspection.get_status_badge_class(),
                    'icon': inspection.get_status_icon(),
                    'inspection_id': inspection.id,
                    'contract_number': inspection.contract_number,
                    'created_at': inspection.created_at,
                    'is_inspection_order': True
                }
            else:
                # إذا لم توجد معاينة (حالة نادرة)
                return {
                    'status': 'not_created',
                    'text': 'لم يتم إنشاء المعاينة',
                    'badge_class': 'bg-warning',
                    'icon': 'fas fa-exclamation-triangle',
                    'inspection_id': None,
                    'contract_number': None,
                    'created_at': None,
                    'is_inspection_order': True
                }
        
        # إذا كان طلب تفصيل أو تركيب
        elif 'tailoring' in self.get_selected_types_list() or 'installation' in self.get_selected_types_list():
            if self.related_inspection_type == 'customer_side':
                return {
                    'status': 'customer_side',
                    'text': 'طرف العميل',
                    'badge_class': 'bg-info',
                    'icon': 'fas fa-user',
                    'inspection_id': None,
                    'contract_number': None,
                    'created_at': None,
                    'is_inspection_order': False
                }
            elif self.related_inspection:
                return {
                    'status': self.related_inspection.status,
                    'text': self.related_inspection.get_status_display(),
                    'badge_class': self.related_inspection.get_status_badge_class(),
                    'icon': self.related_inspection.get_status_icon(),
                    'inspection_id': self.related_inspection.id,
                    'contract_number': self.related_inspection.contract_number,
                    'created_at': self.related_inspection.created_at,
                    'is_inspection_order': False
                }
            else:
                return {
                    'status': 'not_related',
                    'text': 'لا يوجد',
                    'badge_class': 'bg-secondary',
                    'icon': 'fas fa-minus',
                    'inspection_id': None,
                    'contract_number': None,
                    'created_at': None,
                    'is_inspection_order': False
                }
        
        # للأنواع الأخرى
        else:
            return {
                'status': 'not_applicable',
                'text': 'لا ينطبق',
                'badge_class': 'bg-secondary',
                'icon': 'fas fa-minus',
                'inspection_id': None,
                'contract_number': None,
                'created_at': None,
                'is_inspection_order': False
            }

@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """تحديث الحالات المرتبطة عند حفظ الطلب"""
    # تجنب الحلقة اللانهائية عن طريق التحقق من وجود علامة التحديث
    if not created and not getattr(instance, '_updating_statuses', False):
        # تحديث جميع الحالات المرتبطة
        instance.update_all_statuses()

# Signal لتحديث حالة الطلب عند تغيير حالة التركيب
@receiver(post_save, sender='installations.InstallationSchedule')
def update_order_installation_status(sender, instance, **kwargs):
    """تحديث حالة الطلب عند تغيير حالة التركيب"""
    try:
        if instance.order:
            # تحديث حالة التركيب في الطلب فقط إذا تغيرت
            if instance.order.installation_status != instance.status:
                instance.order.installation_status = instance.status
                # استخدام update_fields لتجنب استدعاء دالة save الكاملة
                instance.order.save(update_fields=['installation_status'])
                
                # تحديث إشارة الإكمال بدون استدعاء save الكاملة
                try:
                    instance.order.update_completion_status()
                except Exception as e:
                    print(f"خطأ في تحديث حالة الإكمال: {e}")
                
                # إذا تم إكمال التركيب، تحديث حالة الطلب إلى مكتمل
                if instance.status == 'completed':
                    if instance.order.order_status not in ['completed', 'delivered']:
                        instance.order.order_status = 'completed'
                        # استخدام update_fields لتجنب استدعاء دالة save الكاملة
                        instance.order.save(update_fields=['order_status'])
    except Exception as e:
        print(f"خطأ في تحديث حالة الطلب من التركيب: {e}")
        pass


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='الطلب'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='المنتج'
    )
    quantity = models.PositiveIntegerField(verbose_name='الكمية')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    item_type = models.CharField(
        max_length=10,
        choices=Order.ITEM_TYPE_CHOICES,
        default='fabric',
        verbose_name='نوع العنصر'
    )
    processing_status = models.CharField(
        max_length=20,
        choices=Order.TRACKING_STATUS_CHOICES,
        default='pending',
        verbose_name='حالة المعالجة'
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    class Meta:
        verbose_name = 'عنصر الطلب'
        verbose_name_plural = 'عناصر الطلب'
        indexes = [
            models.Index(fields=['order'], name='order_item_order_idx'),
            models.Index(fields=['product'], name='order_item_product_idx'),
            models.Index(fields=['processing_status'], name='order_item_status_idx'),
            models.Index(fields=['item_type'], name='order_item_type_idx'),
        ]
    def __str__(self):
        return f'{self.product.name} ({self.quantity})'
    @property
    def total_price(self):
        """Calculate total price for this item"""
        if self.quantity is None or self.unit_price is None:
            return 0
        return self.quantity * self.unit_price
    def save(self, *args, **kwargs):
        """Save order item with validation"""
        try:
            # التحقق من أن الطلب له مفتاح أساسي
            if not self.order.pk:
                raise models.ValidationError('يجب حفظ الطلب أولاً قبل إنشاء عنصر الطلب')
            super().save(*args, **kwargs)
            # تحديث السعر النهائي للطلب
            try:
                self.order.calculate_final_price()
                self.order.save(update_fields=['final_price'])
            except Exception as e:
                pass
        except Exception as e:
            pass
            raise


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'نقداً'),
        ('bank_transfer', 'تحويل بنكي'),
        ('check', 'شيك'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name='الطلب')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash', verbose_name='طريقة الدفع')
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الدفع')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='رقم المرجع')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='تم الإنشاء بواسطة')
    class Meta:
        verbose_name = 'دفعة'
        verbose_name_plural = 'الدفعات'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['order'], name='payment_order_idx'),
            models.Index(fields=['payment_method'], name='payment_method_idx'),
            models.Index(fields=['payment_date'], name='payment_date_idx'),
            models.Index(fields=['created_by'], name='payment_created_by_idx'),
        ]
    def __str__(self):
        return f'{self.order.order_number} - {self.amount} ({self.get_payment_method_display()})'
    def save(self, *args, **kwargs):
        """Update order's paid amount when payment is saved"""
        try:
            # التحقق من أن الطلب له مفتاح أساسي
            if not self.order.pk:
                raise models.ValidationError('يجب حفظ الطلب أولاً قبل إنشاء دفعة')
            super().save(*args, **kwargs)
            # Update order's paid amount
            try:
                total_payments = Payment.objects.filter(order=self.order).aggregate(
                    total=models.Sum('amount')
                )['total'] or 0
                self.order.paid_amount = total_payments
                self.order.save(update_fields=['paid_amount'])
            except Exception as e:
                pass
        except Exception as e:
            pass
            raise


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs', verbose_name=_('الطلب'))
    old_status = models.CharField(max_length=20, choices=Order.TRACKING_STATUS_CHOICES, verbose_name=_('الحالة السابقة'))
    new_status = models.CharField(max_length=20, choices=Order.TRACKING_STATUS_CHOICES, verbose_name=_('الحالة الجديدة'))
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_('تم التغيير بواسطة'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ التغيير'))
    class Meta:
        verbose_name = _('سجل حالة الطلب')
        verbose_name_plural = _('سجلات حالة الطلب')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='status_log_order_idx'),
            models.Index(fields=['created_at'], name='status_log_date_idx'),
        ]
    def __str__(self):
        return f'{self.order.order_number} - {self.get_new_status_display()}'
    def save(self, *args, **kwargs):
        try:
            # التحقق من أن الطلب له مفتاح أساسي
            if not self.order.pk:
                raise models.ValidationError('يجب حفظ الطلب أولاً قبل إنشاء سجل حالة')
            if not self.old_status and self.order:
                self.old_status = self.order.tracking_status
            super().save(*args, **kwargs)
            # تحديث حالة الطلب
            try:
                if self.order and self.new_status != self.order.tracking_status:
                    self.order.tracking_status = self.new_status
                    self.order.last_notification_date = timezone.now()
                    self.order.save(update_fields=['tracking_status', 'last_notification_date'])
            except Exception as e:
                pass
        except Exception as e:
            pass
            raise


class ManufacturingDeletionLog(models.Model):
    """سجل حذف أوامر التصنيع"""
    order_id = models.PositiveIntegerField(
        verbose_name=_('معرف الطلب المحذوف'),
        default=0
    )
    order_number = models.CharField(
        max_length=50,
        verbose_name='رقم الطلب المحذوف',
        blank=True,
        null=True
    )
    manufacturing_order_id = models.PositiveIntegerField(
        verbose_name='معرف أمر التصنيع المحذوف'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='تم الحذف بواسطة'
    )
    deleted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الحذف'
    )
    reason = models.TextField(
        blank=True,
        verbose_name='سبب الحذف'
    )
    manufacturing_order_data = models.JSONField(
        default=dict,
        verbose_name='بيانات أمر التصنيع المحذوف'
    )

    class Meta:
        verbose_name = 'سجل حذف أمر تصنيع'
        verbose_name_plural = 'سجلات حذف أوامر التصنيع'
        ordering = ['-deleted_at']

    def __str__(self):
        return f'حذف أمر تصنيع #{self.manufacturing_order_id} - {self.order_number}'


class DeliveryTimeSettings(models.Model):
    """إعدادات مواعيد التسليم للطلبات والمعاينات"""
    ORDER_TYPE_CHOICES = [
        ('normal', 'طلب عادي'),
        ('vip', 'طلب VIP'),
        ('inspection', 'معاينة'),
    ]
    
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        verbose_name='نوع الطلب'
    )
    delivery_days = models.PositiveIntegerField(
        verbose_name='عدد أيام التسليم',
        help_text='عدد الأيام المتوقعة للتسليم'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='مفعل'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    
    class Meta:
        verbose_name = 'إعداد موعد التسليم'
        verbose_name_plural = 'إعدادات مواعيد التسليم'
        unique_together = ['order_type']
        ordering = ['order_type']
    
    def __str__(self):
        return f"{self.get_order_type_display()} - {self.delivery_days} يوم"
    
    @classmethod
    def get_delivery_days(cls, order_type):
        """الحصول على عدد أيام التسليم لنوع طلب معين"""
        try:
            setting = cls.objects.get(order_type=order_type, is_active=True)
            return setting.delivery_days
        except cls.DoesNotExist:
            # القيم الافتراضية
            defaults = {
                'normal': 15,
                'vip': 7,
                'inspection': 2,  # 48 ساعة
            }
            return defaults.get(order_type, 15)

    def get_scheduling_date(self):
        """إرجاع تاريخ الجدولة للعرض في الجدول"""
        try:
            from installations.models import InstallationSchedule
            installation = InstallationSchedule.objects.filter(order=self).first()
            if installation and installation.scheduled_date:
                return installation.scheduled_date
        except:
            pass
        return None

    def get_scheduling_date_display(self):
        """إرجاع تاريخ الجدولة مع التنسيق للعرض"""
        scheduling_date = self.get_scheduling_date()
        if scheduling_date:
            return scheduling_date.strftime('%Y-%m-%d')
        return None


# استيراد نماذج الفواتير
from .invoice_models import InvoiceTemplate, InvoicePrintLog
