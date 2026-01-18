from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MasterProfile, User


@receiver(post_save, sender=User)
def create_master_profile(sender, instance, created, **kwargs):
    """Create MasterProfile when a User with role=master is created."""
    if created and instance.role == User.Role.MASTER:
        MasterProfile.objects.create(user=instance)
