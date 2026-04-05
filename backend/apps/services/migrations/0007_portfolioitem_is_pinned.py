from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0006_masterservice_unique_master_custom_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolioitem",
            name="is_pinned",
            field=models.BooleanField(default=False, help_text="Закреплено наверху"),
        ),
        migrations.AlterModelOptions(
            name="portfolioitem",
            options={
                "ordering": ["-is_pinned", "-created_at"],
                "verbose_name": "Работа в портфолио",
                "verbose_name_plural": "Работы в портфолио",
            },
        ),
    ]
