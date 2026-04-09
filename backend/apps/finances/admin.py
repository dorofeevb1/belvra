from django.contrib import admin
from .models import Expense, FinancialGoal


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['master', 'category', 'amount', 'date', 'is_recurring']
    list_filter = ['category', 'is_recurring', 'date']
    search_fields = ['master__name', 'description']


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = ['master', 'target_amount', 'period', 'is_active']
    list_filter = ['period', 'is_active']
