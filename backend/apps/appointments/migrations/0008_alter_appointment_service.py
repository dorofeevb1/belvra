import django.db.models.deletion
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0007_clientnote"),
        ("services", "0007_portfolioitem_is_pinned"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="service",
            field=django.db.models.fields.related.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="appointments",
                to="services.service",
            ),
        ),
    ]
