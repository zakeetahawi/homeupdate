# Generated migration - Create default QR Design Settings

from django.db import migrations


def create_default_settings(apps, schema_editor):
    """إنشاء إعدادات افتراضية"""
    QRDesignSettings = apps.get_model("public", "QRDesignSettings")

    # التحقق من عدم وجود إعدادات
    if not QRDesignSettings.objects.exists():
        QRDesignSettings.objects.create(
            logo_text="الخواجة",
            logo_text_en="Elkhawaga",
            color_primary="#d4af37",
            color_secondary="#b8860b",
            color_background="#1a1a2e",
            color_surface="#16213e",
            color_text="#ffffff",
            color_text_secondary="#c0c0c0",
            website_url="https://elkhawaga.com",
            complaint_url="/complaints/create/",
            complaint_button_text="إنشاء شكوى",
            complaint_button_text_en="Create Complaint",
            layout_style="modern",
            card_border_radius=15,
            enable_animations=True,
            enable_glassmorphism=True,
            show_logo=True,
            show_website_button=True,
            show_social_media=True,
            show_complaint_button=True,
            show_footer=True,
            footer_text="© 2025 الخواجة - جميع الحقوق محفوظة",
        )


def delete_settings(apps, schema_editor):
    """حذف الإعدادات عند التراجع"""
    QRDesignSettings = apps.get_model("public", "QRDesignSettings")
    QRDesignSettings.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("public", "0003_qrdesignsettings"),
    ]

    operations = [
        migrations.RunPython(create_default_settings, delete_settings),
    ]
