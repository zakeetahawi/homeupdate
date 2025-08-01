# Generated by Django 4.2.21 on 2025-07-17 15:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('manufacturing', '0001_initial'),
        ('orders', '0005_order_related_inspection_type'),
        ('installations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstallationOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('installation_order_number', models.CharField(max_length=50, unique=True, verbose_name='رقم أمر التركيب')),
                ('status', models.CharField(choices=[('pending_approval', 'قيد الموافقة'), ('approved', 'موافق عليه'), ('ready_for_installation', 'جاهز للتركيب'), ('scheduled', 'مجدول'), ('in_progress', 'قيد التنفيذ'), ('completed', 'مكتمل'), ('cancelled', 'ملغي'), ('modification_required', 'يحتاج تعديل'), ('modification_in_progress', 'التعديل قيد التنفيذ'), ('modification_completed', 'التعديل مكتمل')], default='pending_approval', max_length=30, verbose_name='حالة أمر التركيب')),
                ('installation_address', models.TextField(verbose_name='عنوان التركيب')),
                ('installation_date', models.DateField(blank=True, null=True, verbose_name='تاريخ التركيب')),
                ('installation_time', models.TimeField(blank=True, null=True, verbose_name='موعد التركيب')),
                ('installation_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='تكلفة التركيب')),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='المبلغ المدفوع')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('completion_date', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الإكمال')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('assigned_team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='installations.installationteam', verbose_name='الفريق المكلف')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='تم الإنشاء بواسطة')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers.customer', verbose_name='العميل')),
                ('manufacturing_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='installation_orders', to='manufacturing.manufacturingorder', verbose_name='أمر التصنيع')),
                ('original_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='installation_orders', to='orders.order', verbose_name='الطلب الأصلي')),
            ],
            options={
                'verbose_name': 'أمر تركيب',
                'verbose_name_plural': 'أوامر التركيب',
                'ordering': ['-created_at'],
            },
        ),
    ]
