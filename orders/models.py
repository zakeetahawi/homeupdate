import json
import os
import logging
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver
from model_utils import FieldTracker

logger = logging.getLogger(__name__)


def validate_pdf_file(value):
    """التحقق من أن الملف المرفوع هو PDF"""
    if value:
        ext = os.path.splitext(value.name)[1]
        if ext.lower() != '.pdf':
            raise ValidationError('يجب أن يكون الملف من نوع PDF فقط')

        # التحقق من حجم الملف (أقل من 50 ميجابايت)
        if value.size > 50 * 1024 * 1024:
            raise ValidationError('حجم الملف يجب أن يكون أقل من 50 ميجابايت')


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
        ('products', 'منتجات'),
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
        default='pending_approval',
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
    
    # إشارة التحديث التلقائي (لمنع التسجيل المكرر في السجلات)
    is_auto_update = models.BooleanField(
        default=False,
        verbose_name='تحديث تلقائي',
        help_text='إشارة للتحديثات التلقائية لمنع التسجيل المكرر'
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
        help_text='يجب أن يكون الملف من نوع PDF وأقل من 50 ميجابايت'
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
    tracker = FieldTracker(fields=[
        'tracking_status', 'status', 'notes', 'contract_number', 'contract_number_2', 'contract_number_3',
        'invoice_number', 'invoice_number_2', 'invoice_number_3', 'delivery_address', 'location_address',
        'expected_delivery_date'
    ])
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
    def calculate_final_price(self, force_update=False):
        """حساب السعر النهائي للطلب مع الخصم"""
        # التحقق من وجود مفتاح أساسي أولاً
        if not self.pk:
            return 0

        # حماية الطلبات المدفوعة من تغيير الأسعار (إلا إذا كان إجباري)
        if not force_update and self.paid_amount > 0:
            # إذا كان هناك مبلغ مدفوع، لا نغير السعر النهائي
            return self.final_price or 0

        # حساب السعر الأساسي من عناصر الطلب مع الخصم
        total = 0
        total_discount = 0

        for item in self.items.select_related('product').all():
            item_total = item.quantity * item.unit_price
            item_discount = item_total * (item.discount_percentage / 100) if item.discount_percentage else 0
            total += item_total
            total_discount += item_discount

        # تحديث القيم في الذاكرة فقط (بدون حفظ)
        # final_price should represent the pre-discount subtotal.
        # final_price_after_discount is provided by the property that subtracts total_discount_amount.
        self.final_price = total
        self.total_amount = total

        # return the pre-discount subtotal to avoid callers accidentally treating
        # the returned value as already-discounted (which would cause double-discounting).
        return total
    
    @property
    def total_discount_amount(self):
        """إجمالي مبلغ الخصم"""
        total_discount = Decimal('0')
        for item in self.items.all():
            try:
                # item.discount_amount is usually a Decimal, but guard against None
                amt = item.discount_amount if item.discount_amount is not None else 0
                total_discount += Decimal(str(amt))
            except Exception:
                # Fallback: treat invalid values as zero
                try:
                    total_discount += Decimal(0)
                except Exception:
                    pass
        return total_discount
    
    @property
    def final_price_after_discount(self):
        """السعر النهائي بعد الخصم"""
        # Coerce None to Decimal(0) to avoid TypeError when final_price not yet calculated
        final = self.final_price if self.final_price is not None else Decimal('0')
        try:
            final_dec = Decimal(str(final))
        except Exception:
            final_dec = Decimal('0')
        return final_dec - self.total_discount_amount
    def save(self, *args, **kwargs):
        try:
            # تحقق مما إذا كان هذا كائن جديد (ليس له مفتاح أساسي)
            is_new = self.pk is None

            # متغيرات لتتبع تغيير الحالة
            old_order_status = None
            old_tracking_status = None

            # إذا كان الطلب موجود مسبقاً، احفظ الحالات القديمة
            if not is_new:
                try:
                    old_instance = Order.objects.get(pk=self.pk)
                    old_order_status = old_instance.order_status
                    old_tracking_status = old_instance.tracking_status
                except Order.DoesNotExist:
                    pass

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
                # لا تعيين افتراضي - يجب أن يكون النوع محدد صراحة
                raise ValidationError('يجب تحديد نوع الطلب')

            # Contract validation - only for tailoring and installation
            if ('tailoring' in selected_types or 'installation' in selected_types):
                # رقم العقد مطلوب فقط إذا كان هناك ملف عقد مرفوع
                if self.contract_file and not self.contract_number:
                    raise ValidationError('رقم العقد مطلوب عند رفع ملف العقد')

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

            # توليد رقم العقد تلقائياً إذا لم يكن موجوداً
            if not self.contract_number and ('tailoring' in selected_types or 'installation' in selected_types):
                self.contract_number = self.generate_unique_contract_number()

            # معالجة حالة طلبات المنتجات
            if 'products' in selected_types:
                # طلبات المنتجات تبدأ بحالة "قيد الانتظار"
                if is_new or not self.order_status:
                    self.order_status = 'pending'
                    self.tracking_status = 'pending'

            # حفظ الطلب أولاً للحصول على مفتاح أساسي
            super().save(*args, **kwargs)
            # التأكد من أن الطلب تم حفظه بنجاح
            if not self.pk:
                raise models.ValidationError('فشل في حفظ الطلب: لم يتم إنشاء مفتاح أساسي')

            # جدولة رفع ملف العقد إلى Google Drive بشكل غير متزامن
            if self.contract_file and not self.is_contract_uploaded_to_drive:
                try:
                    # استخدام مهمة خلفية لرفع الملف
                    from .tasks import upload_contract_to_drive_async
                    upload_contract_to_drive_async.delay(self.pk)
                    logger.info(f"تم جدولة رفع ملف العقد للطلب {self.order_number}")
                except Exception as e:
                    logger.error(f"خطأ في جدولة رفع ملف العقد للطلب {self.order_number}: {str(e)}")
                    # في حالة فشل الجدولة، نحاول الرفع المباشر كبديل
                    try:
                        success, message = self.upload_contract_to_google_drive()
                        if success:
                            logger.info(f"تم رفع ملف العقد للطلب {self.order_number} بنجاح (مباشر)")
                        else:
                            logger.warning(f"فشل في رفع ملف العقد للطلب {self.order_number}: {message}")
                    except Exception as e2:
                        logger.error(f"خطأ في رفع ملف العقد للطلب {self.order_number}: {str(e2)}")
            # جدولة حساب السعر النهائي بشكل غير متزامن لتجنب البطء
            if is_new or 'final_price' not in kwargs.get('update_fields', []):
                try:
                    from .tasks import calculate_order_totals_async
                    calculate_order_totals_async.delay(self.pk)
                except Exception as e:
                    # في حالة فشل الجدولة، نحسب السعر مباشرة
                    try:
                        final_price = self.calculate_final_price()
                        if self.final_price != final_price:
                            self.final_price = final_price
                            self.total_amount = final_price
                            super().save(update_fields=['final_price', 'total_amount'])
                    except Exception as calc_error:
                        logger.error(f"خطأ في حساب السعر النهائي للطلب {self.order_number}: {str(calc_error)}")
                        self.final_price = 0
                        super().save(update_fields=['final_price'])

            # إنشاء الإشعارات المناسبة
            # تم إزالة استدعاءات دوال الإشعارات
            pass

        except Exception as e:
            # تسجيل الخطأ
            logger.error(f"خطأ في حفظ الطلب {getattr(self, 'order_number', 'غير محدد')}: {str(e)}")
            raise

    def delete(self, *args, **kwargs):
        """حذف الطلب مع حذف السجلات المرتبطة بشكل آمن"""
        from django.db import connection, transaction
        from django.db.models.signals import post_delete
        from . import signals as order_signals

        # تعيين علامة لتجنب تشغيل signals أثناء الحذف
        self._is_being_deleted = True

        # تعطيل signal حذف عناصر الطلب مؤقتاً
        post_delete.disconnect(order_signals.log_order_item_deletion, sender=OrderItem)

        try:
            # استخدام معاملة واحدة لحذف السجلات والطلب
            with transaction.atomic():
                # حذف سجلات OrderStatusLog أولاً باستخدام raw SQL
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM orders_orderstatuslog WHERE order_id = %s", [self.pk])

                # حذف الطلب (سيتم حذف العناصر المرتبطة تلقائياً بسبب CASCADE)
                super().delete(*args, **kwargs)
        finally:
            # إعادة تفعيل signal حذف عناصر الطلب
            post_delete.connect(order_signals.log_order_item_deletion, sender=OrderItem)

# (وصل الإشارات يتم بعد تعريف الكلاس في أسفل الملف)
    # تم إزالة دالة create_order_notifications

    # تم إزالة دالة create_status_change_notification

    def notify_status_change(self, old_status, new_status, changed_by=None, notes=''):
        """إرسال إشعار عند تغيير حالة تتبع الطلب"""
        # إنشاء سجل لتغيير الحالة فقط
        OrderStatusLog.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes
        )


    def calculate_expected_delivery_date(self):
        """حساب تاريخ التسليم المتوقع بناءً على نوع الطلب ونوع الخدمة"""
        if not self.order_date:
            return None

        # تحديد نوع الطلب والخدمة
        selected_types = self.get_selected_types_list()

        # تحديد نوع الطلب
        order_type = 'vip' if self.status == 'vip' else 'normal'

        # تحديد نوع الخدمة (أول نوع في القائمة حسب الأولوية)
        service_type = None
        service_priority = ['inspection', 'accessory', 'products', 'installation', 'tailoring']
        for service in service_priority:
            if service in selected_types:
                service_type = service
                break

        # الحصول على عدد الأيام من الإعدادات المحدثة
        try:
            days_to_add = DeliveryTimeSettings.get_delivery_days(
                order_type=order_type,
                service_type=service_type
            )
        except Exception as e:
            logger.error(f"خطأ في جلب إعدادات التسليم: {str(e)}")
            # القيم الافتراضية
            default_days = {
                'inspection': 2,
                'accessory': 5,
                'products': 3,
                'installation': 10,
                'tailoring': 7,
                'vip': 7,
                'normal': 15
            }

            # استخدام نوع الخدمة أولاً، ثم نوع الطلب
            if service_type and service_type in default_days:
                days_to_add = default_days[service_type]
            elif order_type in default_days:
                days_to_add = default_days[order_type]
            else:
                days_to_add = 15

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

    def generate_unique_contract_number(self):
        """توليد رقم عقد فريد بصيغة c1, c2, c3, إلخ"""
        if not self.customer:
            return "c1"
        
        try:
            # البحث عن آخر رقم عقد لهذا العميل يبدأ بـ "c"
            last_orders = Order.objects.filter(
                customer=self.customer,
                contract_number__isnull=False,
                contract_number__startswith='c'
            ).exclude(pk=self.pk).order_by('-contract_number')
            
            next_num = 1
            if last_orders.exists():
                # Extract the highest contract number
                for order in last_orders:
                    try:
                        # Extract number from format like "c1", "c2", etc.
                        contract_num_str = order.contract_number.lower()
                        if contract_num_str.startswith('c'):
                            num = int(contract_num_str[1:])
                            if num >= next_num:
                                next_num = num + 1
                    except (ValueError, IndexError):
                        continue
            
            # التأكد من عدم تكرار رقم العقد
            max_attempts = 100
            for attempt in range(max_attempts):
                potential_contract_number = f"c{next_num}"
                
                # التحقق من عدم وجود رقم مكرر (باستثناء الطلب الحالي)
                if not Order.objects.filter(
                    customer=self.customer,
                    contract_number=potential_contract_number
                ).exclude(pk=self.pk).exists():
                    return potential_contract_number
                
                next_num += 1
            
            # إذا فشل في العثور على رقم فريد، استخدم رقم عشوائي كبير
            import random
            return f"c{random.randint(100, 999)}"
            
        except Exception as e:
            logger.error(f"Error generating contract number: {e}")
            return "c1"

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
            'tailoring': 'تسليم',
            'products': 'منتجات',
            'fabric': 'أقمشة',
            'transport': 'نقل'
        }

        return type_map.get(types_list[0], types_list[0])

    def get_selected_types_display(self):
        """Get display names for all selected types"""
        types_list = self.get_selected_types_list()
        if not types_list:
            return "غير محدد"

        type_map = {
            'inspection': 'معاينة',
            'installation': 'تركيب',
            'accessory': 'إكسسوار',
            'tailoring': 'تسليم',
            'products': 'منتجات',
            'fabric': 'أقمشة',
            'transport': 'نقل'
        }

        arabic_types = [type_map.get(t, t) for t in types_list]
        return ', '.join(arabic_types)

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        # حساب المبلغ المتبقي بناءً على الحساب الفعلي وليس على المديونية
        paid = self.paid_amount if self.paid_amount is not None else Decimal('0')
        try:
            paid_dec = Decimal(str(paid))
        except Exception:
            paid_dec = Decimal('0')
        # استخدام المبلغ النهائي بعد الخصم بدلاً من المبلغ الإجمالي قبل الخصم
        final_amount = self.final_price_after_discount
        remaining = final_amount - paid_dec
        return remaining

    @property
    def remaining_amount_display(self):
        """عرض المبلغ المتبقي مع التنسيق المناسب"""
        remaining = self.remaining_amount
        if remaining > 0:
            return remaining
        elif remaining < 0:
            return abs(remaining)  # إرجاع القيمة المطلقة للعرض
        else:
            return Decimal('0')

    @property
    def is_customer_credit(self):
        """التحقق من وجود رصيد للعميل (دفع أكثر من المطلوب)"""
        return self.remaining_amount < 0
    @property
    def is_fully_paid(self):
        """التحقق من سداد الطلب بالكامل"""
        return self.remaining_amount <= 0

    @property
    def debt_amount(self):
        """حساب مبلغ المديونية (المبلغ المتبقي)"""
        remaining = self.remaining_amount
        return remaining if remaining > 0 else Decimal('0')

    def calculate_total(self):
        """حساب المبلغ الإجمالي من عناصر الطلب"""
        total = 0
        for item in self.items.all():
            if item.quantity and item.unit_price:
                total += item.quantity * item.unit_price

        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

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
            mo = self.manufacturing_order
            if mo and mo.completion_date:
                return mo.completion_date.date()
            # إذا كان تم التسليم، التحقق من تاريخ التسليم الفعلي
            elif self.order_status == 'delivered' and mo and mo.delivery_date:
                return mo.delivery_date.date()
        
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
        # تجنب التحديث المتكرر من مصادر مختلفة
        if (getattr(self, '_updating_installation_status', False) or
            getattr(self, '_updating_installation_status_bulk', False) or
            getattr(self, '_updating_from_signal', False)):
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
        """
        منطق أولوية الحالة:
        - طلب المنتجات: أولوية للتقطيع (cutting)
        - طلب المعاينة: أولوية للمعاينة (inspection)
        - طلب التركيب: أولوية للتصنيع (manufacturing)، ثم التركيبات (installation)
        - طلب التسليم: أولوية للتصنيع (manufacturing)
        - غير ذلك: الحالة الأساسية
        """
        types = self.get_selected_types_list()
        # أولوية المنتجات: cutting
        if 'products' in types:
            try:
                cutting_items = self.items.filter(cutting_status__in=['pending', 'in_progress'])
                if cutting_items.exists():
                    return {
                        'status': 'cutting',
                        'source': 'cutting',
                        'manufacturing_status': None
                    }
            except Exception:
                pass
            # إذا لا يوجد تقطيع، أولوية التصنيع
            if hasattr(self, 'manufacturing_order') and self.manufacturing_order:
                manufacturing_status = self.manufacturing_order.status
                return {
                    'status': manufacturing_status,
                    'source': 'manufacturing',
                    'manufacturing_status': manufacturing_status
                }
            else:
                return {
                    'status': self.order_status,
                    'source': 'order',
                    'manufacturing_status': None
                }
        # أولوية المعاينة
        if 'inspection' in types:
            inspection = self.inspections.first()
            if inspection:
                if inspection.status == 'completed':
                    return {
                        'status': 'completed',
                        'source': 'inspection',
                        'manufacturing_status': None
                    }
                else:
                    return {
                        'status': inspection.status,
                        'source': 'inspection',
                        'manufacturing_status': None
                    }
            else:
                return {
                    'status': self.order_status,
                    'source': 'order',
                    'manufacturing_status': None
                }
        # أولوية التركيب: التصنيع ثم التركيبات
        if 'installation' in types:
            if hasattr(self, 'manufacturing_order') and self.manufacturing_order:
                manufacturing_status = self.manufacturing_order.status
                # إذا المصنع جاهز للتركيب أو بعده، اعرض حالة التركيبات
                if manufacturing_status in ['ready_install', 'completed', 'delivered']:
                    self.update_installation_status()
                    return {
                        'status': self.installation_status,
                        'source': 'installation',
                        'manufacturing_status': manufacturing_status
                    }
                else:
                    return {
                        'status': manufacturing_status,
                        'source': 'manufacturing',
                        'manufacturing_status': manufacturing_status
                    }
            else:
                return {
                    'status': self.order_status,
                    'source': 'order',
                    'manufacturing_status': None
                }
        # أولوية التسليم: التصنيع
        if 'tailoring' in types:
            if hasattr(self, 'manufacturing_order') and self.manufacturing_order:
                manufacturing_status = self.manufacturing_order.status
                return {
                    'status': manufacturing_status,
                    'source': 'manufacturing',
                    'manufacturing_status': manufacturing_status
                }
            else:
                return {
                    'status': self.order_status,
                    'source': 'order',
                    'manufacturing_status': None
                }
        # غير ذلك: الحالة الأساسية
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
                'postponed_by_customer': 'bg-secondary text-dark',  # مؤجل من طرف العميل
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
            # إضافة حالة التقطيع
            if status == 'cutting':
                return 'bg-info'
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
                'postponed_by_customer': 'fas fa-pause-circle',
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
            if status == 'cutting':
                return 'fas fa-cut'
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
                'postponed_by_customer': 'مؤجل من طرف العميل',
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
            if status == 'cutting':
                return 'قيد التقطيع'
            return order_texts.get(status, status)
    
    @property
    def manufacturing_order(self):
        """إرجاع أحدث أمر تصنيع مرتبط بالطلب"""
        # إذا كان هناك قيمة محفوظة مؤقتاً، استخدمها
        if hasattr(self, '_cached_manufacturing_order'):
            return self._cached_manufacturing_order
        
        try:
            return self.manufacturing_orders.latest('created_at')
        except Exception:
            return None
    
    @property
    def is_manufacturing_order(self):
        """التحقق من وجود أمر تصنيع مرتبط بالطلب"""
        return self.manufacturing_order is not None
    
    @property
    def is_delivered_manufacturing_order(self):
        """التحقق من أن أمر التصنيع تم تسليمه"""
        mo = self.manufacturing_order
        if mo:
            return mo.status == 'delivered'
        return False

    def get_display_inspection_status(self):
        """
        إرجاع حالة المعاينة حسب نوع الطلب:
        1. طلب معاينة: يعرض حالة المعاينة المنشأة
        2. طلب تفصيل/تركيب: يعرض زر تفاصيل المعاينة أو طرف العميل
        """
        # إذا كان طلب معاينة - يجب أن تكون هناك معاينة منشأة
        if 'inspection' in self.get_selected_types_list():
            # البحث عن المعاينة المرتبطة بالطلب
            inspection = self.inspections.first()
            if inspection:
                # ترجمة نص حالة المعاينة إلى العربية من خريطة ثابتة لضمان الاتساق
                inspection_texts = {
                    'not_scheduled': 'غير مجدولة',
                    'pending': 'قيد الانتظار',
                    'scheduled': 'مجدولة',
                    'in_progress': 'قيد التنفيذ',
                    'completed': 'مكتمل',
                    'cancelled': 'ملغية',
                    'postponed_by_customer': 'مؤجل من طرف العميل',
                }
                return {
                    'status': inspection.status,
                    'text': inspection_texts.get(inspection.status, inspection.get_status_display()),
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
                # استخدم نفس خريطة النصوص لضمان العربية
                inspection_texts = {
                    'not_scheduled': 'غير مجدولة',
                    'pending': 'قيد الانتظار',
                    'scheduled': 'مجدولة',
                    'in_progress': 'قيد التنفيذ',
                    'completed': 'مكتمل',
                    'cancelled': 'ملغية',
                    'postponed_by_customer': 'مؤجل من طرف العميل',
                }
                rel = self.related_inspection
                return {
                    'status': rel.status,
                    'text': inspection_texts.get(rel.status, rel.get_status_display()),
                    'badge_class': rel.get_status_badge_class(),
                    'icon': rel.get_status_icon(),
                    'inspection_id': rel.id,
                    'contract_number': rel.contract_number,
                    'created_at': rel.created_at,
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
        
        # للإكسسوار والأنواع الأخرى
        elif 'accessory' in self.get_selected_types_list():
            return {
                'status': 'not_applicable',
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

    def get_cutting_orders(self):
        """الحصول على أوامر التقطيع المرتبطة بهذا الطلب"""
        try:
            from cutting.models import CuttingOrder
            return CuttingOrder.objects.filter(order=self)
        except:
            return []

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
        # تجنب التحديث المتكرر من التحديث المجمع
        if hasattr(instance, '_bulk_update') or hasattr(instance.order, '_updating_installation_status_bulk'):
            return

        if instance.order:
            # تحديث حالة التركيب في الطلب فقط إذا تغيرت
            if instance.order.installation_status != instance.status:
                # إضافة علامة لتجنب الحلقة اللانهائية
                setattr(instance.order, '_updating_from_signal', True)
                instance.order.installation_status = instance.status
                # استخدام update_fields لتجنب استدعاء دالة save الكاملة
                instance.order.save(update_fields=['installation_status'])
                # إزالة العلامة
                delattr(instance.order, '_updating_from_signal')
                
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


# Signals for OrderItem to keep order totals in sync and update cutting status
from django.db.models.signals import post_save as oi_post_save, post_delete as oi_post_delete


def _recompute_order_totals(order_id):
    try:
        from .tasks import calculate_order_totals_async
        calculate_order_totals_async.delay(order_id)
    except Exception:
        try:
            order = Order.objects.get(pk=order_id)
            # Force recalculation locally when Celery is not available
            order.calculate_final_price(force_update=True)
            order.total_amount = order.final_price
            order.save(update_fields=['final_price', 'total_amount'])
        except Exception:
            pass


def _update_order_cutting_flag(order):
    try:
        # إذا وُجدت عناصر في حالة تقطيع غير مكتملة، ضع حالة الطلب إلى 'in_progress' للتقطيع
        if order.items.filter(cutting_status__in=['pending', 'in_progress']).exists():
            # نضع علامة تتبع أو نحدّث order_status إلى 'in_progress' إن كان مناسباً
            # لكن من الأفضل استخدام عرض مخصص - هنا نحافظ على order_status إذا لم يكن 'in_progress'
            if order.order_status != 'in_progress':
                order.order_status = 'in_progress'
                order.save(update_fields=['order_status'])
        else:
            # إذا لم توجد عناصر قيد التقطيع، لا نغيّر الحالة هنا (قد يتولّى المصنع/التوصيل إدارة الحالة)
            pass
    except Exception:
        pass


def order_item_saved(sender, instance, created, **kwargs):
    # إعادة حساب إجماليات الطلب
    if instance and instance.order:
        try:
            # التحقق من أن الطلب لا يزال موجوداً
            if Order.objects.filter(pk=instance.order.pk).exists():
                _recompute_order_totals(instance.order.pk)
                _update_order_cutting_flag(instance.order)
        except Exception:
            # تجاهل الأخطاء إذا كان الطلب قيد الحذف
            pass


def order_item_deleted(sender, instance, **kwargs):
    if instance and instance.order:
        try:
            # التحقق من أن الطلب لا يزال موجوداً
            if Order.objects.filter(pk=instance.order.pk).exists():
                _recompute_order_totals(instance.order.pk)
                _update_order_cutting_flag(instance.order)
        except Exception:
            # تجاهل الأخطاء إذا كان الطلب قيد الحذف
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
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        verbose_name='الكمية',
        help_text='يمكن إدخال قيم عشرية مثل 4.25 متر'
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='سعر الوحدة')
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='نسبة الخصم %',
        help_text='نسبة الخصم من 0% إلى 15%'
    )
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

    # حقول التقطيع الجديدة
    cutting_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'قيد الانتظار'),
            ('in_progress', 'قيد التقطيع'),
            ('completed', 'مكتمل'),
            ('rejected', 'مرفوض'),
        ],
        default='pending',
        verbose_name='حالة التقطيع'
    )

    cutter_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اسم القصاص'
    )

    permit_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='رقم الإذن'
    )

    receiver_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اسم المستلم'
    )

    cutting_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ التقطيع'
    )

    delivery_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ التسليم'
    )

    bag_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='رقم الشنطة'
    )

    additional_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='كمية إضافية'
    )

    cutting_notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات التقطيع'
    )

    rejection_reason = models.TextField(
        blank=True,
        verbose_name='سبب الرفض'
    )

    # إضافة tracker لتتبع التغييرات
    tracker = FieldTracker(fields=[
        'quantity', 'unit_price', 'product', 'discount_percentage',
        'cutting_status', 'cutter_name', 'permit_number', 'receiver_name'
    ])
    
    class Meta:
        verbose_name = 'عنصر الطلب'
        verbose_name_plural = 'عناصر الطلب'
        indexes = [
            models.Index(fields=['order'], name='order_item_order_idx'),
            models.Index(fields=['product'], name='order_item_product_idx'),
            models.Index(fields=['processing_status'], name='order_item_status_idx'),
            models.Index(fields=['item_type'], name='order_item_type_idx'),
            models.Index(fields=['cutting_status'], name='order_item_cutting_status_idx'),
            models.Index(fields=['cutter_name'], name='order_item_cutter_idx'),
            models.Index(fields=['receiver_name'], name='order_item_receiver_idx'),
            models.Index(fields=['cutting_date'], name='order_item_cutting_date_idx'),
        ]
    def __str__(self):
        return f'{self.product.name} ({self.get_clean_quantity_display()})'
    
    def get_clean_quantity_display(self):
        """إرجاع الكمية بدون أصفار زائدة"""
        if self.quantity is None:
            return '0'
        
        str_value = str(self.quantity)
        if '.' in str_value:
            str_value = str_value.rstrip('0')
            if str_value.endswith('.'):
                str_value = str_value[:-1]
        return str_value
    @property
    def total_price(self):
        """Calculate total price for this item before discount"""
        if self.quantity is None or self.unit_price is None:
            return 0
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self):
        """مبلغ الخصم"""
        if self.discount_percentage is None or self.discount_percentage == 0:
            return 0
        from decimal import Decimal
        return self.total_price * (Decimal(str(self.discount_percentage)) / Decimal('100'))
    
    @property
    def total_after_discount(self):
        """الإجمالي بعد الخصم"""
        return self.total_price - self.discount_amount
    
    def get_clean_discount_display(self):
        """إرجاع نسبة الخصم بدون أصفار زائدة"""
        if self.discount_percentage is None or self.discount_percentage == 0:
            return '0'
        
        str_value = str(self.discount_percentage)
        if '.' in str_value:
            str_value = str_value.rstrip('0')
            if str_value.endswith('.'):
                str_value = str_value[:-1]
        return str_value

    # دوال مساعدة لحقول التقطيع
    @property
    def total_quantity_with_additional(self):
        """الكمية الإجمالية (الأصلية + الإضافية)"""
        return self.quantity + self.additional_quantity

    def mark_cutting_completed(self, cutter_name, permit_number, receiver_name, user, notes=''):
        """تعيين عنصر التقطيع كمكتمل"""
        from django.utils import timezone

        self.cutting_status = 'completed'
        self.cutter_name = cutter_name
        self.permit_number = permit_number
        self.receiver_name = receiver_name
        self.cutting_date = timezone.now()
        self.delivery_date = timezone.now()
        self.cutting_notes = notes
        self.save()

    def mark_cutting_rejected(self, reason, user):
        """تعيين عنصر التقطيع كمرفوض"""
        self.cutting_status = 'rejected'
        self.rejection_reason = reason
        self.save()

    def get_cutting_status_display_color(self):
        """إرجاع لون حالة التقطيع للعرض"""
        colors = {
            'pending': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'rejected': 'danger'
        }
        return colors.get(self.cutting_status, 'secondary')

    @property
    def is_cutting_completed(self):
        """التحقق من اكتمال التقطيع"""
        return self.cutting_status == 'completed'

    @property
    def is_cutting_rejected(self):
        """التحقق من رفض التقطيع"""
        return self.cutting_status == 'rejected'

    @property
    def has_cutting_data(self):
        """التحقق من وجود بيانات التقطيع"""
        return bool(self.cutter_name and self.permit_number and self.receiver_name)

    def save(self, *args, **kwargs):
        """Save order item with validation"""
        try:
            # التحقق من أن الطلب له مفتاح أساسي
            if not self.order.pk:
                raise models.ValidationError('يجب حفظ الطلب أولاً قبل إنشاء عنصر الطلب')

            # التحقق من حماية الطلبات المدفوعة
            is_new = self.pk is None
            force_update = getattr(self, '_force_price_update', False)

            if not is_new and not force_update and self.order.paid_amount > 0:
                # إذا كان الطلب مدفوع، تحقق من التغييرات في السعر
                try:
                    old_item = OrderItem.objects.get(pk=self.pk)
                    if (old_item.unit_price != self.unit_price or
                        old_item.quantity != self.quantity or
                        old_item.discount_percentage != self.discount_percentage):

                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"محاولة تعديل أسعار طلب مدفوع {self.order.order_number}")

                        # يمكن إضافة استثناء هنا لمنع التعديل تماماً
                        # raise models.ValidationError('لا يمكن تعديل أسعار الطلبات المدفوعة')

                        # أو السماح بالتعديل مع تسجيل تحذير
                        pass
                except OrderItem.DoesNotExist:
                    pass

            super().save(*args, **kwargs)

            # تحديث السعر النهائي للطلب (مع مراعاة الحماية)
            if is_new or force_update:
                try:
                    from .tasks import calculate_order_totals_async
                    calculate_order_totals_async.delay(self.order.pk)
                except Exception as e:
                    # في حالة فشل الجدولة، نحدث السعر مباشرة
                    try:
                        self.order.calculate_final_price(force_update=force_update)
                        self.order.save(update_fields=['final_price', 'total_amount'])
                    except Exception as calc_error:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"خطأ في تحديث السعر النهائي للطلب {self.order.pk}: {str(calc_error)}")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في حفظ عنصر الطلب: {str(e)}")
            raise


# وصل إشارات OrderItem الآن
from django.db.models.signals import post_save as oi_post_save, post_delete as oi_post_delete
oi_post_save.connect(order_item_saved, sender=OrderItem)
oi_post_delete.connect(order_item_deleted, sender=OrderItem)


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

                # تحديث المديونية إذا كانت موجودة
                try:
                    from installations.models import CustomerDebt
                    debt = CustomerDebt.objects.filter(order=self.order, is_paid=False).first()
                    if debt:
                        remaining = self.order.remaining_amount
                        if remaining <= 0:
                            # الطلب مدفوع بالكامل، احذف المديونية أو اجعلها مدفوعة
                            debt.is_paid = True
                            debt.payment_date = timezone.now()
                            debt.payment_receiver_name = getattr(self, 'created_by', None)
                            if debt.payment_receiver_name:
                                debt.payment_receiver_name = debt.payment_receiver_name.get_full_name() or debt.payment_receiver_name.username
                            debt.save()
                        else:
                            # حدث مبلغ المديونية
                            debt.debt_amount = remaining
                            debt.save()
                except Exception:
                    pass
            except Exception as e:
                pass
        except Exception as e:
            pass
            raise


class OrderNote(models.Model):
    """نموذج موحد لملاحظات الطلب من جميع الأقسام"""
    NOTE_TYPES = [
        ('general', 'عام'),
        ('inspection', 'معاينة'),
        ('installation', 'تركيب'),
        ('manufacturing', 'تصنيع'),
        ('delivery', 'تسليم'),
        ('payment', 'دفع'),
        ('complaint', 'شكوى'),
        ('status_change', 'تغيير حالة'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_notes', verbose_name='الطلب')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='general', verbose_name='نوع الملاحظة')
    title = models.CharField(max_length=200, blank=True, verbose_name='عنوان الملاحظة')
    content = models.TextField(verbose_name='محتوى الملاحظة')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='تم الإنشاء بواسطة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    is_important = models.BooleanField(default=False, verbose_name='ملاحظة مهمة')
    is_visible_to_customer = models.BooleanField(default=False, verbose_name='مرئية للعميل')

    class Meta:
        verbose_name = 'ملاحظة الطلب'
        verbose_name_plural = 'ملاحظات الطلب'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'note_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_note_type_display()} - {self.title or self.content[:50]}"

    def get_icon(self):
        """إرجاع أيقونة حسب نوع الملاحظة"""
        icons = {
            'general': 'fas fa-sticky-note',
            'inspection': 'fas fa-search',
            'installation': 'fas fa-tools',
            'manufacturing': 'fas fa-industry',
            'delivery': 'fas fa-truck',
            'payment': 'fas fa-money-bill',
            'complaint': 'fas fa-exclamation-triangle',
            'status_change': 'fas fa-exchange-alt',
        }
        return icons.get(self.note_type, 'fas fa-sticky-note')

    def get_color_class(self):
        """إرجاع فئة اللون حسب نوع الملاحظة"""
        colors = {
            'general': 'primary',
            'inspection': 'info',
            'installation': 'success',
            'manufacturing': 'warning',
            'delivery': 'secondary',
            'payment': 'success',
            'complaint': 'danger',
            'status_change': 'dark',
        }
        return colors.get(self.note_type, 'primary')


class OrderStatusLog(models.Model):
    # أنواع التغييرات
    CHANGE_TYPE_CHOICES = [
        ('status', 'تغيير حالة'),
        ('customer', 'تغيير عميل'),
        ('price', 'تغيير سعر'),
        ('date', 'تغيير تاريخ'),
        ('manufacturing', 'تحديث تصنيع'),
        ('installation', 'تحديث تركيب'),
        ('cutting', 'تحديث تقطيع'),
        ('inspection', 'تحديث معاينة'),
        ('complaint', 'تحديث شكوى'),
        ('payment', 'تحديث دفع'),
        ('general', 'تحديث عام'),
        ('creation', 'إنشاء طلب'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs', verbose_name=_('الطلب'))
    old_status = models.CharField(max_length=25, choices=Order.ORDER_STATUS_CHOICES, verbose_name=_('الحالة السابقة'))
    new_status = models.CharField(max_length=25, choices=Order.ORDER_STATUS_CHOICES, verbose_name=_('الحالة الجديدة'))
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_('تم التغيير بواسطة'))
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ التغيير'))

    # حقول جديدة لتفاصيل التغيير
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default='status',
        verbose_name=_('نوع التغيير')
    )
    change_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('تفاصيل التغيير'),
        help_text=_('تفاصيل إضافية عن التغيير في صيغة JSON')
    )
    is_automatic = models.BooleanField(
        default=False,
        verbose_name=_('تغيير تلقائي'),
        help_text=_('هل هذا التغيير تم تلقائياً أم يدوياً')
    )
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
    def _status_label(self, code):
        """Return a human-friendly label for a status code based on order type.
        Try order-type-specific choices first, then general choices.
        """
        if not code:
            return ''

        # محاولة الحصول على الحالات المحددة حسب نوع الطلب
        if self.order:
            order_types = self.order.get_selected_types_list()
            specific_choices = self.get_status_choices_for_order_type(order_types)
            specific_map = dict(specific_choices)
            if code in specific_map:
                return specific_map[code]

        # الحالات العامة كبديل
        try:
            order_map = dict(self.order.ORDER_STATUS_CHOICES)
        except Exception:
            order_map = dict(Order.ORDER_STATUS_CHOICES) if 'Order' in globals() else {}
        tracking_map = dict(Order.TRACKING_STATUS_CHOICES) if 'Order' in globals() else {}

        if code in order_map:
            return order_map[code]
        if code in tracking_map:
            return tracking_map[code]
        return code

    @property
    def old_status_pretty(self):
        return self._status_label(self.old_status or '')

    @property
    def new_status_pretty(self):
        return self._status_label(self.new_status or '')

    @property
    def change_type_display(self):
        """عرض نوع التغيير بشكل جميل"""
        return dict(self.CHANGE_TYPE_CHOICES).get(self.change_type, self.change_type)

    @property
    def change_icon(self):
        """أيقونة حسب نوع التغيير ونوع الطلب"""
        # أيقونات أساسية
        base_icons = {
            'customer': 'fas fa-user',
            'price': 'fas fa-dollar-sign',
            'date': 'fas fa-calendar',
            'manufacturing': 'fas fa-industry',
            'installation': 'fas fa-tools',
            'cutting': 'fas fa-cut',
            'inspection': 'fas fa-search',
            'complaint': 'fas fa-exclamation-triangle',
            'payment': 'fas fa-credit-card',
            'creation': 'fas fa-plus-circle',
        }

        # أيقونات خاصة للتغييرات العامة
        if self.change_type == 'general' and self.change_details:
            field_name = self.change_details.get('field_name', '')
            if field_name == 'عناصر الطلب':
                return 'fas fa-list'
            elif field_name == 'أنواع الطلب':
                return 'fas fa-tags'
            elif field_name == 'الملاحظات':
                return 'fas fa-sticky-note'
            elif 'العقد' in field_name:
                return 'fas fa-file-contract'
            elif 'الفاتورة' in field_name:
                return 'fas fa-file-invoice'
            elif 'العنوان' in field_name or 'الموقع' in field_name:
                return 'fas fa-map-marker-alt'
            elif field_name == 'وضع الطلب':
                return 'fas fa-star'
            else:
                return 'fas fa-edit'

        # أيقونات خاصة بحالات أنواع الطلبات
        if self.change_type == 'status' and self.order:
            order_types = self.order.get_selected_types_list()

            # أيقونات حسب نوع الطلب
            if 'inspection' in order_types:
                return 'fas fa-search'  # معاينة
            elif 'installation' in order_types:
                return 'fas fa-tools'  # تركيب
            elif 'products' in order_types:
                return 'fas fa-cut'  # تقطيع/منتجات
            elif 'accessory' in order_types:
                return 'fas fa-gem'  # إكسسوار
            elif 'tailoring' in order_types:
                return 'fas fa-shipping-fast'  # تسليم
            else:
                return 'fas fa-exchange-alt'  # حالة عامة

        return base_icons.get(self.change_type, 'fas fa-info-circle')

    def _get_order_type_name(self, order_types):
        """إرجاع اسم نوع الطلب بالعربية"""
        if not order_types:
            return 'الطلب'

        type_names = {
            'inspection': 'المعاينة',
            'installation': 'التركيب',
            'products': 'المنتجات',
            'accessory': 'الإكسسوار',
            'tailoring': 'التسليم',
        }

        # إرجاع أول نوع موجود
        for order_type in order_types:
            if order_type in type_names:
                return type_names[order_type]

        return 'الطلب'

    @property
    def change_color(self):
        """لون حسب نوع التغيير"""
        colors = {
            'status': 'primary',
            'customer': 'info',
            'price': 'success',
            'date': 'warning',
            'manufacturing': 'secondary',
            'installation': 'dark',
            'cutting': 'warning',
            'inspection': 'info',
            'complaint': 'danger',
            'payment': 'success',
            'general': 'light',
            'creation': 'primary',
        }
        return colors.get(self.change_type, 'secondary')

    def get_detailed_description(self):
        """وصف مفصل للتغيير"""
        if self.change_type == 'creation':
            return 'تم إنشاء الطلب'
        elif self.change_type == 'status':
            if self.old_status == self.new_status:
                return f'تأكيد الحالة: {self.new_status_pretty}'
            else:
                # تحديد نوع الطلب لعرض الوصف المناسب
                if self.order:
                    order_types = self.order.get_selected_types_list()
                    order_type_name = self._get_order_type_name(order_types)
                    return f'تم تبديل حالة {order_type_name} من {self.old_status_pretty} إلى {self.new_status_pretty}'
                else:
                    return f'تم تبديل الحالة من {self.old_status_pretty} إلى {self.new_status_pretty}'
        elif self.change_type == 'customer' and self.change_details:
            old_customer = self.change_details.get('old_customer_name', 'غير محدد')
            new_customer = self.change_details.get('new_customer_name', 'غير محدد')
            return f'تم تغيير العميل من {old_customer} إلى {new_customer}'
        elif self.change_type == 'price' and self.change_details:
            old_price = self.change_details.get('old_price', 0)
            new_price = self.change_details.get('new_price', 0)
            return f'تم تغيير السعر من {old_price} إلى {new_price}'
        elif self.change_type == 'date' and self.change_details:
            field_name = self.change_details.get('field_name', 'التاريخ')
            old_date = self.change_details.get('old_date', 'غير محدد')
            new_date = self.change_details.get('new_date', 'غير محدد')
            return f'تم تغيير {field_name} من {old_date} إلى {new_date}'
        elif self.change_type == 'manufacturing':
            # عرض خاص لتحديثات التصنيع
            return self.notes or f'تحديث حالة التصنيع من {self.old_status_pretty} إلى {self.new_status_pretty}'
        elif self.change_type == 'installation':
            # عرض خاص لتحديثات التركيب
            return self.notes or f'تحديث حالة التركيب من {self.old_status_pretty} إلى {self.new_status_pretty}'
        elif self.change_type == 'cutting':
            # عرض خاص لتحديثات التقطيع
            return self.notes or f'تحديث حالة التقطيع من {self.old_status_pretty} إلى {self.new_status_pretty}'
        elif self.change_type == 'inspection':
            # عرض خاص لتحديثات المعاينة
            return self.notes or f'تحديث حالة المعاينة من {self.old_status_pretty} إلى {self.new_status_pretty}'
        elif self.change_type == 'complaint':
            # عرض خاص لتحديثات الشكاوى
            return self.notes or f'تحديث حالة الشكوى من {self.old_status_pretty} إلى {self.new_status_pretty}'
        elif self.change_type == 'general':
            # عرض محسن للتغييرات العامة
            if self.change_details and self.change_details.get('field_name'):
                field_name = self.change_details.get('field_name')
                if field_name == 'عناصر الطلب':
                    # عرض خاص لتغييرات عناصر الطلب
                    return self.notes or f'تم تعديل {field_name}'
                elif field_name == 'أنواع الطلب':
                    return f'تم تغيير أنواع الطلب من "{self.old_status}" إلى "{self.new_status}"'
                else:
                    # استخدام القيم من change_details بدلاً من old_status/new_status
                    old_val = self.change_details.get('old_value', 'غير محدد')
                    new_val = self.change_details.get('new_value', 'غير محدد')
                    return f'تم تغيير {field_name} من "{old_val}" إلى "{new_val}"'
            elif self.notes:
                return self.notes
            else:
                return 'تم إجراء تعديل عام على الطلب'
        elif self.notes:
            return self.notes
        else:
            return f'{self.change_type_display}'
    def save(self, *args, **kwargs):
        try:
            # التحقق من أن الطلب له مفتاح أساسي
            if not self.order.pk:
                raise models.ValidationError('يجب حفظ الطلب أولاً قبل إنشاء سجل حالة')

            # تحديد نوع التغيير تلقائياً إذا لم يتم تحديده
            # لا نغير change_type إذا كان محدداً بالفعل (مثل 'manufacturing', 'installation', إلخ)
            if not self.change_type:
                if not self.pk:  # سجل جديد
                    if not self.old_status:
                        self.change_type = 'creation'
                    elif self.old_status != self.new_status:
                        self.change_type = 'status'

            # اختر المصدر Canonical: استخدم order_status إذا كان موجودًا، وإلا التراجع إلى tracking_status
            if not self.old_status and self.order:
                self.old_status = getattr(self.order, 'order_status', None) or getattr(self.order, 'tracking_status', None)

            super().save(*args, **kwargs)

            # تحديث حالة الطلب فقط إذا كان هذا تغيير حالة وليس تلقائي
            if self.change_type == 'status' and not self.is_automatic:
                try:
                    # عندما يتم حفظ سجل الحالة، نحدث الحقل Canonical `order_status` إن كان مناسبًا
                    if self.order and self.new_status != getattr(self.order, 'order_status', None):
                        # حدّث الحقل canonical
                        try:
                            self.order.order_status = self.new_status
                            self.order.last_notification_date = timezone.now()
                            self.order.save(update_fields=['order_status', 'last_notification_date'])
                        except Exception:
                            # في حالة عدم وجود الحقل، استخدام tracking_status القديم كاحتياط
                            self.order.tracking_status = self.new_status
                            self.order.last_notification_date = timezone.now()
                            self.order.save(update_fields=['tracking_status', 'last_notification_date'])
                except Exception as e:
                    pass
        except Exception as e:
            pass
            raise

    @classmethod
    def get_status_choices_for_order_type(cls, order_types):
        """إرجاع خيارات الحالة المناسبة لنوع الطلب"""
        if not order_types:
            return cls.ORDER_STATUS_CHOICES

        # حالات المعاينة
        if 'inspection' in order_types:
            try:
                from inspections.models import Inspection
                return Inspection.STATUS_CHOICES
            except ImportError:
                pass

        # حالات التركيب
        elif 'installation' in order_types:
            try:
                from installations.models import InstallationSchedule
                return InstallationSchedule.STATUS_CHOICES
            except ImportError:
                pass

        # حالات التصنيع
        elif 'tailoring' in order_types or 'accessory' in order_types:
            try:
                from manufacturing.models import ManufacturingOrder
                return ManufacturingOrder.STATUS_CHOICES
            except ImportError:
                pass

        # حالات التقطيع للمنتجات
        elif 'products' in order_types:
            try:
                from cutting.models import CuttingOrder
                return CuttingOrder.STATUS_CHOICES
            except ImportError:
                pass

        # الحالات العامة للطلب
        return cls.ORDER_STATUS_CHOICES

    @classmethod
    def create_detailed_log(cls, order, change_type, old_value=None, new_value=None,
                           changed_by=None, notes='', field_name=None, **extra_details):
        """إنشاء سجل مفصل للتغيير"""
        try:
            change_details = extra_details.copy()

            # حفظ القيم الأساسية دائماً
            change_details.update({
                'field_name': field_name,
                'old_value': str(old_value) if old_value not in [None, ''] else 'غير محدد',
                'new_value': str(new_value) if new_value not in [None, ''] else 'غير محدد',
            })

            if change_type == 'customer':
                change_details.update({
                    'old_customer_name': getattr(old_value, 'name', str(old_value)) if old_value else 'غير محدد',
                    'new_customer_name': getattr(new_value, 'name', str(new_value)) if new_value else 'غير محدد',
                })
            elif change_type == 'price':
                change_details.update({
                    'old_price': float(old_value) if old_value else 0,
                    'new_price': float(new_value) if new_value else 0,
                })
            elif change_type == 'date':
                change_details.update({
                    'old_date': str(old_value) if old_value else 'غير محدد',
                    'new_date': str(new_value) if new_value else 'غير محدد',
                })

            # تحديد الحالات
            if change_type == 'status':
                # للتغييرات في الحالة، استخدم القيم المرسلة
                old_status = old_value or getattr(order, 'order_status', '')
                new_status = new_value or getattr(order, 'order_status', '')
            else:
                # للتغييرات الأخرى، استخدم حالة الطلب الحالية
                current_status = getattr(order, 'order_status', None) or getattr(order, 'tracking_status', '')
                old_status = current_status
                new_status = current_status

            return cls.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                notes=notes,
                change_type=change_type,
                change_details=change_details,
                is_automatic=changed_by is None
            )
        except Exception:
            # تجاهل الأخطاء إذا كان الطلب قيد الحذف أو حدث خطأ في المفتاح الأجنبي
            return None


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
    """إعدادات مواعيد التسليم للطلبات والخدمات"""
    ORDER_TYPE_CHOICES = [
        ('normal', 'طلب عادي'),
        ('vip', 'طلب VIP'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('accessory', 'إكسسوار'),
        ('products', 'منتجات'),
        ('installation', 'تركيب'),
        ('tailoring', 'تسليم'),
        ('inspection', 'معاينة'),
    ]

    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        verbose_name='نوع الطلب',
        null=True,
        blank=True
    )
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        verbose_name='نوع الخدمة',
        null=True,
        blank=True
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
        unique_together = ['order_type', 'service_type']
        ordering = ['service_type', 'order_type']
    
    def __str__(self):
        parts = []
        if self.service_type:
            parts.append(self.get_service_type_display())
        if self.order_type:
            parts.append(self.get_order_type_display())

        if parts:
            return f"{' - '.join(parts)} - {self.delivery_days} يوم"
        else:
            return f"إعداد عام - {self.delivery_days} يوم"

    @classmethod
    def get_delivery_days(cls, order_type=None, service_type=None):
        """الحصول على عدد أيام التسليم بناءً على نوع الطلب ونوع الخدمة"""
        try:
            # البحث بالأولوية: نوع الخدمة + نوع الطلب
            if service_type and order_type:
                # البحث عن تطابق كامل (خدمة + نوع طلب)
                setting = cls.objects.filter(
                    service_type=service_type,
                    order_type=order_type,
                    is_active=True
                ).first()
                if setting:
                    return setting.delivery_days

            # إذا لم يوجد تطابق كامل، ابحث بنوع الخدمة فقط (بدون نوع طلب محدد)
            if service_type:
                setting = cls.objects.filter(
                    service_type=service_type,
                    order_type__isnull=True,
                    is_active=True
                ).first()
                if setting:
                    return setting.delivery_days

            # إذا لم يوجد، ابحث بنوع الطلب فقط (بدون نوع خدمة محدد)
            if order_type:
                setting = cls.objects.filter(
                    order_type=order_type,
                    service_type__isnull=True,
                    is_active=True
                ).first()
                if setting:
                    return setting.delivery_days

        except Exception as e:
            logger.error(f"خطأ في جلب إعدادات التسليم: {str(e)}")

        # القيم الافتراضية
        defaults = {
            'normal': 15,
            'vip': 7,
            'inspection': 2,
            'accessory': 5,
            'products': 3,
            'installation': 10,
            'tailoring': 7,
        }

        # إرجاع القيمة الافتراضية بناءً على نوع الخدمة أو نوع الطلب
        if service_type and service_type in defaults:
            return defaults[service_type]
        elif order_type and order_type in defaults:
            return defaults[order_type]
        else:
            return 15

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


class OrderItemModificationLog(models.Model):
    """سجل تعديلات عناصر الطلب"""
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='modification_logs', verbose_name='عنصر الطلب')
    field_name = models.CharField(max_length=50, verbose_name='اسم الحقل')
    old_value = models.TextField(verbose_name='القيمة السابقة')
    new_value = models.TextField(verbose_name='القيمة الجديدة')
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='تم التعديل بواسطة')
    modified_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التعديل')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'سجل تعديل عنصر الطلب'
        verbose_name_plural = 'سجلات تعديل عناصر الطلب'
        ordering = ['-modified_at']
        indexes = [
            models.Index(fields=['order_item'], name='item_mod_log_item_idx'),
            models.Index(fields=['modified_at'], name='item_mod_log_date_idx'),
        ]

    def __str__(self):
        return f'{self.order_item.product.name} - {self.field_name} ({self.modified_at.strftime("%Y-%m-%d %H:%M")})'

    def get_field_display_name(self):
        """إرجاع اسم الحقل بالعربية"""
        field_names = {
            'quantity': 'الكمية',
            'unit_price': 'سعر الوحدة',
            'product': 'المنتج',
            'notes': 'الملاحظات',
        }
        return field_names.get(self.field_name, self.field_name)

    def get_clean_old_value(self):
        """إرجاع القيمة السابقة منسقة"""
        if self.field_name == 'quantity':
            try:
                from decimal import Decimal
                value = Decimal(self.old_value)
                str_value = str(value)
                if '.' in str_value:
                    str_value = str_value.rstrip('0')
                    if str_value.endswith('.'):
                        str_value = str_value[:-1]
                return str_value
            except:
                return self.old_value
        elif self.field_name == 'unit_price':
            try:
                from decimal import Decimal
                value = Decimal(self.old_value)
                return f"{value} ج.م"
            except:
                return self.old_value
        elif self.field_name == 'product':
            try:
                from inventory.models import Product
                product = Product.objects.get(id=self.old_value)
                return product.name
            except:
                return self.old_value
        return self.old_value

    def get_clean_new_value(self):
        """إرجاع القيمة الجديدة منسقة"""
        if self.field_name == 'quantity':
            try:
                from decimal import Decimal
                value = Decimal(self.new_value)
                str_value = str(value)
                if '.' in str_value:
                    str_value = str_value.rstrip('0')
                    if str_value.endswith('.'):
                        str_value = str_value[:-1]
                return str_value
            except:
                return self.new_value
        elif self.field_name == 'unit_price':
            try:
                from decimal import Decimal
                value = Decimal(self.new_value)
                return f"{value} ج.م"
            except:
                return self.new_value
        elif self.field_name == 'product':
            try:
                from inventory.models import Product
                product = Product.objects.get(id=self.new_value)
                return product.name
            except:
                return self.new_value
        return self.new_value


class OrderModificationLog(models.Model):
    """سجل تعديلات الطلب الشامل"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='modification_logs', verbose_name='الطلب')
    modification_type = models.CharField(max_length=50, verbose_name='نوع التعديل')
    old_total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='المبلغ الإجمالي السابق')
    new_total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='المبلغ الإجمالي الجديد')
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='تم التعديل بواسطة')
    modified_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التعديل')
    details = models.TextField(verbose_name='تفاصيل التعديل')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    
    # تمييز نوع التعديل
    is_manual_modification = models.BooleanField(
        default=False, 
        verbose_name='تعديل يدوي',
        help_text='إذا كان هذا التعديل تم بواسطة المستخدم مباشرة وليس تلقائياً'
    )
    
    # بيانات التعديل التفصيلية
    modified_fields = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='الحقول المعدلة',
        help_text='قاموس يحتوي على الحقول المعدلة وقيمها السابقة والجديدة'
    )

    class Meta:
        verbose_name = 'سجل تعديل الطلب'
        verbose_name_plural = 'سجلات تعديل الطلبات'
        ordering = ['-modified_at']
        indexes = [
            models.Index(fields=['order'], name='order_mod_log_order_idx'),
            models.Index(fields=['modified_at'], name='order_mod_log_date_idx'),
        ]

    def __str__(self):
        return f'{self.order.order_number} - {self.modification_type} ({self.modified_at.strftime("%Y-%m-%d %H:%M")})'

    def get_clean_old_total(self):
        """إرجاع المبلغ السابق منسق"""
        if self.old_total_amount is not None:
            return f"{self.old_total_amount} ج.م"
        return "غير محدد"

    def get_clean_new_total(self):
        """إرجاع المبلغ الجديد منسق"""
        if self.new_total_amount is not None:
            return f"{self.new_total_amount} ج.م"
        return "غير محدد"


# استيراد نماذج العقود
from .contract_models import ContractTemplate, ContractCurtain, ContractPrintLog

# استيراد نماذج الويزارد
from .wizard_models import DraftOrder, DraftOrderItem
