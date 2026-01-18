"""
خدمة توليد ملفات PDF للعقود
"""

import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from ..contract_models import ContractCurtain, ContractPrintLog, ContractTemplate
from ..models import Order


class ContractGenerationService:
    """خدمة توليد العقود"""

    def __init__(self, order, template=None):
        """
        تهيئة الخدمة

        Args:
            order: الطلب المراد إنشاء عقد له
            template: قالب العقد (اختياري، سيتم استخدام القالب الافتراضي إذا لم يُحدد)
        """
        self.order = order
        self.template = template or ContractTemplate.get_default_template()

        if not self.template:
            raise ValueError("لا يوجد قالب عقد متاح")

    def generate_html(self):
        """توليد HTML للعقد"""
        # الحصول على ستائر العقد
        curtains = ContractCurtain.objects.filter(order=self.order).order_by("sequence")

        # حساب عدد أيام التشغيل
        working_days = None
        if self.order.expected_delivery_date and self.order.created_at:
            # تحويل created_at إلى date للمقارنة الصحيحة
            created_date = (
                self.order.created_at.date()
                if hasattr(self.order.created_at, "date")
                else self.order.created_at
            )
            delivery_date = self.order.expected_delivery_date
            # التأكد من أن كلاهما date objects
            if hasattr(delivery_date, "date"):
                delivery_date = delivery_date.date()
            delta = delivery_date - created_date
            working_days = delta.days

        # حساب إجمالي الأمتار من جميع الأقمشة
        total_meters = 0
        # تعريف ترتيب الأولويات للأقمشة
        fabric_priority = {
            "heavy": 1,
            "light": 2,
            "blackout": 3,
            "additional": 4,
            "extra": 4,
        }

        # حساب إجمالي الأمتار وترتيب الأقمشة
        total_meters = 0
        for curtain in curtains:
            fabrics_list = list(curtain.fabrics.all())

            # دالة مساعدة للحصول على الأولوية
            def get_priority(fabric):
                return fabric_priority.get(
                    fabric.fabric_type, 99
                )  # 99 للأنواع غير المعروفة لتظهر في النهاية

            # ترتيب الأقمشة
            curtain.sorted_fabrics = sorted(fabrics_list, key=get_priority)

            for fabric in fabrics_list:
                # تجاهل الأحزمة من إجمالي الأمتار لأنها تظهر كقطع في الجدول
                if "حزام" in fabric.display_name:
                    continue
                total_meters += float(fabric.meters) if fabric.meters else 0

        # تجميع المواد لملخص المواد (Material Summary)
        materials_map = {}

        # 1. تجميع الأقمشة
        for curtain in curtains:
            for fabric in curtain.fabrics.all():
                name = fabric.display_name
                # تحديد المفتاح (الاسم)
                if not name:
                    continue

                # تخطي الأحزمة
                if "حزام" in name:
                    continue

                # تمييز الأقمشة الخارجية
                # تمييز الأقمشة الخارجية
                is_external = False

                # التحقق إذا كان العقد لطلب نهائي أو مسودة
                if curtain.order:  # طلب نهائي
                    # في الطلب النهائي، القماش الخارجي ليس له order_item
                    if not fabric.order_item and fabric.fabric_name:
                        is_external = True
                elif curtain.draft_order:  # مسودة
                    # في المسودة، القماش الخارجي ليس له draft_order_item
                    if not fabric.draft_order_item and fabric.fabric_name:
                        is_external = True
                else:
                    # حالة احتياطية (Check fallback)
                    if (
                        not fabric.order_item
                        and not fabric.draft_order_item
                        and fabric.fabric_name
                    ):
                        is_external = True

                if is_external:
                    name = f"{name} (خارجي)"

                if name not in materials_map:
                    materials_map[name] = {
                        "name": name,
                        "type": "fabric",
                        "total_quantity": 0.0,
                        "sewing_quantity": 0.0,
                        "unit": "متر" if fabric.meters > 0 else "قطعة",
                        "usages": [],
                    }

                # حساب الكمية
                fabric_qty = float(fabric.meters)
                materials_map[name]["total_quantity"] += fabric_qty

                # حساب كمية الخياطة بناءً على نوع التفصيل
                # الأنواع التي تحسب الضعف
                DOUBLE_QTY_TYPES = [
                    "ويف كبسولة",
                    "تكسير يمين شمال",
                    "تكسير يمين",
                    "تكسير شمال",
                    "كالونات 9 سنتم",
                ]

                t_type_display = fabric.get_tailoring_type_display()
                multiplier = 1
                if t_type_display in DOUBLE_QTY_TYPES:
                    multiplier = 2

                materials_map[name]["sewing_quantity"] += fabric_qty * multiplier

                # إضافة وصف الاستخدام (الشرح الذكي)
                type_display = fabric.get_fabric_type_display()
                usage_desc = f"{type_display} في {curtain.room_name}"
                materials_map[name]["usages"].append(usage_desc)

                # تخزين نوع القماش لاستخدامه في البادج (نأخذ أول نوع نجده لهذا الاسم)
                if "fabric_type" not in materials_map[name] and fabric.fabric_type:
                    materials_map[name]["fabric_type"] = fabric.fabric_type

                # محاولة الحصول على بيانات التصنيع (رقم الإذن والشنطة)
                # نحتاج الوصول إلى OrderItem المرتبط
                try:
                    # استيراد هنا لتجنب Circular Import
                    from manufacturing.models import ManufacturingOrderItem

                    order_item = fabric.order_item
                    if order_item:
                        # البحث عن عنصر تصنيع مرتبط
                        mf_items = ManufacturingOrderItem.objects.filter(
                            order_item=order_item
                        )

                        for mf_item in mf_items:
                            if mf_item.permit_number:
                                if "permits" not in materials_map[name]:
                                    materials_map[name]["permits"] = set()
                                materials_map[name]["permits"].add(
                                    mf_item.permit_number
                                )

                            if mf_item.bag_number:
                                if "bags" not in materials_map[name]:
                                    materials_map[name]["bags"] = set()
                                materials_map[name]["bags"].add(mf_item.bag_number)
                except Exception as e:
                    pass

                # تجميع أنواع التفصيل
                if fabric.tailoring_type:
                    if "tailoring_types" not in materials_map[name]:
                        materials_map[name]["tailoring_types"] = set()
                    materials_map[name]["tailoring_types"].add(t_type_display)

        # لا تفعل شيئًا للإكسسوارات (User requested to exclude accessories)
        # تم إزالة كود تجميع الإكسسوارات

        # معالجة الشرح الذكي النهائي وحساب المجموع
        materials_summary = []
        grand_total_quantity = 0
        grand_total_sewing = 0

        for key, item in materials_map.items():
            # تجميع الاستخدامات: "ثقيل في : مجلس، صالة"
            usage_by_type = {}
            for usage in item["usages"]:
                if " في " in usage:
                    u_type, u_room = usage.split(" في ", 1)
                else:
                    u_type, u_room = "استخدام", usage

                if u_type not in usage_by_type:
                    usage_by_type[u_type] = []
                usage_by_type[u_type].append(u_room)

            final_descriptions = []
            for u_type, rooms in usage_by_type.items():
                unique_rooms = sorted(list(set(rooms)))
                rooms_str = "، ".join(unique_rooms)
                final_descriptions.append(f"{u_type} في: {rooms_str}")

            item["smart_description"] = " - ".join(final_descriptions)

            # تنسيق أرقام الأذونات والشنط
            if "permits" in item and item["permits"]:
                item["permits_str"] = "، ".join(sorted(list(item["permits"])))

            if "bags" in item and item["bags"]:
                item["bags_str"] = "، ".join(sorted(list(item["bags"])))

            # المجاميع الكلية
            grand_total_quantity += item["total_quantity"]
            grand_total_sewing += item["sewing_quantity"]

            # تحويل أنواع التفصيل لقائمة
            if "tailoring_types" in item:
                item["tailoring_types_list"] = sorted(list(item["tailoring_types"]))
            else:
                item["tailoring_types_list"] = []

            materials_summary.append(item)

        # ترتيب الملخص
        materials_summary.sort(key=lambda x: x["name"])

        # جلب خط الإنتاج
        production_line_name = ""
        try:
            mfg_order = self.order.manufacturing_orders.first()
            if mfg_order and mfg_order.production_line:
                production_line_name = mfg_order.production_line.name
        except Exception:
            pass

        # تجهيز البيانات للقالب
        context = {
            "order": self.order,
            "customer": self.order.customer,
            "production_line_name": production_line_name,
            "curtains": curtains,
            "materials_summary": materials_summary,
            "grand_total_quantity": grand_total_quantity,
            "grand_total_sewing": grand_total_sewing,
            "template": self.template,
            "settings": self.template,  # إضافة settings للوصول إلى بيانات الشركة
            "working_days": working_days,  # إضافة عدد أيام التشغيل
            "total_meters": total_meters,  # إجمالي الأمتار
            "MEDIA_URL": settings.MEDIA_URL,  # إضافة MEDIA_URL
            "MEDIA_ROOT": settings.MEDIA_ROOT,  # إضافة MEDIA_ROOT
            "company_name": self.template.company_name,
            "company_logo": self.template.company_logo,
            "company_address": self.template.company_address,
            "company_phone": self.template.company_phone,
            "company_email": self.template.company_email,
            "company_website": self.template.company_website,
            "company_tax_number": self.template.company_tax_number,
            "company_commercial_register": self.template.company_commercial_register,
            "primary_color": self.template.primary_color,
            "secondary_color": self.template.secondary_color,
            "accent_color": self.template.accent_color,
            "font_family": self.template.font_family,
            "font_size": self.template.font_size,
            "header_text": self.template.header_text,
            "footer_text": self.template.footer_text,
            "terms_text": self.template.terms_text,
        }

        # استخدام القالب الجديد
        html_content = render_to_string("orders/contract_template.html", context)

        return html_content

    def generate_pdf(self):
        """
        توليد ملف PDF للعقد - محسّن للأداء

        Returns:
            BytesIO: ملف PDF
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            # توليد HTML
            html_content = self.generate_html()

            # إعداد الخطوط - محسّن
            font_config = FontConfiguration()

            # CSS إضافي من القالب
            css_content = self.template.css_styles if self.template.css_styles else ""

            # CSS أساسي للعقد - مناسب لصفحة عمودية
            base_css = """
            @page {
                size: A4 portrait;
                margin: 1.5cm;
            }
            body {
                font-family: 'Arial', 'Segoe UI', Tahoma, sans-serif;
                font-size: 9px;
                direction: rtl;
                text-align: right;
                color: #000;
            }
            """

            # دمج CSS - CSS الإضافي من القالب فقط إذا كان موجوداً
            if css_content:
                full_css = base_css + "\n" + css_content
            else:
                full_css = base_css

            # توليد PDF مع تحسينات الأداء
            pdf_file = BytesIO()

            # استخدام base_url بشكل صحيح
            base_url = settings.MEDIA_ROOT if hasattr(settings, "MEDIA_ROOT") else None

            HTML(string=html_content, base_url=base_url).write_pdf(
                pdf_file,
                stylesheets=[CSS(string=full_css, font_config=font_config)],
                font_config=font_config,
                # تحسينات الأداء
                optimize_images=True,  # تحسين الصور
            )

            pdf_file.seek(0)
            file_size = len(pdf_file.getvalue())
            logger.info(
                f"✅ PDF generated successfully - Size: {file_size / 1024:.2f} KB"
            )

            return pdf_file

        except Exception as e:
            logger.error(f"❌ Error generating PDF: {str(e)}", exc_info=True)
            raise

    def save_contract_to_order(self, user=None):
        """
        حفظ العقد في الطلب

        Args:
            user: المستخدم الذي قام بإنشاء العقد

        Returns:
            bool: True إذا تم الحفظ بنجاح
        """
        try:
            # توليد PDF
            pdf_file = self.generate_pdf()

            # التحقق من حجم الملف (الذهاب لنهاية الملف للحصول على الحجم)
            pdf_file.seek(0, 2)  # الذهاب لنهاية الملف
            file_size = pdf_file.tell()
            pdf_file.seek(0)  # العودة للبداية

            if not pdf_file or file_size == 0:
                import logging

                logger = logging.getLogger(__name__)
                logger.error("فشل توليد PDF - الملف فارغ")
                return False

            # تجهيز اسم العميل للملف (إزالة المسافات والأحرف الخاصة)
            customer_name = ""
            if self.order.customer:
                # تنظيف اسم العميل: إزالة المسافات والأحرف الخاصة
                customer_name = (
                    self.order.customer.name.replace(" ", "_")
                    .replace("/", "_")
                    .replace("\\", "_")
                )
                # الحد من طول اسم العميل
                if len(customer_name) > 30:
                    customer_name = customer_name[:30]

            # إضافة timestamp لتجنب مشاكل cache المتصفح
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # اسم الملف مع timestamp لضمان اسم فريد في كل مرة
            if customer_name:
                filename = f"contract_{self.order.order_number}_{customer_name}_{timestamp}.pdf"
            else:
                # في حالة عدم وجود عميل، استخدم رقم الطلب مع timestamp
                filename = f"contract_{self.order.order_number}_{timestamp}.pdf"

            # المسار الكامل للملف
            full_path = os.path.join(settings.MEDIA_ROOT, "contracts", filename)

            # إنشاء المجلد إذا لم يكن موجوداً
            contract_dir = os.path.join(settings.MEDIA_ROOT, "contracts")
            os.makedirs(contract_dir, exist_ok=True)

            # حذف جميع الملفات القديمة لنفس الطلب (تنظيف)
            if os.path.exists(contract_dir):
                prefix = f"contract_{self.order.order_number}_"
                deleted_count = 0
                for old_file in os.listdir(contract_dir):
                    if old_file.startswith(prefix) and old_file.endswith(".pdf"):
                        try:
                            old_file_path = os.path.join(contract_dir, old_file)
                            if os.path.isfile(old_file_path):
                                os.remove(old_file_path)
                                deleted_count += 1
                        except Exception as e:
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.warning(f"فشل حذف الملف القديم {old_file}: {e}")

                if deleted_count > 0:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"🗑️ تم حذف {deleted_count} ملف قديم للطلب {self.order.order_number}"
                    )

            # حفظ الملف في الطلب
            pdf_file.seek(0)  # التأكد من أن المؤشر في بداية الملف
            self.order.contract_file.save(
                filename, ContentFile(pdf_file.read()), save=True
            )

            # التحقق من أن الملف تم حفظه بنجاح
            if not self.order.contract_file or not os.path.exists(
                self.order.contract_file.path
            ):
                import logging

                logger = logging.getLogger(__name__)
                logger.error("فشل حفظ ملف العقد - الملف غير موجود بعد الحفظ")
                return False

            # تسجيل عملية الإنشاء
            ContractPrintLog.objects.create(
                order=self.order,
                template=self.template,
                printed_by=user,
                print_type="auto",
            )

            # تحديث عداد استخدام القالب
            self.template.increment_usage()

            return True

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في حفظ العقد: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def generate_contract_for_order(order_id, template_id=None, user=None):
        """
        توليد عقد لطلب معين

        Args:
            order_id: معرف الطلب
            template_id: معرف القالب (اختياري)
            user: المستخدم

        Returns:
            bool: True إذا تم التوليد بنجاح
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"📝 بدء توليد العقد للطلب #{order_id}")

        try:
            order = Order.objects.get(id=order_id)
            logger.info(f"✅ تم العثور على الطلب {order.order_number}")
            template = None

            if template_id:
                template = ContractTemplate.objects.get(id=template_id)

            service = ContractGenerationService(order, template)
            return service.save_contract_to_order(user)

        except Order.DoesNotExist:
            logger.error(f"❌ الطلب {order_id} غير موجود")
            return False
        except ContractTemplate.DoesNotExist:
            logger.error(f"❌ القالب {template_id} غير موجود")
            return False
        except Exception as e:
            logger.error(
                f"❌ خطأ في توليد العقد للطلب {order_id}: {str(e)}", exc_info=True
            )
            return False
