import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { AuthService, NotificationService } from '../../../core/services';
import { ProBadgeComponent } from '../../../shared/components/pro-badge.component';
import {
  SubscriptionPlan,
  SubscriptionPeriod,
  MASTER_PLANS
} from '../../../core/models';

@Component({
  selector: 'app-master-subscription',
  standalone: true,
  imports: [CommonModule, ProBadgeComponent],
  styleUrls: ['./subscription.component.scss'],
  template: `
    <div class="subscription-page">
      <!-- Header -->
      <header class="page-header">
        <h1 class="page-title">
          @if (subscriptionService.isPro()) {
            Ваша PRO подписка
          } @else {
            Перейдите на PRO
          }
        </h1>
        <p class="page-subtitle">
          @if (subscriptionService.isPro()) {
            Управляйте вашей подпиской и следите за лимитами
          } @else {
            Разблокируйте все возможности и развивайте свой бизнес
          }
        </p>
      </header>

      <!-- Current Subscription Status (if PRO) -->
      @if (subscriptionService.isPro() && subscriptionService.subscription()) {
        <div class="current-subscription">
          <div class="subscription-info">
            <div class="subscription-details">
              <div class="subscription-icon">
                <svg fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clip-rule="evenodd"/>
                </svg>
              </div>
              <div class="subscription-text">
                <h3>
                  PRO подписка
                  <app-pro-badge [size]="'sm'" [showIcon]="false" />
                </h3>
                <p>
                  @if (subscriptionService.daysUntilExpiry() !== null) {
                    @if (subscriptionService.subscription()?.cancelAtPeriodEnd) {
                      Истекает через {{ subscriptionService.daysUntilExpiry() }} дн.
                    } @else {
                      Следующее продление через {{ subscriptionService.daysUntilExpiry() }} дн.
                    }
                  }
                </p>
              </div>
            </div>

            <div class="subscription-actions">
              @if (subscriptionService.subscription()?.cancelAtPeriodEnd) {
                <button
                  type="button"
                  class="btn-reactivate"
                  [disabled]="subscriptionService.loading()"
                  (click)="reactivateSubscription()"
                >
                  Возобновить подписку
                </button>
              } @else {
                <button
                  type="button"
                  class="btn-cancel"
                  [disabled]="subscriptionService.loading()"
                  (click)="cancelSubscription()"
                >
                  Отменить автопродление
                </button>
              }
            </div>
          </div>
        </div>
      }

      <!-- Period Toggle -->
      <div class="period-toggle">
        <div class="toggle-container">
          <button
            type="button"
            class="toggle-btn"
            [class.active]="selectedPeriod() === 'monthly'"
            (click)="selectedPeriod.set('monthly')"
          >
            Месяц
          </button>
          <button
            type="button"
            class="toggle-btn"
            [class.active]="selectedPeriod() === 'yearly'"
            (click)="selectedPeriod.set('yearly')"
          >
            Год
            <span class="discount-badge">-30%</span>
          </button>
        </div>
      </div>

      <!-- Plans Grid -->
      <div class="plans-grid">
        @for (plan of displayedPlans(); track plan.id) {
          <div class="plan-card" [class.pro]="plan.tier === 'pro'">
            @if (plan.isPopular) {
              <span class="popular-badge">Популярный</span>
            }

            <!-- Plan Header -->
            <div class="plan-header">
              <h3 class="plan-name">
                {{ plan.name }}
                @if (plan.tier === 'pro') {
                  <span class="pro-badge-inline">PRO</span>
                }
              </h3>

              <div class="plan-price">
                <span class="price-amount">{{ plan.price | number }}₽</span>
                <span class="price-period">/{{ plan.period === 'monthly' ? 'мес' : 'год' }}</span>
              </div>

              @if (plan.originalPrice && plan.originalPrice > plan.price) {
                <div class="price-savings">
                  <span class="original-price">{{ plan.originalPrice | number }}₽</span>
                  <span class="savings-amount">Экономия {{ plan.originalPrice - plan.price | number }}₽</span>
                </div>
              }
            </div>

            <!-- Features List -->
            <ul class="features-list">
              @for (feature of plan.features; track feature.name) {
                <li class="feature-item" [class.included]="feature.included" [class.excluded]="!feature.included">
                  @if (feature.included) {
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                  } @else {
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                  }
                  <span>{{ feature.description }}</span>
                </li>
              }
            </ul>

            <!-- CTA Button -->
            @if (plan.tier === 'free') {
              <button type="button" class="plan-cta secondary" disabled>
                @if (subscriptionService.currentTier() === 'free') {
                  Текущий план
                } @else {
                  Бесплатный
                }
              </button>
            } @else {
              @if (subscriptionService.isPro()) {
                <button type="button" class="plan-cta secondary" disabled>
                  Текущий план
                </button>
              } @else {
                <button
                  type="button"
                  class="plan-cta primary"
                  [disabled]="subscriptionService.loading()"
                  (click)="subscribeToPlan(plan)"
                >
                  @if (subscriptionService.loading()) {
                    <svg class="spinner" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  } @else {
                    Оформить подписку
                  }
                </button>
              }
            }
          </div>
        }
      </div>

      <!-- Usage Stats (for FREE users) -->
      @if (!subscriptionService.isPro()) {
        <div class="usage-section">
          <h3 class="section-title">Ваше использование</h3>

          <div class="usage-grid">
            <!-- Appointments -->
            <div class="usage-card">
              <div class="usage-header">
                <span class="usage-label">Записи в месяц</span>
                <span class="usage-value">
                  {{ subscriptionService.usageStats().appointmentsThisMonth }}/{{ subscriptionService.limits().maxAppointmentsPerMonth || '∞' }}
                </span>
              </div>
              <div class="usage-bar">
                <div
                  class="usage-fill"
                  [class.normal]="getAppointmentsPercent() < 80"
                  [class.warning]="getAppointmentsPercent() >= 80 && getAppointmentsPercent() < 100"
                  [class.danger]="getAppointmentsPercent() >= 100"
                  [style.width.%]="getAppointmentsPercent()"
                ></div>
              </div>
            </div>

            <!-- Services -->
            <div class="usage-card">
              <div class="usage-header">
                <span class="usage-label">Услуги</span>
                <span class="usage-value">
                  {{ subscriptionService.usageStats().servicesCount }}/{{ subscriptionService.limits().maxServicesCount || '∞' }}
                </span>
              </div>
              <div class="usage-bar">
                <div
                  class="usage-fill"
                  [class.normal]="getServicesPercent() < 80"
                  [class.warning]="getServicesPercent() >= 80 && getServicesPercent() < 100"
                  [class.danger]="getServicesPercent() >= 100"
                  [style.width.%]="getServicesPercent()"
                ></div>
              </div>
            </div>

            <!-- Portfolio -->
            <div class="usage-card">
              <div class="usage-header">
                <span class="usage-label">Портфолио</span>
                <span class="usage-value">
                  {{ subscriptionService.usageStats().portfolioItemsCount }}/{{ subscriptionService.limits().maxPortfolioItems || '∞' }}
                </span>
              </div>
              <div class="usage-bar">
                <div
                  class="usage-fill"
                  [class.normal]="getPortfolioPercent() < 80"
                  [class.warning]="getPortfolioPercent() >= 80 && getPortfolioPercent() < 100"
                  [class.danger]="getPortfolioPercent() >= 100"
                  [style.width.%]="getPortfolioPercent()"
                ></div>
              </div>
            </div>
          </div>
        </div>
      }

      <!-- FAQ Section -->
      <div class="faq-section">
        <h3 class="section-title">Часто задаваемые вопросы</h3>

        <div class="faq-list">
          @for (faq of faqs; track faq.question) {
            <details class="faq-item">
              <summary>
                {{ faq.question }}
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </summary>
              <p>{{ faq.answer }}</p>
            </details>
          }
        </div>
      </div>
    </div>
  `
})
export class SubscriptionComponent implements OnInit {
  subscriptionService = inject(SubscriptionService);
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);

  selectedPeriod = signal<SubscriptionPeriod>('monthly');

  displayedPlans = computed(() => {
    const period = this.selectedPeriod();
    return MASTER_PLANS.filter(p =>
      p.tier === 'free' || p.period === period
    );
  });

  faqs = [
    {
      question: 'Как работает PRO подписка?',
      answer: 'PRO подписка даёт вам доступ к расширенным возможностям: безлимит записей, услуг и портфолио, PRO-бейдж, буст в поиске, AI-ассистент, расширенная аналитика и многое другое.'
    },
    {
      question: 'Могу ли я отменить подписку?',
      answer: 'Да, вы можете отменить автопродление в любой момент. Подписка будет действовать до конца оплаченного периода.'
    },
    {
      question: 'Как происходит оплата?',
      answer: 'Оплата происходит через безопасную платёжную систему. После оплаты подписка активируется автоматически.'
    },
    {
      question: 'Что произойдёт после окончания подписки?',
      answer: 'После окончания PRO подписки ваш аккаунт вернётся на бесплатный тариф. Все ваши данные сохранятся, но будут действовать ограничения бесплатного плана.'
    }
  ];

  ngOnInit(): void {
    this.subscriptionService.loadSubscription().subscribe();
    this.subscriptionService.loadUsageStats().subscribe();
  }

  subscribeToPlan(plan: SubscriptionPlan): void {
    const returnUrl = window.location.origin + '/master/subscription?success=true';

    this.subscriptionService.subscribeToPlan(plan.id, returnUrl).subscribe({
      next: (response) => {
        if (response?.payment_url) {
          window.location.href = response.payment_url;
        }
      },
      error: (error) => {
        console.error('Subscription error:', error);
        this.notificationService.error('Не удалось оформить подписку. Попробуйте позже.');
      }
    });
  }

  cancelSubscription(): void {
    this.subscriptionService.cancelSubscription().subscribe({
      next: (success) => {
        if (success) {
          this.notificationService.success('Автопродление отменено. Подписка будет действовать до конца периода.');
        } else {
          this.notificationService.error('Не удалось отменить подписку');
        }
      }
    });
  }

  reactivateSubscription(): void {
    this.subscriptionService.reactivateSubscription().subscribe({
      next: (success) => {
        if (success) {
          this.notificationService.success('Подписка возобновлена');
        } else {
          this.notificationService.error('Не удалось возобновить подписку');
        }
      }
    });
  }

  getAppointmentsPercent(): number {
    const limit = this.subscriptionService.limits().maxAppointmentsPerMonth;
    if (!limit) return 0;
    const used = this.subscriptionService.usageStats().appointmentsThisMonth;
    return Math.min(100, (used / limit) * 100);
  }

  getServicesPercent(): number {
    const limit = this.subscriptionService.limits().maxServicesCount;
    if (!limit) return 0;
    const used = this.subscriptionService.usageStats().servicesCount;
    return Math.min(100, (used / limit) * 100);
  }

  getPortfolioPercent(): number {
    const limit = this.subscriptionService.limits().maxPortfolioItems;
    if (!limit) return 0;
    const used = this.subscriptionService.usageStats().portfolioItemsCount;
    return Math.min(100, (used / limit) * 100);
  }
}
