from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

@receiver(pre_save, sender='orders.Order')
def track_price_changes(sender, instance, **kwargs):
    """تتبع تغييرات الأسعار في الطلبات"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        try:
            Order = instance.__class__
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.final_price != instance.final_price:
                instance.price_changed = True
                instance.modified_at = timezone.now()
        except Order.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(post_save, sender='orders.Order')
def handle_order_creation(sender, instance, created, **kwargs):
    """معالجة إنشاء الطلب وربطه بالتركيبات والمصنع"""

    if created:
        # إذا كان نوع الطلب يحتوي على تركيب، إنشاء طلب تركيب تلقائياً
        if hasattr(instance, 'selected_types') and instance.selected_types:
            if 'installation' in instance.selected_types or 'تركيب' in instance.selected_types:
                create_installation_order(instance)

        # إنشاء طلب إنتاج في المصنع لجميع الطلبات
        create_production_order(instance)

        # تحديد خيار التسليم الافتراضي
        set_default_delivery_option(instance)


def create_installation_order(order):
    """إنشاء طلب تركيب تلقائياً"""
    try:
        from installations.models_new import InstallationNew, InstallationTeamNew

        # تحديد تاريخ التركيب المتوقع (7 أيام للـ VIP، 15 يوم للعادي)
        if hasattr(order, 'customer') and order.customer and getattr(order.customer, 'is_vip', False):
            scheduled_date = order.created_at.date() + timedelta(days=7)
        else:
            scheduled_date = order.created_at.date() + timedelta(days=15)

        # البحث عن فريق متاح
        available_team = find_available_team(scheduled_date, order.branch)

        # إنشاء طلب التركيب
        installation = InstallationNew.objects.create(
            # معلومات العميل
            customer_name=order.customer.name if order.customer else '',
            customer_phone=order.customer.phone if order.customer else '',
            customer_address=getattr(order, 'delivery_address', '') or (order.customer.address if order.customer else ''),

            # معلومات الطلب
            order=order,
            order_reference=order.order_number,
            salesperson_name=order.salesperson.name if order.salesperson else '',
            branch_name=order.branch.name if order.branch else '',

            # تفاصيل التركيب
            windows_count=calculate_windows_count(order),
            location_type='residential',  # افتراضي
            priority='high' if (order.customer and getattr(order.customer, 'is_vip', False)) else 'normal',

            # الجدولة
            order_date=order.created_at.date(),
            scheduled_date=scheduled_date,
            expected_delivery_date=order.expected_delivery_date,

            # الفريق
            team=available_team,

            # الحالة
            status='pending',

            # ملاحظات
            special_notes=f'تم إنشاؤه تلقائياً من الطلب #{order.order_number}',

            # المنشئ
            created_by=order.created_by
        )

        print(f"✅ تم إنشاء طلب تركيب #{installation.id} للطلب #{order.order_number}")

    except Exception as e:
        print(f"❌ خطأ في إنشاء طلب التركيب للطلب #{order.order_number}: {e}")


def create_production_order(order):
    """إنشاء طلب إنتاج في المصنع"""
    try:
        from factory.models import ProductionOrder, ProductionLine

        # البحث عن خط إنتاج متاح
        production_line = ProductionLine.objects.filter(is_active=True).first()

        # إنشاء طلب الإنتاج
        production_order = ProductionOrder.objects.create(
            order=order,
            production_line=production_line,
            status='pending',
            estimated_completion=order.expected_delivery_date,
            notes=f'تم إنشاؤه تلقائياً من الطلب #{order.order_number}'
        )

        print(f"✅ تم إنشاء طلب إنتاج #{production_order.id} للطلب #{order.order_number}")

    except Exception as e:
        print(f"❌ خطأ في إنشاء طلب الإنتاج للطلب #{order.order_number}: {e}")


def find_available_team(target_date, branch=None):
    """البحث عن فريق متاح في تاريخ محدد"""
    try:
        from installations.models_new import InstallationNew, InstallationTeamNew

        # البحث عن الفرق النشطة
        teams_query = InstallationTeamNew.objects.filter(is_active=True)

        if branch:
            teams_query = teams_query.filter(branch=branch)

        # البحث عن فريق بأقل عدد تركيبات في ذلك التاريخ
        for team in teams_query:
            daily_installations = InstallationNew.objects.filter(
                team=team,
                scheduled_date=target_date
            ).count()

            # إذا كان الفريق لديه أقل من 13 تركيب (الحد الأقصى)
            if daily_installations < 13:
                return team

        # إذا لم يوجد فريق متاح، إرجاع أول فريق نشط
        return teams_query.first()

    except Exception as e:
        print(f"❌ خطأ في البحث عن فريق متاح: {e}")
        return None


def calculate_windows_count(order):
    """حساب عدد الشبابيك من عناصر الطلب"""
    try:
        windows_count = 0

        # البحث في عناصر الطلب عن الشبابيك
        if hasattr(order, 'items'):
            for item in order.items.all():
                # إذا كان المنتج يحتوي على كلمة "شباك" أو "نافذة"
                if any(word in item.product.name.lower() for word in ['شباك', 'نافذة', 'window']):
                    windows_count += item.quantity

        # إذا لم يتم العثور على شبابيك، استخدم قيمة افتراضية
        return max(windows_count, 1)

    except Exception as e:
        print(f"❌ خطأ في حساب عدد الشبابيك: {e}")
        return 1


def set_default_delivery_option(order):
    """تحديد خيار التسليم الافتراضي حسب نوع الطلب"""
    try:
        # التحقق من أن الطلب يحتوي على أنواع مختارة
        if hasattr(order, 'selected_types') and order.selected_types:
            # إذا كان نوع الطلب يحتوي على تركيب، التسليم للمنزل
            if 'installation' in order.selected_types or 'تركيب' in order.selected_types:
                order.delivery_type = 'home'
                order.delivery_address = order.customer.address if order.customer else ''
                order.save(update_fields=['delivery_type', 'delivery_address'])
                print(f"✅ تم تحديد التسليم للمنزل للطلب #{order.order_number}")

            # إذا كان نوع الطلب تفصيل، الاستلام من الفرع
            elif 'tailoring' in order.selected_types or 'تفصيل' in order.selected_types:
                order.delivery_type = 'branch'
                order.save(update_fields=['delivery_type'])
                print(f"✅ تم تحديد الاستلام من الفرع للطلب #{order.order_number}")

    except Exception as e:
        print(f"❌ خطأ في تحديد خيار التسليم للطلب #{order.order_number}: {e}")


# إشارة لتحديث حالة التركيبات عند تغيير حالة طلب الإنتاج
@receiver(post_save, sender='factory.ProductionOrder')
def update_installation_status(sender, instance, **kwargs):
    """تحديث حالة التركيب عند اكتمال الإنتاج"""
    try:
        from installations.models_new import InstallationNew

        # البحث عن التركيب المرتبط بهذا الطلب
        installations = InstallationNew.objects.filter(order=instance.order)

        for installation in installations:
            # إذا اكتمل الإنتاج، تحديث حالة التركيب إلى "جاهز للتركيب"
            if instance.status == 'completed':
                installation.status = 'ready_for_installation'
                installation.production_completed_at = timezone.now()
                installation.save(update_fields=['status', 'production_completed_at'])
                print(f"✅ تم تحديث التركيب #{installation.id} إلى جاهز للتركيب")

            # إذا كان الإنتاج قيد التنفيذ
            elif instance.status == 'in_progress':
                if installation.status == 'pending':
                    installation.status = 'in_production'
                    installation.production_started_at = timezone.now()
                    installation.save(update_fields=['status', 'production_started_at'])
                    print(f"✅ تم تحديث التركيب #{installation.id} إلى قيد الإنتاج")

            # إذا تم إلغاء الإنتاج
            elif instance.status == 'cancelled':
                installation.status = 'cancelled'
                installation.save(update_fields=['status'])
                print(f"✅ تم إلغاء التركيب #{installation.id}")

    except Exception as e:
        print(f"❌ خطأ في تحديث حالة التركيب: {e}")