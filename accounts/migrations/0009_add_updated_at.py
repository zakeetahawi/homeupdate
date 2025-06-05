from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_branchmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='branchmessage',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث'),
        ),
    ]
