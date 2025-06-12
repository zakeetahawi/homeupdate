from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_branchmessage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='branchmessage',
            name='color',
        ),
        migrations.AddField(
            model_name='branchmessage',
            name='color',
            field=models.CharField(default='primary', max_length=50, verbose_name='لون الرسالة'),
        ),
    ]
