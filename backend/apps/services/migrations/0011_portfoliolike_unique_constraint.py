"""Convert PortfolioLike unique_together to UniqueConstraint."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0010_add_missing_indexes"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="portfoliolike",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="portfoliolike",
            constraint=models.UniqueConstraint(
                fields=["user", "portfolio_item"],
                name="unique_user_portfolio_like",
            ),
        ),
    ]
