"""
خدمة الإشعارات البسيطة والجميلة 🎨
Simple & Beautiful Notification Service
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from accounts.models import SimpleNotification, ComplaintNotification, GroupNotification, GroupNotificationRead
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SimpleNotificationService:
    """خدمة الإشعارات البسيطة والجميلة"""
    
    @classmethod
    def create_order_notification(
        cls,
        customer_name: str,
        order_number: str,
        status: str,
        notification_type: str = 'order_updated',
        priority: str = 'normal',
        recipient: User = None,
        related_object = None
    ):
        """
        إنشاء إشعار طلب بسيط وجميل
        
        Args:
            customer_name: اسم العميل
            order_number: رقم الطلب
            status: حالة الطلب
            notification_type: نوع الإشعار
            priority: الأولوية
            recipient: المستلم
            related_object: الكائن المرتبط
        """
        try:
            # تحديد العنوان حسب نوع الإشعار
            titles = {
                'order_created': f'طلب جديد من {customer_name}',
                'order_updated': f'تحديث طلب {customer_name}',
                'order_completed': f'اكتمل طلب {customer_name}',
                'order_cancelled': f'تم إلغاء طلب {customer_name}',
                'inspection_scheduled': f'معاينة مجدولة لـ {customer_name}',
                'manufacturing_started': f'بدء تصنيع طلب {customer_name}',
                'installation_completed': f'تم تركيب طلب {customer_name}',
            }
            
            title = titles.get(notification_type, f'تحديث طلب {customer_name}')
            
            # تحديد ContentType إذا كان هناك كائن مرتبط
            content_type = None
            object_id = None
            if related_object:
                content_type = ContentType.objects.get_for_model(related_object)
                object_id = related_object.pk
            
            # إنشاء الإشعار
            notification = SimpleNotification.objects.create(
                title=title,
                customer_name=customer_name,
                order_number=order_number,
                status=status,
                notification_type=notification_type,
                priority=priority,
                recipient=recipient,
                content_type=content_type,
                object_id=object_id
            )
            
            logger.info(f"تم إنشاء إشعار طلب: {title} للمستخدم {recipient}")
            return notification
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء إشعار الطلب: {str(e)}")
            return None
    
    @classmethod
    def create_complaint_notification(
        cls,
        customer_name: str,
        complaint_number: str,
        title: str,
        complaint_type: str = 'new',
        priority: str = 'medium',
        recipient: User = None,
        related_object = None
    ):
        """
        إنشاء إشعار شكوى منفصل
        
        Args:
            customer_name: اسم العميل
            complaint_number: رقم الشكوى
            title: عنوان الشكوى
            complaint_type: نوع الإشعار
            priority: الأولوية
            recipient: المستلم
            related_object: الكائن المرتبط
        """
        try:
            # تحديد ContentType إذا كان هناك كائن مرتبط
            content_type = None
            object_id = None
            if related_object:
                content_type = ContentType.objects.get_for_model(related_object)
                object_id = related_object.pk
            
            # إنشاء إشعار الشكوى
            notification = ComplaintNotification.objects.create(
                title=title,
                customer_name=customer_name,
                complaint_number=complaint_number,
                complaint_type=complaint_type,
                priority=priority,
                recipient=recipient,
                content_type=content_type,
                object_id=object_id
            )
            
            logger.info(f"تم إنشاء إشعار شكوى: {title} للمستخدم {recipient}")
            return notification
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء إشعار الشكوى: {str(e)}")
            return None
    
    @classmethod
    def notify_order_status_change(cls, order, old_status, new_status, changed_by=None):
        """إشعار تغيير حالة الطلب"""
        if not order.created_by:
            return None
            
        # تحديد نوع الإشعار والأولوية
        notification_type = 'order_updated'
        priority = 'normal'
        
        if new_status in ['ready', 'delivered']:
            notification_type = 'order_completed'
            priority = 'high'
        elif new_status == 'cancelled':
            notification_type = 'order_cancelled'
            priority = 'high'
        elif old_status == 'pending' and new_status == 'processing':
            notification_type = 'order_created'
            priority = 'normal'
        
        # تحديد النص الجميل للحالة
        status_names = {
            'pending': 'في قائمة الانتظار',
            'processing': 'قيد المعالجة',
            'warehouse': 'في المستودع',
            'factory': 'في المصنع',
            'cutting': 'قيد القص',
            'ready': 'جاهز للتسليم',
            'delivered': 'تم التسليم',
            'cancelled': 'ملغي'
        }
        
        status_text = status_names.get(new_status, new_status)
        
        return cls.create_order_notification(
            customer_name=order.customer.name,
            order_number=order.order_number,
            status=status_text,
            notification_type=notification_type,
            priority=priority,
            recipient=order.created_by,
            related_object=order
        )
    
    @classmethod
    def notify_new_order(cls, order):
        """إشعار طلب جديد حسب الهيكل الهرمي للأدوار"""
        notifications = []

        # 1. إشعار البائع/منشئ الطلب
        if order.salesperson:
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status='تم إنشاء الطلب بنجاح',
                notification_type='order_created',
                priority='normal',
                recipient=order.salesperson.user,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        # 2. إشعار مديري الفرع (البحث عن مديري الفرع في الأقسام)
        if order.branch:
            # البحث عن مديري الفرع في قسم الإدارة
            try:
                from accounts.models import Department
                admin_dept = Department.objects.get(code='administration')
                branch_managers = admin_dept.users.filter(is_active=True)

                for manager in branch_managers:
                    notification = cls.create_order_notification(
                        customer_name=order.customer.name,
                        order_number=order.order_number,
                        status=f'طلب جديد في فرع {order.branch.name}',
                        notification_type='order_created',
                        priority='normal',
                        recipient=manager,
                        related_object=order
                    )
                    if notification:
                        notifications.append(notification)

            except Department.DoesNotExist:
                logger.warning("قسم الإدارة غير موجود")

        # 3. إشعار المدير العام (مدير النظام)
        from accounts.models import User
        admin_users = User.objects.filter(is_superuser=True, is_active=True)
        for admin in admin_users:
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status='طلب جديد في النظام',
                notification_type='order_created',
                priority='normal',
                recipient=admin,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        # 4. إشعارات الأقسام المختصة حسب نوع الخدمة
        order_items = order.items.all()

        # إشعار قسم المعاينات
        if any(item.service_type == 'inspection' for item in order_items):
            notifications.extend(cls._notify_department(
                'inspections', order, 'طلب معاينة جديد', 'inspection_scheduled', 'high'
            ))

        # إشعار قسم التصنيع
        if any(item.service_type in ['tailoring', 'manufacturing'] for item in order_items):
            notifications.extend(cls._notify_department(
                'manufacturing', order, 'طلب تصنيع جديد', 'order_created', 'normal'
            ))

        # إشعار قسم التركيبات (للمتابعة المستقبلية)
        if any(item.service_type == 'installation' for item in order_items):
            notifications.extend(cls._notify_department(
                'installations', order, 'طلب تركيب مجدول', 'order_created', 'normal'
            ))

        logger.info(f"تم إنشاء {len(notifications)} إشعار للطلب الجديد {order.order_number}")
        return notifications

    @classmethod
    def _notify_department(cls, dept_code, order, status, notification_type, priority):
        """إشعار قسم معين"""
        notifications = []

        try:
            from accounts.models import Department
            department = Department.objects.get(code=dept_code)
            users = department.users.filter(is_active=True)

            for user in users:
                notification = cls.create_order_notification(
                    customer_name=order.customer.name,
                    order_number=order.order_number,
                    status=status,
                    notification_type=notification_type,
                    priority=priority,
                    recipient=user,
                    related_object=order
                )
                if notification:
                    notifications.append(notification)

        except Department.DoesNotExist:
            logger.warning(f"القسم غير موجود: {dept_code}")

        return notifications

    @classmethod
    def notify_order_ready_for_installation(cls, order):
        """إشعار جاهزية الطلب للتركيب"""
        notifications = []

        # 1. إشعار قسم التركيبات
        notifications.extend(cls._notify_department(
            'installations', order, 'طلب جاهز للتركيب', 'installation_ready', 'high'
        ))

        # 2. إشعار البائع/منشئ الطلب
        if order.salesperson:
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status='طلبك جاهز للتركيب',
                notification_type='installation_ready',
                priority='high',
                recipient=order.salesperson.user,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        logger.info(f"تم إنشاء {len(notifications)} إشعار لجاهزية التركيب {order.order_number}")
        return notifications

    @classmethod
    def notify_installation_completed(cls, order):
        """إشعار اكتمال التركيب"""
        notifications = []

        # 1. إشعار البائع/منشئ الطلب
        if order.salesperson:
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status='تم اكتمال التركيب',
                notification_type='installation_completed',
                priority='normal',
                recipient=order.salesperson.user,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        # 2. إشعار مديري الفرع
        if order.branch:
            try:
                from accounts.models import Department
                admin_dept = Department.objects.get(code='administration')
                branch_managers = admin_dept.users.filter(is_active=True)

                for manager in branch_managers:
                    notification = cls.create_order_notification(
                        customer_name=order.customer.name,
                        order_number=order.order_number,
                        status=f'تم اكتمال التركيب في فرع {order.branch.name}',
                        notification_type='installation_completed',
                        priority='normal',
                        recipient=manager,
                        related_object=order
                    )
                    if notification:
                        notifications.append(notification)

            except Department.DoesNotExist:
                logger.warning("قسم الإدارة غير موجود")

        # 3. إشعار المدير العام
        from accounts.models import User
        admin_users = User.objects.filter(is_superuser=True, is_active=True)
        for admin in admin_users:
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status='تم اكتمال التركيب',
                notification_type='installation_completed',
                priority='normal',
                recipient=admin,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        # 4. إشعار قسم التصنيع (للمتابعة)
        notifications.extend(cls._notify_department(
            'manufacturing', order, 'تم اكتمال تركيب الطلب', 'installation_completed', 'normal'
        ))

        logger.info(f"تم إنشاء {len(notifications)} إشعار لاكتمال التركيب {order.order_number}")
        return notifications

    @classmethod
    def notify_order_modification(cls, order, modification_details):
        """إشعار تعديل الطلب"""
        notifications = []

        # 1. إشعار قسم التصنيع
        notifications.extend(cls._notify_department(
            'manufacturing', order, f'تعديل على الطلب: {modification_details}', 'order_modified', 'high'
        ))

        # 2. إشعار البائع/منشئ الطلب
        if order.salesperson:
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status=f'تم تعديل طلبك: {modification_details}',
                notification_type='order_modified',
                priority='high',
                recipient=order.salesperson.user,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        logger.info(f"تم إنشاء {len(notifications)} إشعار لتعديل الطلب {order.order_number}")
        return notifications

    @classmethod
    def notify_order_status_change_comprehensive(cls, order, old_status, new_status, changed_by=None):
        """إشعار شامل لتغيير حالة الطلب لجميع الأقسام المعنية"""
        notifications = []

        # تحديد الرسالة حسب نوع التغيير
        status_messages = {
            'pending_approval': 'في انتظار الموافقة',
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد التصنيع',
            'ready_install': 'جاهز للتركيب',
            'completed': 'مكتمل',
            'delivered': 'تم التسليم',
            'rejected': 'مرفوض',
            'cancelled': 'ملغي',
        }

        old_status_text = status_messages.get(old_status, old_status)
        new_status_text = status_messages.get(new_status, new_status)

        # تحديد الأقسام المعنية حسب الحالة الجديدة
        departments_to_notify = []
        priority = 'normal'

        if new_status == 'pending_approval':
            departments_to_notify = ['manufacturing', 'administration']
            priority = 'high'
        elif new_status == 'in_progress':
            departments_to_notify = ['manufacturing', 'quality_control']
            priority = 'high'
        elif new_status == 'ready_install':
            departments_to_notify = ['installations', 'customer_service']
            priority = 'high'
        elif new_status == 'completed':
            departments_to_notify = ['installations', 'customer_service', 'administration', 'accounting']
            priority = 'normal'
        elif new_status == 'delivered':
            departments_to_notify = ['customer_service', 'administration', 'accounting']
            priority = 'normal'
        elif new_status == 'rejected':
            departments_to_notify = ['customer_service', 'administration']
            priority = 'high'
        elif new_status == 'cancelled':
            departments_to_notify = ['manufacturing', 'installations', 'customer_service', 'administration']
            priority = 'medium'

        # إرسال إشعارات للأقسام المعنية
        for dept_code in departments_to_notify:
            try:
                from accounts.models import Department
                department = Department.objects.get(code=dept_code)
                users = department.users.filter(is_active=True)

                for user in users:
                    # تجنب إرسال إشعار للشخص الذي قام بالتغيير
                    if changed_by and user == changed_by:
                        continue

                    notification = cls.create_order_notification(
                        customer_name=order.customer.name,
                        order_number=order.order_number,
                        status=f'تم تغيير حالة الطلب من "{old_status_text}" إلى "{new_status_text}"',
                        notification_type='status_change',
                        priority=priority,
                        recipient=user,
                        related_object=order
                    )
                    if notification:
                        notifications.append(notification)

            except Department.DoesNotExist:
                logger.warning(f"القسم {dept_code} غير موجود")

        # إشعار البائع/منشئ الطلب
        if order.salesperson and (not changed_by or order.salesperson.user != changed_by):
            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status=f'تم تغيير حالة طلبك من "{old_status_text}" إلى "{new_status_text}"',
                notification_type='status_change',
                priority=priority,
                recipient=order.salesperson.user,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        # إشعار المدير العام
        from accounts.models import User
        admin_users = User.objects.filter(is_superuser=True, is_active=True)
        for admin in admin_users:
            if changed_by and admin == changed_by:
                continue

            notification = cls.create_order_notification(
                customer_name=order.customer.name,
                order_number=order.order_number,
                status=f'تم تغيير حالة الطلب من "{old_status_text}" إلى "{new_status_text}"',
                notification_type='status_change',
                priority=priority,
                recipient=admin,
                related_object=order
            )
            if notification:
                notifications.append(notification)

        logger.info(f"تم إنشاء {len(notifications)} إشعار لتغيير حالة الطلب {order.order_number} من {old_status} إلى {new_status}")
        return notifications

    @classmethod
    def create_unique_group_notification(
        cls,
        title: str,
        message: str,
        notification_type: str,
        order_number: str = '',
        customer_name: str = '',
        priority: str = 'normal',
        target_users: list = None,
        created_by = None,
        related_object = None
    ):
        """
        إنشاء إشعار جماعي مرة واحدة فقط
        يتحقق من وجود إشعار مماثل قبل الإنشاء
        """
        try:
            # التحقق من وجود إشعار مماثل
            existing_notification = GroupNotification.objects.filter(
                notification_type=notification_type,
                order_number=order_number,
                customer_name=customer_name,
                title=title
            ).first()

            if existing_notification:
                logger.info(f"إشعار موجود بالفعل: {title} - {order_number}")
                return existing_notification

            # إنشاء إشعار جديد
            notification = GroupNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                order_number=order_number,
                customer_name=customer_name,
                priority=priority,
                created_by=created_by,
                related_object_id=related_object.pk if related_object else None,
                related_object_type=related_object.__class__.__name__ if related_object else ''
            )

            # إضافة المستخدمين المستهدفين
            if target_users:
                notification.target_users.set(target_users)

            logger.info(f"تم إنشاء إشعار جماعي جديد: {title} لـ {len(target_users) if target_users else 0} مستخدم")
            return notification

        except Exception as e:
            logger.error(f"خطأ في إنشاء الإشعار الجماعي: {str(e)}")
            return None

    @classmethod
    def notify_order_status_change_unique(cls, order, old_status, new_status, changed_by=None):
        """إشعار شامل لتغيير حالة الطلب مع منع التكرار"""

        # تحديد الرسالة حسب نوع التغيير
        status_messages = {
            'pending_approval': 'في انتظار الموافقة',
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد التصنيع',
            'ready_install': 'جاهز للتركيب',
            'completed': 'مكتمل',
            'delivered': 'تم التسليم',
            'rejected': 'مرفوض',
            'cancelled': 'ملغي',
        }

        old_status_text = status_messages.get(old_status, old_status)
        new_status_text = status_messages.get(new_status, new_status)

        # تحديد الأقسام المعنية حسب الحالة الجديدة
        departments_to_notify = []
        priority = 'normal'

        if new_status == 'pending_approval':
            departments_to_notify = ['manufacturing', 'administration']
            priority = 'high'
        elif new_status == 'in_progress':
            departments_to_notify = ['manufacturing', 'quality_control']
            priority = 'high'
        elif new_status == 'ready_install':
            departments_to_notify = ['installations', 'customer_service']
            priority = 'high'
        elif new_status == 'completed':
            departments_to_notify = ['installations', 'customer_service', 'administration', 'accounting']
            priority = 'normal'
        elif new_status == 'delivered':
            departments_to_notify = ['customer_service', 'administration', 'accounting']
            priority = 'normal'
        elif new_status == 'rejected':
            departments_to_notify = ['customer_service', 'administration']
            priority = 'high'
        elif new_status == 'cancelled':
            departments_to_notify = ['manufacturing', 'installations', 'customer_service', 'administration']
            priority = 'medium'

        # جمع المستخدمين المعنيين
        target_users = []

        # إضافة مستخدمي الأقسام المعنية
        for dept_code in departments_to_notify:
            try:
                from accounts.models import Department
                department = Department.objects.get(code=dept_code)
                dept_users = department.users.filter(is_active=True)
                target_users.extend(dept_users)
            except Department.DoesNotExist:
                logger.warning(f"القسم {dept_code} غير موجود")

        # إضافة البائع/منشئ الطلب
        if order.salesperson:
            try:
                # البحث عن المستخدم المرتبط بالبائع
                if hasattr(order.salesperson, 'user') and order.salesperson.user:
                    target_users.append(order.salesperson.user)
                elif hasattr(order.salesperson, 'created_by') and order.salesperson.created_by:
                    target_users.append(order.salesperson.created_by)
            except Exception as e:
                logger.warning(f"لا يمكن العثور على مستخدم للبائع {order.salesperson}: {e}")

        # إضافة منشئ الطلب إذا كان موجوداً
        if hasattr(order, 'created_by') and order.created_by:
            target_users.append(order.created_by)

        # إضافة المدير العام
        from accounts.models import User
        admin_users = User.objects.filter(is_superuser=True, is_active=True)
        target_users.extend(admin_users)

        # إزالة التكرارات واستبعاد من قام بالتغيير
        unique_users = list(set(target_users))
        if changed_by:
            unique_users = [user for user in unique_users if user != changed_by]

        # إنشاء الإشعار الجماعي
        title = f"تغيير حالة الطلب {order.order_number}"
        message = f"تم تغيير حالة طلب العميل {order.customer.name} من '{old_status_text}' إلى '{new_status_text}'"

        notification = cls.create_unique_group_notification(
            title=title,
            message=message,
            notification_type='order_status_changed',
            order_number=order.order_number,
            customer_name=order.customer.name,
            priority=priority,
            target_users=unique_users,
            created_by=changed_by,
            related_object=order
        )

        return notification
    
    @classmethod
    def notify_complaint_created(cls, complaint):
        """إشعار شكوى جديدة"""
        notifications = []
        
        # إشعار المسؤول المعين
        if complaint.assigned_to:
            notification = cls.create_complaint_notification(
                customer_name=complaint.customer.name,
                complaint_number=complaint.complaint_number,
                title=f'شكوى جديدة من {complaint.customer.name}',
                complaint_type='new',
                priority='high' if complaint.priority == 'urgent' else 'medium',
                recipient=complaint.assigned_to,
                related_object=complaint
            )
            if notification:
                notifications.append(notification)
        
        # إشعار قسم خدمة العملاء
        from accounts.models import Department
        try:
            customer_service = Department.objects.get(code='customer_service')
            users = customer_service.users.filter(is_active=True)
            
            for user in users:
                if user != complaint.assigned_to:  # تجنب الإشعار المكرر
                    notification = cls.create_complaint_notification(
                        customer_name=complaint.customer.name,
                        complaint_number=complaint.complaint_number,
                        title=f'شكوى جديدة من {complaint.customer.name}',
                        complaint_type='new',
                        priority='medium',
                        recipient=user,
                        related_object=complaint
                    )
                    if notification:
                        notifications.append(notification)
                        
        except Department.DoesNotExist:
            logger.warning("قسم خدمة العملاء غير موجود")
        
        return notifications
    
    @classmethod
    def notify_complaint_status_change(cls, complaint, old_status, new_status):
        """إشعار تغيير حالة الشكوى"""
        if not complaint.assigned_to:
            return None
            
        # تحديد نوع الإشعار
        complaint_type = 'in_progress'
        priority = 'medium'
        
        if new_status == 'resolved':
            complaint_type = 'resolved'
            priority = 'high'
        elif new_status == 'closed':
            complaint_type = 'closed'
            priority = 'low'
        elif new_status == 'escalated':
            complaint_type = 'escalated'
            priority = 'critical'
        
        # تحديد النص الجميل للحالة
        status_names = {
            'new': 'جديدة',
            'assigned': 'معينة',
            'in_progress': 'قيد المعالجة',
            'resolved': 'محلولة',
            'closed': 'مغلقة',
            'escalated': 'مصعدة'
        }
        
        status_text = status_names.get(new_status, new_status)
        
        return cls.create_complaint_notification(
            customer_name=complaint.customer.name,
            complaint_number=complaint.complaint_number,
            title=f'تحديث شكوى {complaint.customer.name} - {status_text}',
            complaint_type=complaint_type,
            priority=priority,
            recipient=complaint.assigned_to,
            related_object=complaint
        )
