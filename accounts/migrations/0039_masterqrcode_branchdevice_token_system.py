# Generated manually for Device Token + QR Master System

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def generate_initial_qr_master(apps, schema_editor):
    """
    توليد QR Master أولي للنظام
    """
    MasterQRCode = apps.get_model('accounts', 'MasterQRCode')
    User = apps.get_model('accounts', 'User')
    
    # البحث عن superuser أول
    superuser = User.objects.filter(is_superuser=True).first()
    
    # توليد QR Master أولي
    import secrets
    initial_code = f"QRM-v1-{secrets.token_urlsafe(16)}"
    
    MasterQRCode.objects.create(
        code=initial_code,
        version=1,
        created_by=superuser,
        is_active=True,
        notes='QR Master أولي تم توليده تلقائياً عند الـ Migration'
    )


def generate_tokens_for_existing_devices(apps, schema_editor):
    """
    توليد device_token لكل الأجهزة الموجودة
    """
    BranchDevice = apps.get_model('accounts', 'BranchDevice')
    
    for device in BranchDevice.objects.all():
        if not device.device_token:
            device.device_token = uuid.uuid4()
            device.save(update_fields=['device_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_create_default_departments_structure'),
    ]

    operations = [
        # إضافة MasterQRCode model
        migrations.CreateModel(
            name='MasterQRCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, help_text='كود QR Master الفريد - لا يُعدّل يدوياً', max_length=100, unique=True, verbose_name='كود QR Master')),
                ('version', models.IntegerField(help_text='رقم الإصدار (v1, v2, v3...) - يزيد تلقائياً', verbose_name='رقم الإصدار')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التوليد')),
                ('is_active', models.BooleanField(default=True, help_text='هل QR Master نشط؟ يمكن إلغاؤه عند الشك في تسريبه', verbose_name='نشط')),
                ('deactivated_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الإلغاء')),
                ('usage_count', models.IntegerField(default=0, help_text='عدد الأجهزة المسجلة بهذا QR', verbose_name='عدد مرات الاستخدام')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='آخر استخدام')),
                ('notes', models.TextField(blank=True, help_text='سبب التجديد أو ملاحظات أخرى', verbose_name='ملاحظات')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_qr_masters', to=settings.AUTH_USER_MODEL, verbose_name='تم التوليد بواسطة')),
                ('deactivated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deactivated_qr_masters', to=settings.AUTH_USER_MODEL, verbose_name='تم الإلغاء بواسطة')),
            ],
            options={
                'verbose_name': 'QR Master',
                'verbose_name_plural': 'QR Masters',
                'ordering': ['-created_at'],
            },
        ),
        
        # إضافة indexes لـ MasterQRCode
        migrations.AddIndex(
            model_name='masterqrcode',
            index=models.Index(fields=['code', 'is_active'], name='accounts_ma_code_43c0ed_idx'),
        ),
        migrations.AddIndex(
            model_name='masterqrcode',
            index=models.Index(fields=['-created_at'], name='accounts_ma_created_2fce03_idx'),
        ),
        
        # إضافة device_token لـ BranchDevice
        migrations.AddField(
            model_name='branchdevice',
            name='device_token',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='معرف فريد دائم للجهاز - يُستخدم للمصادقة', unique=True, verbose_name='رمز الجهاز'),
        ),
        
        # إضافة registered_with_qr_version
        migrations.AddField(
            model_name='branchdevice',
            name='registered_with_qr_version',
            field=models.IntegerField(blank=True, help_text='رقم إصدار QR Master المستخدم لتسجيل هذا الجهاز', null=True, verbose_name='رقم إصدار QR المستخدم للتسجيل'),
        ),
        
        # تعديل device_fingerprint - لم تعد unique (يمكن أن تتكرر مؤقتاً)
        migrations.AlterField(
            model_name='branchdevice',
            name='device_fingerprint',
            field=models.CharField(blank=True, db_index=True, help_text='بصمة المتصفح - قد تتغير مع التحديثات', max_length=64, null=True, verbose_name='بصمة الجهاز'),
        ),
        
        # تعديل hardware_serial - لم تعد unique
        migrations.AlterField(
            model_name='branchdevice',
            name='hardware_serial',
            field=models.CharField(blank=True, db_index=True, help_text='الرقم التسلسلي للجهاز (Hardware UUID/Serial) - احتياطي', max_length=200, null=True, verbose_name='الرقم التسلسلي للجهاز'),
        ),
        
        # توليد QR Master أولي
        migrations.RunPython(generate_initial_qr_master),
        
        # توليد tokens للأجهزة الموجودة
        migrations.RunPython(generate_tokens_for_existing_devices),
    ]
