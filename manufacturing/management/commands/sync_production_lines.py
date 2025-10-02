"""
سكريبت تلقائي لمزامنة خطوط الإنتاج وربط أوامر التصنيع
يطبق منطق توزيع محدد بناءً على الفروع وأنواع الطلبات
"""

import json
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import models, transaction

from accounts.models import Branch
from manufacturing.models import ManufacturingOrder, ProductionLine


class Command(BaseCommand):
    help = (
        "مزامنة خطوط الإنتاج وربط أوامر التصنيع بناءً على قواعد الفروع والأنواع المحددة"
    )

    def get_distribution_rules(self):
        """تعريف قواعد التوزيع المحددة يدوياً - الإعدادات الافتراضية المحدثة"""
        return {
            "هاني رمسيس": {
                "branches": [
                    'فرع الازهر 3 "الحمزاوي"',
                    'فرع الازهر 2 "Karam"',
                    'فرع الازهر 1 "طلعت"',
                    "فرع القلعه",  # إضافة فرع القلعة
                ],
                "order_types": ["installation", "custom"],
                "special_rules": True,  # قواعد خاصة: تركيب من فروع محددة + تفصيل من جميع الفروع
                "description": "خط هاني رمسيس - تركيب من 4 فروع محددة + تفصيل من جميع الفروع",
            },
            "ايهاب يوسف": {
                "branches": [
                    "فرع المول",
                    "فرع النحاس",
                    "فرع المعادي",
                    "Open Air",
                    "east hup",
                ],
                "order_types": ["installation"],
                "description": "خط ايهاب يوسف - فروع محددة - طلبات تركيب فقط",
            },
            "ريمون فوزي": {
                "branches": [
                    "فرع اكتوبر",
                    "فرع الدقي",
                    "فرع فيصل",
                    "فرع الشيخ زايد",
                    "فرع الساحل الشمالي",
                    "فرع النزهه",
                ],
                "order_types": ["installation"],
                "description": "خط ريمون فوزي - فروع محددة - طلبات تركيب فقط",
            },
            "خط الاكسسوارات": {
                "branches": "all",  # جميع الفروع
                "order_types": ["accessory"],
                "description": "خط الاكسسوارات - جميع الفروع - طلبات اكسسوار فقط",
            },
        }

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم تنفيذه بدون تطبيق التغييرات",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="فرض التحديث حتى لو كانت الطلبات مرتبطة بخطوط أخرى",
        )
        parser.add_argument(
            "--backup-settings",
            action="store_true",
            help="إنشاء نسخة احتياطية من الإعدادات الحالية",
        )
        parser.add_argument(
            "--create-missing-lines",
            action="store_true",
            help="إنشاء خطوط إنتاج جديدة للأنواع غير المدعومة",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.force = options["force"]
        self.backup_settings = options["backup_settings"]

        self.stdout.write(self.style.SUCCESS("🚀 بدء مزامنة خطوط الإنتاج..."))

        if self.backup_settings:
            self.create_backup()

        # قراءة قواعد التوزيع المحددة
        distribution_rules = self.get_distribution_rules()

        # عرض قواعد التوزيع
        self.display_distribution_rules(distribution_rules)

        # تحليل أوامر التصنيع حسب الفروع والأنواع
        orders_analysis = self.analyze_orders_by_branches_and_types()

        # عرض التحليل
        self.display_detailed_analysis(orders_analysis)

        # إنشاء خطوط الإنتاج المفقودة
        self.create_missing_production_lines(distribution_rules)

        # تطبيق المزامنة الجديدة
        if not self.dry_run:
            self.apply_new_synchronization(distribution_rules, orders_analysis)
        else:
            self.stdout.write(
                self.style.WARNING("🔍 وضع المعاينة - لن يتم تطبيق أي تغييرات")
            )
            self.preview_new_synchronization(distribution_rules, orders_analysis)

    def create_backup(self):
        """إنشاء نسخة احتياطية من الإعدادات"""
        self.stdout.write("📋 إنشاء نسخة احتياطية من الإعدادات...")

        backup_data = {"production_lines": [], "orders_assignment": {}}

        # نسخ خطوط الإنتاج
        for line in ProductionLine.objects.all():
            backup_data["production_lines"].append(
                {
                    "id": line.id,
                    "name": line.name,
                    "description": line.description,
                    "is_active": line.is_active,
                    "capacity_per_day": line.capacity_per_day,
                    "priority": line.priority,
                    "supported_order_types": line.supported_order_types,
                }
            )

        # نسخ ربط الطلبات
        for order in ManufacturingOrder.objects.filter(production_line__isnull=False):
            backup_data["orders_assignment"][order.id] = {
                "production_line_id": order.production_line.id,
                "production_line_name": order.production_line.name,
            }

        # حفظ النسخة الاحتياطية
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"production_lines_backup_{timestamp}.json"

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"✅ تم حفظ النسخة الاحتياطية: {backup_file}")
        )

    def create_missing_production_lines(self, rules):
        """إنشاء خطوط الإنتاج المفقودة تلقائياً"""
        self.stdout.write("\n🏭 فحص وإنشاء خطوط الإنتاج المطلوبة...")

        created_count = 0
        for line_name, config in rules.items():
            try:
                line = ProductionLine.objects.get(name=line_name)
                self.stdout.write(f"   ✅ {line_name}: موجود مسبقاً")
            except ProductionLine.DoesNotExist:
                # إنشاء خط الإنتاج الجديد
                line = ProductionLine.objects.create(
                    name=line_name,
                    description=config["description"],
                    is_active=True,
                    priority=self.get_default_priority(line_name),
                    supported_order_types=config["order_types"],
                )

                # ربط الفروع إذا كانت محددة
                if config["branches"] != "all":
                    for branch_name in config["branches"]:
                        try:
                            branch = Branch.objects.get(name=branch_name)
                            line.branches.add(branch)
                        except Branch.DoesNotExist:
                            self.stdout.write(f"     ⚠️  فرع غير موجود: {branch_name}")

                line.save()
                created_count += 1
                self.stdout.write(f"   🆕 {line_name}: تم إنشاؤه")

        if created_count > 0:
            self.stdout.write(f"✅ تم إنشاء {created_count} خط إنتاج جديد")
        else:
            self.stdout.write("ℹ️  جميع خطوط الإنتاج موجودة مسبقاً")

    def get_default_priority(self, line_name):
        """تحديد الأولوية الافتراضية لخط الإنتاج"""
        priorities = {
            "هاني رمسيس": 7,  # أولوية عالية لأنه يتعامل مع نوعين من الطلبات
            "ايهاب يوسف": 5,
            "ريمون فوزي": 4,
            "خط الاكسسوارات": 1,
        }
        return priorities.get(line_name, 2)

    def display_distribution_rules(self, rules):
        """عرض قواعد التوزيع المحددة"""
        self.stdout.write("\n📋 قواعد التوزيع المحددة:")
        self.stdout.write("=" * 60)

        for line_name, config in rules.items():
            self.stdout.write(f"\n🏭 {line_name}:")
            self.stdout.write(f'   📝 الوصف: {config["description"]}')

            if config["branches"] == "all":
                self.stdout.write(f"   🌍 الفروع: جميع الفروع")
            else:
                self.stdout.write(f'   🏢 الفروع المحددة ({len(config["branches"])}):')
                for branch in config["branches"]:
                    self.stdout.write(f"      • {branch}")

            self.stdout.write(f'   🏷️  أنواع الطلبات: {config["order_types"]}')

    def analyze_orders_by_branches_and_types(self):
        """تحليل أوامر التصنيع حسب الفروع والأنواع"""
        analysis = {
            "total_orders": 0,
            "by_branch": defaultdict(lambda: defaultdict(int)),
            "by_type": defaultdict(int),
            "branch_totals": defaultdict(int),
            "unassigned_branches": 0,
            "unassigned_types": 0,
        }

        all_orders = ManufacturingOrder.objects.all()
        analysis["total_orders"] = all_orders.count()

        for order in all_orders:
            # تحديد الفرع
            branch_name = self.get_order_branch(order)

            # تحديد النوع
            order_type = order.order_type or "غير محدد"

            # إحصائيات
            analysis["by_branch"][branch_name][order_type] += 1
            analysis["by_type"][order_type] += 1
            analysis["branch_totals"][branch_name] += 1

            if branch_name == "غير محدد":
                analysis["unassigned_branches"] += 1
            if order_type == "غير محدد":
                analysis["unassigned_types"] += 1

        return analysis

    def get_order_branch(self, order):
        """استخراج اسم الفرع من أمر التصنيع"""
        branch = None
        if hasattr(order, "order") and order.order:
            if hasattr(order.order, "branch") and order.order.branch:
                branch = order.order.branch
            elif (
                hasattr(order.order, "customer")
                and order.order.customer
                and hasattr(order.order.customer, "branch")
            ):
                branch = order.order.customer.branch

        return branch.name if branch else "غير محدد"

    def display_detailed_analysis(self, analysis):
        """عرض التحليل المفصل للطلبات حسب الفروع والأنواع"""
        self.stdout.write("\n📊 تحليل مفصل للطلبات:")
        self.stdout.write("=" * 60)

        self.stdout.write(f'📦 إجمالي الطلبات: {analysis["total_orders"]}')
        self.stdout.write(f'❌ طلبات بدون فرع: {analysis["unassigned_branches"]}')
        self.stdout.write(f'❌ طلبات بدون نوع: {analysis["unassigned_types"]}')

        self.stdout.write("\n📋 توزيع الأنواع:")
        for order_type, count in analysis["by_type"].items():
            self.stdout.write(f"   • {order_type}: {count}")

        self.stdout.write("\n🏢 توزيع الفروع (أهم 10):")
        sorted_branches = sorted(
            analysis["branch_totals"].items(), key=lambda x: x[1], reverse=True
        )
        for branch_name, count in sorted_branches[:10]:
            self.stdout.write(f"   • {branch_name}: {count}")

            # عرض تفاصيل الأنواع لهذا الفرع
            branch_types = analysis["by_branch"][branch_name]
            type_details = ", ".join(
                [f"{otype}({count})" for otype, count in branch_types.items()]
            )
            self.stdout.write(f"     └─ {type_details}")

    def apply_new_synchronization(self, rules, analysis):
        """تطبيق المزامنة الجديدة بناءً على القواعد المحددة"""
        self.stdout.write("\n🔄 تطبيق المزامنة الجديدة...")

        with transaction.atomic():
            updated_count = 0

            # إعادة تعيين جميع الطلبات أولاً إذا كان في وضع force
            if self.force:
                self.stdout.write("\n🔄 إعادة تعيين جميع الطلبات...")
                reset_count = ManufacturingOrder.objects.all().update(
                    production_line=None
                )
                self.stdout.write(f"   ✅ تم إعادة تعيين {reset_count} طلب")

            # تطبيق كل قاعدة على حدة
            for line_name, config in rules.items():
                self.stdout.write(f"\n🔄 معالجة خط: {line_name}")

                # البحث عن خط الإنتاج
                try:
                    production_line = ProductionLine.objects.get(name=line_name)
                except ProductionLine.DoesNotExist:
                    self.stdout.write(f"   ❌ خط الإنتاج غير موجود: {line_name}")
                    continue

                # تحديد الطلبات المطابقة للقواعد
                matching_orders = self.get_matching_orders(config, analysis)

                if matching_orders.exists():
                    count = matching_orders.update(production_line=production_line)
                    self.stdout.write(f"   ✅ تم ربط {count} طلب")
                    updated_count += count
                else:
                    self.stdout.write(f"   ℹ️  لا توجد طلبات مطابقة")

            # إصلاح الحالات (جاهز للتركيب = مكتمل)
            ready_orders = ManufacturingOrder.objects.filter(status="ready_install")
            if ready_orders.exists():
                self.stdout.write(f'\n🔧 تحديث حالة "جاهز للتركيب" إلى "مكتمل"...')
                ready_count = ready_orders.count()
                ready_orders.update(status="completed")
                self.stdout.write(f"   ✅ تم تحديث {ready_count} طلب")

            # عرض النتائج النهائية
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("✅ تمت المزامنة الجديدة بنجاح!"))
            self.stdout.write(f"📊 إجمالي الطلبات المحدثة: {updated_count}")

            # إحصائيات نهائية
            final_analysis = self.analyze_orders_by_branches_and_types()
            unassigned_count = ManufacturingOrder.objects.filter(
                production_line__isnull=True
            ).count()
            self.stdout.write(f"❌ طلبات غير مرتبطة: {unassigned_count}")

    def get_matching_orders(self, config, analysis):
        """الحصول على الطلبات المطابقة لقواعد خط الإنتاج"""

        # قواعد خاصة لخط هاني رمسيس
        if config.get("special_rules") and "هاني رمسيس" in str(
            config.get("description", "")
        ):
            return self.get_hani_ramsis_orders(config)

        # القواعد العادية للخطوط الأخرى
        query = models.Q()

        # فلترة حسب النوع
        if config["order_types"]:
            query &= models.Q(order_type__in=config["order_types"])

        # فلترة حسب الفروع
        if config["branches"] != "all":
            # الحصول على IDs الفروع المحددة
            branch_ids = []
            for branch_name in config["branches"]:
                try:
                    branch = Branch.objects.get(name=branch_name)
                    branch_ids.append(branch.id)
                except Branch.DoesNotExist:
                    self.stdout.write(f"   ⚠️  فرع غير موجود: {branch_name}")

            if branch_ids:
                # البحث في الطلبات الأصلية
                branch_query = models.Q(order__branch_id__in=branch_ids) | models.Q(
                    order__customer__branch_id__in=branch_ids
                )
                query &= branch_query

        return ManufacturingOrder.objects.filter(query)

    def get_hani_ramsis_orders(self, config):
        """قواعد خاصة لخط هاني رمسيس: تركيب من فروع محددة + تفصيل من جميع الفروع"""

        # الحصول على IDs الفروع المحددة لطلبات التركيب
        branch_ids = []
        for branch_name in config["branches"]:
            try:
                branch = Branch.objects.get(name=branch_name)
                branch_ids.append(branch.id)
            except Branch.DoesNotExist:
                self.stdout.write(f"   ⚠️  فرع غير موجود: {branch_name}")

        # بناء الاستعلام المركب
        query = models.Q()

        if branch_ids:
            # طلبات التركيب من الفروع المحددة
            installation_query = models.Q(order_type="installation") & (
                models.Q(order__branch_id__in=branch_ids)
                | models.Q(order__customer__branch_id__in=branch_ids)
            )
            query |= installation_query

        # طلبات التفصيل من جميع الفروع
        custom_query = models.Q(order_type="custom")
        query |= custom_query

        return ManufacturingOrder.objects.filter(query)

    def preview_new_synchronization(self, rules, analysis):
        """معاينة المزامنة الجديدة"""
        self.stdout.write("\n🔍 معاينة المزامنة الجديدة:")
        self.stdout.write("=" * 60)

        total_preview = 0

        for line_name, config in rules.items():
            self.stdout.write(f"\n🏭 {line_name}:")

            # حساب الطلبات المطابقة
            matching_orders = self.get_matching_orders(config, analysis)
            count = matching_orders.count()
            total_preview += count

            self.stdout.write(f"   📦 الطلبات المطابقة: {count}")

            if count > 0:
                # عرض عينة من الطلبات
                sample_orders = matching_orders[:5]
                for order in sample_orders:
                    branch_name = self.get_order_branch(order)
                    self.stdout.write(
                        f"      • {order.manufacturing_code} - {branch_name} - {order.order_type}"
                    )

                if count > 5:
                    self.stdout.write(f"      ... و {count - 5} طلب آخر")

        self.stdout.write(f"\n📊 إجمالي الطلبات التي ستتم معالجتها: {total_preview}")

    def read_current_settings(self):
        """قراءة الإعدادات الحالية لخطوط الإنتاج"""
        settings = {}

        for line in ProductionLine.objects.filter(is_active=True).order_by("-priority"):
            settings[line.id] = {
                "name": line.name,
                "description": line.description,
                "priority": line.priority,
                "capacity_per_day": line.capacity_per_day,
                "supported_order_types": line.supported_order_types or [],
                "is_active": line.is_active,
                "object": line,
            }

        return settings

    def display_current_settings(self, settings):
        """عرض الإعدادات الحالية"""
        self.stdout.write("\n📋 الإعدادات الحالية لخطوط الإنتاج:")
        self.stdout.write("=" * 60)

        for line_id, config in settings.items():
            self.stdout.write(f'\n🏭 {config["name"]} (ID: {line_id})')
            self.stdout.write(f'   📝 الوصف: {config["description"]}')
            self.stdout.write(f'   ⭐ الأولوية: {config["priority"]}')
            self.stdout.write(
                f'   📊 الطاقة اليومية: {config["capacity_per_day"] or "غير محدد"}'
            )
            self.stdout.write(
                f'   🏷️  الأنواع المدعومة: {config["supported_order_types"]}'
            )
            self.stdout.write(f'   ✅ نشط: {config["is_active"]}')

    def analyze_manufacturing_orders(self):
        """تحليل أوامر التصنيع الحالية"""
        analysis = {
            "total_orders": 0,
            "assigned_orders": 0,
            "unassigned_orders": 0,
            "orders_by_type": defaultdict(int),
            "orders_by_status": defaultdict(int),
            "mismatched_assignments": [],
        }

        all_orders = ManufacturingOrder.objects.all()
        analysis["total_orders"] = all_orders.count()

        for order in all_orders:
            # تحليل الأنواع
            order_type = order.order_type or "غير محدد"
            analysis["orders_by_type"][order_type] += 1

            # تحليل الحالات
            analysis["orders_by_status"][order.status] += 1

            # تحليل الربط
            if order.production_line:
                analysis["assigned_orders"] += 1

                # فحص التطابق مع إعدادات خط الإنتاج
                line = order.production_line
                if line.supported_order_types and order.order_type:
                    if order.order_type not in line.supported_order_types:
                        analysis["mismatched_assignments"].append(
                            {
                                "order_id": order.id,
                                "order_code": order.manufacturing_code,
                                "order_type": order.order_type,
                                "line_name": line.name,
                                "line_supported_types": line.supported_order_types,
                            }
                        )
            else:
                analysis["unassigned_orders"] += 1

        return analysis

    def display_orders_analysis(self, analysis):
        """عرض تحليل أوامر التصنيع"""
        self.stdout.write("\n📊 تحليل أوامر التصنيع:")
        self.stdout.write("=" * 60)

        self.stdout.write(f'📦 إجمالي الطلبات: {analysis["total_orders"]}')
        self.stdout.write(f'🔗 طلبات مرتبطة: {analysis["assigned_orders"]}')
        self.stdout.write(f'❌ طلبات غير مرتبطة: {analysis["unassigned_orders"]}')

        self.stdout.write("\n📋 توزيع الأنواع:")
        for order_type, count in analysis["orders_by_type"].items():
            self.stdout.write(f"   • {order_type}: {count}")

        self.stdout.write("\n📈 توزيع الحالات:")
        for status, count in analysis["orders_by_status"].items():
            status_display = dict(ManufacturingOrder.STATUS_CHOICES).get(status, status)
            self.stdout.write(f"   • {status_display}: {count}")

        if analysis["mismatched_assignments"]:
            self.stdout.write(
                f'\n⚠️  طلبات مرتبطة بخطوط غير متطابقة: {len(analysis["mismatched_assignments"])}'
            )
            for mismatch in analysis["mismatched_assignments"][:5]:  # عرض أول 5 فقط
                self.stdout.write(
                    f'   • {mismatch["order_code"]}: نوع {mismatch["order_type"]} '
                    f'في خط {mismatch["line_name"]} (يدعم: {mismatch["line_supported_types"]})'
                )
            if len(analysis["mismatched_assignments"]) > 5:
                self.stdout.write(
                    f'   ... و {len(analysis["mismatched_assignments"]) - 5} أخرى'
                )

    def preview_synchronization(self, settings, analysis):
        """معاينة ما سيتم تنفيذه"""
        self.stdout.write("\n🔍 معاينة المزامنة:")
        self.stdout.write("=" * 60)

        # تحليل التوزيع المقترح
        proposed_distribution = self.calculate_proposed_distribution(settings, analysis)

        for line_id, config in settings.items():
            line_name = config["name"]
            supported_types = config["supported_order_types"]

            if line_id in proposed_distribution:
                proposed_count = proposed_distribution[line_id]["total"]
                type_breakdown = proposed_distribution[line_id]["by_type"]

                self.stdout.write(f"\n🏭 {line_name}:")
                self.stdout.write(f"   📋 الأنواع المدعومة: {supported_types}")
                self.stdout.write(f"   📦 الطلبات المقترحة: {proposed_count}")

                for order_type, count in type_breakdown.items():
                    self.stdout.write(f"      • {order_type}: {count}")

    def calculate_proposed_distribution(self, settings, analysis):
        """حساب التوزيع المقترح للطلبات بذكاء"""
        distribution = {}

        # ترتيب خطوط الإنتاج حسب الأولوية
        sorted_lines = sorted(
            settings.items(), key=lambda x: x[1]["priority"], reverse=True
        )

        # تجميع الخطوط حسب الأنواع المدعومة
        lines_by_type = defaultdict(list)
        for line_id, config in sorted_lines:
            supported_types = config["supported_order_types"]
            if supported_types:
                for order_type in supported_types:
                    lines_by_type[order_type].append((line_id, config))

        # توزيع ذكي للطلبات
        for line_id, config in sorted_lines:
            distribution[line_id] = {"total": 0, "by_type": defaultdict(int)}

            supported_types = config["supported_order_types"]

            if supported_types:
                for order_type in supported_types:
                    if order_type in analysis["orders_by_type"]:
                        total_orders = analysis["orders_by_type"][order_type]
                        supporting_lines = lines_by_type[order_type]

                        if supporting_lines:
                            # توزيع حسب الأولوية
                            line_priority = config["priority"]
                            total_priority = sum(
                                line[1]["priority"] for line in supporting_lines
                            )

                            # حساب النسبة بناءً على الأولوية
                            if total_priority > 0:
                                ratio = line_priority / total_priority
                                assigned_count = int(total_orders * ratio)
                            else:
                                assigned_count = total_orders // len(supporting_lines)

                            distribution[line_id]["by_type"][
                                order_type
                            ] = assigned_count
                            distribution[line_id]["total"] += assigned_count
            else:
                # إذا لم يحدد أنواع، يحصل على الطلبات غير المصنفة
                unassigned_types = set(analysis["orders_by_type"].keys()) - set().union(
                    *[
                        config["supported_order_types"]
                        for config in settings.values()
                        if config["supported_order_types"]
                    ]
                )
                for order_type in unassigned_types:
                    count = analysis["orders_by_type"][order_type]
                    distribution[line_id]["by_type"][order_type] = count
                    distribution[line_id]["total"] += count

        return distribution

    def apply_synchronization(self, settings, analysis):
        """تطبيق المزامنة الفعلية"""
        self.stdout.write("\n🔄 تطبيق المزامنة...")

        with transaction.atomic():
            # إحصائيات التحديث
            updated_count = 0
            created_assignments = 0
            fixed_mismatches = 0

            # ترتيب خطوط الإنتاج حسب الأولوية
            sorted_lines = sorted(
                settings.items(), key=lambda x: x[1]["priority"], reverse=True
            )

            # تطبيق الربط حسب الأولوية والأنواع المدعومة
            for line_id, config in sorted_lines:
                line = config["object"]
                supported_types = config["supported_order_types"]

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
                                models.Q(production_line__isnull=True)
                                | ~models.Q(
                                    production_line__supported_order_types__contains=[
                                        order_type
                                    ]
                                )
                            )

                        count = orders_to_assign.update(production_line=line)
                        if count > 0:
                            self.stdout.write(
                                f"   ✅ تم ربط {count} طلب من نوع {order_type}"
                            )
                            updated_count += count

                else:
                    # إذا لم يحدد أنواع، يمكنه التعامل مع الطلبات غير المرتبطة
                    unassigned_orders = ManufacturingOrder.objects.filter(
                        production_line__isnull=True
                    )
                    count = unassigned_orders.update(production_line=line)
                    if count > 0:
                        self.stdout.write(f"   ✅ تم ربط {count} طلب غير مرتبط")
                        updated_count += count

            # إصلاح الحالات (جاهز للتركيب = مكتمل)
            ready_orders = ManufacturingOrder.objects.filter(status="ready_install")
            if ready_orders.exists():
                self.stdout.write(f'\n🔧 تحديث حالة "جاهز للتركيب" إلى "مكتمل"...')
                ready_count = ready_orders.count()
                ready_orders.update(status="completed")
                self.stdout.write(f"   ✅ تم تحديث {ready_count} طلب")

            # عرض النتائج النهائية
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("✅ تمت المزامنة بنجاح!"))
            self.stdout.write(f"📊 إجمالي الطلبات المحدثة: {updated_count}")

            # إحصائيات نهائية
            final_analysis = self.analyze_manufacturing_orders()
            self.stdout.write(
                f'📦 طلبات مرتبطة الآن: {final_analysis["assigned_orders"]}'
            )
            self.stdout.write(
                f'❌ طلبات غير مرتبطة: {final_analysis["unassigned_orders"]}'
            )

            if final_analysis["mismatched_assignments"]:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  لا تزال هناك {len(final_analysis["mismatched_assignments"])} '
                        "طلبات مرتبطة بخطوط غير متطابقة"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("✅ جميع الطلبات مرتبطة بخطوط متطابقة!")
                )
