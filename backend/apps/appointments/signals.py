"""Signals for appointments domain — sync denormalized fields."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review
from .services import recalculate_master_rating


@receiver(post_save, sender=Review)
def on_review_saved(sender, instance, **kwargs):
    """Recalculate master rating when a review is created or updated."""
    recalculate_master_rating(instance.appointment.master_id)


@receiver(post_delete, sender=Review)
def on_review_deleted(sender, instance, **kwargs):
    """Recalculate master rating when a review is deleted."""
    recalculate_master_rating(instance.appointment.master_id)
