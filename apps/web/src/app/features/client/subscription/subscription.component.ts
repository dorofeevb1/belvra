import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { AuthService, NotificationService } from '../../../core/services';
import { ApiService } from '../../../core/services/api.service';
import { ProBadgeComponent } from '../../../shared/components/pro-badge.component';
import {
  SubscriptionPlan,
  SubscriptionPeriod,
  CLIENT_PLANS
} from '../../../core/models';

@Component({
  selector: 'app-client-subscription',
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
            Станьте PRO клиентом
          }
        </h1>
        <p class="page-subtitle">
          @if (subscriptionService.isPro()) {
            Управляйте вашей подпиской и пользуйтесь привилегиями
          } @else {
            Приоритетная запись, расширенный поиск и полная история
          }
        </p>
      </header>

      <!-- Current Subscription Status (if PRO) -->
      @if (subscriptionService.isPro() && (subscriptionService.subscription() || subscriptionService.isEarlyAdopter())) {
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
                  @if (subscriptionService.isEarlyAdopter()) {
                    <span class="early-adopter-label">Пожизненная Pro подписка (Early Adopter)</span>
                  } @else if (subscriptionService.daysUntilExpiry() !== null) {
                    @if (subscriptionService.subscription()?.cancelAtPeriodEnd) {
                      Истекает через {{ subscriptionService.daysUntilExpiry() }} дн.
                    } @else {
                      Следующее продление через {{ subscriptionService.daysUntilExpiry() }} дн.
                    }
                  }
                </p>
              </div>
            </div>

            @if (!subscriptionService.isEarlyAdopter()) {
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
            }
          </div>

          <!-- PRO Benefits Summary -->
          <div class="pro-benefits-summary">
            <div class="benefit-stat">
              <div class="benefit-value">VIP</div>
              <div class="benefit-label">Приоритет записи</div>
            </div>
            <div class="benefit-stat">
              <div class="benefit-value">&infin;</div>
              <div class="benefit-label">Безлимит избранных</div>
            </div>
            <div class="benefit-stat">
              <div class="benefit-value">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <div class="benefit-label">Расширенный поиск</div>
            </div>
          </div>
        </div>
      }

      <!-- Period Toggle -->
      @if (!subscriptionService.isPro()) {
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
              <span class="discount-badge">-29%</span>
            </button>
          </div>
        </div>
      }

      <!-- Plans Grid -->
      @if (!subscriptionService.isPro()) {
        <div class="plans-grid">
          @for (plan of displayedPlans(); track plan.id) {
            <div class="plan-card" [class.pro]="plan.tier === 'pro'">
              @if (plan.isPopular) {
                <span class="popular-badge">Рекомендуем</span>
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
            </div>
          }
        </div>
      }

      <!-- Benefits Section (for non-PRO users) -->
      @if (!subscriptionService.isPro()) {
        <div class="benefits-section">
          <h3 class="section-title">Преимущества PRO</h3>

          <div class="benefits-grid">
            <div class="benefit-card">
              <div class="benefit-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
              </div>
              <h4>Приоритетная запись</h4>
              <p>Записывайтесь первыми к популярным мастерам</p>
            </div>

            <div class="benefit-card">
              <div class="benefit-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
              </div>
              <h4>Расширенный поиск</h4>
              <p>Находите мастеров по расширенным критериям</p>
            </div>

            <div class="benefit-card">
              <div class="benefit-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
              </div>
              <h4>Полная история</h4>
              <p>Доступ к полной истории записей и статистике расходов</p>
            </div>
          </div>
        </div>
      }

      <!-- Referral Program -->
      @if (referralCode()) {
        <div class="referral-section">
          <h3 class="section-title">Реферальная программа</h3>
          <p class="section-subtitle">Приглашайте друзей и получайте 1 месяц PRO бесплатно за каждого</p>

          <div class="referral-card">
            <div class="referral-code-block">
              <span class="referral-label">Ваш реферальный код</span>
              <div class="referral-code-row">
                <code class="referral-code">{{ referralCode() }}</code>
                <button type="button" class="btn-copy" (click)="copyReferralCode()">
                  @if (codeCopied()) {
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:20px;height:20px">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                    </svg>
                  } @else {
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:20px;height:20px">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                  }
                </button>
              </div>
              <button type="button" class="btn-share" (click)="copyReferralLink()">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:16px;height:16px">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
                </svg>
                Скопировать ссылку для приглашения
              </button>
            </div>

            @if (referralStats()) {
              <div class="referral-stats">
                <div class="referral-stat">
                  <span class="stat-value">{{ referralStats()!.total_referrals }}</span>
                  <span class="stat-label">Приглашено</span>
                </div>
                <div class="referral-stat">
                  <span class="stat-value">{{ referralStats()!.rewards_applied }}</span>
                  <span class="stat-label">Награды получены</span>
                </div>
                <div class="referral-stat">
                  <span class="stat-value">{{ referralStats()!.rewards_pending }}</span>
                  <span class="stat-label">Ожидают</span>
                </div>
              </div>
            }
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
export class ClientSubscriptionComponent implements OnInit {
  subscriptionService = inject(SubscriptionService);
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);
  private apiService = inject(ApiService);

  selectedPeriod = signal<SubscriptionPeriod>('monthly');
  referralCode = signal('');
  referralStats = signal<{ total_referrals: number; rewards_applied: number; rewards_pending: number } | null>(null);
  codeCopied = signal(false);

  displayedPlans = computed(() => {
    const period = this.selectedPeriod();
    return CLIENT_PLANS.filter(p =>
      p.tier === 'free' || p.period === period
    );
  });

  faqs = [
    {
      question: 'Что даёт PRO подписка клиенту?',
      answer: 'PRO подписка даёт приоритетную запись к популярным мастерам, безлимит избранных, расширенный поиск, полную историю записей и статистику расходов.'
    },
    {
      question: 'Что такое приоритетная запись?',
      answer: 'PRO клиенты получают доступ к записи раньше остальных, когда мастер открывает новые слоты. Это особенно удобно для популярных мастеров.'
    },
    {
      question: 'Что такое расширенный поиск?',
      answer: 'Расширенный поиск позволяет находить мастеров по дополнительным критериям: рейтинг, отзывы, доступность, специализация и другие параметры.'
    },
    {
      question: 'Могу ли я отменить подписку?',
      answer: 'Да, вы можете отменить автопродление в любой момент. Подписка будет действовать до конца оплаченного периода.'
    }
  ];

  ngOnInit(): void {
    this.subscriptionService.loadSubscription().subscribe();
    this.loadReferralStats();
  }

  subscribeToPlan(plan: SubscriptionPlan): void {
    const returnUrl = window.location.origin + '/payment/result?success=true';

    this.subscriptionService.subscribeToPlan(plan.id, returnUrl).subscribe({
      next: async (response: any) => {
        if (response?.payment_id) {
          const success = await this.subscriptionService.openPaymentWidget(
            response.payment_id,
            response.payment_url || ''
          );
          if (success) {
            this.notificationService.success('Оплата прошла успешно!');
            this.subscriptionService.loadSubscription().subscribe();
            this.subscriptionService.loadUsageStats().subscribe();
          }
        } else if (response?.payment_url) {
          window.location.href = response.payment_url;
        }
      },
      error: (error: any) => {
        console.error('Subscription error:', error);
        this.notificationService.error('Не удалось оформить подписку. Попробуйте позже.');
      }
    });
  }

  loadReferralStats(): void {
    this.apiService.getReferralStats().subscribe({
      next: (data) => {
        this.referralCode.set(data.referral_code || '');
        this.referralStats.set({
          total_referrals: data.total_referrals || 0,
          rewards_applied: data.rewards_applied || 0,
          rewards_pending: data.rewards_pending || 0
        });
      },
      error: () => {}
    });
  }

  copyReferralCode(): void {
    const code = this.referralCode();
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        this.codeCopied.set(true);
        this.notificationService.success('Код скопирован!');
        setTimeout(() => this.codeCopied.set(false), 2000);
      });
    }
  }

  copyReferralLink(): void {
    const code = this.referralCode();
    if (code) {
      const link = `${window.location.origin}/register?ref=${code}`;
      navigator.clipboard.writeText(link).then(() => {
        this.notificationService.success('Ссылка скопирована!');
      });
    }
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
}
