# Generated manually

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='Название')),
                ('tier', models.CharField(choices=[('free', 'Бесплатный'), ('pro', 'Pro')], default='free', max_length=20)),
                ('user_type', models.CharField(choices=[('master', 'Мастер'), ('client', 'Клиент')], max_length=20)),
                ('period', models.CharField(choices=[('monthly', 'Месяц'), ('yearly', 'Год')], default='monthly', max_length=20)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('original_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('max_appointments_per_month', models.PositiveIntegerField(default=0, help_text='0 = unlimited')),
                ('max_services_count', models.PositiveIntegerField(default=0, help_text='0 = unlimited')),
                ('max_portfolio_items', models.PositiveIntegerField(default=0, help_text='0 = unlimited')),
                ('commission_percent', models.DecimalField(decimal_places=2, default=5.0, help_text='Platform commission percentage', max_digits=5)),
                ('search_boost_enabled', models.BooleanField(default=False)),
                ('analytics_level', models.CharField(choices=[('none', 'Нет'), ('basic', 'Базовая'), ('advanced', 'Расширенная')], default='none', max_length=20)),
                ('priority_booking', models.BooleanField(default=False)),
                ('cashback_percent', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('discount_percent', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('ai_assistant_enabled', models.BooleanField(default=False)),
                ('advanced_notifications', models.BooleanField(default=False)),
                ('export_data_enabled', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'План подписки',
                'verbose_name_plural': 'Планы подписок',
                'ordering': ['user_type', 'tier', 'period'],
                'unique_together': {('tier', 'user_type', 'period')},
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('active', 'Активна'), ('cancelled', 'Отменена'), ('expired', 'Истекла'), ('pending', 'Ожидает оплаты'), ('past_due', 'Просрочена')], db_index=True, default='pending', max_length=20)),
                ('current_period_start', models.DateTimeField(blank=True, null=True)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('cancel_at_period_end', models.BooleanField(default=False)),
                ('auto_renew', models.BooleanField(default=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('yookassa_payment_method_id', models.CharField(blank=True, max_length=255)),
                ('appointments_this_month', models.PositiveIntegerField(default=0)),
                ('last_usage_reset', models.DateField(blank=True, null=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='subscriptions.subscriptionplan')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Подписка',
                'verbose_name_plural': 'Подписки',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SubscriptionPayment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='RUB', max_length=3)),
                ('status', models.CharField(choices=[('pending', 'Ожидает'), ('succeeded', 'Успешно'), ('failed', 'Неудачно'), ('cancelled', 'Отменено'), ('refunded', 'Возвращено')], db_index=True, default='pending', max_length=20)),
                ('external_payment_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('confirmation_url', models.URLField(blank=True, max_length=500)),
                ('payment_method', models.CharField(blank=True, max_length=50)),
                ('is_recurring', models.BooleanField(default=False)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='subscriptions.subscription')),
            ],
            options={
                'verbose_name': 'Платёж за подписку',
                'verbose_name_plural': 'Платежи за подписки',
                'ordering': ['-created_at'],
            },
        ),
    ]
