"""
Subscription services with T-Bank payment integration.
"""

import logging
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.notifications import NotificationService
from apps.core.tbank import TBankService
from apps.services.models import MasterService, PortfolioItem
from apps.users.models import User

from .models import Referral, Subscription, SubscriptionPayment, SubscriptionPlan

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing master subscriptions via T-Bank."""

    def __init__(self):
        self.tbank = TBankService()

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

        For paid plans, creates a T-Bank payment and returns a payment URL.
        """
        # Check if user already has this subscription
        try:
            existing_subscription = user.subscription
            if existing_subscription.plan == plan and existing_subscription.is_active:
                return {
                    "subscription_id": str(existing_subscription.id),
                    "payment_id": None,
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
                "payment_id": None,
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

        # Create payment record
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=plan.price,
            status=SubscriptionPayment.Status.PENDING
        )

        # Create T-Bank payment
        result = self._create_tbank_payment(
            payment=payment,
            plan=plan,
            user=user,
            return_url=return_url,
            save_payment_method=save_payment_method,
        )

        return {
            "subscription_id": str(subscription.id),
            "payment_id": result.get("payment_id"),
            "payment_url": result.get("confirmation_url"),
            "status": "pending",
            "message": "Перейдите по ссылке для оплаты"
        }

    def _create_tbank_payment(
        self,
        payment: SubscriptionPayment,
        plan: SubscriptionPlan,
        user: User,
        return_url: str,
        save_payment_method: bool = True,
    ) -> dict:
        """Create payment via T-Bank Init endpoint."""
        try:
            # Test mode
            if self.tbank.test_mode:
                mock_payment_id = f"tbank_sub_test_{uuid.uuid4().hex[:12]}"
                separator = "&" if "?" in return_url else "?"
                mock_url = f"{return_url}{separator}test_payment={mock_payment_id}&payment_id={payment.id}"

                payment.external_payment_id = mock_payment_id
                payment.confirmation_url = mock_url
                payment.save()

                logger.info(f"Created TEST T-Bank subscription payment {mock_payment_id}")
                return {
                    "payment_id": mock_payment_id,
                    "confirmation_url": mock_url,
                    "status": "pending",
                    "test_mode": True,
                }

            amount_kopecks = int(payment.amount * 100)
            description = f"Подписка {plan.name}"[:140]

            # Build webhook URL for T-Bank notifications
            frontend_url = getattr(settings, "FRONTEND_URL", "https://belvra.ru")
            notification_url = f"{frontend_url}/api/v1/subscriptions/webhook/"

            params = {
                "Amount": amount_kopecks,
                "OrderId": str(payment.id),
                "Description": description,
                "CustomerKey": str(user.id),
                "SuccessURL": return_url,
                "FailURL": return_url.replace('success=true', 'success=false') if 'success=true' in return_url else return_url + ('&' if '?' in return_url else '?') + 'success=false',
                "NotificationURL": notification_url,
                "DATA": {
                    "payment_id": str(payment.id),
                    "subscription_id": str(payment.subscription_id),
                    "user_id": str(user.id),
                    "plan_id": str(plan.id),
                },
            }

            # Save card for recurring payments
            if save_payment_method:
                params["Recurrent"] = "Y"

            # Add receipt for FZ-54
            if getattr(settings, "TBANK_SEND_RECEIPT", False):
                taxation = getattr(settings, "TBANK_TAXATION", "usn_income")
                receipt = {
                    "Taxation": taxation,
                    "Items": [
                        {
                            "Name": description[:128],
                            "Price": amount_kopecks,
                            "Quantity": 1.0,
                            "Amount": amount_kopecks,
                            "Tax": "none",
                            "PaymentMethod": "full_payment",
                            "PaymentObject": "service",
                        }
                    ],
                }
                if user.email:
                    receipt["Email"] = user.email
                params["Receipt"] = receipt

            data = self.tbank._request("Init", params)

            payment.external_payment_id = str(data["PaymentId"])
            payment.confirmation_url = data["PaymentURL"]
            payment.save()

            logger.info(f"Created T-Bank subscription payment {data['PaymentId']}")

            return {
                "payment_id": str(data["PaymentId"]),
                "confirmation_url": data["PaymentURL"],
                "status": data.get("Status", "NEW"),
            }

        except Exception as e:
            logger.error(f"Error creating T-Bank subscription payment: {e}")
            payment.status = SubscriptionPayment.Status.FAILED
            payment.error_message = str(e)
            payment.save()
            raise

    @transaction.atomic
    def process_successful_payment(self, payment: SubscriptionPayment, rebill_id: str = None):
        """Process a successful subscription payment."""
        if payment.status == SubscriptionPayment.Status.SUCCEEDED:
            logger.info(f"Subscription payment {payment.id} already succeeded, skipping")
            return

        payment.status = SubscriptionPayment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save()

        subscription = payment.subscription
        plan = subscription.plan

        # Calculate period
        now = timezone.now()
        if plan.period == SubscriptionPlan.Period.MONTHLY:
            period_end = now + timedelta(days=30)
        else:
            period_end = now + timedelta(days=365)

        subscription.status = Subscription.Status.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.auto_renew = True

        # Save RebillId for recurring payments via T-Bank Charge
        if rebill_id:
            subscription.tbank_rebill_id = rebill_id  # Reuse field for T-Bank RebillId

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

        # Apply referral reward to referrer
        self._apply_referral_reward(subscription.user)

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

        try:
            if immediately:
                message = "Ваша подписка отменена"
            else:
                if subscription.current_period_end:
                    end_date = subscription.current_period_end.strftime('%d.%m.%Y')
                    message = f"Ваша подписка будет отменена {end_date}"
                else:
                    message = "Ваша подписка будет отменена"

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
        """
        Renew subscription using saved RebillId via T-Bank Charge.
        """
        rebill_id = subscription.tbank_rebill_id  # Stores T-Bank RebillId
        if not rebill_id:
            logger.warning(f"No saved RebillId for subscription {subscription.id}")
            return None

        if not subscription.auto_renew:
            logger.info(f"Auto-renew disabled for subscription {subscription.id}")
            return None

        plan = subscription.plan
        if plan.is_free:
            return None

        # Create recurring payment record
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=plan.price,
            status=SubscriptionPayment.Status.PENDING,
            is_recurring=True
        )

        # Test mode: auto-succeed
        if self.tbank.test_mode:
            self.process_successful_payment(payment, rebill_id)
            return payment

        try:
            amount_kopecks = int(payment.amount * 100)
            params = {
                "PaymentId": "",  # Will be set by Init
                "RebillId": rebill_id,
                "Amount": amount_kopecks,
            }

            # First, Init a new payment
            init_params = {
                "Amount": amount_kopecks,
                "OrderId": str(payment.id),
                "Description": f"Продление подписки {plan.name}"[:140],
                "CustomerKey": str(subscription.user_id),
                "DATA": {
                    "payment_id": str(payment.id),
                    "subscription_id": str(subscription.id),
                    "is_recurring": "true",
                },
            }

            if getattr(settings, "TBANK_SEND_RECEIPT", False):
                taxation = getattr(settings, "TBANK_TAXATION", "usn_income")
                init_params["Receipt"] = {
                    "Taxation": taxation,
                    "Items": [
                        {
                            "Name": f"Продление подписки {plan.name}"[:128],
                            "Price": amount_kopecks,
                            "Quantity": 1.0,
                            "Amount": amount_kopecks,
                            "Tax": "none",
                            "PaymentMethod": "full_payment",
                            "PaymentObject": "service",
                        }
                    ],
                }
                if subscription.user.email:
                    init_params["Receipt"]["Email"] = subscription.user.email

            init_data = self.tbank._request("Init", init_params)
            tbank_payment_id = str(init_data["PaymentId"])

            payment.external_payment_id = tbank_payment_id
            payment.save()

            # Charge using saved card (RebillId)
            charge_params = {
                "PaymentId": tbank_payment_id,
                "RebillId": rebill_id,
            }
            self.tbank._request("Charge", charge_params)

            logger.info(f"Initiated T-Bank Charge for subscription {subscription.id}")
            # Payment result will come via notification webhook
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
            "appointments_limit": appointments_limit if appointments_limit > 0 else -1,
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

    @transaction.atomic
    def _apply_referral_reward(self, referred_user: User):
        """Apply referral reward when a referred user subscribes to Pro."""
        if not referred_user.referred_by:
            return

        referral = Referral.objects.filter(
            referrer=referred_user.referred_by,
            referred_user=referred_user,
            status=Referral.Status.PENDING
        ).first()

        if not referral:
            return

        referrer = referred_user.referred_by

        try:
            referrer_sub = referrer.subscription
        except Subscription.DoesNotExist:
            referrer_sub = self.create_free_subscription(referrer)

        # If referrer is on free plan, upgrade to Pro for 1 month
        if referrer_sub.plan.is_free:
            user_type = referrer_sub.plan.user_type
            pro_plan = SubscriptionPlan.objects.filter(
                tier=SubscriptionPlan.Tier.PRO,
                user_type=user_type,
                period=SubscriptionPlan.Period.MONTHLY
            ).first()

            if pro_plan:
                now = timezone.now()
                referrer_sub.plan = pro_plan
                referrer_sub.status = Subscription.Status.ACTIVE
                referrer_sub.current_period_start = now
                referrer_sub.current_period_end = now + timedelta(days=30)
                referrer_sub.auto_renew = False
                referrer_sub.save()
        else:
            # If referrer already has Pro, extend by 30 days
            if referrer_sub.current_period_end:
                referrer_sub.current_period_end += timedelta(days=30)
                referrer_sub.save(update_fields=["current_period_end"])

        referral.status = Referral.Status.APPLIED
        referral.applied_at = timezone.now()
        referral.save()

        try:
            NotificationService.create_notification(
                user=referrer,
                notification_type="referral_reward",
                title="Реферальная награда",
                message=f"Ваш приглашённый {referred_user.full_name} оформил подписку! "
                        f"Вы получили 1 месяц Pro бесплатно.",
            )
        except Exception as e:
            logger.error(f"Error sending referral reward notification: {e}")

        logger.info(f"Applied referral reward for referrer {referrer.id}")
