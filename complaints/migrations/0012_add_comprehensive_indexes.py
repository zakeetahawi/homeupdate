# Generated manually for comprehensive performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('complaints', '0011_alter_complaint_assigned_to'),
    ]

    operations = [
        # إضافة فهارس مفقودة على Complaint
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['complaint_type'], name='complaint_type_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['branch'], name='complaint_branch_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['related_order'], name='complaint_order_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['resolved_at'], name='complaint_resolved_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['closed_at'], name='complaint_closed_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['assigned_department'], name='complaint_dept_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['created_by'], name='complaint_creator_idx'),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(fields=['updated_at'], name='complaint_updated_idx'),
        ),
        
        # فهارس مركبة للأداء
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(
                fields=['customer', 'status', 'created_at'],
                name='complaint_cust_sts_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(
                fields=['status', 'priority', 'created_at'],
                name='complaint_sts_pri_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(
                fields=['assigned_to', 'status', 'deadline'],
                name='complaint_asn_sts_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(
                fields=['branch', 'status', 'created_at'],
                name='complaint_br_sts_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(
                fields=['complaint_type', 'status', 'created_at'],
                name='complaint_type_sts_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='complaint',
            index=models.Index(
                fields=['related_order', 'status'],
                name='complaint_ord_sts_idx'
            ),
        ),
        
        # إضافة فهارس على ComplaintType
        migrations.AddIndex(
            model_name='complainttype',
            index=models.Index(fields=['is_active'], name='comptype_active_idx'),
        ),
        migrations.AddIndex(
            model_name='complainttype',
            index=models.Index(fields=['order'], name='comptype_order_idx'),
        ),
        migrations.AddIndex(
            model_name='complainttype',
            index=models.Index(fields=['responsible_department'], name='comptype_dept_idx'),
        ),
    ]
