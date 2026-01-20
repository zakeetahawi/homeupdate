"""
Management command to recalculate prices for unpaid items
أمر إداري لإعادة حساب الأسعار للعناصر غير المدفوعة
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from factory_accounting.models import (
    CardMeasurementSplit,
    FactoryAccountingSettings,
    FactoryCard,
)


class Command(BaseCommand):
    help = 'إعادة حساب الأسعار للعناصر غير المدفوعة بناءً على الإعدادات الحالية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cutters',
            action='store_true',
            help='إعادة حساب تكاليف القصاص فقط',
        )
        parser.add_argument(
            '--tailors',
            action='store_true',
            help='إعادة حساب تكاليف الخياطين فقط',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم تحديثه دون تطبيق التغييرات',
        )

    def handle(self, *args, **options):
        settings = FactoryAccountingSettings.get_settings()
        
        dry_run = options.get('dry_run', False)
        cutters_only = options.get('cutters', False)
        tailors_only = options.get('tailors', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 وضع المعاينة - لن يتم تطبيق أي تغييرات'))
        
        total_updated = 0
        
        # Recalculate cutter costs
        if not tailors_only:
            self.stdout.write('\n📊 إعادة حساب تكاليف القصاص...')
            unpaid_cards = FactoryCard.objects.filter(
                Q(status='pending') | Q(status='in_production')
            ).exclude(status='paid')
            
            cutter_count = 0
            for card in unpaid_cards:
                old_cost = card.total_cutter_cost
                new_cost = card.total_billable_meters * settings.default_cutter_rate
                
                if old_cost != new_cost:
                    if dry_run:
                        self.stdout.write(
                            f'  • البطاقة {card.order_number}: {old_cost} ← {new_cost} ج.م'
                        )
                    else:
                        card.cutter_price = settings.default_cutter_rate
                        card.total_cutter_cost = new_cost
                        card.save(update_fields=['cutter_price', 'total_cutter_cost'])
                    cutter_count += 1
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ سيتم تحديث {cutter_count} بطاقة قصاص')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ تم تحديث {cutter_count} بطاقة قصاص')
                )
            total_updated += cutter_count
        
        # Recalculate tailor costs
        if not cutters_only:
            self.stdout.write('\n🧵 إعادة حساب تكاليف الخياطين...')
            unpaid_splits = CardMeasurementSplit.objects.filter(is_paid=False)
            
            tailor_count = 0
            for split in unpaid_splits:
                # Get current rate (custom or global)
                current_rate = split.tailor.get_rate()
                old_value = split.monetary_value
                new_value = split.share_amount * current_rate
                
                if old_value != new_value:
                    if dry_run:
                        self.stdout.write(
                            f'  • {split.tailor.name} - البطاقة {split.factory_card.order_number}: '
                            f'{old_value} ← {new_value} ج.م (سعر: {current_rate})'
                        )
                    else:
                        split.unit_rate = current_rate
                        split.monetary_value = new_value
                        split.save(update_fields=['unit_rate', 'monetary_value'])
                    tailor_count += 1
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ سيتم تحديث {tailor_count} تقسيم خياط')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ تم تحديث {tailor_count} تقسيم خياط')
                )
            total_updated += tailor_count
        
        # Final summary
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'🔍 المعاينة: سيتم تحديث {total_updated} عنصر إجمالاً'
                )
            )
            self.stdout.write(
                self.style.NOTICE(
                    'قم بتشغيل الأمر بدون --dry-run لتطبيق التغييرات'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ اكتمل! تم تحديث {total_updated} عنصر إجمالاً'
                )
            )
        self.stdout.write('='*60 + '\n')
