import json
from decimal import Decimal
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Order, OrderItem, Payment, OrderStatusLog, ManufacturingDeletionLog
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
import logging
from django.db import models


logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Order)
def track_order_changes(sender, instance, **kwargs):
    """تتبع جميع التغييرات على الطلب وتسجيلها في OrderStatusLog"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        # تجاهل التحديثات التلقائية
        if instance.is_auto_update:
            return
            
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            
            # قائمة الحقول التي نريد تتبع تغييراتها
            tracked_fields = [
                'contract_number', 'contract_number_2', 'contract_number_3',
                'invoice_number', 'invoice_number_2', 'invoice_number_3',
                'order_number', 'customer', 'salesperson', 'branch',
                'expected_delivery_date', 'final_price', 'paid_amount',
                'order_status', 'tracking_status', 'status', 'notes'
            ]
            
            changes = []
            for field in tracked_fields:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                
                if old_value != new_value:
                    # الحصول على أسماء العرض للحقول ذات الاختيارات
                    if field == 'order_status':
                        old_display = dict(Order.ORDER_STATUS_CHOICES).get(old_value, old_value)
                        new_display = dict(Order.ORDER_STATUS_CHOICES).get(new_value, new_value)
                        changes.append(f'حالة الطلب: من "{old_display}" إلى "{new_display}"')
                    elif field == 'tracking_status':
                        old_display = dict(Order.TRACKING_STATUS_CHOICES).get(old_value, old_value)
                        new_display = dict(Order.TRACKING_STATUS_CHOICES).get(new_value, new_value)
                        changes.append(f'حالة التتبع: من "{old_display}" إلى "{new_display}"')
                    elif field == 'status':
                        old_display = dict(Order.STATUS_CHOICES).get(old_value, old_value)
                        new_display = dict(Order.STATUS_CHOICES).get(new_value, new_value)
                        changes.append(f'الحالة: من "{old_display}" إلى "{new_display}"')
                    elif field in ['contract_number', 'contract_number_2', 'contract_number_3']:
                        changes.append(f'رقم العقد ({field.replace("contract_number", "" or "الأساسي")}): من "{old_value or "غير محدد"}" إلى "{new_value or "غير محدد"}"')
                    elif field in ['invoice_number', 'invoice_number_2', 'invoice_number_3']:
                        changes.append(f'رقم الفاتورة ({field.replace("invoice_number", "" or "الأساسي")}): من "{old_value or "غير محدد"}" إلى "{new_value or "غير محدد"}"')
                    elif field == 'order_number':
                        changes.append(f'رقم الطلب: من "{old_value}" إلى "{new_value}"')
                    elif field == 'expected_delivery_date':
                        changes.append(f'تاريخ التسليم المتوقع: من "{old_value}" إلى "{new_value}"')
                    elif field == 'final_price':
                        changes.append(f'السعر النهائي: من "{old_value}" إلى "{new_value}"')
                    elif field == 'paid_amount':
                        changes.append(f'المبلغ المدفوع: من "{old_value}" إلى "{new_value}"')
                    elif field == 'notes':
                        changes.append(f'الملاحظات تم تعديلها')
                    elif field == 'customer':
                        old_customer = old_value.name if old_value else "غير محدد"
                        new_customer = new_value.name if new_value else "غير محدد"
                        changes.append(f'العميل: من "{old_customer}" إلى "{new_customer}"')
                    elif field == 'salesperson':
                        old_salesperson = old_value.user.username if old_value and old_value.user else "غير محدد"
                        new_salesperson = new_value.user.username if new_value and new_value.user else "غير محدد"
                        changes.append(f'البائع: من "{old_salesperson}" إلى "{new_salesperson}"')
                    elif field == 'branch':
                        old_branch = old_value.name if old_value else "غير محدد"
                        new_branch = new_value.name if new_value else "غير محدد"
                        changes.append(f'الفرع: من "{old_branch}" إلى "{new_branch}"')
            
            # إذا كان هناك تغييرات، سجلها
            if changes:
                # الحصول على المستخدم الحالي من thread local storage
                current_user = None
                try:
                    from accounts.middleware.current_user import get_current_user
                    current_user = get_current_user()
                except:
                    pass
                
                # إذا لم نتمكن من الحصول على المستخدم، نبحث عن آخر مستخدم قام بتعديل
                if not current_user:
                    try:
                        # البحث عن آخر سجل للطلب نفسه
                        last_log = OrderStatusLog.objects.filter(order=instance).order_by('-created_at').first()
                        if last_log and last_log.changed_by:
                            current_user = last_log.changed_by
                        else:
                            # البحث عن آخر سجل للعميل نفسه
                            from customers.models import Customer
                            if instance.customer:
                                customer_logs = OrderStatusLog.objects.filter(
                                    order__customer=instance.customer
                                ).order_by('-created_at')[:5]
                                for log in customer_logs:
                                    if log.changed_by:
                                        current_user = log.changed_by
                                        break
                    except:
                        pass
                
                # تسجيل التغييرات
                try:
                    OrderStatusLog.objects.create(
                        order=instance,
                        old_status=old_instance.order_status,
                        new_status=instance.order_status,  # نفس الحالة لأن هذا تعديل وليس تغيير حالة
                        changed_by=current_user,
                        notes=f'تعديل الطلب: {"، ".join(changes)}'
                    )
                except Exception as e:
                    logger.error(f"خطأ في تسجيل تعديل الطلب {instance.order_number}: {e}")
                    
        except Order.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(pre_save, sender='orders.Order')
def track_price_changes(sender, instance, **kwargs):
    """تتبع تغييرات الأسعار في الطلبات"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        # تجاهل التحديثات التلقائية
        if instance.is_auto_update:
            return
            
        try:
            Order = instance.__class__
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.final_price != instance.final_price:
                # لا نسجل التعديلات إذا كان هذا تحديث تلقائي (غير من قبل المستخدم)
                if not instance.is_auto_update:
                    instance.price_changed = True
                    instance.modified_at = timezone.now()
                    # حفظ القيمة القديمة للتتبع
                    instance._old_total_amount = old_instance.final_price
        except Order.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(post_save, sender=Order)
def create_manufacturing_order_on_order_creation(sender, instance, created, **kwargs):
    """
    Creates a ManufacturingOrder automatically when a new Order is created
    with specific types ('installation', 'tailoring', 'accessory').
    """
    if created:
        # print(f"--- SIGNAL TRIGGERED for Order PK: {instance.pk} ---")
        # print(f"Raw selected_types from instance: {instance.selected_types}")
        
        MANUFACTURING_TYPES = {'installation', 'tailoring', 'accessory'}
        
        order_types = set()
        try:
            # selected_types is stored as a JSON string, so we need to parse it.
            parsed_types = json.loads(instance.selected_types)
            if isinstance(parsed_types, list):
                order_types = set(parsed_types)
            # print(f"Successfully parsed types: {order_types}")
        except (json.JSONDecodeError, TypeError):
            # print(f"Could not parse selected_types. Value was: {instance.selected_types}")
            # Fallback for plain string if needed, though not expected
            if isinstance(instance.selected_types, str):
                order_types = {instance.selected_types}

        if order_types.intersection(MANUFACTURING_TYPES):
            # print(f"MATCH FOUND: Order types {order_types} intersect with {MANUFACTURING_TYPES}. Creating manufacturing order...")

            # Determine the appropriate order_type for manufacturing
            manufacturing_order_type = ''
            if 'installation' in order_types:
                manufacturing_order_type = 'installation'
            elif 'tailoring' in order_types:
                manufacturing_order_type = 'custom'
            elif 'accessory' in order_types:
                manufacturing_order_type = 'accessory'

            # Use a transaction to ensure both creations happen or neither.
            from django.db import transaction
            with transaction.atomic():
                from datetime import timedelta
                expected_date = instance.expected_delivery_date or (instance.created_at + timedelta(days=15)).date()

                # import ManufacturingOrder here to avoid circular import at module load
                from manufacturing.models import ManufacturingOrder

                mfg_order, created_mfg = ManufacturingOrder.objects.get_or_create(
                    order=instance,
                    defaults={
                        'order_type': manufacturing_order_type,
                        'status': 'pending_approval',
                        'notes': instance.notes,
                        'order_date': instance.created_at.date(),
                        'expected_delivery_date': expected_date,
                        'contract_number': instance.contract_number,
                        'invoice_number': instance.invoice_number,
                    }
                )

                # Also update the original order's tracking status
                if created_mfg:
                    # تحديث بدون إطلاق الإشارات لتجنب الrecursion
                    Order.objects.filter(pk=instance.pk).update(
                        tracking_status='factory',
                        order_status='pending_approval'
                    )
                    # print(f"SUCCESS: Created ManufacturingOrder PK: {mfg_order.pk} and updated Order PK: {instance.pk} tracking_status to 'factory'")
                else:
                    pass  # ManufacturingOrder already existed

@receiver(post_save, sender='manufacturing.ManufacturingOrder')
def sync_order_from_manufacturing(sender, instance, created, **kwargs):
    """Ensure the linked Order has its order_status and tracking_status updated
    when the ManufacturingOrder changes. This prevents display mismatches where
    manufacturing is completed but Order still shows an older manufacturing state.
    """
    try:
        order = getattr(instance, 'order', None)
        if not order:
            return

        # Map manufacturing status to order.tracking_status (same mapping as management command)
        status_mapping = {
            'pending_approval': 'factory',
            'pending': 'factory',
            'in_progress': 'factory',
            'ready_install': 'ready',
            'completed': 'ready',
            'delivered': 'delivered',
            'rejected': 'factory',
            'cancelled': 'factory',
        }

        new_order_status = instance.status
        new_tracking_status = status_mapping.get(instance.status, order.tracking_status)

        # Only update if something changed to avoid recursion/noise
        update_fields = []
        if order.order_status != new_order_status:
            order.order_status = new_order_status
            update_fields.append('order_status')
        if order.tracking_status != new_tracking_status:
            order.tracking_status = new_tracking_status
            update_fields.append('tracking_status')

        if update_fields:
            # Use update to avoid triggering heavy save logic where appropriate
            from django.db import transaction
            with transaction.atomic():
                Order.objects.filter(pk=order.pk).update(**{f: getattr(order, f) for f in update_fields})

            # Log status change
            try:
                # حاول الحصول على المستخدم الذي أنشأ أمر التصنيع إذا كان متاحاً
                mfg_creator = getattr(instance, 'created_by', None)
                # إن لم يتوفر، استخدم منشئ الطلب كاحتياط لتسجيل من قام بالتغيير
                if not mfg_creator and order and getattr(order, 'created_by', None):
                    mfg_creator = order.created_by
                old_st = order.tracker.previous('order_status') or order.tracker.previous('tracking_status') or ''
                new_st = getattr(order, 'order_status', order.tracking_status)
                OrderStatusLog.objects.create(
                    order=order,
                    old_status=old_st,
                    new_status=new_st,
                    changed_by=mfg_creator,
                    notes=f'مزامنة حالة الطلب من أمر التصنيع ({instance.get_status_display()})'
                )
            except Exception:
                pass
    except Exception:
        # avoid letting signal exceptions break the caller
        import logging
        logging.getLogger(__name__).exception('خطأ أثناء مزامنة حالة الطلب من ManufacturingOrder')

@receiver(post_save, sender=Order)
def create_inspection_on_order_creation(sender, instance, created, **kwargs):
    """
    إنشاء معاينة تلقائية عند إنشاء طلب من نوع معاينة
    """
    if created:
        order_types = instance.get_selected_types_list()
        print(f"🔍 تم إنشاء طلب جديد {instance.order_number}")
        print(f"📋 selected_types (raw): {instance.selected_types}")
        print(f"📋 الأنواع المستخرجة: {order_types}")
        print(f"📋 نوع البيانات: {type(order_types)}")

        if 'inspection' in order_types:
            print(f"📋 الطلب {instance.order_number} من نوع معاينة - سيتم إنشاء معاينة تلقائية")
            try:
                from django.db import transaction
                with transaction.atomic():
                    from inspections.models import Inspection
                    # استخدم تاريخ الطلب كـ request_date
                    request_date = instance.order_date.date() if instance.order_date else timezone.now().date()
                    # حاول استخراج تاريخ تنفيذ محدد من notes أو من بيانات الطلب إذا كان ذلك ممكناً (يمكنك تطوير هذا لاحقاً)
                    scheduled_date = request_date + timedelta(days=2)
                    # التحقق من البائع وإعداد المعاين
                    inspector = instance.created_by
                    responsible_employee = None

                    # إذا كان البائع له حساب مستخدم، استخدمه كمعاين
                    if instance.salesperson and instance.salesperson.user:
                        inspector = instance.salesperson.user
                        responsible_employee = instance.salesperson
                    elif instance.salesperson:
                        # البائع موجود لكن بدون حساب مستخدم
                        responsible_employee = instance.salesperson
                        inspector = instance.created_by  # استخدم منشئ الطلب كمعاين

                    print(f"📋 المعاين: {inspector}")
                    print(f"📋 الموظف المسؤول: {responsible_employee}")

                    inspection = Inspection.objects.create(
                        customer=instance.customer,
                        branch=instance.branch,
                        inspector=inspector,
                        responsible_employee=responsible_employee,
                        order=instance,
                        contract_number=instance.contract_number,  # إضافة رقم العقد
                        is_from_orders=True,
                        request_date=request_date,
                        scheduled_date=scheduled_date,
                        status='pending',
                        notes=f'معاينة تلقائية للطلب رقم {instance.order_number}',
                        order_notes=instance.notes,
                        created_by=instance.created_by,
                        windows_count=1  # قيمة افتراضية
                    )
                    print(f"✅ تم إنشاء معاينة تلقائية للطلب {instance.order_number} - معرف المعاينة: {inspection.id}")
                    Order.objects.filter(pk=instance.pk).update(
                        tracking_status='processing',
                        order_status='pending'
                    )
            except Exception as e:
                import traceback
                error_msg = f"❌ خطأ في إنشاء معاينة تلقائية للطلب {instance.order_number}: {str(e)}"
                print(f"\033[31m{error_msg}\033[0m")
                traceback.print_exc()
        else:
            pass


def set_default_delivery_option(order):
    """تحديد خيار التسليم الافتراضي حسب نوع الطلب"""
    if not hasattr(order, 'delivery_option'):
        return
        
    # إذا كان الطلب يحتوي على تركيب، تحديد التسليم مع التركيب
    if hasattr(order, 'selected_types') and order.selected_types:
        if 'installation' in order.selected_types or 'تركيب' in order.selected_types:
            Order.objects.filter(pk=order.pk).update(delivery_option='with_installation')
    # إذا كان الطلب تسليم في الفرع
    elif hasattr(order, 'delivery_type') and order.delivery_type == 'branch':
        Order.objects.filter(pk=order.pk).update(delivery_option='branch_pickup')
    # إذا كان الطلب توصيل منزلي
    elif hasattr(order, 'delivery_type') and order.delivery_type == 'home':
        Order.objects.filter(pk=order.pk).update(delivery_option='home_delivery')


def find_available_team(target_date, branch=None):
    """البحث عن فريق متاح في تاريخ محدد"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء نظام التركيبات
    return None


def calculate_windows_count(order):
    """حساب عدد الشبابيك من عناصر الطلب"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء النظام
    return 1


def create_production_order(order):
    """إنشاء طلب إنتاج"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء نظام المصنع
    return None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """معالج حفظ الطلب"""
    if created:
        # إنشاء سجل حالة أولية
        OrderStatusLog.objects.create(
            order=instance,
            old_status='',
            new_status=getattr(instance, 'order_status', instance.tracking_status),
            changed_by=getattr(instance, 'created_by', None),
            notes='تم إنشاء الطلب'
        )
    else:
        # التحقق من تغيير الحالة
        if hasattr(instance, '_tracking_status_changed') and instance._tracking_status_changed:
            # الحصول على الحالة السابقة من tracker
            old_status = instance.tracker.previous('tracking_status')
            if old_status is None:
                old_status = 'pending'  # قيمة افتراضية إذا لم تكن موجودة
            
            OrderStatusLog.objects.create(
                order=instance,
                old_status=old_status,
                new_status=getattr(instance, 'order_status', instance.tracking_status),
                changed_by=getattr(instance, '_modified_by', None),
                notes='تم تغيير حالة الطلب'
            )
        
        # تتبع التغييرات في المبلغ الإجمالي
        from .models import OrderModificationLog
        
        if hasattr(instance, '_old_total_amount') and instance._old_total_amount != instance.final_price:
            OrderModificationLog.objects.create(
                order=instance,
                modification_type='تعديلات البيانات الأساسية',
                old_total_amount=instance._old_total_amount,
                new_total_amount=instance.final_price,
                modified_by=getattr(instance, '_modified_by', None),
                details=f'تم تغيير إجمالي المبلغ من {instance._old_total_amount} إلى {instance.final_price}',
                notes='تعديل في المبلغ الإجمالي للطلب'
            )
        
        # تتبع التغييرات في حقول الطلب الأساسية إذا كان هناك مستخدم محدد
        modified_by = getattr(instance, '_modified_by', None)
        if modified_by:
            order_fields_to_track = [
                'contract_number', 'contract_number_2', 'contract_number_3',
                'invoice_number', 'invoice_number_2', 'invoice_number_3',
                'notes', 'delivery_address', 'location_address',
                'expected_delivery_date'
            ]
            
            field_changes = []
            field_labels = {
                'contract_number': 'رقم العقد',
                'contract_number_2': 'رقم العقد الإضافي 2',
                'contract_number_3': 'رقم العقد الإضافي 3',
                'invoice_number': 'رقم الفاتورة',
                'invoice_number_2': 'رقم الفاتورة الإضافي 2',
                'invoice_number_3': 'رقم الفاتورة الإضافي 3',
                'notes': 'الملاحظات',
                'delivery_address': 'عنوان التسليم',
                'location_address': 'عنوان التركيب',
                'expected_delivery_date': 'تاريخ التسليم المتوقع'
            }
            
            modified_fields_data = {}
            
            for field_name in order_fields_to_track:
                try:
                    if instance.tracker.has_changed(field_name):
                        old_value = instance.tracker.previous(field_name)
                        new_value = getattr(instance, field_name)
                        field_changes.append(f"{field_labels[field_name]}: {old_value or 'غير محدد'} → {new_value or 'غير محدد'}")
                        modified_fields_data[field_name] = {
                            'old': old_value,
                            'new': new_value
                        }
                except Exception:
                    # تخطي الحقول غير المتتبعة
                    continue
            
            if field_changes:
                OrderModificationLog.objects.create(
                    order=instance,
                    modification_type='تعديل حقول الطلب الأساسية',
                    modified_by=modified_by,
                    details=' | '.join(field_changes),
                    notes='تعديل يدوي في حقول الطلب الأساسية',
                    is_manual_modification=True,
                    modified_fields=modified_fields_data
                )

@receiver(post_save, sender=OrderItem)
def order_item_post_save(sender, instance, created, **kwargs):
    """معالج حفظ عنصر الطلب"""
    if created:
        # تحديث المبلغ الإجمالي للطلب (للطلبات الجديدة فقط)
        # Force recalculation to ensure stored final_price matches items
        try:
            instance.order.calculate_final_price(force_update=True)
            # تحديث مباشر في قاعدة البيانات لتجنب التكرار الذاتي
            instance.order._is_auto_update = True  # تمييز التحديث التلقائي
            Order.objects.filter(pk=instance.order.pk).update(
                final_price=instance.order.final_price,
                total_amount=instance.order.final_price
            )
        except Exception:
            # As a fallback, schedule async calculation
            try:
                from .tasks import calculate_order_totals_async
                calculate_order_totals_async.delay(instance.order.pk)
            except Exception:
                pass
        # لا نسجل تعديلات عند الإنشاء الأولي
        return
    else:
        # تتبع التغييرات في عنصر الطلب
        from .models import OrderItemModificationLog, OrderModificationLog
        
        # التحقق من التغييرات في الكمية
        if instance.tracker.has_changed('quantity'):
            old_quantity = instance.tracker.previous('quantity')
            new_quantity = instance.quantity
            
            OrderItemModificationLog.objects.create(
                order_item=instance,
                field_name='quantity',
                old_value=str(old_quantity) if old_quantity is not None else '',
                new_value=str(new_quantity) if new_quantity is not None else '',
                modified_by=getattr(instance, '_modified_by', None),
                notes=f'تم تغيير كمية المنتج {instance.product.name}'
            )
        
        # التحقق من التغييرات في سعر الوحدة
        if instance.tracker.has_changed('unit_price'):
            old_price = instance.tracker.previous('unit_price')
            new_price = instance.unit_price
            
            OrderItemModificationLog.objects.create(
                order_item=instance,
                field_name='unit_price',
                old_value=str(old_price) if old_price is not None else '',
                new_value=str(new_price) if new_price is not None else '',
                modified_by=getattr(instance, '_modified_by', None),
                notes=f'تم تغيير سعر الوحدة للمنتج {instance.product.name}'
            )
        
        # التحقق من التغييرات في المنتج
        if instance.tracker.has_changed('product'):
            old_product_id = instance.tracker.previous('product')
            new_product_id = instance.product.id
            
            try:
                from inventory.models import Product
                old_product = Product.objects.get(id=old_product_id) if old_product_id else None
                new_product = instance.product
                
                OrderItemModificationLog.objects.create(
                    order_item=instance,
                    field_name='product',
                    old_value=old_product.name if old_product else '',
                    new_value=new_product.name,
                    modified_by=getattr(instance, '_modified_by', None),
                    notes=f'تم تغيير المنتج من {old_product.name if old_product else "غير محدد"} إلى {new_product.name}'
                )
            except Product.DoesNotExist:
                pass
        
        # التحقق من التغييرات في نسبة الخصم
        if instance.tracker.has_changed('discount_percentage'):
            old_discount = instance.tracker.previous('discount_percentage')
            new_discount = instance.discount_percentage
            
            OrderItemModificationLog.objects.create(
                order_item=instance,
                field_name='discount_percentage',
                old_value=f"{old_discount}%" if old_discount is not None else "0%",
                new_value=f"{new_discount}%" if new_discount is not None else "0%",
                modified_by=getattr(instance, '_modified_by', None),
                notes=f'تم تغيير نسبة الخصم للمنتج {instance.product.name}'
            )
        
        # إنشاء سجل تعديل شامل للطلب
        # الاحتفاظ بتسجيل السجل فقط إن وُجد مستخدم محدد، لكن دعنا نسمح دائماً بإعادة الحساب
        has_user_modifier = bool(getattr(instance, '_modified_by', None))

        if any([
            instance.tracker.has_changed('quantity'),
            instance.tracker.has_changed('unit_price'),
            instance.tracker.has_changed('product'),
            instance.tracker.has_changed('discount_percentage')
        ]):
            # الحصول على المبلغ القديم قبل التعديل
            old_total = instance.order.final_price
            
            # حساب المبلغ الجديد بعد التعديل
            # نحتاج إلى حساب المبلغ الجديد يدوياً بناءً على التغييرات
            total_change = 0
            modification_details = []
            
            if instance.tracker.has_changed('quantity'):
                old_quantity = instance.tracker.previous('quantity')
                new_quantity = instance.quantity
                current_price = instance.unit_price
                quantity_change = (new_quantity - old_quantity) * current_price
                total_change += quantity_change
                modification_details.append(f"الكمية: {old_quantity} → {new_quantity}")
            
            if instance.tracker.has_changed('unit_price'):
                old_price = instance.tracker.previous('unit_price')
                new_price = instance.unit_price
                current_quantity = instance.quantity
                # التأكد من أن الأنواع متوافقة
                old_price = Decimal(str(old_price)) if old_price is not None else Decimal('0')
                new_price = Decimal(str(new_price)) if new_price is not None else Decimal('0')
                current_quantity = Decimal(str(current_quantity)) if current_quantity is not None else Decimal('0')
                price_change = (new_price - old_price) * current_quantity
                total_change += price_change
                modification_details.append(f"السعر: {old_price} → {new_price} ج.م")
            
            if instance.tracker.has_changed('product'):
                old_product_id = instance.tracker.previous('product')
                try:
                    from inventory.models import Product
                    old_product = Product.objects.get(id=old_product_id) if old_product_id else None
                    modification_details.append(f"المنتج: {old_product.name if old_product else 'غير محدد'} → {instance.product.name}")
                except Product.DoesNotExist:
                    modification_details.append(f"المنتج: غير محدد → {instance.product.name}")
            
            if instance.tracker.has_changed('discount_percentage'):
                old_discount = instance.tracker.previous('discount_percentage')
                new_discount = instance.discount_percentage
                modification_details.append(f"الخصم: {old_discount}% → {new_discount}%")
            
            new_total = old_total + total_change
            
            # إنشاء سجل تعديل شامل مع تفاصيل العناصر (فقط إذا وُجد مستخدم محدد)
            if has_user_modifier:
                OrderModificationLog.objects.create(
                    order=instance.order,
                    modification_type='تعديل الأصناف الموجودة',
                    old_total_amount=old_total,
                    new_total_amount=new_total,
                    modified_by=getattr(instance, '_modified_by', None),
                    details=f"تعديل {instance.product.name}: {' | '.join(modification_details)}",
                    notes='تعديل في عناصر الطلب',
                    is_manual_modification=True,
                    modified_fields={
                        'order_items': [{
                            'item_id': instance.pk,
                            'product': instance.product.name,
                            'changes': modification_details
                        }]
                    }
                )
            # بعد تسجيل التعديل، نعيد حساب إجماليات الطلب ونحدث الحقول المخزنة فوراً
            try:
                # لا نغيّر الأسعار إذا كان الطلب مدفوعًا بالفعل إلا إذا طُلب صراحة
                allow_force = getattr(instance, '_force_price_update', False)
                if float(getattr(instance.order, 'paid_amount', 0)) == 0 or allow_force:
                    instance.order.calculate_final_price(force_update=True)
                    instance.order._is_auto_update = True
                    Order.objects.filter(pk=instance.order.pk).update(
                        final_price=instance.order.final_price,
                        total_amount=instance.order.final_price
                    )
                else:
                    # إذا كان هناك دفعات، نجدد عبر مهمة خلفية لتجنب تغيير أسعار مدفوعة دون سجل
                    try:
                        from .tasks import calculate_order_totals_async
                        calculate_order_totals_async.delay(instance.order.pk)
                    except Exception:
                        pass
            except Exception:
                # كاحتياط، حاول جدولة المهمة الخلفية
                try:
                    from .tasks import calculate_order_totals_async
                    calculate_order_totals_async.delay(instance.order.pk)
                except Exception:
                    pass

@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """معالج حفظ الدفعة"""
    if created:
        # تحديث المبلغ المدفوع للطلب
        order = instance.order
        paid_amount = order.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        # تحديث مباشر في قاعدة البيانات لتجنب التكرار الذاتي
        Order.objects.filter(pk=order.pk).update(paid_amount=paid_amount, payment_verified=True)

# إشارات تحديث حالة الطلب من الأقسام الأخرى
# تم إزالة signal التركيب لتجنب الحلقة اللانهائية - يتم التعامل معه في orders/models.py

# تم تعطيل هذا signal لتجنب التضارب مع inspections/signals.py
# @receiver(post_save, sender='inspections.Inspection')
# def update_order_inspection_status(sender, instance, created, **kwargs):
#     """تحديث حالة الطلب عند تغيير حالة المعاينة - معطل لتجنب التضارب"""
#     try:
#         if instance.order:
#             order = instance.order
#             order.update_inspection_status()
#             order.update_completion_status()
#     except Exception as e:
#         logger.error(f"خطأ في تحديث حالة المعاينة للطلب: {str(e)}")

@receiver(post_save, sender='manufacturing.ManufacturingOrder')
def update_order_manufacturing_status(sender, instance, created, **kwargs):
    """تحديث حالة الطلب عند تغيير حالة التصنيع"""
    try:
        order = instance.order

        # تجاهل التحديث إذا كان إنشاء جديد لتجنب التضارب
        if created:
            return

        # مطابقة مباشرة بين حالات التصنيع والطلب
        status_mapping = {
            'pending_approval': 'pending_approval',
            'pending': 'pending',
            'in_progress': 'in_progress',
            'ready_install': 'ready_install',
            'completed': 'completed',
            'delivered': 'delivered',
            'rejected': 'rejected',
            'cancelled': 'cancelled',
        }

        new_status = status_mapping.get(instance.status)

        # تحديث الحالة فقط إذا تغيرت لتجنب التكرار الذاتي
        if new_status and new_status != order.order_status:
            Order.objects.filter(pk=order.pk).update(order_status=new_status)
            order.refresh_from_db()
            order.update_completion_status()
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة التصنيع للطلب {instance.order.id}: {str(e)}")

# إشارة حذف أوامر التصنيع
@receiver(post_delete, sender='manufacturing.ManufacturingOrder')
def log_manufacturing_order_deletion(sender, instance, **kwargs):
    """تسجيل حذف أمر التصنيع"""
    try:
        # حفظ بيانات أمر التصنيع قبل الحذف
        manufacturing_data = {
            'id': instance.id,
            'status': instance.status,
            'order_type': instance.order_type,
            'contract_number': instance.contract_number,
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
        }
        
        ManufacturingDeletionLog.objects.create(
            order=instance.order,
            manufacturing_order_id=instance.id,
            manufacturing_order_data=manufacturing_data,
            reason='تم حذف أمر التصنيع'
        )
        
        # تحديث حالة الطلب
        Order.objects.filter(pk=instance.order.pk).update(order_status='manufacturing_deleted')
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل حذف أمر التصنيع: {str(e)}")


# ==================== 🎨 إشعارات الطلبات التلقائية ====================

# تم إزالة signal إنشاء الإشعارات المكررة - يتم التعامل مع الإشعارات في Order.save()
# تم إزالة signal إنشاء الإشعارات المكررة - يتم التعامل مع الإشعارات في Order.save()
# @receiver(post_save, sender=Order)
# def order_created_notification(sender, instance, created, **kwargs):
#     """إنشاء إشعارات عند إنشاء طلب جديد - تم تعطيله لتجنب التكرار"""
#     pass


# تم إزالة signal تغيير حالة الطلب المكرر - يتم التعامل مع الإشعارات في Order.save()
# @receiver(pre_save, sender=Order)
# def order_status_change_notification(sender, instance, **kwargs):
#     """إنشاء إشعارات عند تغيير حالة الطلب - تم تعطيله لتجنب التكرار"""
#     pass


# تم إزالة signal تغيير حالة الطلب الشامل المكرر - يتم التعامل مع الإشعارات في Order.save()
# @receiver(pre_save, sender=Order)
# def comprehensive_order_status_change_notification(sender, instance, **kwargs):
#     """إنشاء إشعارات شاملة عند تغيير حالة الطلب - تم تعطيله لتجنب التكرار"""
#     pass

# تم إزالة الكود المتبقي من signal تغيير الحالة المحذوف


# تم إزالة دالة manufacturing_order_notification


# ===== إشارات التخزين المؤقت =====

@receiver(pre_save, sender='orders.OrderItem')
def track_order_item_changes(sender, instance, **kwargs):
    """تتبع تغييرات عناصر الطلب"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        try:
            OrderItem = instance.__class__
            old_instance = OrderItem.objects.get(pk=instance.pk)
            # حفظ القيم القديمة للتتبع
            instance._old_quantity = old_instance.quantity
            instance._old_unit_price = old_instance.unit_price
            instance._old_product_id = old_instance.product.id
            instance._old_discount_percentage = old_instance.discount_percentage
        except OrderItem.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(post_save, sender=Order)
def invalidate_order_cache_on_save(sender, instance, created, **kwargs):
    """إلغاء التخزين المؤقت عند حفظ طلب"""
    try:
        from .cache import OrderCache

        # إلغاء إحصائيات الطلبات
        OrderCache.invalidate_order_stats_cache()

        # إلغاء بيانات العميل إذا تم تحديثها
        if instance.customer_id:
            OrderCache.invalidate_customer_cache(instance.customer_id)

        logger.debug(f"تم إلغاء التخزين المؤقت للطلب {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للطلب {instance.pk}: {str(e)}")


@receiver(post_delete, sender=Order)
def invalidate_order_cache_on_delete(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت عند حذف طلب"""
    try:
        from .cache import OrderCache

        # إلغاء إحصائيات الطلبات
        OrderCache.invalidate_order_stats_cache()

        logger.debug(f"تم إلغاء التخزين المؤقت بعد حذف الطلب {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت بعد حذف الطلب {instance.pk}: {str(e)}")


@receiver(post_save, sender='orders.DeliveryTimeSettings')
def invalidate_delivery_settings_cache_on_save(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت لإعدادات التسليم عند التحديث"""
    try:
        from .cache import OrderCache
        OrderCache.invalidate_delivery_settings_cache()
        logger.debug("تم إلغاء التخزين المؤقت لإعدادات التسليم")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت لإعدادات التسليم: {str(e)}")


@receiver(post_save, sender='customers.Customer')
def invalidate_customer_cache_on_save(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت لبيانات العميل عند التحديث"""
    try:
        from .cache import OrderCache
        OrderCache.invalidate_customer_cache(instance.pk)
        logger.debug(f"تم إلغاء التخزين المؤقت للعميل {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للعميل {instance.pk}: {str(e)}")


@receiver(post_save, sender='inventory.Product')
def invalidate_product_cache_on_save(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت للمنتجات عند التحديث"""
    try:
        from .cache import OrderCache
        OrderCache.invalidate_product_search_cache()
        logger.debug(f"تم إلغاء التخزين المؤقت للمنتجات بعد تحديث المنتج {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للمنتجات: {str(e)}")


@receiver(post_delete, sender='inventory.Product')
def invalidate_product_cache_on_delete(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت للمنتجات عند الحذف"""
    try:
        from .cache import OrderCache
        OrderCache.invalidate_product_search_cache()
        logger.debug(f"تم إلغاء التخزين المؤقت للمنتجات بعد حذف المنتج {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للمنتجات بعد الحذف: {str(e)}")


logger.info("تم تحميل إشارات التخزين المؤقت للطلبات")
