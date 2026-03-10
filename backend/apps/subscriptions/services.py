"""
Subscription services with YooKassa integration.
"""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from yookassa import Configuration, Payment as YooKassaPayment
from yookassa.domain.common import ConfirmationType
from yookassa.domain.models import Amount

from apps.core.notifications import NotificationService
from apps.services.models import MasterService, PortfolioItem
from apps.users.models import User

from .models import Subscription, SubscriptionPayment, SubscriptionPlan

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing user subscriptions."""

    def __init__(self):
        """Initialize YooKassa configuration."""
        self.test_mode = not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY
        if not self.test_mode:
            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    def get_or_create_free_subscription(self, user: User) -> Subscription:
        """Get existing subscription or create a free one."""
        try:
            return user.subscription
        except Subscription.DoesNotExist:
            return self.create_free_subscription(user)

    @transaction.atomic
    def create_free_subscription(self, user: User) -> Subscription:
        """Create a free subscription for a user."""
        user_type = SubscriptionPlan.UserType.MASTER if user.is_master else SubscriptionPlan.UserType.CLIENT

        # Get or create free plan
        free_plan, _ = SubscriptionPlan.objects.get_or_create(
            tier=SubscriptionPlan.Tier.FREE,
            user_type=user_type,
            period=SubscriptionPlan.Period.MONTHLY,
            defaults={
                "name": f"Бесплатный ({user_type})",
                "price": Decimal("0"),
                "max_appointments_per_month": 10 if user_type == SubscriptionPlan.UserType.MASTER else 0,
                "max_services_count": 5 if user_type == SubscriptionPlan.UserType.MASTER else 0,
                "max_portfolio_items": 5 if user_type == SubscriptionPlan.UserType.MASTER else 0,
                "commission_percent": Decimal("10.00"),
            }
        )

        subscription = Subscription.objects.create(
            user=user,
            plan=free_plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=None,  # Free plan never expires
            auto_renew=False
        )

        logger.info(f"Created free subscription for user {user.id}")
        return subscription

    @transaction.atomic
    def subscribe(
        self,
        user: User,
        plan: SubscriptionPlan,
        return_url: str,
        save_payment_method: bool = True,
        payment_method: Optional[str] = None
    ) -> dict:
        """
        Subscribe user to a plan.

        Args:
            user: User to subscribe
            plan: Subscription plan
            return_url: URL to redirect after payment
            save_payment_method: Whether to save payment method for recurring
            payment_method: Preferred payment method

        Returns:
            dict with subscription_id, payment_url, status
        """
        # Check if user already has a subscription
        try:
            existing_subscription = user.subscription
            if existing_subscription.plan == plan and existing_subscription.is_active:
                return {
                    "subscription_id": str(existing_subscription.id),
                    "payment_url": None,
                    "status": "already_subscribed",
                    "message": "Вы уже подписаны на этот план"
                }
        except Subscription.DoesNotExist:
            existing_subscription = None

        # Free plan - no payment needed
        if plan.is_free:
            if existing_subscription:
                existing_subscription.plan = plan
                existing_subscription.status = Subscription.Status.ACTIVE
                existing_subscription.save()
                subscription = existing_subscription
            else:
                subscription = self.create_free_subscription(user)

            return {
                "subscription_id": str(subscription.id),
                "payment_url": None,
                "status": "active",
                "message": "Подписка на бесплатный план активирована"
            }

        # Create or update subscription
        if existing_subscription:
            subscription = existing_subscription
            subscription.plan = plan
            subscription.status = Subscription.Status.PENDING
            subscription.save()
        else:
            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                status=Subscription.Status.PENDING
            )

        # Create payment
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=plan.price,
            status=SubscriptionPayment.Status.PENDING
        )

        # Create YooKassa payment
        result = self._create_yookassa_payment(
            payment=payment,
            plan=plan,
            user=user,
            return_url=return_url,
            save_payment_method=save_payment_method,
            payment_method=payment_method
        )

        return {
            "subscription_id": str(subscription.id),
            "payment_url": result.get("confirmation_url"),
            "status": "pending",
            "message": "Перейдите по ссылке для оплаты"
        }

    def _create_yookassa_payment(
        self,
        payment: SubscriptionPayment,
        plan: SubscriptionPlan,
        user: User,
        return_url: str,
        save_payment_method: bool = True,
        payment_method: Optional[str] = None
    ) -> dict:
        """Create payment in YooKassa."""
        try:
            idempotency_key = str(payment.id)

            # Test mode - return mock response
            if self.test_mode:
                mock_payment_id = f"test_sub_{uuid.uuid4().hex[:16]}"
                separator = "&" if "?" in return_url else "?"
                mock_confirmation_url = f"{return_url}{separator}test_payment={mock_payment_id}&payment_id={payment.id}"

                payment.external_payment_id = mock_payment_id
                payment.confirmation_url = mock_confirmation_url
                payment.save()

                logger.info(f"Created TEST subscription payment {mock_payment_id}")

                return {
                    "payment_id": mock_payment_id,
                    "confirmation_url": mock_confirmation_url,
                    "status": "pending",
                    "test_mode": True
                }

            payment_data = {
                "amount": Amount(
                    value=str(payment.amount),
                    currency="RUB"
                ),
                "confirmation": {
                    "type": ConfirmationType.REDIRECT,
                    "return_url": return_url
                },
                "capture": True,
                "description": f"Подписка {plan.name}",
                "metadata": {
                    "payment_id": str(payment.id),
                    "subscription_id": str(payment.subscription_id),
                    "user_id": str(user.id),
                    "plan_id": str(plan.id),
                },
                "save_payment_method": save_payment_method,
            }

            if payment_method:
                payment_data["payment_method_data"] = {"type": payment_method}

            yoo_payment = YooKassaPayment.create(payment_data, idempotency_key)

            payment.external_payment_id = yoo_payment.id
            payment.confirmation_url = yoo_payment.confirmation.confirmation_url
            payment.save()

            logger.info(f"Created YooKassa subscription payment {yoo_payment.id}")

            return {
                "payment_id": yoo_payment.id,
                "confirmation_url": yoo_payment.confirmation.confirmation_url,
                "status": yoo_payment.status
            }

        except Exception as e:
            logger.error(f"Error creating subscription payment: {e}")
            payment.status = SubscriptionPayment.Status.FAILED
            payment.error_message = str(e)
            payment.save()
            raise

    @transaction.atomic
    def process_successful_payment(self, payment: SubscriptionPayment, payment_method_id: str = None):
        """Process a successful subscription payment."""
        # Idempotency: skip if already processed
        if payment.status == SubscriptionPayment.Status.SUCCEEDED:
            logger.info(f"Subscription payment {payment.id} already succeeded, skipping")
            return

        payment.status = SubscriptionPayment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save()

        subscription = payment.subscription
        plan = subscription.plan

        # Calculate period based on plan
        now = timezone.now()
        if plan.period == SubscriptionPlan.Period.MONTHLY:
            period_end = now + timedelta(days=30)
        else:  # Yearly
            period_end = now + timedelta(days=365)

        subscription.status = Subscription.Status.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.auto_renew = True

        if payment_method_id:
            subscription.yookassa_payment_method_id = payment_method_id

        subscription.save()

        # Send notification
        try:
            NotificationService.create_notification(
                user=subscription.user,
                notification_type="subscription_activated",
                title="Подписка активирована",
                message=f"Ваша подписка {plan.name} успешно активирована до {period_end.strftime('%d.%m.%Y')}",
            )
        except Exception as e:
            logger.error(f"Error sending subscription notification: {e}")

        logger.info(f"Activated subscription {subscription.id} until {period_end}")

    @transaction.atomic
    def cancel_subscription(
        self,
        subscription: Subscription,
        immediately: bool = False,
        reason: str = ""
    ) -> Subscription:
        """Cancel a subscription."""
        if immediately:
            subscription.status = Subscription.Status.CANCELLED
            subscription.cancelled_at = timezone.now()
        else:
            subscription.cancel_at_period_end = True

        subscription.auto_renew = False
        subscription.save()

        # Send notification
        try:
            if immediately:
                message = "Ваша подписка отменена"
            else:
                message = f"Ваша подписка будет отменена {subscription.current_period_end.strftime('%d.%m.%Y')}"

            NotificationService.create_notification(
                user=subscription.user,
                notification_type="subscription_cancelled",
                title="Подписка отменена",
                message=message,
            )
        except Exception as e:
            logger.error(f"Error sending cancellation notification: {e}")

        logger.info(f"Cancelled subscription {subscription.id}, immediately={immediately}")
        return subscription

    @transaction.atomic
    def reactivate_subscription(self, subscription: Subscription) -> Subscription:
        """Reactivate a cancelled subscription."""
        if subscription.status == Subscription.Status.CANCELLED:
            raise ValueError("Нельзя возобновить полностью отменённую подписку")

        subscription.cancel_at_period_end = False
        subscription.auto_renew = True
        subscription.save()

        logger.info(f"Reactivated subscription {subscription.id}")
        return subscription

    @transaction.atomic
    def change_plan(
        self,
        subscription: Subscription,
        new_plan: SubscriptionPlan,
        immediately: bool = False
    ) -> dict:
        """Change subscription plan."""
        if new_plan == subscription.plan:
            return {
                "status": "unchanged",
                "message": "Вы уже на этом плане"
            }

        # Downgrade to free
        if new_plan.is_free:
            if immediately:
                subscription.plan = new_plan
                subscription.status = Subscription.Status.ACTIVE
                subscription.current_period_end = None
                subscription.save()
            else:
                subscription.cancel_at_period_end = True
                subscription.save()
                # The actual downgrade will happen via celery task when period ends

            return {
                "status": "downgraded",
                "message": "План изменён на бесплатный"
            }

        # Upgrade requires payment
        return {
            "status": "payment_required",
            "new_plan_id": str(new_plan.id),
            "message": "Для смены плана требуется оплата"
        }

    @transaction.atomic
    def renew_subscription(self, subscription: Subscription) -> Optional[SubscriptionPayment]:
        """Renew subscription using saved payment method."""
        if not subscription.yookassa_payment_method_id:
            logger.warning(f"No saved payment method for subscription {subscription.id}")
            return None

        if not subscription.auto_renew:
            logger.info(f"Auto-renew disabled for subscription {subscription.id}")
            return None

        plan = subscription.plan
        if plan.is_free:
            return None

        # Create recurring payment
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=plan.price,
            status=SubscriptionPayment.Status.PENDING,
            is_recurring=True
        )

        # Process with YooKassa using saved payment method
        if self.test_mode:
            # Auto-succeed test payments
            self.process_successful_payment(payment)
            return payment

        try:
            idempotency_key = str(payment.id)

            yoo_payment = YooKassaPayment.create({
                "amount": Amount(value=str(payment.amount), currency="RUB"),
                "capture": True,
                "payment_method_id": subscription.yookassa_payment_method_id,
                "description": f"Продление подписки {plan.name}",
                "metadata": {
                    "payment_id": str(payment.id),
                    "subscription_id": str(subscription.id),
                    "is_recurring": True
                }
            }, idempotency_key)

            payment.external_payment_id = yoo_payment.id
            payment.save()

            if yoo_payment.status == "succeeded":
                self.process_successful_payment(payment, yoo_payment.payment_method.id)

            return payment

        except Exception as e:
            logger.error(f"Error renewing subscription {subscription.id}: {e}")
            payment.status = SubscriptionPayment.Status.FAILED
            payment.error_message = str(e)
            payment.save()

            subscription.status = Subscription.Status.PAST_DUE
            subscription.save()

            return payment

    def get_usage_stats(self, subscription: Subscription) -> dict:
        """Get subscription usage statistics."""
        user = subscription.user
        plan = subscription.plan

        # Get current counts
        if user.is_master and hasattr(user, "master_profile"):
            master = user.master_profile
            services_count = MasterService.objects.filter(master=master).count()
            portfolio_count = PortfolioItem.objects.filter(master=master).count()
        else:
            services_count = 0
            portfolio_count = 0

        appointments_limit = plan.max_appointments_per_month
        services_limit = plan.max_services_count
        portfolio_limit = plan.max_portfolio_items

        return {
            "appointments_used": subscription.appointments_this_month,
            "appointments_limit": appointments_limit if appointments_limit > 0 else -1,  # -1 = unlimited
            "appointments_remaining": max(0, appointments_limit - subscription.appointments_this_month) if appointments_limit > 0 else -1,
            "services_count": services_count,
            "services_limit": services_limit if services_limit > 0 else -1,
            "services_remaining": max(0, services_limit - services_count) if services_limit > 0 else -1,
            "portfolio_items_count": portfolio_count,
            "portfolio_items_limit": portfolio_limit if portfolio_limit > 0 else -1,
            "portfolio_items_remaining": max(0, portfolio_limit - portfolio_count) if portfolio_limit > 0 else -1,
            "plan_tier": plan.tier,
            "plan_name": plan.name
        }

    def check_limit(self, subscription: Subscription, limit_type: str) -> dict:
        """Check if a specific limit is reached."""
        user = subscription.user
        plan = subscription.plan

        if limit_type == "appointments":
            current = subscription.appointments_this_month
            limit = plan.max_appointments_per_month
        elif limit_type == "services":
            if user.is_master and hasattr(user, "master_profile"):
                current = MasterService.objects.filter(master=user.master_profile).count()
            else:
                current = 0
            limit = plan.max_services_count
        elif limit_type == "portfolio":
            if user.is_master and hasattr(user, "master_profile"):
                current = PortfolioItem.objects.filter(master=user.master_profile).count()
            else:
                current = 0
            limit = plan.max_portfolio_items
        else:
            return {
                "allowed": True,
                "current": 0,
                "limit": 0,
                "remaining": 0,
                "message": "Неизвестный тип лимита"
            }

        if limit == 0:  # Unlimited
            return {
                "allowed": True,
                "current": current,
                "limit": -1,
                "remaining": -1,
                "message": "Без ограничений"
            }

        remaining = max(0, limit - current)
        allowed = current < limit

        return {
            "allowed": allowed,
            "current": current,
            "limit": limit,
            "remaining": remaining,
            "message": None if allowed else f"Достигнут лимит ({current}/{limit}). Обновите подписку для увеличения лимита."
        }

    @transaction.atomic
    def expire_subscription(self, subscription: Subscription):
        """Expire a subscription that has passed its end date."""
        subscription.status = Subscription.Status.EXPIRED
        subscription.save()

        # Send notification
        try:
            NotificationService.create_notification(
                user=subscription.user,
                notification_type="subscription_expired",
                title="Подписка истекла",
                message="Ваша подписка истекла. Продлите подписку для продолжения использования всех функций.",
            )
        except Exception as e:
            logger.error(f"Error sending expiration notification: {e}")

        logger.info(f"Expired subscription {subscription.id}")

    @transaction.atomic
    def downgrade_to_free(self, subscription: Subscription):
        """Downgrade subscription to free plan."""
        user_type = subscription.plan.user_type

        free_plan = SubscriptionPlan.objects.filter(
            tier=SubscriptionPlan.Tier.FREE,
            user_type=user_type
        ).first()

        if not free_plan:
            logger.error(f"Free plan not found for user type {user_type}")
            return

        subscription.plan = free_plan
        subscription.status = Subscription.Status.ACTIVE
        subscription.current_period_end = None
        subscription.cancel_at_period_end = False
        subscription.auto_renew = False
        subscription.save()

        # Send notification
        try:
            NotificationService.create_notification(
                user=subscription.user,
                notification_type="subscription_downgraded",
                title="Подписка понижена",
                message="Ваша подписка переведена на бесплатный план.",
            )
        except Exception as e:
            logger.error(f"Error sending downgrade notification: {e}")

        logger.info(f"Downgraded subscription {subscription.id} to free plan")
