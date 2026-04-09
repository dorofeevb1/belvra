"""Change Appointment.client on_delete from CASCADE to SET_NULL, add db_index."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0008_alter_appointment_service"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="client",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="client_appointments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
