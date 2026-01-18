from celery import shared_task
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


@shared_task
def cleanup_expired_tokens():
    """Remove expired tokens from the blacklist."""
    OutstandingToken.objects.filter(expires_at__lt=timezone.now()).delete()
    return "Expired tokens cleaned up"
