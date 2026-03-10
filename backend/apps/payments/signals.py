"""
Signals for payment models.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.payments.models import Payment, Wallet, Withdrawal
from apps.users.models import MasterProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MasterProfile)
def create_master_wallet(sender, instance, created, **kwargs):
    """Create a wallet for new master profiles."""
    if created:
        with transaction.atomic():
            Wallet.objects.get_or_create(master=instance)
        logger.info(f"Created wallet for master {instance.id}")


@receiver(post_save, sender=Payment)
def payment_status_changed(sender, instance, created, **kwargs):
    """Handle payment status changes."""
    if created:
        logger.info(f"New payment created: {instance.id}")

        # Schedule status check task
        from apps.payments.tasks import process_pending_payment
        process_pending_payment.apply_async(
            args=[str(instance.id)],
            countdown=60  # Check after 1 minute
        )


@receiver(post_save, sender=Withdrawal)
def withdrawal_created(sender, instance, created, **kwargs):
    """Handle withdrawal creation."""
    if created:
        logger.info(f"New withdrawal request: {instance.id}")

        # Schedule processing task
        from apps.payments.tasks import process_withdrawal
        process_withdrawal.apply_async(
            args=[str(instance.id)],
            countdown=5  # Process after 5 seconds
        )
