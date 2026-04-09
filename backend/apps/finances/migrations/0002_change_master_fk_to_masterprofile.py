"""Change Expense and FinancialGoal FK from User to MasterProfile.

This migration:
1. Adds a temporary master_profile FK (nullable)
2. Migrates data: looks up MasterProfile by user_id
3. Removes old master FK to User
4. Renames master_profile -> master
5. Removes manual id field (now inherited from TimeStampedModel parent)
"""

import django.db.models.deletion
from django.db import migrations, models


def migrate_expense_fk(apps, schema_editor):
    """Populate master_profile FK from existing User FK."""
    Expense = apps.get_model("finances", "Expense")
    MasterProfile = apps.get_model("users", "MasterProfile")
    for expense in Expense.objects.all().iterator():
        try:
            mp = MasterProfile.objects.get(user_id=expense.master_id)
            expense.master_profile_id = mp.pk
            expense.save(update_fields=["master_profile_id"])
        except MasterProfile.DoesNotExist:
            pass  # orphan expense — will be cleaned up


def migrate_goal_fk(apps, schema_editor):
    """Populate master_profile FK from existing User FK."""
    FinancialGoal = apps.get_model("finances", "FinancialGoal")
    MasterProfile = apps.get_model("users", "MasterProfile")
    for goal in FinancialGoal.objects.all().iterator():
        try:
            mp = MasterProfile.objects.get(user_id=goal.master_id)
            goal.master_profile_id = mp.pk
            goal.save(update_fields=["master_profile_id"])
        except MasterProfile.DoesNotExist:
            pass


def reverse_migrate(apps, schema_editor):
    """Reverse: populate master (User) FK from master_profile."""
    Expense = apps.get_model("finances", "Expense")
    for expense in Expense.objects.select_related("master_profile").all():
        if expense.master_profile:
            expense.master_id = expense.master_profile.user_id
            expense.save(update_fields=["master_id"])

    FinancialGoal = apps.get_model("finances", "FinancialGoal")
    for goal in FinancialGoal.objects.select_related("master_profile").all():
        if goal.master_profile:
            goal.master_id = goal.master_profile.user_id
            goal.save(update_fields=["master_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("finances", "0001_initial"),
        ("users", "0011_user_soft_delete"),
    ]

    operations = [
        # Step 1: Add temporary master_profile FK (nullable)
        migrations.AddField(
            model_name="expense",
            name="master_profile",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="expenses_new",
                to="users.masterprofile",
            ),
        ),
        migrations.AddField(
            model_name="financialgoal",
            name="master_profile",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="financial_goals_new",
                to="users.masterprofile",
            ),
        ),

        # Step 2: Migrate data
        migrations.RunPython(migrate_expense_fk, migrations.RunPython.noop),
        migrations.RunPython(migrate_goal_fk, migrations.RunPython.noop),

        # Step 3: Remove old master FK to User
        migrations.RemoveField(
            model_name="expense",
            name="master",
        ),
        migrations.RemoveField(
            model_name="financialgoal",
            name="master",
        ),

        # Step 4: Rename master_profile -> master
        migrations.RenameField(
            model_name="expense",
            old_name="master_profile",
            new_name="master",
        ),
        migrations.RenameField(
            model_name="financialgoal",
            old_name="master_profile",
            new_name="master",
        ),

        # Step 5: Make master non-nullable
        migrations.AlterField(
            model_name="expense",
            name="master",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="expenses",
                to="users.masterprofile",
            ),
        ),
        migrations.AlterField(
            model_name="financialgoal",
            name="master",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="financial_goals",
                to="users.masterprofile",
            ),
        ),
    ]
