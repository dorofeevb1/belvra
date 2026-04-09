"""Signals for services domain — sync denormalized fields."""

from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import PortfolioItem, PortfolioLike


@receiver(post_save, sender=PortfolioLike)
def on_portfolio_like_created(sender, instance, created, **kwargs):
    """Increment likes_count atomically when a like is added."""
    if created:
        PortfolioItem.objects.filter(pk=instance.portfolio_item_id).update(
            likes_count=F("likes_count") + 1
        )


@receiver(post_delete, sender=PortfolioLike)
def on_portfolio_like_deleted(sender, instance, **kwargs):
    """Decrement likes_count atomically when a like is removed."""
    PortfolioItem.objects.filter(pk=instance.portfolio_item_id).update(
        likes_count=F("likes_count") - 1
    )
