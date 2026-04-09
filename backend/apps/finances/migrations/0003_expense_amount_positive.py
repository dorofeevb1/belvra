"""Add CheckConstraint for positive expense amount."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0002_change_master_fk_to_masterprofile"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="expense_amount_positive",
            ),
        ),
    ]
