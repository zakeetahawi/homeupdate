# Generated manually on 2025-11-27

from django.db import migrations, models
import django.db.models.deletion
import orders.models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0071_add_invoice_image_field'),
    ]

    operations = [
        # إنشاء جدول صور الفاتورة للطلبات
        migrations.CreateModel(
            name='OrderInvoiceImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(
                    upload_to='invoices/images/%Y/%m/',
                    validators=[orders.models.validate_invoice_image],
                    verbose_name='صورة الفاتورة'
                )),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الرفع')),
                ('order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoice_images',
                    to='orders.order',
                    verbose_name='الطلب'
                )),
            ],
            options={
                'verbose_name': 'صورة فاتورة',
                'verbose_name_plural': 'صور الفواتير',
                'ordering': ['uploaded_at'],
            },
        ),
        # إنشاء جدول صور الفاتورة للمسودات
        migrations.CreateModel(
            name='DraftOrderInvoiceImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(
                    upload_to='invoices/images/drafts/%Y/%m/',
                    verbose_name='صورة الفاتورة'
                )),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الرفع')),
                ('draft_order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoice_images_new',
                    to='orders.draftorder',
                    verbose_name='مسودة الطلب'
                )),
            ],
            options={
                'verbose_name': 'صورة فاتورة مسودة',
                'verbose_name_plural': 'صور فواتير المسودات',
                'ordering': ['uploaded_at'],
            },
        ),
    ]
