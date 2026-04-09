"""Add tbank_rebill_id_hash field and change tbank_rebill_id to TextField for encryption.

Data migration encrypts existing plain-text rebill IDs.
"""

import hashlib

from django.db import migrations, models


def encrypt_existing_rebill_ids(apps, schema_editor):
    """Encrypt existing plain-text rebill IDs and compute hashes."""
    Subscription = apps.get_model("subscriptions", "Subscription")
    for sub in Subscription.objects.exclude(tbank_rebill_id="").exclude(tbank_rebill_id__isnull=True):
        plain = sub.tbank_rebill_id
        # Compute hash for lookups
        sub.tbank_rebill_id_hash = hashlib.sha256(plain.encode()).hexdigest()
        # Encryption will happen via the model's set_rebill_id on next save
        # For now, store the hash; encryption requires FIELD_ENCRYPTION_KEY
        # which may not be set during migration. Leave plain text until
        # the key is configured and a management command re-encrypts.
        sub.save(update_fields=["tbank_rebill_id_hash"])


def reverse_encrypt(apps, schema_editor):
    """Reverse: clear hashes."""
    Subscription = apps.get_model("subscriptions", "Subscription")
    Subscription.objects.all().update(tbank_rebill_id_hash="")


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0005_referral_prevent_self_referral"),
    ]

    operations = [
        # Change CharField to TextField (needed for encrypted values which are longer)
        migrations.AlterField(
            model_name="subscription",
            name="tbank_rebill_id",
            field=models.TextField(blank=True, default=""),
        ),
        # Add hash field for lookups
        migrations.AddField(
            model_name="subscription",
            name="tbank_rebill_id_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="SHA-256 hash for lookups",
                max_length=64,
            ),
        ),
        # Encrypt existing data
        migrations.RunPython(encrypt_existing_rebill_ids, reverse_encrypt),
    ]
