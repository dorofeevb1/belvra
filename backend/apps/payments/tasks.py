"""
Celery tasks for payment processing.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal
from apps.payments.services import PaymentService, TBankService, WithdrawalService, YooKassaService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_pending_payment(self, payment_id: str):
    """
    Check and process a pending payment.

    This task is called after payment creation to periodically
    check payment status until it's completed or expired.
    """
    try:
        payment = Payment.objects.get(id=payment_id)

        if payment.status != Payment.PaymentStatus.PENDING:
            logger.info(f"Payment {payment_id} is no longer pending: {payment.status}")
            return

        # Check if payment is expired (15 minutes)
        expiry_time = payment.created_at + timedelta(minutes=15)
        if timezone.now() > expiry_time:
            payment.status = Payment.PaymentStatus.CANCELLED
            payment.payment_metadata["cancellation_reason"] = "Истекло время ожидания оплаты"
            payment.save()
            logger.info(f"Payment {payment_id} expired")
            return

        # Check status in payment provider
        if payment.payment_provider == Payment.PaymentProvider.TINKOFF:
            provider_service = TBankService()
        else:
            provider_service = YooKassaService()
        status_data = provider_service.get_payment_status(payment.external_payment_id)

        if status_data["status"] == "succeeded":
            payment_service = PaymentService()
            payment_service.process_successful_payment(
                payment,
                status_data.get("payment_method")
            )
            logger.info(f"Payment {payment_id} succeeded")

        elif status_data["status"] == "canceled":
            payment.status = Payment.PaymentStatus.CANCELLED
            payment.save()
            logger.info(f"Payment {payment_id} was canceled")

        else:
            # Still pending, reschedule check
            self.retry(countdown=30)

    except Payment.DoesNotExist:
        logger.error(f"Payment {payment_id} not found")
    except Exception as e:
        logger.error(f"Error processing payment {payment_id}: {e}")
        self.retry(exc=e)


@shared_task
def release_held_funds():
    """
    Release funds from pending to available balance.

    This task runs periodically to move funds that have
    passed the hold period to available balance.
    """
    now = timezone.now()

    # Find payments ready for release
    payments = Payment.objects.filter(
        status=Payment.PaymentStatus.SUCCEEDED,
        available_at__lte=now,
        payment_metadata__released=None  # Not yet released
    )

    payment_service = PaymentService()
    released_count = 0

    for payment in payments:
        try:
            with transaction.atomic():
                payment_service.release_held_funds(payment)
                payment.payment_metadata["released"] = True
                payment.payment_metadata["released_at"] = str(now)
                payment.save()
                released_count += 1
        except Exception as e:
            logger.error(f"Error releasing funds for payment {payment.id}: {e}")

    logger.info(f"Released funds for {released_count} payments")
    return released_count


@shared_task
def process_auto_withdrawals():
    """
    Process automatic withdrawals for masters with auto-withdraw enabled.

    This task runs daily to create withdrawal requests for
    masters who have enabled automatic withdrawals.
    """
    min_auto_withdraw = getattr(settings, "MIN_AUTO_WITHDRAWAL_AMOUNT", Decimal("1000.00"))

    wallets = Wallet.objects.filter(
        auto_withdraw=True,
        available_balance__gte=min_auto_withdraw
    )

    withdrawal_service = WithdrawalService()
    processed_count = 0

    for wallet in wallets:
        try:
            # Get default payout destination
            destination = PayoutDestination.objects.filter(
                master=wallet.master,
                is_default=True,
                is_verified=True
            ).first()

            if not destination:
                logger.warning(f"No default destination for master {wallet.master_id}")
                continue

            with transaction.atomic():
                withdrawal = withdrawal_service.create_withdrawal(
                    wallet=wallet,
                    amount=wallet.available_balance,
                    method=destination.destination_type,
                    destination=destination,
                )

                # Process immediately
                withdrawal_service.process_withdrawal(withdrawal, destination)
                processed_count += 1

        except Exception as e:
            logger.error(f"Error processing auto-withdrawal for wallet {wallet.id}: {e}")

    logger.info(f"Processed {processed_count} auto-withdrawals")
    return processed_count


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def process_withdrawal(self, withdrawal_id: str):
    """
    Process a single withdrawal request.

    This task handles the actual payout to the master.
    """
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)

        if withdrawal.status != Withdrawal.WithdrawalStatus.PENDING:
            logger.info(f"Withdrawal {withdrawal_id} is not pending: {withdrawal.status}")
            return

        destination = PayoutDestination.objects.filter(
            master=withdrawal.wallet.master,
            is_default=True,
            is_verified=True
        ).first()

        if not destination:
            withdrawal.status = Withdrawal.WithdrawalStatus.REJECTED
            withdrawal.rejection_reason = "Не найден способ вывода"
            withdrawal.save()

            # Return funds
            wallet = withdrawal.wallet
            wallet.hold_balance -= withdrawal.amount
            wallet.available_balance += withdrawal.amount
            wallet.save()
            return

        withdrawal_service = WithdrawalService()
        withdrawal_service.process_withdrawal(withdrawal, destination)

        logger.info(f"Processed withdrawal {withdrawal_id}")

    except Withdrawal.DoesNotExist:
        logger.error(f"Withdrawal {withdrawal_id} not found")
    except Exception as e:
        logger.error(f"Error processing withdrawal {withdrawal_id}: {e}")
        self.retry(exc=e)


@shared_task
def sync_payment_statuses():
    """
    Synchronize payment statuses with YooKassa.

    This task runs periodically to catch any missed webhooks
    and ensure payment statuses are up to date.
    """
    # Check pending payments older than 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)

    pending_payments = Payment.objects.filter(
        status=Payment.PaymentStatus.PENDING,
        created_at__lte=cutoff_time,
        external_payment_id__isnull=False
    )[:100]  # Process in batches

    yookassa = YooKassaService()
    tbank = TBankService()
    payment_service = PaymentService()
    synced_count = 0

    for payment in pending_payments:
        try:
            if payment.payment_provider == Payment.PaymentProvider.TINKOFF:
                status_data = tbank.get_payment_status(payment.external_payment_id)
            else:
                status_data = yookassa.get_payment_status(payment.external_payment_id)

            if status_data["status"] == "succeeded":
                payment_service.process_successful_payment(
                    payment,
                    status_data.get("payment_method")
                )
                synced_count += 1

            elif status_data["status"] == "canceled":
                payment.status = Payment.PaymentStatus.CANCELLED
                payment.save()
                synced_count += 1

        except Exception as e:
            logger.error(f"Error syncing payment {payment.id}: {e}")

    logger.info(f"Synced {synced_count} payment statuses")
    return synced_count


@shared_task
def cleanup_expired_payments():
    """
    Clean up expired pending payments.

    This task marks old pending payments as cancelled
    to keep the database clean.
    """
    expiry_time = timezone.now() - timedelta(hours=1)

    expired_count = Payment.objects.filter(
        status=Payment.PaymentStatus.PENDING,
        created_at__lte=expiry_time
    ).update(
        status=Payment.PaymentStatus.CANCELLED,
    )

    logger.info(f"Cleaned up {expired_count} expired payments")
    return expired_count


@shared_task
def generate_daily_report():
    """
    Generate daily payment report for analytics.

    This task creates a summary of daily payment activity.
    """
    from django.db.models import Avg, Count, Sum

    yesterday = timezone.now().date() - timedelta(days=1)

    # Aggregate payment data
    payments = Payment.objects.filter(
        paid_at__date=yesterday,
        status=Payment.PaymentStatus.SUCCEEDED
    )

    report = payments.aggregate(
        total_amount=Sum("amount"),
        total_commission=Sum("commission"),
        total_net=Sum("net_amount"),
        payment_count=Count("id"),
        average_amount=Avg("amount"),
    )

    # Aggregate withdrawal data
    withdrawals = Withdrawal.objects.filter(
        completed_at__date=yesterday,
        status=Withdrawal.WithdrawalStatus.COMPLETED
    )

    withdrawal_report = withdrawals.aggregate(
        total_withdrawn=Sum("net_amount"),
        withdrawal_count=Count("id"),
    )

    combined_report = {
        "date": str(yesterday),
        "payments": report,
        "withdrawals": withdrawal_report,
    }

    logger.info(f"Daily report for {yesterday}: {combined_report}")
    return combined_report
