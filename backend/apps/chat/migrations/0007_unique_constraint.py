"""Convert Chat unique_together to UniqueConstraint."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0006_chatmessage_sender_set_null"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="chat",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="chat",
            constraint=models.UniqueConstraint(
                fields=["master", "client"],
                name="unique_chat_master_client",
            ),
        ),
    ]
