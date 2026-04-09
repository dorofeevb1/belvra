from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    MasterLocation,
    MasterNotificationSettings,
    MasterProfile,
    MasterSocialLinks,
    User,
)


@receiver(post_save, sender=User)
def create_master_profile(sender, instance, created, **kwargs):
    """Create MasterProfile when a User with role=master is created."""
    if created and instance.role == User.Role.MASTER:
        MasterProfile.objects.create(user=instance)


@receiver(post_save, sender=MasterProfile)
def create_master_related_objects(sender, instance, created, **kwargs):
    """Create related O2O objects when MasterProfile is created."""
    if created:
        MasterLocation.objects.get_or_create(master=instance)
        MasterSocialLinks.objects.get_or_create(master=instance)
        MasterNotificationSettings.objects.get_or_create(master=instance)
