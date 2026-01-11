# Generated migration for advanced design fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("public", "0004_create_default_qr_settings"),
    ]

    operations = [
        # Typography Settings
        migrations.AddField(
            model_name="qrdesignsettings",
            name="font_family",
            field=models.CharField(
                max_length=100,
                default="Cairo",
                verbose_name="نوع الخط",
                help_text="مثل: Cairo, Tajawal, Almarai",
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="font_size_base",
            field=models.IntegerField(
                default=16, verbose_name="حجم الخط الأساسي", help_text="بالبكسل (12-24)"
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="font_weight_heading",
            field=models.CharField(
                max_length=20,
                default="700",
                choices=[
                    ("400", "عادي"),
                    ("500", "متوسط"),
                    ("600", "سميك"),
                    ("700", "سميك جداً"),
                    ("800", "أكثر سماكة"),
                ],
                verbose_name="وزن خط العناوين",
            ),
        ),
        # Spacing & Sizing
        migrations.AddField(
            model_name="qrdesignsettings",
            name="card_padding",
            field=models.IntegerField(
                default=30,
                verbose_name="مسافة داخلية للبطاقة",
                help_text="بالبكسل (20-50)",
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="card_max_width",
            field=models.IntegerField(
                default=450,
                verbose_name="أقصى عرض للبطاقة",
                help_text="بالبكسل (400-600)",
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="element_spacing",
            field=models.IntegerField(
                default=20,
                verbose_name="المسافة بين العناصر",
                help_text="بالبكسل (10-40)",
            ),
        ),
        # Shadow & Effects
        migrations.AddField(
            model_name="qrdesignsettings",
            name="card_shadow_intensity",
            field=models.CharField(
                max_length=20,
                default="medium",
                choices=[
                    ("none", "بدون ظل"),
                    ("light", "خفيف"),
                    ("medium", "متوسط"),
                    ("strong", "قوي"),
                ],
                verbose_name="قوة ظل البطاقة",
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="enable_gradient_bg",
            field=models.BooleanField(default=True, verbose_name="تفعيل تدرج الخلفية"),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="enable_hover_effects",
            field=models.BooleanField(
                default=True, verbose_name="تفعيل تأثيرات التمرير"
            ),
        ),
        # Button Styles
        migrations.AddField(
            model_name="qrdesignsettings",
            name="button_style",
            field=models.CharField(
                max_length=20,
                default="rounded",
                choices=[
                    ("square", "مربع"),
                    ("rounded", "زوايا منحنية"),
                    ("pill", "حبة دواء"),
                ],
                verbose_name="شكل الأزرار",
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="button_size",
            field=models.CharField(
                max_length=20,
                default="medium",
                choices=[
                    ("small", "صغير"),
                    ("medium", "متوسط"),
                    ("large", "كبير"),
                ],
                verbose_name="حجم الأزرار",
            ),
        ),
        # Price Display
        migrations.AddField(
            model_name="qrdesignsettings",
            name="price_font_size",
            field=models.IntegerField(
                default=48, verbose_name="حجم خط السعر", help_text="بالبكسل (32-72)"
            ),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="show_price_badge",
            field=models.BooleanField(
                default=True,
                verbose_name="إظهار شارة السعر",
                help_text="خلفية مميزة لقسم السعر",
            ),
        ),
        # Product Card Enhancements
        migrations.AddField(
            model_name="qrdesignsettings",
            name="show_product_icon",
            field=models.BooleanField(default=True, verbose_name="إظهار أيقونة المنتج"),
        ),
        migrations.AddField(
            model_name="qrdesignsettings",
            name="show_category_badge",
            field=models.BooleanField(default=True, verbose_name="إظهار شارة التصنيف"),
        ),
    ]
