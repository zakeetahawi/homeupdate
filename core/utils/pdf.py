"""
أدوات مشتركة لتوليد ملفات PDF باستخدام weasyprint.
WARN-002: خط Noto Naskh Arabic لا يمكن تحميله في weasyprint.

يوفر هذا الملف:
- دالة get_arabic_font_css(): تُرجع CSS مع @font-face للخطوط العربية
- دالة get_font_config(): تُرجع كائن FontConfiguration
- دالة build_pdf(html_string, extra_css=""): تنشئ PDF مع دعم الخطوط العربية
"""

from io import BytesIO

ARABIC_FONT_CSS = """
@font-face {
    font-family: 'Noto Naskh Arabic';
    font-style: normal;
    font-weight: 400;
    src: url('file:///usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf') format('truetype');
}
@font-face {
    font-family: 'Noto Naskh Arabic';
    font-style: normal;
    font-weight: 500;
    src: url('file:///usr/share/fonts/noto/NotoNaskhArabic-Medium.ttf') format('truetype');
}
@font-face {
    font-family: 'Noto Naskh Arabic';
    font-style: normal;
    font-weight: 600;
    src: url('file:///usr/share/fonts/noto/NotoNaskhArabic-SemiBold.ttf') format('truetype');
}
@font-face {
    font-family: 'Noto Naskh Arabic';
    font-style: normal;
    font-weight: 700;
    src: url('file:///usr/share/fonts/noto/NotoNaskhArabic-Bold.ttf') format('truetype');
}
"""

PDF_BASE_CSS = ARABIC_FONT_CSS + """
@page {
    size: A4;
    margin: 1.5cm;
}
body {
    font-family: 'Noto Naskh Arabic', 'Arial', Tahoma, sans-serif;
    direction: rtl;
    text-align: right;
}
"""


def get_arabic_font_css(extra_css: str = "") -> str:
    """إرجاع CSS الكامل مع @font-face للخطوط العربية."""
    return PDF_BASE_CSS + ("\n" + extra_css if extra_css else "")


def get_font_config():
    """إرجاع كائن FontConfiguration من weasyprint."""
    from weasyprint.text.fonts import FontConfiguration
    return FontConfiguration()


def build_pdf(
    html_string: str,
    extra_css: str = "",
    base_url: str = None,
) -> bytes:
    """
    إنشاء ملف PDF من HTML مع دعم الخطوط العربية.

    Args:
        html_string: محتوى HTML
        extra_css: CSS إضافي يُضاف بعد الـ CSS الأساسي
        base_url: مسار أساسي لتحديد المسارات النسبية (اختياري)

    Returns:
        bytes: محتوى ملف PDF
    """
    from weasyprint import CSS, HTML

    font_config = get_font_config()
    full_css = get_arabic_font_css(extra_css)

    html_obj = HTML(string=html_string, base_url=base_url)
    pdf_bytes = html_obj.write_pdf(
        stylesheets=[CSS(string=full_css, font_config=font_config)],
        font_config=font_config,
    )
    return pdf_bytes
