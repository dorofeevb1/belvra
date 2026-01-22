# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0003_add_master_service_to_appointment'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='is_archived',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
