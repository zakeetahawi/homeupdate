"""
أمر Django لتنظيف أكواد المنتجات - إزالة الأصفار البادئة
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Product


class Command(BaseCommand):
    help = 'إزالة الأصفار البادئة من أكواد المنتجات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض التغييرات بدون تطبيقها',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.WARNING('تنظيف أكواد المنتجات'))
        self.stdout.write('=' * 60)
        
        # البحث عن المنتجات بأكواد تبدأ بصفر
        products_to_update = Product.objects.filter(code__regex=r'^0[0-9]+')
        total = products_to_update.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ لا توجد منتجات تحتاج تنظيف'))
            return
        
        self.stdout.write(f'\n📊 وجدت {total} منتج بأكواد تبدأ بصفر\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 وضع المعاينة - لن يتم تطبيق التغييرات\n'))
        
        updated = 0
        skipped = 0
        deleted = 0
        errors = 0
        
        for product in products_to_update:
            old_code = product.code
            new_code = old_code.lstrip('0') or '0'
            
            # تخطي إذا كان الكود لم يتغير
            if old_code == new_code:
                skipped += 1
                continue
            
            # التحقق من وجود تعارض
            conflict = Product.objects.filter(code=new_code).exclude(id=product.id).first()
            
            if conflict:
                # يوجد تعارض - احذف المنتج الذي يبدأ بصفر
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'🗑️  سيتم حذف: {old_code:15} (تعارض مع {new_code}) - {product.name[:40]}'
                        )
                    )
                else:
                    try:
                        product_name = product.name
                        product.delete()
                        self.stdout.write(
                            self.style.WARNING(
                                f'🗑️  تم حذف: {old_code:15} (تعارض مع {new_code}) - {product_name[:40]}'
                            )
                        )
                        deleted += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'❌ خطأ في حذف {old_code}: {str(e)}')
                        )
                        errors += 1
                continue
            
            if dry_run:
                self.stdout.write(f'  {old_code:15} → {new_code:15} ({product.name[:40]})')
            else:
                try:
                    with transaction.atomic():
                        product.code = new_code
                        product.save(update_fields=['code'])
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ {old_code:15} → {new_code:15}')
                        )
                        updated += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ خطأ في {old_code}: {str(e)}')
                    )
                    errors += 1
        
        # الملخص
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 الملخص:'))
        self.stdout.write(f'  إجمالي المنتجات: {total}')
        if not dry_run:
            self.stdout.write(f'  ✅ تم التحديث: {updated}')
            if deleted > 0:
                self.stdout.write(self.style.WARNING(f'  🗑️  تم الحذف: {deleted}'))
        self.stdout.write(f'  ⏭️  تم التخطي: {skipped}')
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ أخطاء: {errors}'))
        self.stdout.write('=' * 60)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n⚠️  لتطبيق التغييرات، شغّل الأمر بدون --dry-run')
            )
