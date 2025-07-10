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
        ('tailoring', 'تفصيل'),
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
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='البائع',
        null=True,
        blank=True
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
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='رقم الطلب'
    )
    order_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الطلب'
    )
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
    contract_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='رقم العقد'
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
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
                raise ValidationError('رقم العقد مطلوب لخدمة التفصيل')
            
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

            # رفع ملف العقد إلى Google Drive إذا كان موجوداً ولم يتم رفعه مسبقاً
            if self.contract_file and not self.is_contract_uploaded_to_drive:
                try:
                    success, message = self.upload_contract_to_google_drive()
                    if success:
                        pass
                    else:
                        pass
                except Exception as e:
                    pass
            # حساب السعر النهائي بعد الحفظ (بعد وجود pk)
            try:
                final_price = self.calculate_final_price()
                if self.final_price != final_price:
                    self.final_price = final_price
                    # حفظ التغيير في السعر النهائي فقط إذا تغير
                    super().save(update_fields=['final_price'])
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
        """حساب تاريخ التسليم المتوقع بناءً على وضع الطلب"""
        if not self.order_date:
            return None

        # تحديد عدد الأيام بناءً على وضع الطلب
        if self.status == 'vip':
            days_to_add = 7
        else:  # normal
            days_to_add = 15

        # حساب التاريخ المتوقع
        expected_date = self.order_date.date() + timedelta(days=days_to_add)
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
            'tailoring': 'تفصيل'
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
        # إذا كان الطلب مكتمل أو جاهز للتركيب أو تم التسليم
        if self.order_status in ['completed', 'ready_install', 'delivered']:
            # التحقق من وجود أمر تصنيع وتاريخ إكمال
            if hasattr(self, 'manufacturing_order') and self.manufacturing_order.completion_date:
                return self.manufacturing_order.completion_date.date()
            # إذا كان تم التسليم، التحقق من تاريخ التسليم الفعلي
            elif self.order_status == 'delivered' and hasattr(self, 'manufacturing_order') and self.manufacturing_order.delivery_date:
                return self.manufacturing_order.delivery_date.date()
        
        # في جميع الحالات الأخرى، إرجاع التاريخ المتوقع
        return self.expected_delivery_date

    def get_delivery_date_label(self):
        """إرجاع تسمية التاريخ المناسبة حسب حالة الطلب"""
        if self.order_status in ['completed', 'ready_install']:
            return "تاريخ الإكمال"
        elif self.order_status == 'delivered':
            return "تاريخ التسليم"
        else:
            return "تاريخ التسليم المتوقع"

@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """دالة تعمل بعد حفظ الطلب مباشرة"""
    if not created and instance.tracker.has_changed('status'):
        instance.send_status_notification()


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='الطلب'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
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
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='manufacturing_deletion_logs',
        verbose_name='الطلب'
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
        return f'حذف أمر تصنيع #{self.manufacturing_order_id} - {self.order.order_number}'
