from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0004_remove_subscription_yookassa_payment_method_id_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="referral",
            constraint=models.CheckConstraint(
                condition=~models.Q(referrer=models.F("referred_user")),
                name="prevent_self_referral",
            ),
        ),
    ]
