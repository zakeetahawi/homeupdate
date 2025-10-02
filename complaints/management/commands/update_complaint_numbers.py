"""
أمر Django لتحديث أرقام الشكاوى الموجودة لتتبع النظام الجديد
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from complaints.models import Complaint
from customers.models import Customer


class Command(BaseCommand):
    help = "تحديث أرقام الشكاوى الموجودة لتتبع النظام الجديد (كود العميل مسبوقاً بحرف P)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض التغييرات المقترحة دون تطبيقها",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="تطبيق التغييرات حتى لو كانت هناك شكاوى بأرقام جديدة",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(self.style.SUCCESS("🔄 بدء تحديث أرقام الشكاوى..."))

        # الحصول على جميع الشكاوى التي لا تتبع النظام الجديد
        complaints_to_update = (
            Complaint.objects.exclude(complaint_number__startswith="P")
            .select_related("customer")
            .order_by("created_at")
        )

        total_complaints = complaints_to_update.count()

        if total_complaints == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ جميع الشكاوى تتبع النظام الجديد بالفعل!")
            )
            return

        self.stdout.write(f"📊 تم العثور على {total_complaints} شكوى تحتاج تحديث")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 وضع المعاينة - لن يتم تطبيق التغييرات")
            )

        updated_count = 0
        errors_count = 0

        # تجميع الشكاوى حسب العميل لضمان التسلسل الصحيح
        customer_complaints = {}
        for complaint in complaints_to_update:
            customer_id = complaint.customer.id
            if customer_id not in customer_complaints:
                customer_complaints[customer_id] = []
            customer_complaints[customer_id].append(complaint)

        try:
            with transaction.atomic():
                for customer_id, complaints in customer_complaints.items():
                    customer = complaints[0].customer
                    customer_code = customer.code if customer.code else "UNKNOWN"

                    self.stdout.write(
                        f"\n👤 معالجة شكاوى العميل: {customer.name} (كود: {customer_code})"
                    )

                    # ترتيب الشكاوى حسب تاريخ الإنشاء
                    complaints.sort(key=lambda x: x.created_at)

                    for index, complaint in enumerate(complaints, 1):
                        old_number = complaint.complaint_number
                        new_number = f"P{customer_code}-{index:03d}"

                        # التحقق من عدم تكرار الرقم الجديد
                        if (
                            Complaint.objects.filter(complaint_number=new_number)
                            .exclude(pk=complaint.pk)
                            .exists()
                        ):

                            if not force:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"❌ الرقم {new_number} موجود بالفعل! "
                                        f"استخدم --force للتجاوز"
                                    )
                                )
                                errors_count += 1
                                continue
                            else:
                                # البحث عن رقم بديل
                                counter = index
                                while (
                                    Complaint.objects.filter(
                                        complaint_number=f"P{customer_code}-{counter:03d}"
                                    )
                                    .exclude(pk=complaint.pk)
                                    .exists()
                                ):
                                    counter += 1
                                new_number = f"P{customer_code}-{counter:03d}"

                        if dry_run:
                            self.stdout.write(f"  📝 {old_number} → {new_number}")
                        else:
                            complaint.complaint_number = new_number
                            complaint.save(update_fields=["complaint_number"])
                            self.stdout.write(f"  ✅ {old_number} → {new_number}")

                        updated_count += 1

                if dry_run:
                    # إلغاء المعاملة في وضع المعاينة
                    transaction.set_rollback(True)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ خطأ أثناء التحديث: {str(e)}"))
            return

        # عرض النتائج النهائية
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"🔍 معاينة مكتملة: {updated_count} شكوى ستتم معالجتها"
                )
            )
            self.stdout.write(
                self.style.WARNING("لتطبيق التغييرات، شغل الأمر بدون --dry-run")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✅ تم تحديث {updated_count} شكوى بنجاح!")
            )
            if errors_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ {errors_count} شكوى لم يتم تحديثها بسبب تضارب الأرقام"
                    )
                )

        self.stdout.write("=" * 50)
