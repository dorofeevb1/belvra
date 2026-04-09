"""Change ChatMessage.sender on_delete from CASCADE to SET_NULL, make nullable."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0005_chat_hidden_for_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatmessage",
            name="sender",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sent_messages",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Отправитель",
            ),
        ),
    ]
