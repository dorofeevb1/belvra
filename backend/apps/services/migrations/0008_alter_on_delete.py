import django.db.models.deletion
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0007_portfolioitem_is_pinned"),
    ]

    operations = [
        migrations.AlterField(
            model_name="masterservice",
            name="service",
            field=django.db.models.fields.related.ForeignKey(
                blank=True,
                help_text="Link to catalog service (optional for custom services)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="masters",
                to="services.service",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="category",
            field=django.db.models.fields.related.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="services",
                to="services.category",
            ),
        ),
    ]
