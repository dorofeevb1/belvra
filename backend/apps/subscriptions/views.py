"""
Views for subscription management.
"""

import csv
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, F, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Referral, Subscription, SubscriptionPayment, SubscriptionPlan
from .serializers import (
    CancelSubscriptionSerializer,
    ChangePlanSerializer,
    CheckLimitSerializer,
    ReferralSerializer,
    ReferralStatsSerializer,
    SubscribeRequestSerializer,
    SubscribeResponseSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
    SubscriptionUsageSerializer,
)
from .services import SubscriptionService

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Подписки"],
    summary="Список планов подписок",
    description="Получение списка всех доступных планов подписок"
)
class SubscriptionPlanListView(generics.ListAPIView):
    """List available subscription plans."""

    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = SubscriptionPlan.objects.filter(is_active=True)

        # Filter by user_type if specified
        user_type = self.request.query_params.get("user_type")
        if user_type:
            queryset = queryset.filter(user_type=user_type)

        return queryset.order_by("user_type", "tier", "period")


@extend_schema(
    tags=["Подписки"],
    summary="Текущая подписка",
    description="Получение информации о текущей подписке пользователя"
)
class CurrentSubscriptionView(APIView):
    """Get current user subscription."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = SubscriptionService()
        subscription = service.get_or_create_free_subscription(request.user)

        # Auto-check pending payments: if subscription is pending and payment was confirmed in T-Bank
        if subscription.status == Subscription.Status.PENDING:
            self._try_activate_pending(subscription, service)

        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    def _try_activate_pending(self, subscription, service):
        """Check if a pending subscription has a confirmed payment in T-Bank."""
        pending_payment = SubscriptionPayment.objects.filter(
            subscription=subscription,
            status=SubscriptionPayment.Status.PENDING
        ).order_by('-created_at').first()

        if not pending_payment or not pending_payment.external_payment_id:
            return

        try:
            tbank_status = service.tbank.get_payment_status(pending_payment.external_payment_id)
            if tbank_status.get('tbank_status') == 'CONFIRMED' or tbank_status.get('status') == 'succeeded':
                # Payment confirmed — activate subscription
                rebill_id = None
                service.process_successful_payment(pending_payment, rebill_id)
                subscription.refresh_from_db()
                logger.info(f"Auto-activated subscription {subscription.id} from pending payment check")
        except Exception as e:
            logger.warning(f"Failed to check T-Bank status for payment {pending_payment.id}: {e}")


@extend_schema(
    tags=["Подписки"],
    summary="Статистика использования",
    description="Получение статистики использования лимитов подписки"
)
class SubscriptionUsageView(APIView):
    """Get subscription usage statistics."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = SubscriptionService()
        subscription = service.get_or_create_free_subscription(request.user)
        usage = service.get_usage_stats(subscription)
        serializer = SubscriptionUsageSerializer(data=usage)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Подписки"],
    summary="Оформить подписку",
    description="Оформление подписки на выбранный план",
    request=SubscribeRequestSerializer,
    responses={200: SubscribeResponseSerializer}
)
class SubscribeView(APIView):
    """Subscribe to a plan."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscribeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = serializer.validated_data["plan_id"]
        payment_method = serializer.validated_data.get("payment_method", "")
        return_url = serializer.validated_data.get("return_url", settings.FRONTEND_URL + "/subscription/success")
        save_payment_method = serializer.validated_data.get("save_payment_method", True)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "План подписки не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Early adopters cannot change their lifetime Pro subscription
        if request.user.is_early_adopter:
            try:
                existing = request.user.subscription
                if existing.plan.is_pro:
                    return Response(
                        {"error": "Early adopters cannot change their lifetime Pro subscription."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Subscription.DoesNotExist:
                pass

        service = SubscriptionService()
        result = service.subscribe(
            user=request.user,
            plan=plan,
            return_url=return_url,
            save_payment_method=save_payment_method,
            payment_method=payment_method or None
        )

        response_serializer = SubscribeResponseSerializer(data=result)
        response_serializer.is_valid()
        return Response(response_serializer.data)


@extend_schema(
    tags=["Подписки"],
    summary="Отменить подписку",
    description="Отмена автопродления подписки",
    request=CancelSubscriptionSerializer
)
class CancelSubscriptionView(APIView):
    """Cancel subscription."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CancelSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Подписка не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        if subscription.plan.is_free:
            return Response(
                {"error": "Бесплатную подписку нельзя отменить"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Early adopters cannot cancel their lifetime Pro subscription
        if request.user.is_early_adopter and subscription.plan.is_pro:
            return Response(
                {"error": "Early adopters cannot change their lifetime Pro subscription."},
                status=status.HTTP_403_FORBIDDEN
            )

        service = SubscriptionService()
        subscription = service.cancel_subscription(
            subscription=subscription,
            immediately=serializer.validated_data.get("immediately", False),
            reason=serializer.validated_data.get("reason", "")
        )

        return Response(SubscriptionSerializer(subscription).data)


@extend_schema(
    tags=["Подписки"],
    summary="Возобновить подписку",
    description="Возобновление автопродления подписки"
)
class ReactivateSubscriptionView(APIView):
    """Reactivate cancelled subscription."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Подписка не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not subscription.cancel_at_period_end:
            return Response(
                {"error": "Подписка не была отменена"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = SubscriptionService()
        try:
            subscription = service.reactivate_subscription(subscription)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SubscriptionSerializer(subscription).data)


@extend_schema(
    tags=["Подписки"],
    summary="Сменить план",
    description="Смена плана подписки",
    request=ChangePlanSerializer
)
class ChangePlanView(APIView):
    """Change subscription plan."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_id = serializer.validated_data["plan_id"]
        immediately = serializer.validated_data.get("immediately", False)

        try:
            new_plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"error": "План подписки не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Подписка не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Early adopters cannot change their lifetime Pro subscription
        if request.user.is_early_adopter and subscription.plan.is_pro:
            return Response(
                {"error": "Early adopters cannot change their lifetime Pro subscription."},
                status=status.HTTP_403_FORBIDDEN
            )

        if new_plan.user_type != subscription.plan.user_type:
            return Response(
                {"error": "Невозможно сменить тип плана"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = SubscriptionService()
        result = service.change_plan(subscription, new_plan, immediately)

        return Response(result)


@extend_schema(
    tags=["Подписки"],
    summary="История платежей",
    description="Получение истории платежей за подписку"
)
class SubscriptionPaymentsView(generics.ListAPIView):
    """List subscription payments."""

    serializer_class = SubscriptionPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            subscription = self.request.user.subscription
            return SubscriptionPayment.objects.filter(
                subscription=subscription
            ).order_by("-created_at")
        except Subscription.DoesNotExist:
            return SubscriptionPayment.objects.none()


@extend_schema(
    tags=["Подписки"],
    summary="Проверка лимита",
    description="Проверка доступности лимита (appointments/services/portfolio)",
    responses={200: CheckLimitSerializer}
)
class CheckLimitView(APIView):
    """Check if a specific limit is reached."""

    permission_classes = [IsAuthenticated]

    def get(self, request, limit_type):
        valid_types = ["appointments", "services", "portfolio"]
        if limit_type not in valid_types:
            return Response(
                {"error": f"Неверный тип лимита. Допустимые: {', '.join(valid_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = SubscriptionService()
        subscription = service.get_or_create_free_subscription(request.user)
        result = service.check_limit(subscription, limit_type)

        serializer = CheckLimitSerializer(data=result)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Подписки"],
    summary="Webhook для оплаты",
    description="Обработка уведомлений от T-Bank для подписок"
)
class SubscriptionWebhookView(APIView):
    """Handle T-Bank notifications for subscription payments."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data

        from apps.core.tbank import TBankService
        tbank = TBankService()

        # Verify token signature
        if not tbank.test_mode and not tbank.verify_notification_token(data):
            logger.warning("Invalid T-Bank subscription notification token")
            return Response("INVALID TOKEN", status=status.HTTP_401_UNAUTHORIZED)

        order_id = data.get("OrderId")
        tbank_status = data.get("Status")
        rebill_id = str(data.get("RebillId", "")) if data.get("RebillId") else None

        logger.info(f"T-Bank subscription notification: OrderId={order_id}, Status={tbank_status}")

        if not order_id:
            return Response("OK", status=status.HTTP_200_OK)

        try:
            payment = SubscriptionPayment.objects.get(id=order_id)
        except SubscriptionPayment.DoesNotExist:
            logger.warning(f"SubscriptionPayment with OrderId={order_id} not found")
            return Response("OK", status=status.HTTP_200_OK)

        if tbank_status == "CONFIRMED":
            if payment.status == SubscriptionPayment.Status.PENDING:
                service = SubscriptionService()
                service.process_successful_payment(payment, rebill_id)
                logger.info(f"Subscription payment {payment.id} confirmed")

        elif tbank_status in ("REJECTED", "DEADLINE_EXPIRED"):
            payment.status = SubscriptionPayment.Status.FAILED
            payment.error_message = f"T-Bank: {tbank_status}"
            payment.save()

            subscription = payment.subscription
            if subscription.status == Subscription.Status.PENDING:
                subscription.status = Subscription.Status.CANCELLED
                subscription.save()
            logger.info(f"Subscription payment {payment.id} rejected: {tbank_status}")

        elif tbank_status == "REVERSED":
            payment.status = SubscriptionPayment.Status.CANCELLED
            payment.save()

            # Deactivate subscription on chargeback/reversal
            subscription = payment.subscription
            if subscription.status == Subscription.Status.ACTIVE:
                subscription.status = Subscription.Status.CANCELLED
                subscription.cancelled_at = timezone.now()
                subscription.auto_renew = False
                subscription.save()
            logger.info(f"Subscription payment {payment.id} reversed, subscription deactivated")

        # T-Bank requires "OK" in response body
        return Response("OK", status=status.HTTP_200_OK)


@extend_schema(
    tags=["Подписки"],
    summary="Тестовое подтверждение оплаты",
    description="Подтверждение тестового платежа (только для test mode)"
)
class TestConfirmPaymentView(APIView):
    """Confirm a test payment (for development only)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")

        if not payment_id:
            return Response(
                {"error": "payment_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = SubscriptionPayment.objects.get(id=payment_id)

            # Check if this is a test payment
            if not payment.external_payment_id or not (
                payment.external_payment_id.startswith("test_") or
                payment.external_payment_id.startswith("tbank_sub_test_")
            ):
                return Response(
                    {"error": "Это не тестовый платёж"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check ownership
            if payment.subscription.user != request.user:
                return Response(
                    {"error": "Нет доступа к этому платежу"},
                    status=status.HTTP_403_FORBIDDEN
                )

            if payment.status != SubscriptionPayment.Status.PENDING:
                return Response(
                    {"error": "Платёж уже обработан"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = SubscriptionService()
            service.process_successful_payment(payment, "test_method_id")

            return Response({
                "status": "success",
                "message": "Тестовый платёж подтверждён",
                "subscription": SubscriptionSerializer(payment.subscription).data
            })

        except SubscriptionPayment.DoesNotExist:
            return Response(
                {"error": "Платёж не найден"},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Реферальная программа"],
    summary="Статистика рефералов",
    description="Реферальный код, количество приглашённых, полученные награды"
)
class ReferralStatsView(APIView):
    """Get referral statistics for current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        referrals = Referral.objects.filter(referrer=user)
        total_referrals = referrals.count()
        rewards_applied = referrals.filter(status=Referral.Status.APPLIED).count()
        rewards_pending = referrals.filter(status=Referral.Status.PENDING).count()

        return Response(ReferralStatsSerializer({
            "referral_code": user.referral_code,
            "total_referrals": total_referrals,
            "rewards_applied": rewards_applied,
            "rewards_pending": rewards_pending,
            "referrals": ReferralSerializer(referrals, many=True).data,
        }).data)


@extend_schema(
    tags=["Реферальная программа"],
    summary="Список рефералов",
    description="Список приглашённых пользователей"
)
class ReferralListView(generics.ListAPIView):
    """List referrals for current user."""

    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Referral.objects.filter(
            referrer=self.request.user
        ).select_related("referred_user")


@extend_schema(
    tags=["Подписки"],
    summary="Экспорт данных в CSV",
    description="Экспорт записей или финансовых данных (только PRO)"
)
class ExportDataView(APIView):
    """Export user data as CSV. Requires export_data_enabled in subscription."""

    permission_classes = [IsAuthenticated]

    VALID_TYPES = ("appointments", "finances")

    def get(self, request, export_type):
        sub = getattr(request.user, "subscription", None)
        if not sub or not sub.is_active or not sub.plan.export_data_enabled:
            return Response(
                {"error": "Экспорт данных доступен только на тарифе PRO"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if export_type not in self.VALID_TYPES:
            return Response(
                {"error": f"Допустимые типы: {', '.join(self.VALID_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.appointments.models import Appointment

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{export_type}.csv"'
        response.write("\ufeff")  # BOM for Excel
        writer = csv.writer(response)

        if not hasattr(request.user, "master_profile"):
            # Client export
            appointments = Appointment.objects.filter(
                client=request.user
            ).select_related("master__user", "service", "master_service").order_by("-date")

            if export_type == "appointments":
                writer.writerow(["Дата", "Время", "Мастер", "Услуга", "Цена", "Статус"])
                for a in appointments:
                    svc = a.master_service.name if a.master_service else (a.service.name if a.service else "")
                    writer.writerow([
                        a.date.strftime("%d.%m.%Y"), a.start_time.strftime("%H:%M"),
                        a.master.user.full_name, svc, a.price,
                        a.get_status_display(),
                    ])
            else:  # finances
                writer.writerow(["Дата", "Услуга", "Мастер", "Цена"])
                for a in appointments.filter(status=Appointment.Status.COMPLETED):
                    svc = a.master_service.name if a.master_service else (a.service.name if a.service else "")
                    writer.writerow([
                        a.date.strftime("%d.%m.%Y"), svc, a.master.user.full_name,
                        a.price,
                    ])
        else:
            # Master export
            master = request.user.master_profile
            appointments = Appointment.objects.filter(
                master=master
            ).select_related("client", "service", "master_service").order_by("-date")

            if export_type == "appointments":
                writer.writerow(["Дата", "Время", "Клиент", "Услуга", "Цена", "Статус"])
                for a in appointments:
                    svc = a.master_service.name if a.master_service else (a.service.name if a.service else "")
                    writer.writerow([
                        a.date.strftime("%d.%m.%Y"), a.start_time.strftime("%H:%M"),
                        a.client.full_name, svc, a.price, a.get_status_display(),
                    ])
            else:  # finances
                writer.writerow([
                    "Дата", "Клиент", "Услуга", "Доход", "Материалы", "Чистый доход",
                ])
                for a in appointments.filter(status=Appointment.Status.COMPLETED):
                    svc = a.master_service.name if a.master_service else (a.service.name if a.service else "")
                    writer.writerow([
                        a.date.strftime("%d.%m.%Y"), a.client.full_name, svc,
                        a.price, a.materials_cost, a.price - a.materials_cost,
                    ])

        return response


@extend_schema(
    tags=["Подписки"],
    summary="Аналитика",
    description="Данные аналитики в зависимости от уровня подписки"
)
class AnalyticsView(APIView):
    """Return analytics data based on subscription analytics_level."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = getattr(request.user, "subscription", None)
        level = sub.plan.analytics_level if (sub and sub.is_active) else "none"

        data = {"level": level}

        if level == "none":
            # Only basic counters
            if hasattr(request.user, "master_profile"):
                master = request.user.master_profile
                data["total_appointments"] = master.master_appointments.filter(
                    status="completed"
                ).count()
                data["rating"] = float(master.rating)
            return Response(data)

        from apps.appointments.models import Appointment

        if not hasattr(request.user, "master_profile"):
            return Response(data)

        master = request.user.master_profile
        completed = Appointment.objects.filter(master=master, status="completed")

        # BASIC: 7-day stats
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        weekly = completed.filter(date__gte=seven_days_ago)

        data["weekly_appointments"] = (
            weekly.annotate(day=TruncDate("date"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        data["weekly_revenue"] = float(weekly.aggregate(total=Sum("price"))["total"] or 0)

        from apps.services.models import MasterService
        data["service_popularity"] = list(
            completed.values(
                name=Coalesce(
                    F("master_service__custom_name"),
                    F("master_service__service__name"),
                    Value("Без названия"),
                )
            )
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        if level == "advanced":
            # ADVANCED: 30/90-day stats
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            ninety_days_ago = timezone.now().date() - timedelta(days=90)

            monthly = completed.filter(date__gte=thirty_days_ago)
            quarterly = completed.filter(date__gte=ninety_days_ago)

            data["monthly_revenue"] = float(monthly.aggregate(total=Sum("price"))["total"] or 0)
            data["quarterly_revenue"] = float(quarterly.aggregate(total=Sum("price"))["total"] or 0)

            # Conversion rate: confirmed+completed / total
            all_monthly = Appointment.objects.filter(master=master, date__gte=thirty_days_ago)
            total_count = all_monthly.count()
            if total_count > 0:
                success_count = all_monthly.filter(
                    status__in=["confirmed", "completed"]
                ).count()
                data["conversion_rate"] = round(success_count / total_count * 100, 1)
            else:
                data["conversion_rate"] = 0

            # Rating trend (monthly avg)
            from apps.appointments.models import Review
            data["rating_trend"] = list(
                Review.objects.filter(
                    appointment__master=master,
                    created_at__date__gte=ninety_days_ago,
                )
                .annotate(month=TruncDate("created_at"))
                .values("month")
                .annotate(avg_rating=Avg("rating"))
                .order_by("month")
            )

            # Top services by revenue
            data["top_services_by_revenue"] = list(
                monthly.values(
                    name=Coalesce(
                        F("master_service__custom_name"),
                        F("master_service__service__name"),
                        Value("Без названия"),
                    )
                )
                .annotate(revenue=Sum("price"), count=Count("id"))
                .order_by("-revenue")[:10]
            )

        return Response(data)
