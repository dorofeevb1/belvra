"""Add CheckConstraints and convert unique_together to UniqueConstraint."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0009_appointment_client_set_null"),
    ]

    operations = [
        # WorkSchedule: unique_together → UniqueConstraint + CheckConstraint
        migrations.AlterUniqueTogether(
            name="workschedule",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="workschedule",
            constraint=models.UniqueConstraint(
                fields=["master", "weekday"],
                name="unique_master_weekday",
            ),
        ),
        migrations.AddConstraint(
            model_name="workschedule",
            constraint=models.CheckConstraint(
                check=models.Q(start_time__lt=models.F("end_time")),
                name="schedule_start_before_end",
            ),
        ),

        # ClientNote: unique_together → UniqueConstraint
        migrations.AlterUniqueTogether(
            name="clientnote",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="clientnote",
            constraint=models.UniqueConstraint(
                fields=["master", "client"],
                name="unique_master_client_note",
            ),
        ),

        # Appointment: CheckConstraints
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.CheckConstraint(
                check=models.Q(start_time__lt=models.F("end_time")),
                name="appt_start_before_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.CheckConstraint(
                check=models.Q(price__gte=0),
                name="appt_price_non_negative",
            ),
        ),

        # Review: CheckConstraint
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_1_to_5",
            ),
        ),
    ]
