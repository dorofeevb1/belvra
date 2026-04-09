from django.db import models

from apps.core.models import TimeStampedModel
from apps.users.models import MasterProfile


class Expense(TimeStampedModel):
    """Master's expense tracking."""

    class Category(models.TextChoices):
        RENT = 'rent', 'Аренда'
        MATERIALS = 'materials', 'Материалы'
        TOOLS = 'tools', 'Инструменты'
        EDUCATION = 'education', 'Обучение'
        TRANSPORT = 'transport', 'Транспорт'
        OTHER = 'other', 'Другое'

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.CharField(max_length=255, blank=True, default='')
    date = models.DateField()
    is_recurring = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['master', 'date']),
            models.Index(fields=['master', 'category']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.amount}₽ ({self.date})"


class FinancialGoal(TimeStampedModel):
    """Master's financial goal."""

    class Period(models.TextChoices):
        MONTH = 'month', 'Месяц'
        YEAR = 'year', 'Год'

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name='financial_goals'
    )
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    period = models.CharField(max_length=10, choices=Period.choices, default='month')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Цель: {self.target_amount}₽ / {self.get_period_display()}"
