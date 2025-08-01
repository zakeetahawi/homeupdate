# Generated by Django 4.2.21 on 2025-07-19 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('installations', '0004_modificationerroranalysis_analyzed_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='installationschedule',
            name='scheduled_date',
            field=models.DateField(blank=True, null=True, verbose_name='تاريخ التركيب'),
        ),
        migrations.AlterField(
            model_name='installationschedule',
            name='scheduled_time',
            field=models.TimeField(blank=True, null=True, verbose_name='موعد التركيب'),
        ),
        migrations.AlterField(
            model_name='installationschedule',
            name='status',
            field=models.CharField(choices=[('needs_scheduling', 'بحاجة جدولة'), ('scheduled', 'مجدول'), ('in_installation', 'قيد التركيب'), ('completed', 'مكتمل'), ('cancelled', 'ملغي'), ('modification_required', 'يحتاج تعديل'), ('modification_in_progress', 'التعديل قيد التنفيذ'), ('modification_completed', 'التعديل مكتمل')], default='needs_scheduling', max_length=30, verbose_name='الحالة'),
        ),
    ]
