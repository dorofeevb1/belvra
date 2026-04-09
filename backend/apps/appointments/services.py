"""Business logic services for appointments domain."""

import logging

from django.db.models import Avg, Count

logger = logging.getLogger(__name__)


def recalculate_master_rating(master_profile_id):
    """Recalculate master's rating and reviews_count from all reviews.

    Uses atomic update to avoid race conditions.
    """
    from apps.appointments.models import Review
    from apps.users.models import MasterProfile

    result = Review.objects.filter(
        appointment__master_id=master_profile_id
    ).aggregate(
        avg=Avg("rating"),
        count=Count("id")
    )

    MasterProfile.objects.filter(pk=master_profile_id).update(
        rating=round(result["avg"] or 0, 2),
        reviews_count=result["count"]
    )
    logger.debug(
        "Recalculated rating for master %s: avg=%s, count=%s",
        master_profile_id, result["avg"], result["count"]
    )
