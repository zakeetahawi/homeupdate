"""
سكريبت تلقائي لمزامنة خطوط الإنتاج وربط أوامر التصنيع
يقرأ الإعدادات الحالية تلقائياً وينفذها حرفياً
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from manufacturing.models import ProductionLine, ManufacturingOrder
from collections import defaultdict
import json


class Command(BaseCommand):
    help = 'مزامنة خطوط الإنتاج وربط أوامر التصنيع بناءً على الإعدادات الحالية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم تنفيذه بدون تطبيق التغييرات',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='فرض التحديث حتى لو كانت الطلبات مرتبطة بخطوط أخرى',
        )
        parser.add_argument(
            '--backup-settings',
            action='store_true',
            help='إنشاء نسخة احتياطية من الإعدادات الحالية',
        )
        parser.add_argument(
            '--create-missing-lines',
            action='store_true',
            help='إنشاء خطوط إنتاج جديدة للأنواع غير المدعومة',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.backup_settings = options['backup_settings']
        
        self.stdout.write(self.style.SUCCESS('🚀 بدء مزامنة خطوط الإنتاج...'))
        
        if self.backup_settings:
            self.create_backup()
        
        # قراءة الإعدادات الحالية
        current_settings = self.read_current_settings()
        
        # عرض الإعدادات المقروءة
        self.display_current_settings(current_settings)
        
        # تحليل أوامر التصنيع
        orders_analysis = self.analyze_manufacturing_orders()
        
        # عرض التحليل
        self.display_orders_analysis(orders_analysis)
        
        # تطبيق المزامنة
        if not self.dry_run:
            self.apply_synchronization(current_settings, orders_analysis)
        else:
            self.stdout.write(self.style.WARNING('🔍 وضع المعاينة - لن يتم تطبيق أي تغييرات'))
            self.preview_synchronization(current_settings, orders_analysis)

    def create_backup(self):
        """إنشاء نسخة احتياطية من الإعدادات"""
        self.stdout.write('📋 إنشاء نسخة احتياطية من الإعدادات...')
        
        backup_data = {
            'production_lines': [],
            'orders_assignment': {}
        }
        
        # نسخ خطوط الإنتاج
        for line in ProductionLine.objects.all():
            backup_data['production_lines'].append({
                'id': line.id,
                'name': line.name,
                'description': line.description,
                'is_active': line.is_active,
                'capacity_per_day': line.capacity_per_day,
                'priority': line.priority,
                'supported_order_types': line.supported_order_types,
            })
        
        # نسخ ربط الطلبات
        for order in ManufacturingOrder.objects.filter(production_line__isnull=False):
            backup_data['orders_assignment'][order.id] = {
                'production_line_id': order.production_line.id,
                'production_line_name': order.production_line.name,
            }
        
        # حفظ النسخة الاحتياطية
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'production_lines_backup_{timestamp}.json'
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(self.style.SUCCESS(f'✅ تم حفظ النسخة الاحتياطية: {backup_file}'))

    def read_current_settings(self):
        """قراءة الإعدادات الحالية لخطوط الإنتاج"""
        settings = {}
        
        for line in ProductionLine.objects.filter(is_active=True).order_by('-priority'):
            settings[line.id] = {
                'name': line.name,
                'description': line.description,
                'priority': line.priority,
                'capacity_per_day': line.capacity_per_day,
                'supported_order_types': line.supported_order_types or [],
                'is_active': line.is_active,
                'object': line
            }
        
        return settings

    def display_current_settings(self, settings):
        """عرض الإعدادات الحالية"""
        self.stdout.write('\n📋 الإعدادات الحالية لخطوط الإنتاج:')
        self.stdout.write('=' * 60)
        
        for line_id, config in settings.items():
            self.stdout.write(f'\n🏭 {config["name"]} (ID: {line_id})')
            self.stdout.write(f'   📝 الوصف: {config["description"]}')
            self.stdout.write(f'   ⭐ الأولوية: {config["priority"]}')
            self.stdout.write(f'   📊 الطاقة اليومية: {config["capacity_per_day"] or "غير محدد"}')
            self.stdout.write(f'   🏷️  الأنواع المدعومة: {config["supported_order_types"]}')
            self.stdout.write(f'   ✅ نشط: {config["is_active"]}')

    def analyze_manufacturing_orders(self):
        """تحليل أوامر التصنيع الحالية"""
        analysis = {
            'total_orders': 0,
            'assigned_orders': 0,
            'unassigned_orders': 0,
            'orders_by_type': defaultdict(int),
            'orders_by_status': defaultdict(int),
            'mismatched_assignments': [],
        }
        
        all_orders = ManufacturingOrder.objects.all()
        analysis['total_orders'] = all_orders.count()
        
        for order in all_orders:
            # تحليل الأنواع
            order_type = order.order_type or 'غير محدد'
            analysis['orders_by_type'][order_type] += 1
            
            # تحليل الحالات
            analysis['orders_by_status'][order.status] += 1
            
            # تحليل الربط
            if order.production_line:
                analysis['assigned_orders'] += 1
                
                # فحص التطابق مع إعدادات خط الإنتاج
                line = order.production_line
                if line.supported_order_types and order.order_type:
                    if order.order_type not in line.supported_order_types:
                        analysis['mismatched_assignments'].append({
                            'order_id': order.id,
                            'order_code': order.manufacturing_code,
                            'order_type': order.order_type,
                            'line_name': line.name,
                            'line_supported_types': line.supported_order_types
                        })
            else:
                analysis['unassigned_orders'] += 1
        
        return analysis

    def display_orders_analysis(self, analysis):
        """عرض تحليل أوامر التصنيع"""
        self.stdout.write('\n📊 تحليل أوامر التصنيع:')
        self.stdout.write('=' * 60)

        self.stdout.write(f'📦 إجمالي الطلبات: {analysis["total_orders"]}')
        self.stdout.write(f'🔗 طلبات مرتبطة: {analysis["assigned_orders"]}')
        self.stdout.write(f'❌ طلبات غير مرتبطة: {analysis["unassigned_orders"]}')

        self.stdout.write('\n📋 توزيع الأنواع:')
        for order_type, count in analysis['orders_by_type'].items():
            self.stdout.write(f'   • {order_type}: {count}')

        self.stdout.write('\n📈 توزيع الحالات:')
        for status, count in analysis['orders_by_status'].items():
            status_display = dict(ManufacturingOrder.STATUS_CHOICES).get(status, status)
            self.stdout.write(f'   • {status_display}: {count}')

        if analysis['mismatched_assignments']:
            self.stdout.write(f'\n⚠️  طلبات مرتبطة بخطوط غير متطابقة: {len(analysis["mismatched_assignments"])}')
            for mismatch in analysis['mismatched_assignments'][:5]:  # عرض أول 5 فقط
                self.stdout.write(
                    f'   • {mismatch["order_code"]}: نوع {mismatch["order_type"]} '
                    f'في خط {mismatch["line_name"]} (يدعم: {mismatch["line_supported_types"]})'
                )
            if len(analysis['mismatched_assignments']) > 5:
                self.stdout.write(f'   ... و {len(analysis["mismatched_assignments"]) - 5} أخرى')

    def preview_synchronization(self, settings, analysis):
        """معاينة ما سيتم تنفيذه"""
        self.stdout.write('\n🔍 معاينة المزامنة:')
        self.stdout.write('=' * 60)

        # تحليل التوزيع المقترح
        proposed_distribution = self.calculate_proposed_distribution(settings, analysis)

        for line_id, config in settings.items():
            line_name = config['name']
            supported_types = config['supported_order_types']

            if line_id in proposed_distribution:
                proposed_count = proposed_distribution[line_id]['total']
                type_breakdown = proposed_distribution[line_id]['by_type']

                self.stdout.write(f'\n🏭 {line_name}:')
                self.stdout.write(f'   📋 الأنواع المدعومة: {supported_types}')
                self.stdout.write(f'   📦 الطلبات المقترحة: {proposed_count}')

                for order_type, count in type_breakdown.items():
                    self.stdout.write(f'      • {order_type}: {count}')

    def calculate_proposed_distribution(self, settings, analysis):
        """حساب التوزيع المقترح للطلبات بذكاء"""
        distribution = {}

        # ترتيب خطوط الإنتاج حسب الأولوية
        sorted_lines = sorted(settings.items(), key=lambda x: x[1]['priority'], reverse=True)

        # تجميع الخطوط حسب الأنواع المدعومة
        lines_by_type = defaultdict(list)
        for line_id, config in sorted_lines:
            supported_types = config['supported_order_types']
            if supported_types:
                for order_type in supported_types:
                    lines_by_type[order_type].append((line_id, config))

        # توزيع ذكي للطلبات
        for line_id, config in sorted_lines:
            distribution[line_id] = {
                'total': 0,
                'by_type': defaultdict(int)
            }

            supported_types = config['supported_order_types']

            if supported_types:
                for order_type in supported_types:
                    if order_type in analysis['orders_by_type']:
                        total_orders = analysis['orders_by_type'][order_type]
                        supporting_lines = lines_by_type[order_type]

                        if supporting_lines:
                            # توزيع حسب الأولوية
                            line_priority = config['priority']
                            total_priority = sum(line[1]['priority'] for line in supporting_lines)

                            # حساب النسبة بناءً على الأولوية
                            if total_priority > 0:
                                ratio = line_priority / total_priority
                                assigned_count = int(total_orders * ratio)
                            else:
                                assigned_count = total_orders // len(supporting_lines)

                            distribution[line_id]['by_type'][order_type] = assigned_count
                            distribution[line_id]['total'] += assigned_count
            else:
                # إذا لم يحدد أنواع، يحصل على الطلبات غير المصنفة
                unassigned_types = set(analysis['orders_by_type'].keys()) - set().union(*[config['supported_order_types'] for config in settings.values() if config['supported_order_types']])
                for order_type in unassigned_types:
                    count = analysis['orders_by_type'][order_type]
                    distribution[line_id]['by_type'][order_type] = count
                    distribution[line_id]['total'] += count

        return distribution

    def apply_synchronization(self, settings, analysis):
        """تطبيق المزامنة الفعلية"""
        self.stdout.write('\n🔄 تطبيق المزامنة...')

        with transaction.atomic():
            # إحصائيات التحديث
            updated_count = 0
            created_assignments = 0
            fixed_mismatches = 0

            # ترتيب خطوط الإنتاج حسب الأولوية
            sorted_lines = sorted(settings.items(), key=lambda x: x[1]['priority'], reverse=True)

            # تطبيق الربط حسب الأولوية والأنواع المدعومة
            for line_id, config in sorted_lines:
                line = config['object']
                supported_types = config['supported_order_types']

                self.stdout.write(f'\n🔄 معالجة خط: {config["name"]}')

                if supported_types:
                    # ربط الطلبات من الأنواع المدعومة
                    for order_type in supported_types:
                        orders_to_assign = ManufacturingOrder.objects.filter(
                            order_type=order_type
                        )

                        if not self.force:
                            # فقط الطلبات غير المرتبطة أو المرتبطة بخطوط غير متطابقة
                            orders_to_assign = orders_to_assign.filter(
                                models.Q(production_line__isnull=True) |
                                ~models.Q(production_line__supported_order_types__contains=[order_type])
                            )

                        count = orders_to_assign.update(production_line=line)
                        if count > 0:
                            self.stdout.write(f'   ✅ تم ربط {count} طلب من نوع {order_type}')
                            updated_count += count

                else:
                    # إذا لم يحدد أنواع، يمكنه التعامل مع الطلبات غير المرتبطة
                    unassigned_orders = ManufacturingOrder.objects.filter(production_line__isnull=True)
                    count = unassigned_orders.update(production_line=line)
                    if count > 0:
                        self.stdout.write(f'   ✅ تم ربط {count} طلب غير مرتبط')
                        updated_count += count

            # إصلاح الحالات (جاهز للتركيب = مكتمل)
            ready_orders = ManufacturingOrder.objects.filter(status='ready_install')
            if ready_orders.exists():
                self.stdout.write(f'\n🔧 تحديث حالة "جاهز للتركيب" إلى "مكتمل"...')
                ready_count = ready_orders.count()
                ready_orders.update(status='completed')
                self.stdout.write(f'   ✅ تم تحديث {ready_count} طلب')

            # عرض النتائج النهائية
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS('✅ تمت المزامنة بنجاح!'))
            self.stdout.write(f'📊 إجمالي الطلبات المحدثة: {updated_count}')

            # إحصائيات نهائية
            final_analysis = self.analyze_manufacturing_orders()
            self.stdout.write(f'📦 طلبات مرتبطة الآن: {final_analysis["assigned_orders"]}')
            self.stdout.write(f'❌ طلبات غير مرتبطة: {final_analysis["unassigned_orders"]}')

            if final_analysis['mismatched_assignments']:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  لا تزال هناك {len(final_analysis["mismatched_assignments"])} '
                        'طلبات مرتبطة بخطوط غير متطابقة'
                    )
                )
            else:
                self.stdout.write(self.style.SUCCESS('✅ جميع الطلبات مرتبطة بخطوط متطابقة!'))
