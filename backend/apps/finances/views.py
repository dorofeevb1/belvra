from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from .models import Expense, FinancialGoal
from .serializers import ExpenseSerializer, FinancialGoalSerializer


def get_period_range(period, date_from=None, date_to=None):
    """Get date range for a given period."""
    now = timezone.now().date()
    if date_from and date_to:
        return date_from, date_to
    if period == 'week':
        start = now - timedelta(days=now.weekday())
        return start, now
    elif period == 'year':
        from datetime import date
        return date(now.year, 1, 1), now
    else:  # month
        from datetime import date
        return date(now.year, now.month, 1), now


def get_prev_period_range(period, start, end):
    """Get the previous period range for comparison."""
    delta = end - start
    return start - delta - timedelta(days=1), start - timedelta(days=1)


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        period = request.query_params.get('period', 'month')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if date_from:
            from datetime import datetime
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if date_to:
            from datetime import datetime
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        start, end = get_period_range(period, date_from, date_to)
        prev_start, prev_end = get_prev_period_range(period, start, end)

        # Current period appointments
        appointments = Appointment.objects.filter(
            master__user=user,
            status='completed',
            date__range=(start, end),
        )

        # Previous period
        prev_appointments = Appointment.objects.filter(
            master__user=user,
            status='completed',
            date__range=(prev_start, prev_end),
        )

        # Income
        agg = appointments.aggregate(
            total_income=Sum('price'),
            materials_total=Sum('materials_cost'),
            count=Count('id'),
            avg_check=Avg('price'),
        )
        total_income = agg['total_income'] or Decimal('0')
        materials_cost = agg['materials_total'] or Decimal('0')
        appointments_count = agg['count'] or 0
        avg_check = agg['avg_check'] or Decimal('0')

        # Manual expenses
        master_profile = getattr(user, 'master_profile', None)
        manual_expenses_total = Expense.objects.filter(
            master=master_profile,
            date__range=(start, end),
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_expenses = materials_cost + manual_expenses_total
        net_profit = total_income - total_expenses

        # Previous period income for comparison
        prev_income = prev_appointments.aggregate(
            total=Sum('price'))['total'] or Decimal('0')
        change_percent = 0
        if prev_income > 0:
            change_percent = float(
                (total_income - prev_income) / prev_income * 100
            )

        # Chart data — group by day for week/month, by month for year
        from django.db.models.functions import TruncDate, TruncMonth
        chart_data = []

        if period == 'year':
            # Group by month
            monthly_income = dict(
                appointments.annotate(month=TruncMonth('date'))
                .values('month')
                .annotate(income=Sum('price'))
                .values_list('month', 'income')
            )
            monthly_expenses = dict(
                Expense.objects.filter(master=master_profile, date__range=(start, end))
                .annotate(month=TruncMonth('date'))
                .values('month')
                .annotate(total=Sum('amount'))
                .values_list('month', 'total')
            )
            monthly_materials = dict(
                appointments.annotate(month=TruncMonth('date'))
                .values('month')
                .annotate(mat=Sum('materials_cost'))
                .values_list('month', 'mat')
            )
            from datetime import date as date_cls
            for m in range(1, end.month + 1):
                month_date = date_cls(end.year, m, 1)
                inc = float(monthly_income.get(month_date, 0) or 0)
                exp = float(monthly_expenses.get(month_date, 0) or 0) + float(
                    monthly_materials.get(month_date, 0) or 0
                )
                month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                               'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
                chart_data.append({
                    'date': month_date.isoformat(),
                    'label': month_names[m - 1],
                    'income': inc,
                    'expenses': exp,
                })
        else:
            # Group by day
            daily_income = dict(
                appointments.annotate(day=TruncDate('date'))
                .values('day')
                .annotate(income=Sum('price'))
                .values_list('day', 'income')
            )
            daily_expenses = dict(
                Expense.objects.filter(master=master_profile, date__range=(start, end))
                .values('date')
                .annotate(total=Sum('amount'))
                .values_list('date', 'total')
            )
            daily_materials = dict(
                appointments.annotate(day=TruncDate('date'))
                .values('day')
                .annotate(mat=Sum('materials_cost'))
                .values_list('day', 'mat')
            )
            current = start
            while current <= end:
                inc = float(daily_income.get(current, 0) or 0)
                exp = float(daily_expenses.get(current, 0) or 0) + float(
                    daily_materials.get(current, 0) or 0
                )
                chart_data.append({
                    'date': current.isoformat(),
                    'income': inc,
                    'expenses': exp,
                })
                current += timedelta(days=1)

        # Top services
        top_services = list(
            appointments.values(
                name=F('master_service__custom_name')
            ).annotate(
                income=Sum('price'),
                count=Count('id'),
            ).order_by('-income')[:5]
        )
        # Fix names: use service name if custom_name is empty
        for s in top_services:
            if not s['name']:
                # Try to get from related service
                s['name'] = 'Услуга'

        # Top clients
        from django.db.models.functions import Concat
        from django.db.models import Value
        top_clients = list(
            appointments.filter(client__isnull=False).annotate(
                full_client_name=Concat(
                    F('client__first_name'), Value(' '), F('client__last_name')
                )
            ).values(
                'full_client_name',
            ).annotate(
                total_spent=Sum('price'),
                visits=Count('id'),
            ).order_by('-total_spent')[:5]
        )
        # Rename key for frontend
        for c in top_clients:
            c['name'] = c.pop('full_client_name', '').strip()

        # Goal
        goal_data = None
        goal = FinancialGoal.objects.filter(
            master=master_profile, is_active=True
        ).first()
        if goal:
            days_in_period = (end - start).days + 1
            days_elapsed = (timezone.now().date() - start).days + 1
            days_left = max(0, days_in_period - days_elapsed)
            daily_rate = (
                float(total_income) / days_elapsed if days_elapsed > 0 else 0
            )
            forecast = daily_rate * days_in_period
            progress = (
                float(total_income) / float(goal.target_amount) * 100
                if goal.target_amount > 0 else 0
            )
            daily_needed = (
                (float(goal.target_amount) - float(total_income)) / days_left
                if days_left > 0 else 0
            )
            goal_data = {
                'target': float(goal.target_amount),
                'current': float(total_income),
                'progress_percent': round(min(progress, 100), 1),
                'days_left': days_left,
                'forecast': round(forecast),
                'daily_needed': round(max(daily_needed, 0)),
            }

        # Tax calculation
        tax_data = None
        master_profile = getattr(user, 'master_profile', None)
        if master_profile and master_profile.tax_system != 'none':
            tax_system = master_profile.tax_system
            rate = {
                'self_employed': Decimal('0.04'),
                'ip_usn6': Decimal('0.06'),
                'ip_usn15': Decimal('0.15'),
            }.get(tax_system, Decimal('0'))

            if tax_system == 'ip_usn15':
                tax_base = net_profit
            else:
                tax_base = total_income

            tax_amount = tax_base * rate
            tax_data = {
                'system': tax_system,
                'rate': float(rate),
                'amount': float(max(tax_amount, 0)),
                'label': f"Отложите на налоги: {int(max(tax_amount, 0)):,}₽".replace(',', ' '),
            }

        # Expense breakdown by category
        expense_breakdown = list(
            Expense.objects.filter(master=master_profile, date__range=(start, end))
            .values('category')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        # Add materials from appointments as a category
        if materials_cost > 0:
            expense_breakdown.insert(0, {
                'category': 'materials',
                'total': float(materials_cost),
            })

        return Response({
            'period': period,
            'date_from': start.isoformat(),
            'date_to': end.isoformat(),
            'total_income': float(total_income),
            'total_expenses': float(total_expenses),
            'materials_cost': float(materials_cost),
            'manual_expenses': float(manual_expenses_total),
            'net_profit': float(net_profit),
            'avg_check': round(float(avg_check)),
            'appointments_count': appointments_count,
            'comparison': {
                'prev_income': float(prev_income),
                'change_percent': round(change_percent, 1),
            },
            'chart_data': chart_data,
            'top_services': top_services,
            'top_clients': top_clients,
            'goal': goal_data,
            'tax': tax_data,
            'expense_breakdown': expense_breakdown,
        })


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        master_profile = getattr(self.request.user, 'master_profile', None)
        if not master_profile:
            return Expense.objects.none()
        qs = Expense.objects.filter(master=master_profile)
        category = self.request.query_params.get('category')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if category:
            qs = qs.filter(category=category)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class GoalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        master_profile = getattr(request.user, 'master_profile', None)
        goal = FinancialGoal.objects.filter(
            master=master_profile, is_active=True
        ).first()
        if not goal:
            return Response({'detail': 'No active goal'}, status=404)
        return Response(FinancialGoalSerializer(goal).data)

    def post(self, request):
        serializer = FinancialGoalSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        master_profile = getattr(request.user, 'master_profile', None)
        FinancialGoal.objects.filter(
            master=master_profile, is_active=True
        ).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
