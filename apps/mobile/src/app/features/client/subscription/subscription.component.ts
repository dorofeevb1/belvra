import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { AuthService, NotificationService } from '../../../core/services';
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
  template: `
    <div class="p-4 sm:p-6 max-w-4xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-2">
          @if (subscriptionService.isPro()) {
            Ваша PRO подписка
          } @else {
            Станьте PRO клиентом
          }
        </h1>
        <p class="text-slate-600 dark:text-slate-400">
          @if (subscriptionService.isPro()) {
            Управляйте вашей подпиской и пользуйтесь привилегиями
          } @else {
            Получите скидки, приоритетную запись и кешбэк
          }
        </p>
      </div>

      <!-- Current Subscription Status (if PRO) -->
      @if (subscriptionService.isPro() && subscriptionService.subscription()) {
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-xl p-6 mb-8 border border-amber-200 dark:border-amber-800">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-full bg-gradient-to-r from-amber-400 to-amber-500 flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clip-rule="evenodd"/>
                </svg>
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-slate-900 dark:text-white">PRO подписка</span>
                  <app-pro-badge [size]="'sm'" [showIcon]="false" />
                </div>
                <p class="text-sm text-slate-600 dark:text-slate-400">
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

            <div class="flex gap-2">
              @if (subscriptionService.subscription()?.cancelAtPeriodEnd) {
                <button
                  type="button"
                  class="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors text-sm font-medium"
                  [disabled]="subscriptionService.loading()"
                  (click)="reactivateSubscription()"
                >
                  Возобновить подписку
                </button>
              } @else {
                <button
                  type="button"
                  class="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors text-sm font-medium"
                  [disabled]="subscriptionService.loading()"
                  (click)="cancelSubscription()"
                >
                  Отменить автопродление
                </button>
              }
            </div>
          </div>

          <!-- PRO Benefits Summary -->
          <div class="mt-4 pt-4 border-t border-amber-200 dark:border-amber-800 grid grid-cols-3 gap-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-amber-600 dark:text-amber-400">10%</div>
              <div class="text-xs text-slate-600 dark:text-slate-400">Скидка на услуги</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-amber-600 dark:text-amber-400">5%</div>
              <div class="text-xs text-slate-600 dark:text-slate-400">Кешбэк</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-amber-600 dark:text-amber-400">VIP</div>
              <div class="text-xs text-slate-600 dark:text-slate-400">Приоритет записи</div>
            </div>
          </div>
        </div>
      }

      <!-- Period Toggle -->
      @if (!subscriptionService.isPro()) {
        <div class="flex justify-center mb-8">
          <div class="inline-flex items-center p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            <button
              type="button"
              class="px-4 py-2 text-sm font-medium rounded-md transition-colors"
              [class.bg-white]="selectedPeriod() === 'monthly'"
              [class.dark:bg-slate-700]="selectedPeriod() === 'monthly'"
              [class.text-slate-900]="selectedPeriod() === 'monthly'"
              [class.dark:text-white]="selectedPeriod() === 'monthly'"
              [class.shadow-sm]="selectedPeriod() === 'monthly'"
              [class.text-slate-600]="selectedPeriod() !== 'monthly'"
              [class.dark:text-slate-400]="selectedPeriod() !== 'monthly'"
              (click)="selectedPeriod.set('monthly')"
            >
              Месяц
            </button>
            <button
              type="button"
              class="px-4 py-2 text-sm font-medium rounded-md transition-colors relative"
              [class.bg-white]="selectedPeriod() === 'yearly'"
              [class.dark:bg-slate-700]="selectedPeriod() === 'yearly'"
              [class.text-slate-900]="selectedPeriod() === 'yearly'"
              [class.dark:text-white]="selectedPeriod() === 'yearly'"
              [class.shadow-sm]="selectedPeriod() === 'yearly'"
              [class.text-slate-600]="selectedPeriod() !== 'yearly'"
              [class.dark:text-slate-400]="selectedPeriod() !== 'yearly'"
              (click)="selectedPeriod.set('yearly')"
            >
              Год
              <span class="absolute -top-2 -right-2 px-1.5 py-0.5 text-[10px] font-bold bg-green-500 text-white rounded-full">
                -29%
              </span>
            </button>
          </div>
        </div>
      }

      <!-- Plans Grid -->
      @if (!subscriptionService.isPro()) {
        <div class="grid md:grid-cols-2 gap-6 mb-8">
          @for (plan of displayedPlans(); track plan.id) {
            <div
              class="relative rounded-2xl p-6 border-2 transition-all"
              [class.border-amber-400]="plan.tier === 'pro'"
              [class.bg-gradient-to-br]="plan.tier === 'pro'"
              [class.from-amber-50]="plan.tier === 'pro'"
              [class.to-orange-50]="plan.tier === 'pro'"
              [class.dark:from-amber-900/10]="plan.tier === 'pro'"
              [class.dark:to-orange-900/10]="plan.tier === 'pro'"
              [class.border-slate-200]="plan.tier !== 'pro'"
              [class.dark:border-slate-700]="plan.tier !== 'pro'"
              [class.bg-white]="plan.tier !== 'pro'"
              [class.dark:bg-slate-800]="plan.tier !== 'pro'"
            >
              @if (plan.isPopular) {
                <div class="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span class="px-3 py-1 bg-gradient-to-r from-amber-400 to-amber-500 text-white text-xs font-bold rounded-full shadow-sm">
                    Рекомендуем
                  </span>
                </div>
              }

              <!-- Plan Header -->
              <div class="mb-6">
                <div class="flex items-center gap-2 mb-2">
                  <h3 class="text-xl font-bold text-slate-900 dark:text-white">{{ plan.name }}</h3>
                  @if (plan.tier === 'pro') {
                    <app-pro-badge [size]="'sm'" [showIcon]="false" />
                  }
                </div>

                <div class="flex items-baseline gap-1">
                  <span class="text-3xl font-bold text-slate-900 dark:text-white">
                    {{ plan.price | number }}₽
                  </span>
                  <span class="text-slate-500 dark:text-slate-400">
                    /{{ plan.period === 'monthly' ? 'мес' : 'год' }}
                  </span>
                </div>

                @if (plan.originalPrice && plan.originalPrice > plan.price) {
                  <div class="mt-1">
                    <span class="text-sm text-slate-400 line-through">{{ plan.originalPrice | number }}₽</span>
                    <span class="text-sm text-green-600 dark:text-green-400 ml-2">
                      Экономия {{ plan.originalPrice - plan.price | number }}₽
                    </span>
                  </div>
                }
              </div>

              <!-- Features List -->
              <ul class="space-y-3 mb-6">
                @for (feature of plan.features; track feature.name) {
                  <li class="flex items-start gap-3">
                    @if (feature.included) {
                      <svg class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                      </svg>
                    } @else {
                      <svg class="w-5 h-5 text-slate-300 dark:text-slate-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                      </svg>
                    }
                    <span
                      class="text-sm"
                      [class.text-slate-700]="feature.included"
                      [class.dark:text-slate-300]="feature.included"
                      [class.text-slate-400]="!feature.included"
                      [class.dark:text-slate-500]="!feature.included"
                    >
                      {{ feature.description }}
                    </span>
                  </li>
                }
              </ul>

              <!-- CTA Button -->
              @if (plan.tier === 'free') {
                <button
                  type="button"
                  class="w-full py-3 px-4 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 rounded-xl font-medium"
                  disabled
                >
                  Текущий план
                </button>
              } @else {
                <button
                  type="button"
                  class="w-full py-3 px-4 bg-gradient-to-r from-amber-400 to-amber-500 text-white rounded-xl font-medium hover:from-amber-500 hover:to-amber-600 transition-all shadow-sm"
                  [disabled]="subscriptionService.loading()"
                  (click)="subscribeToPlan(plan)"
                >
                  @if (subscriptionService.loading()) {
                    <svg class="animate-spin h-5 w-5 mx-auto" fill="none" viewBox="0 0 24 24">
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
        <div class="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700 mb-8">
          <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Преимущества PRO</h3>

          <div class="grid sm:grid-cols-3 gap-6">
            <div class="text-center">
              <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <h4 class="font-medium text-slate-900 dark:text-white mb-1">Скидка 10%</h4>
              <p class="text-sm text-slate-600 dark:text-slate-400">На все услуги у любого мастера</p>
            </div>

            <div class="text-center">
              <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
              </div>
              <h4 class="font-medium text-slate-900 dark:text-white mb-1">Приоритетная запись</h4>
              <p class="text-sm text-slate-600 dark:text-slate-400">Записывайтесь первыми к популярным мастерам</p>
            </div>

            <div class="text-center">
              <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/>
                </svg>
              </div>
              <h4 class="font-medium text-slate-900 dark:text-white mb-1">Кешбэк 5%</h4>
              <p class="text-sm text-slate-600 dark:text-slate-400">Возврат с каждой оплаченной услуги</p>
            </div>
          </div>
        </div>
      }

      <!-- FAQ Section -->
      <div class="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Часто задаваемые вопросы</h3>

        <div class="space-y-4">
          @for (faq of faqs; track faq.question) {
            <details class="group">
              <summary class="flex items-center justify-between cursor-pointer py-2 text-slate-900 dark:text-white font-medium">
                {{ faq.question }}
                <svg class="w-5 h-5 text-slate-400 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
              </summary>
              <p class="text-sm text-slate-600 dark:text-slate-400 pt-2 pb-4">
                {{ faq.answer }}
              </p>
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

  selectedPeriod = signal<SubscriptionPeriod>('monthly');

  displayedPlans = computed(() => {
    const period = this.selectedPeriod();
    return CLIENT_PLANS.filter(p =>
      p.tier === 'free' || p.period === period
    );
  });

  faqs = [
    {
      question: 'Как работает скидка 10%?',
      answer: 'Скидка автоматически применяется при оплате любых услуг у всех мастеров на платформе. Вы сразу видите сниженную цену.'
    },
    {
      question: 'Что такое приоритетная запись?',
      answer: 'PRO клиенты получают доступ к записи раньше остальных, когда мастер открывает новые слоты. Это особенно удобно для популярных мастеров.'
    },
    {
      question: 'Как работает кешбэк?',
      answer: 'После каждой оплаченной услуги 5% возвращается на ваш баланс в приложении. Накопленные средства можно использовать для оплаты следующих услуг.'
    },
    {
      question: 'Могу ли я отменить подписку?',
      answer: 'Да, вы можете отменить автопродление в любой момент. Подписка будет действовать до конца оплаченного периода, накопленный кешбэк сохранится.'
    }
  ];

  ngOnInit(): void {
    this.subscriptionService.loadSubscription().subscribe();
  }

  subscribeToPlan(plan: SubscriptionPlan): void {
    const returnUrl = window.location.origin + '/client/subscription?success=true';

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
}
