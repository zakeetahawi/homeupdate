# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0004_create_welcome_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappmessagetemplate',
            name='header',
            field=models.CharField(blank=True, help_text='نص العنوان (اختياري، حد أقصى 60 حرف)', max_length=60, null=True, verbose_name='العنوان (Header)'),
        ),
        migrations.AddField(
            model_name='whatsappmessagetemplate',
            name='footer',
            field=models.CharField(blank=True, help_text='نص التذييل (اختياري، حد أقصى 60 حرف)', max_length=60, null=True, verbose_name='التذييل (Footer)'),
        ),
        migrations.AlterField(
            model_name='whatsappmessagetemplate',
            name='template_text',
            field=models.TextField(help_text='استخدم {{customer_name}}, {{order_number}}, إلخ للمتغيرات (أقواس مزدوجة)', verbose_name='نص القالب'),
        ),
    ]
