# Generated migration to remove hardware_serial and device_fingerprint fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0047_add_can_export_field'),
    ]

    operations = [
        # حذف hardware_serial و device_fingerprint من BranchDevice
        migrations.RemoveField(
            model_name='branchdevice',
            name='hardware_serial',
        ),
        migrations.RemoveField(
            model_name='branchdevice',
            name='device_fingerprint',
        ),
        
        # حذف hardware_serial و device_fingerprint من UnauthorizedDeviceAttempt  
        migrations.RemoveField(
            model_name='unauthorizeddeviceattempt',
            name='hardware_serial',
        ),
        migrations.RemoveField(
            model_name='unauthorizeddeviceattempt',
            name='device_fingerprint',
        ),
    ]
