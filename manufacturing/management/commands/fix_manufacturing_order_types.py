"""
أمر Django لإصلاح أنواع أوامر التصنيع الفارغة أو الخاطئة
"""

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from manufacturing.models import ManufacturingOrder


class Command(BaseCommand):
    help = "إصلاح أنواع أوامر التصنيع الفارغة أو الخاطئة"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض المشاكل فقط بدون إصلاح",
        )
        parser.add_argument(
            "--year",
            type=int,
            help="السنة المراد فحصها (افتراضي: جميع السنوات)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        year = options.get("year")

        self.stdout.write(self.style.SUCCESS("=== فحص وإصلاح أنواع أوامر التصنيع ==="))

        # تطبيق فلتر السنة إذا تم تحديدها
        queryset = ManufacturingOrder.objects.all()
        if year:
            queryset = queryset.filter(order_date__year=year)
            self.stdout.write(f"فحص السنة: {year}")
        else:
            self.stdout.write("فحص جميع السنوات")

        # 1. فحص الأوامر الفارغة
        empty_orders = queryset.filter(order_type="")
        self.stdout.write(f"\nأوامر التصنيع بـ order_type فارغ: {empty_orders.count()}")

        fixed_count = 0

        if empty_orders.exists():
            self.stdout.write("\nتفاصيل الأوامر الفارغة:")

            for mfg in empty_orders:
                try:
                    # تحليل selected_types
                    selected_types = mfg.order.selected_types
                    parsed_types = json.loads(selected_types) if selected_types else []

                    # تحديد النوع المناسب
                    correct_type = self.determine_order_type(parsed_types)

                    self.stdout.write(
                        f"  طلب {mfg.order.order_number}: "
                        f"selected_types={selected_types}, "
                        f"النوع المطلوب={correct_type}"
                    )

                    if correct_type and not dry_run:
                        with transaction.atomic():
                            mfg.order_type = correct_type
                            mfg.save()
                            fixed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"    ✅ تم إصلاح الطلب {mfg.order.order_number}"
                                )
                            )
                    elif correct_type:
                        self.stdout.write(f"    🔧 سيتم إصلاحه إلى: {correct_type}")
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"    ⚠️  لا يمكن تحديد النوع المناسب")
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ❌ خطأ في معالجة الطلب {mfg.order.order_number}: {e}"
                        )
                    )

        # 2. فحص الأوامر غير المتطابقة
        self.stdout.write("\n=== فحص الأوامر غير المتطابقة ===")

        mismatched_orders = []
        for mfg in queryset.exclude(order_type=""):
            try:
                selected_types = mfg.order.selected_types
                parsed_types = json.loads(selected_types) if selected_types else []
                correct_type = self.determine_order_type(parsed_types)

                if correct_type and correct_type != mfg.order_type:
                    mismatched_orders.append((mfg, correct_type))

            except Exception:
                continue

        self.stdout.write(f"أوامر التصنيع غير المتطابقة: {len(mismatched_orders)}")

        if mismatched_orders:
            self.stdout.write("\nتفاصيل الأوامر غير المتطابقة:")

            for mfg, correct_type in mismatched_orders:
                self.stdout.write(
                    f"  طلب {mfg.order.order_number}: "
                    f"حالي={mfg.order_type}, صحيح={correct_type}"
                )

                if not dry_run:
                    with transaction.atomic():
                        mfg.order_type = correct_type
                        mfg.save()
                        fixed_count += 1
                        self.stdout.write(self.style.SUCCESS(f"    ✅ تم إصلاح النوع"))
                else:
                    self.stdout.write(f"    🔧 سيتم إصلاحه")

        # 3. إحصائيات نهائية
        self.stdout.write("\n=== الإحصائيات النهائية ===")

        if not dry_run and fixed_count > 0:
            # إعادة حساب الإحصائيات
            final_stats = self.get_statistics(queryset)
            self.display_statistics(final_stats)

            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 تم إصلاح {fixed_count} أمر تصنيع بنجاح!")
            )
        elif dry_run:
            current_stats = self.get_statistics(queryset)
            self.display_statistics(current_stats)

            total_issues = empty_orders.count() + len(mismatched_orders)
            if total_issues > 0:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️  يوجد {total_issues} مشكلة تحتاج إصلاح")
                )
                self.stdout.write("استخدم الأمر بدون --dry-run للإصلاح")
            else:
                self.stdout.write(self.style.SUCCESS("\n✅ لا توجد مشاكل!"))
        else:
            self.stdout.write("لا توجد مشاكل للإصلاح")

    def determine_order_type(self, parsed_types):
        """تحديد نوع أمر التصنيع من selected_types"""
        if not parsed_types:
            return None

        if "installation" in parsed_types:
            return "installation"
        elif "tailoring" in parsed_types:
            return "custom"
        elif "accessory" in parsed_types:
            return "accessory"
        else:
            return None

    def get_statistics(self, queryset):
        """حساب الإحصائيات"""
        from django.db.models import Count

        total = queryset.count()
        by_type = (
            queryset.values("order_type").annotate(count=Count("id")).order_by("-count")
        )

        return {"total": total, "by_type": list(by_type)}

    def display_statistics(self, stats):
        """عرض الإحصائيات"""
        self.stdout.write(f'إجمالي أوامر التصنيع: {stats["total"]}')
        self.stdout.write("التوزيع حسب النوع:")

        for item in stats["by_type"]:
            order_type = item["order_type"] or "فارغ"
            count = item["count"]

            if order_type == "installation":
                type_name = "تركيب"
            elif order_type == "custom":
                type_name = "تفصيل"
            elif order_type == "accessory":
                type_name = "اكسسوار"
            elif order_type == "فارغ":
                type_name = "فارغ"
            else:
                type_name = f"غير معروف ({order_type})"

            self.stdout.write(f"  {type_name}: {count}")
