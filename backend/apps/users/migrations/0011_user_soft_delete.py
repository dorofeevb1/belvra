"""Add soft delete fields to User model."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_user_is_online_user_last_seen_blockeduser"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_deleted",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="user",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
