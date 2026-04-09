from rest_framework import serializers
from .models import Expense, FinancialGoal


class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'amount', 'category', 'category_display',
            'description', 'date', 'is_recurring', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['master'] = self.context['request'].user.master_profile
        return super().create(validated_data)


class FinancialGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialGoal
        fields = ['id', 'target_amount', 'period', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        master_profile = self.context['request'].user.master_profile
        validated_data['master'] = master_profile
        # Deactivate previous goals
        FinancialGoal.objects.filter(
            master=master_profile, is_active=True
        ).update(is_active=False)
        validated_data['is_active'] = True
        return super().create(validated_data)
