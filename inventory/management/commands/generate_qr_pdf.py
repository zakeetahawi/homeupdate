"""
Management command to generate a comprehensive PDF with all QR codes
Uses Arabic font support and matches qr-export page layout
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from inventory.models import Product
from io import BytesIO
import os
import base64

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# Arabic text support
import arabic_reshaper
from bidi.algorithm import get_display


class Command(BaseCommand):
    help = 'Generate comprehensive PDF with all product QR codes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=int,
            help='Generate PDF for specific category ID only',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='media/qr_codes/all_products_qr.pdf',
            help='Output file path',
        )

    def handle(self, *args, **options):
        category_id = options.get('category')
        output_path = options.get('output')
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.stdout.write(self.style.NOTICE('Starting PDF generation...'))
        
        # Register Arabic font
        try:
            # Prefer DejaVu Sans which supports BOTH Arabic and English well
            font_paths = [
                '/usr/share/fonts/TTF/DejaVuSans.ttf',
                '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/noto/NotoSansArabic-Regular.ttf',
                '/usr/share/fonts/noto/NotoSansArabic-Bold.ttf',
                '/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf',
                '/usr/share/fonts/noto/NotoKufiArabic-Regular.ttf',
            ]
            
            registered_font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        # Register as 'Arabic' to keep existing style references working
                        font_name = 'Arabic'
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        registered_font = font_path
                        self.stdout.write(self.style.SUCCESS(f'Registered font: {font_path} (supporting mixed text)'))
                        
                        # Register Bold variant if available (hacky but works for this simple use)
                        if 'DejaVuSans.ttf' in font_path:
                            bold_path = font_path.replace('.ttf', '-Bold.ttf')
                            if os.path.exists(bold_path):
                                pdfmetrics.registerFont(TTFont('Arabic-Bold', bold_path))
                        break
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Failed to register {font_path}: {e}'))
            
            if not registered_font:
                self.stdout.write(self.style.WARNING('No Arabic font found! Text may appear as squares.'))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not register Arabic font: {e}'))
        
        # Get products
        products = Product.objects.select_related('category').filter(
            code__isnull=False
        ).exclude(code='').order_by('name')
        
        if category_id:
            products = products.filter(category_id=category_id)
            self.stdout.write(f'Filtering by category ID: {category_id}')
        
        total_count = products.count()
        self.stdout.write(f'Found {total_count} products to include')
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No products found!'))
            return
        
        # Generate PDF
        self.generate_pdf(products, output_path, total_count)
        
        self.stdout.write(self.style.SUCCESS(f'PDF generated successfully: {output_path}'))
        
        # Get file size
        file_size = os.path.getsize(output_path)
        self.stdout.write(f'File size: {file_size / 1024 / 1024:.2f} MB')

    def reshape_arabic(self, text):
        """Reshape Arabic text for proper display in PDF"""
        if not text:
            return ""
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except:
            return str(text)

    def generate_pdf(self, products, output_path, total_count):
        """Generate the PDF with QR codes in 3-column layout"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Define styles
        try:
            # Arabic Title Style
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Heading1'],
                fontName='Arabic',
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=20,
                leading=22
            )
            # Normal Arabic Text Style
            arabic_normal = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_CENTER,
                leading=12
            )
            # Product Name Style
            product_name_style = ParagraphStyle(
                'ProductName',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=11,
                alignment=TA_CENTER,
                leading=14,
                spaceAfter=2
            )
            # Code Style
            code_style = ParagraphStyle(
                'ProductCode',
                parent=styles['Normal'],
                fontName='Helvetica', # Codes are usually English/Numbers
                fontSize=9,
                alignment=TA_CENTER,
                textColor='#666666',
                leading=12
            )
            # Price Style
            price_style = ParagraphStyle(
                'ProductPrice',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_CENTER,
                textColor='#f39c12', # Orange/Gold color like web
                leading=12
            )
        except:
            # Fallback if font registration failed
            title_style = styles['Heading1']
            arabic_normal = styles['Normal']
            product_name_style = styles['Normal']
            code_style = styles['Normal']
            price_style = styles['Normal']
        
        # Title
        title_text = self.reshape_arabic('رموز QR للمنتجات - الخواجة')
        elements.append(Paragraph(title_text, title_style))
        
        # Count info
        count_text = self.reshape_arabic(f'إجمالي المنتجات: {total_count}')
        elements.append(Paragraph(count_text, arabic_normal))
        elements.append(Spacer(1, 20))
        
        # Process products in batches
        batch_size = 500
        processed = 0
        
        for start in range(0, total_count, batch_size):
            batch = products[start:start + batch_size]
            table_data = []
            current_row = []
            
            for product in batch:
                processed += 1
                
                # Get QR code
                if product.qr_code_base64:
                    qr_data = base64.b64decode(product.qr_code_base64)
                else:
                    # Generate if missing
                    product.generate_qr()
                    product.save(update_fields=['qr_code_base64'])
                    if product.qr_code_base64:
                        qr_data = base64.b64decode(product.qr_code_base64)
                    else:
                        continue
                
                if qr_data:
                    qr_buffer = BytesIO(qr_data)
                    qr_img = Image(qr_buffer, width=3.5*cm, height=3.5*cm)
                    
                    # Prepare Texts
                    name_text = self.reshape_arabic(product.name[:30] + '...' if len(product.name) > 30 else product.name)
                    code_text = product.code
                    
                    # Currency formatting
                    currency = dict(Product.CURRENCY_CHOICES).get(product.currency, product.currency)
                    price_text = self.reshape_arabic(f"{product.price} {currency}")
                    
                    # Create cell content (QR + Name + Code + Price)
                    # We use a nested table to draw a border around each item
                    item_content = [
                        [qr_img],
                        [Paragraph(f"<b>{name_text}</b>", product_name_style)],
                        [Paragraph(code_text, code_style)],
                        [Paragraph(f"<b>{price_text}</b>", price_style)],
                    ]
                    
                    cell_table = Table(item_content, colWidths=[5.5*cm])
                    cell_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        # Border around the item card
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.Color(0.9, 0.9, 0.9)), 
                        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.98, 0.98, 0.98)), # Slight grey background
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ]))
                    
                    current_row.append(cell_table)
                
                # After 3 items, add row to table
                if len(current_row) == 3:
                    table_data.append(current_row)
                    current_row = []
                
                # Progress update every 500 products
                if processed % 500 == 0:
                    self.stdout.write(f'Processed {processed}/{total_count} products...')
            
            # Add remaining items in last row
            if current_row:
                while len(current_row) < 3:
                    current_row.append('')
                table_data.append(current_row)
            
            # Create table for this batch
            if table_data:
                col_width = 6.3*cm # Slightly wider columns
                table = Table(table_data, colWidths=[col_width, col_width, col_width])
                table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    # No grid for the main table, just spacing
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                elements.append(table)
                # Add page break between batches if needed, or rely on automatic flow
                # elements.append(PageBreak()) 
        
        # Build PDF
        self.stdout.write('Building PDF document...')
        doc.build(elements)
