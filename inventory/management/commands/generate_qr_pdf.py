"""
Management command to generate PDF with BaseProduct QR codes only
Optimized for smaller file size with compression
"""

import base64
import os
from io import BytesIO

# Arabic text support
import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from django.core.management.base import BaseCommand

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from inventory.models import BaseProduct


class Command(BaseCommand):
    help = "Generate PDF with BaseProduct QR codes (optimized for smaller file size)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            type=int,
            help="Generate PDF for specific category ID only",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="media/qr_codes/base_products_qr.pdf",
            help="Output file path",
        )
        parser.add_argument(
            "--compress",
            action="store_true",
            default=True,
            help="Enable PDF compression (default: True)",
        )

    def handle(self, *args, **options):
        category_id = options.get("category")
        output_path = options.get("output")
        compress = options.get("compress", True)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self.stdout.write(
            self.style.NOTICE("🔄 Starting BaseProduct QR PDF generation...")
        )
        self.stdout.write(
            f'   Compression: {"✅ Enabled" if compress else "❌ Disabled"}'
        )

        # Register Arabic font
        self.register_fonts()

        # ✅ Fetch ONLY BaseProducts (Active)
        base_products = (
            BaseProduct.objects.filter(is_active=True)
            .select_related("category")
            .order_by("code")
        )

        if category_id:
            base_products = base_products.filter(category_id=category_id)
            self.stdout.write(f"   Filtering by category ID: {category_id}")

        total_count = base_products.count()

        self.stdout.write(f"   Found {total_count} BaseProducts")

        if total_count == 0:
            self.stdout.write(self.style.WARNING("⚠️  No products found!"))
            return

        # Generate PDF
        self.generate_pdf(base_products, output_path, total_count, compress)

        self.stdout.write(
            self.style.SUCCESS(f"✅ PDF generated successfully: {output_path}")
        )

        # Get file size
        file_size = os.path.getsize(output_path)
        self.stdout.write(f"   File size: {file_size / 1024 / 1024:.2f} MB")
        self.stdout.write(
            f"   Average: {file_size / total_count / 1024:.2f} KB per product"
        )

    def register_fonts(self):
        try:
            # Prefer DejaVu Sans which supports BOTH Arabic and English well
            font_paths = [
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/noto/NotoSansArabic-Regular.ttf",
                "/usr/share/fonts/noto/NotoSansArabic-Bold.ttf",
                "static/fonts/NotoSansArabic-Regular.ttf",
                "static/fonts/NotoSansArabic-Bold.ttf",
            ]

            registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font_name = "Arabic"
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        self.stdout.write(
                            self.style.SUCCESS(f"Registered font: {font_path}")
                        )
                        registered = True
                        break
                    except Exception as e:
                        pass

            if not registered:
                self.stdout.write(
                    self.style.WARNING(
                        "No Arabic font found! Text may appear as squares."
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not register Arabic font: {e}")
            )

    def reshape_arabic(self, text):
        """Reshape Arabic text for proper display in PDF"""
        if not text:
            return ""
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except:
            return str(text)

    def generate_pdf(self, items, output_path, total_count, compress=True):
        """Generate the PDF with QR codes in 3x3cm grid with compression"""

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.5 * cm,
            leftMargin=0.5 * cm,
            topMargin=1.0 * cm,
            bottomMargin=1.0 * cm,
            # ✅ Enable compression
            compress=compress,
        )

        elements = []
        styles = getSampleStyleSheet()

        # Define styles
        try:
            title_style = ParagraphStyle(
                "ArabicTitle",
                parent=styles["Heading1"],
                fontName="Arabic",
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=15,
                leading=22,
            )
            arabic_normal = ParagraphStyle(
                "ArabicNormal",
                parent=styles["Normal"],
                fontName="Arabic",
                fontSize=10,
                alignment=TA_CENTER,
                leading=12,
            )
            product_name_style = ParagraphStyle(
                "ProductName",
                parent=styles["Normal"],
                fontName="Arabic",
                fontSize=8,  # Smaller for compactness
                alignment=TA_CENTER,
                leading=9,
                spaceBefore=1,
            )
        except:
            title_style = styles["Heading1"]
            arabic_normal = styles["Normal"]
            product_name_style = styles["Normal"]

        # Header
        title_text = self.reshape_arabic("رموز QR للمنتجات الأساسية - الخواجة")
        elements.append(Paragraph(title_text, title_style))

        count_text = self.reshape_arabic(f"إجمالي المنتجات: {total_count}")
        elements.append(Paragraph(count_text, arabic_normal))
        elements.append(Spacer(1, 10))

        # Grid Setup - 5 items per row
        ITEMS_PER_ROW = 5
        COL_WIDTH = 3.8 * cm

        table_data = []
        current_row = []
        processed = 0
        skipped = 0

        for item in items:
            processed += 1

            # Generate/Get QR
            if not item.qr_code_base64:
                item.generate_qr()
                try:
                    if hasattr(item, "save"):
                        item.save(update_fields=["qr_code_base64"])
                except:
                    pass

            qr_base64 = item.qr_code_base64

            if qr_base64:
                try:
                    qr_data = base64.b64decode(qr_base64)
                    qr_buffer = BytesIO(qr_data)

                    # ✅ 3cm x 3cm QR with lazy loading
                    qr_img = Image(qr_buffer, width=3 * cm, height=3 * cm, lazy=2)

                    # Name Truncation
                    raw_name = item.name
                    if len(raw_name) > 20:  # Shorter truncation
                        raw_name = raw_name[:20] + ".."
                    name_text = self.reshape_arabic(raw_name)

                    # Code display
                    code_text = f"<font size='7'>{item.code}</font>"

                    # Inner Cell Content: QR Image + Code + Name
                    cell_content = [
                        [qr_img],
                        [Paragraph(code_text, product_name_style)],
                        [Paragraph(f"<b>{name_text}</b>", product_name_style)],
                    ]

                    # Inner Table for alignment
                    inner_table = Table(cell_content, colWidths=[3.2 * cm])
                    inner_table.setStyle(
                        TableStyle(
                            [
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 1),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                            ]
                        )
                    )

                    current_row.append(inner_table)

                except Exception as e:
                    self.stdout.write(f"⚠️  Error processing {item.code}: {e}")
                    skipped += 1
                    current_row.append("")
            else:
                skipped += 1
                current_row.append("")

            # Row Management
            if len(current_row) == ITEMS_PER_ROW:
                table_data.append(current_row)
                current_row = []

            if processed % 100 == 0:
                self.stdout.write(f"   Processed {processed}/{total_count}...")

        # Fill last row
        if current_row:
            while len(current_row) < ITEMS_PER_ROW:
                current_row.append("")
            table_data.append(current_row)

        # Build Main Grid Table
        if table_data:
            main_table = Table(table_data, colWidths=[COL_WIDTH] * ITEMS_PER_ROW)
            main_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ]
                )
            )
            elements.append(main_table)

        if skipped > 0:
            self.stdout.write(f"   ⚠️  Skipped {skipped} items without QR codes")

        self.stdout.write("   Building PDF document...")
        doc.build(elements)
