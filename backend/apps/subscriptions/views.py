"""
Views for subscription management.
"""

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Subscription, SubscriptionPayment, SubscriptionPlan
from .serializers import (
    CancelSubscriptionSerializer,
    ChangePlanSerializer,
    CheckLimitSerializer,
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
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)


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

        from apps.payments.services import TBankService
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
            logger.info(f"Subscription payment {payment.id} reversed")

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
