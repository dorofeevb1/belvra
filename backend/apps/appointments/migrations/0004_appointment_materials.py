"""
Migration to add materials tracking fields to Appointment.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0003_add_master_service_to_appointment"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="used_materials",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Использованные материалы",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="materials_cost",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Стоимость материалов",
                max_digits=10,
            ),
        ),
    ]
