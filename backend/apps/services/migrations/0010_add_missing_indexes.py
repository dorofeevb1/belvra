"""Add missing indexes for MasterService and PortfolioItem."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0009_masterservice_materials_cost"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="masterservice",
            index=models.Index(
                fields=["master", "is_active"],
                name="idx_msvc_master_active",
            ),
        ),
        migrations.AddIndex(
            model_name="portfolioitem",
            index=models.Index(
                fields=["master", "-created_at"],
                name="idx_portfolio_master_created",
            ),
        ),
    ]
