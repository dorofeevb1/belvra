from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_add_referral_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="privacy_version_accepted",
            field=models.CharField(
                blank=True, default="", max_length=10,
                verbose_name="Версия политики конфиденциальности",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="terms_version_accepted",
            field=models.CharField(
                blank=True, default="", max_length=10,
                verbose_name="Версия пользовательского соглашения",
            ),
        ),
    ]
