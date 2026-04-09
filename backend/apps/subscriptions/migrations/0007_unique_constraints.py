"""Convert unique_together to UniqueConstraint for SubscriptionPlan and Referral."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0006_encrypt_tbank_rebill_id"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="subscriptionplan",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="subscriptionplan",
            constraint=models.UniqueConstraint(
                fields=["tier", "user_type", "period"],
                name="unique_plan_tier_type_period",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="referral",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="referral",
            constraint=models.UniqueConstraint(
                fields=["referrer", "referred_user"],
                name="unique_referral_pair",
            ),
        ),
    ]
