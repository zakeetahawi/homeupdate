# Generated manually for comprehensive performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("installations", "0013_installationschedule_inst_status_date_idx_and_more"),
    ]

    operations = [
        # إضافة فهارس محسّنة على InstallationSchedule
        # completion_date already exists in model, no need to add index
        migrations.AddIndex(
            model_name="installationschedule",
            index=models.Index(fields=["updated_at"], name="inst_updated_at_idx"),
        ),
        # InstallationSchedule has: order, team, scheduled_date, scheduled_time,
        # location_type, windows_count, status, notes, completion_date, created_at, updated_at
        # Already has indexes in Meta for: status+scheduled_date, order+status, team+scheduled_date, etc.
        # إضافة فهارس على InstallationTeam
        migrations.AddIndex(
            model_name="installationteam",
            index=models.Index(fields=["is_active"], name="inst_team_active_idx"),
        ),
        # InstallationTeam has: name, technicians (M2M), driver, is_active, created_at, updated_at
        # No branch field
        # إضافة فهارس على Technician
        migrations.AddIndex(
            model_name="technician",
            index=models.Index(fields=["is_active"], name="technician_active_idx"),
        ),
        migrations.AddIndex(
            model_name="technician",
            index=models.Index(fields=["phone"], name="technician_phone_idx"),
        ),
        migrations.AddIndex(
            model_name="technician",
            index=models.Index(fields=["department"], name="technician_dept_idx"),
        ),
        # إضافة فهارس على Driver
        migrations.AddIndex(
            model_name="driver",
            index=models.Index(fields=["is_active"], name="driver_active_idx"),
        ),
        migrations.AddIndex(
            model_name="driver",
            index=models.Index(fields=["phone"], name="driver_phone_idx"),
        ),
    ]
