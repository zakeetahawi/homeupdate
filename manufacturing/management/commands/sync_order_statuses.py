from django.core.management.base import BaseCommand
from django.db import transaction
from manufacturing.models import ManufacturingOrder
from orders.models import Order


class Command(BaseCommand):
    help = 'مزامنة حالات الطلبات مع حالات التصنيع'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            action='store_true',
            help='عرض التغييرات بدون تطبيقها',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='إجبار التحديث حتى لو كانت الحالات متطابقة',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write('🔄 بدء مزامنة حالات الطلبات مع التصنيع...')
        
        # الحصول على جميع أوامر التصنيع
        manufacturing_orders = ManufacturingOrder.objects.select_related('order').all()
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        with transaction.atomic():
            for mfg_order in manufacturing_orders:
                try:
                    order = mfg_order.order
                    if not order:
                        continue
                    
                    # تحديد الحالات الجديدة
                    order_status_mapping = {
                        'pending_approval': 'pending_approval',
                        'pending': 'pending',
                        'in_progress': 'in_progress',
                        'ready_install': 'ready_install',
                        'completed': 'completed',
                        'delivered': 'delivered',
                        'rejected': 'rejected',
                        'cancelled': 'cancelled',
                    }
                    
                    tracking_status_mapping = {
                        'pending_approval': 'factory',
                        'pending': 'factory',
                        'in_progress': 'factory',
                        'ready_install': 'ready',
                        'completed': 'ready',
                        'delivered': 'delivered',
                        'rejected': 'factory',
                        'cancelled': 'factory',
                    }
                    
                    installation_status_mapping = {
                        'pending_approval': 'needs_scheduling',
                        'pending': 'needs_scheduling', 
                        'in_progress': 'needs_scheduling',
                        'ready_install': 'scheduled',
                        'completed': 'completed',
                        'delivered': 'completed',
                        'rejected': 'needs_scheduling',
                        'cancelled': 'cancelled',
                    }
                    
                    new_order_status = order_status_mapping.get(mfg_order.status)
                    new_tracking_status = tracking_status_mapping.get(mfg_order.status)
                    new_installation_status = installation_status_mapping.get(mfg_order.status)
                    
                    # التحقق من الحاجة للتحديث
                    needs_update = (
                        force or
                        order.order_status != new_order_status or
                        order.tracking_status != new_tracking_status or
                        (mfg_order.order_type == 'installation' and order.installation_status != new_installation_status)
                    )
                    
                    if needs_update:
                        if not dry_run:
                            # تحديث الحالات
                            update_fields = {
                                'order_status': new_order_status,
                                'tracking_status': new_tracking_status
                            }
                            
                            if mfg_order.order_type == 'installation':
                                update_fields['installation_status'] = new_installation_status
                            
                            Order.objects.filter(pk=order.pk).update(**update_fields)
                            
                            # تحديث التركيبات المرتبطة
                            if mfg_order.order_type == 'installation' and new_installation_status:
                                try:
                                    from installations.models import InstallationSchedule
                                    InstallationSchedule.objects.filter(order=order).update(
                                        status=new_installation_status
                                    )
                                except ImportError:
                                    pass
                        
                        self.stdout.write(
                            f'✅ {order.order_number}: '
                            f'{order.order_status} → {new_order_status}, '
                            f'{order.tracking_status} → {new_tracking_status}'
                            + (f', {order.installation_status} → {new_installation_status}' 
                               if mfg_order.order_type == 'installation' else '')
                        )
                        updated_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'❌ خطأ في الطلب {order.order_number}: {str(e)}')
                    )
        
        # عرض النتائج
        self.stdout.write('\n📊 نتائج المزامنة:')
        self.stdout.write(f'✅ تم التحديث: {updated_count}')
        self.stdout.write(f'⏭️ تم التخطي: {skipped_count}')
        self.stdout.write(f'❌ أخطاء: {error_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ هذا كان اختبار فقط - لم يتم تطبيق التغييرات'))
        else:
            self.stdout.write(self.style.SUCCESS('🎉 تمت المزامنة بنجاح!'))
