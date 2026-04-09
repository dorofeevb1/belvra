"""Decompose MasterProfile: add MasterLocation, MasterSocialLinks, MasterNotificationSettings.

Also converts unique_together to UniqueConstraint + adds CheckConstraint for BlockedUser.
TAX_SYSTEM_CHOICES → TextChoices (no DB change, only choices representation).
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


def populate_new_models(apps, schema_editor):
    """Copy data from MasterProfile deprecated fields into new O2O models."""
    MasterProfile = apps.get_model("users", "MasterProfile")
    MasterLocation = apps.get_model("users", "MasterLocation")
    MasterSocialLinks = apps.get_model("users", "MasterSocialLinks")
    MasterNotificationSettings = apps.get_model("users", "MasterNotificationSettings")

    for mp in MasterProfile.objects.all().iterator():
        MasterLocation.objects.get_or_create(
            master=mp,
            defaults={
                "address": mp.address,
                "latitude": mp.latitude,
                "longitude": mp.longitude,
            }
        )
        MasterSocialLinks.objects.get_or_create(
            master=mp,
            defaults={
                "telegram": mp.telegram,
                "instagram": mp.instagram,
                "vk": mp.vk,
                "whatsapp": mp.whatsapp,
            }
        )
        MasterNotificationSettings.objects.get_or_create(
            master=mp,
            defaults={
                "email_notifications": mp.email_notifications,
                "sms_notifications": mp.sms_notifications,
                "push_notifications": mp.push_notifications,
                "reminder_hours": mp.reminder_hours,
            }
        )


def reverse_populate(apps, schema_editor):
    """Reverse: copy data back from new models to MasterProfile fields."""
    MasterProfile = apps.get_model("users", "MasterProfile")
    MasterLocation = apps.get_model("users", "MasterLocation")
    MasterSocialLinks = apps.get_model("users", "MasterSocialLinks")
    MasterNotificationSettings = apps.get_model("users", "MasterNotificationSettings")

    for mp in MasterProfile.objects.all().iterator():
        try:
            loc = MasterLocation.objects.get(master=mp)
            mp.address = loc.address
            mp.latitude = loc.latitude
            mp.longitude = loc.longitude
        except MasterLocation.DoesNotExist:
            pass
        try:
            sl = MasterSocialLinks.objects.get(master=mp)
            mp.telegram = sl.telegram
            mp.instagram = sl.instagram
            mp.vk = sl.vk
            mp.whatsapp = sl.whatsapp
        except MasterSocialLinks.DoesNotExist:
            pass
        try:
            ns = MasterNotificationSettings.objects.get(master=mp)
            mp.email_notifications = ns.email_notifications
            mp.sms_notifications = ns.sms_notifications
            mp.push_notifications = ns.push_notifications
            mp.reminder_hours = ns.reminder_hours
        except MasterNotificationSettings.DoesNotExist:
            pass
        mp.save()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_user_soft_delete"),
    ]

    operations = [
        # --- New models ---
        migrations.CreateModel(
            name="MasterLocation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("master", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="location",
                    to="users.masterprofile",
                )),
            ],
            options={
                "verbose_name": "Локация мастера",
                "verbose_name_plural": "Локации мастеров",
            },
        ),
        migrations.CreateModel(
            name="MasterSocialLinks",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("telegram", models.CharField(blank=True, max_length=100)),
                ("instagram", models.CharField(blank=True, max_length=100)),
                ("vk", models.CharField(blank=True, max_length=200)),
                ("whatsapp", models.CharField(blank=True, max_length=20)),
                ("master", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="social_links",
                    to="users.masterprofile",
                )),
            ],
            options={
                "verbose_name": "Соцсети мастера",
                "verbose_name_plural": "Соцсети мастеров",
            },
        ),
        migrations.CreateModel(
            name="MasterNotificationSettings",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email_notifications", models.BooleanField(default=True)),
                ("sms_notifications", models.BooleanField(default=False)),
                ("push_notifications", models.BooleanField(default=True)),
                ("reminder_hours", models.PositiveIntegerField(default=24)),
                ("master", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notification_settings",
                    to="users.masterprofile",
                )),
            ],
            options={
                "verbose_name": "Настройки уведомлений мастера",
                "verbose_name_plural": "Настройки уведомлений мастеров",
            },
        ),

        # --- Data migration ---
        migrations.RunPython(populate_new_models, reverse_populate),

        # --- Convert unique_together → UniqueConstraint ---
        migrations.AlterUniqueTogether(
            name="favoritemaster",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="favoritemaster",
            constraint=models.UniqueConstraint(
                fields=["user", "master"],
                name="unique_favorite_user_master",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="blockeduser",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="blockeduser",
            constraint=models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_blocker_blocked",
            ),
        ),
        migrations.AddConstraint(
            model_name="blockeduser",
            constraint=models.CheckConstraint(
                check=~models.Q(blocker=models.F("blocked")),
                name="no_self_block",
            ),
        ),
    ]
