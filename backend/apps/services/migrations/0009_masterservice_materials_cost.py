from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0008_alter_on_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="masterservice",
            name="materials_cost",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Cost of materials for this service",
                max_digits=10,
            ),
        ),
    ]
