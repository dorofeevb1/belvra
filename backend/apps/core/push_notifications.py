"""
Push notification service for mobile apps.
Supports Firebase Cloud Messaging (FCM) for both iOS and Android.
"""

import logging
from typing import Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class PushNotificationService:
    """
    Service for sending push notifications via Firebase Cloud Messaging.

    Setup required:
    1. Create Firebase project at https://console.firebase.google.com
    2. Download service account JSON file
    3. Set FIREBASE_CREDENTIALS_PATH in settings
    4. Install firebase-admin: pip install firebase-admin
    """

    _initialized = False

    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK."""
        if cls._initialized:
            return

        try:
            import firebase_admin
            from firebase_admin import credentials

            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)

            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.warning("FIREBASE_CREDENTIALS_PATH not set. Push notifications disabled.")
        except ImportError:
            logger.warning("firebase-admin not installed. Push notifications disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")

    @classmethod
    def send_to_token(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        badge: Optional[int] = None,
        sound: str = "default"
    ) -> bool:
        """
        Send push notification to a single device token.

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload
            badge: Badge number for iOS
            sound: Sound name

        Returns:
            True if sent successfully, False otherwise
        """
        if not cls._initialized:
            cls.initialize()

        if not cls._initialized:
            logger.warning("Firebase not initialized. Skipping push notification.")
            return False

        try:
            from firebase_admin import messaging

            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body
            )

            # Build platform-specific configs
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound=sound,
                    click_action="FLUTTER_NOTIFICATION_CLICK"
                )
            )

            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=sound,
                        badge=badge
                    )
                )
            )

            # Build message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=token,
                android=android_config,
                apns=apns_config
            )

            # Send
            response = messaging.send(message)
            logger.info(f"Push notification sent successfully: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False

    @classmethod
    def send_to_tokens(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None,
        badge: Optional[int] = None,
        sound: str = "default"
    ) -> Dict[str, int]:
        """
        Send push notification to multiple device tokens.

        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            badge: Badge number for iOS
            sound: Sound name

        Returns:
            Dict with success_count and failure_count
        """
        if not cls._initialized:
            cls.initialize()

        if not cls._initialized:
            logger.warning("Firebase not initialized. Skipping push notifications.")
            return {"success_count": 0, "failure_count": len(tokens)}

        if not tokens:
            return {"success_count": 0, "failure_count": 0}

        try:
            from firebase_admin import messaging

            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body
            )

            # Build platform-specific configs
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound=sound,
                    click_action="FLUTTER_NOTIFICATION_CLICK"
                )
            )

            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=sound,
                        badge=badge
                    )
                )
            )

            # Build multicast message
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=tokens,
                android=android_config,
                apns=apns_config
            )

            # Send
            response = messaging.send_each_for_multicast(message)

            result = {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }

            logger.info(f"Push notifications sent: {result}")

            # Handle failed tokens (deactivate them)
            if response.failure_count > 0:
                cls._handle_failed_tokens(tokens, response.responses)

            return result

        except Exception as e:
            logger.error(f"Failed to send push notifications: {e}")
            return {"success_count": 0, "failure_count": len(tokens)}

    @classmethod
    def _handle_failed_tokens(cls, tokens: List[str], responses: List) -> None:
        """Deactivate tokens that failed to receive notifications."""
        from firebase_admin import messaging
        from .models import DeviceToken

        failed_tokens = []
        for idx, response in enumerate(responses):
            if not response.success:
                error = response.exception
                # Check if token is invalid
                if isinstance(error, (
                    messaging.UnregisteredError,
                    messaging.InvalidArgumentError
                )):
                    failed_tokens.append(tokens[idx])

        if failed_tokens:
            DeviceToken.objects.filter(token__in=failed_tokens).update(is_active=False)
            logger.info(f"Deactivated {len(failed_tokens)} invalid device tokens")

    @classmethod
    def send_to_user(
        cls,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        notification_type: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Send push notification to all active devices of a user.

        Args:
            user_id: User UUID
            title: Notification title
            body: Notification body
            data: Additional data payload
            notification_type: Type of notification for routing in app

        Returns:
            Dict with success_count and failure_count
        """
        from .models import DeviceToken

        tokens = list(
            DeviceToken.objects.filter(
                user_id=user_id,
                is_active=True
            ).values_list('token', flat=True)
        )

        if not tokens:
            logger.info(f"No active device tokens for user {user_id}")
            return {"success_count": 0, "failure_count": 0}

        # Add notification type to data
        if notification_type:
            data = data or {}
            data["type"] = notification_type

        return cls.send_to_tokens(tokens, title, body, data)


def send_push_notification(
    user_id: str,
    title: str,
    body: str,
    data: Optional[Dict] = None,
    notification_type: Optional[str] = None
) -> Dict[str, int]:
    """
    Convenience function to send push notification to a user.

    This is the main function to use from other parts of the application.
    """
    return PushNotificationService.send_to_user(
        user_id=user_id,
        title=title,
        body=body,
        data=data,
        notification_type=notification_type
    )
