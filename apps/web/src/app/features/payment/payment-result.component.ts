import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-payment-result',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="payment-result-page">
      <div class="result-container">
        @if (isLoading()) {
          <div class="result-card">
            <div class="spinner-lg"></div>
            <h2>Проверяем статус оплаты...</h2>
          </div>
        } @else if (isSuccess()) {
          <div class="result-card success">
            <div class="result-icon success-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <h1>Оплата прошла успешно</h1>
            <p class="result-description">
              Ваша подписка PRO активирована. Все возможности уже доступны.
            </p>
            <div class="result-details">
              @if (amount()) {
                <div class="detail-row">
                  <span>Сумма</span>
                  <span class="detail-value">{{ amount() }} &#8381;</span>
                </div>
              }
              @if (orderId()) {
                <div class="detail-row">
                  <span>Номер заказа</span>
                  <span class="detail-value order-id">{{ orderId() }}</span>
                </div>
              }
            </div>
            <div class="result-actions">
              <a [routerLink]="dashboardLink()" class="btn btn-primary btn-lg">
                Перейти в личный кабинет
              </a>
              <a [routerLink]="subscriptionLink()" class="btn btn-outline btn-lg">
                Моя подписка
              </a>
            </div>
          </div>
        } @else {
          <div class="result-card error">
            <div class="result-icon error-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <h1>Оплата не прошла</h1>
            <p class="result-description">
              {{ errorMessage() }}
            </p>
            <div class="result-actions">
              <a [routerLink]="subscriptionLink()" class="btn btn-primary btn-lg">
                Попробовать снова
              </a>
              <a [routerLink]="dashboardLink()" class="btn btn-outline btn-lg">
                Вернуться в кабинет
              </a>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .payment-result-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      background: var(--color-bg-secondary);
    }

    .result-container {
      width: 100%;
      max-width: 480px;
    }

    .result-card {
      background: var(--color-bg-primary);
      border-radius: 1rem;
      padding: 2.5rem 2rem;
      text-align: center;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
    }

    .result-icon {
      width: 80px;
      height: 80px;
      margin: 0 auto 1.5rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;

      svg {
        width: 48px;
        height: 48px;
      }
    }

    .success-icon {
      background: rgba(34, 197, 94, 0.1);
      color: #22c55e;
    }

    .error-icon {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }

    h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--color-text-primary);
      margin: 0 0 0.75rem;
    }

    .result-description {
      font-size: 0.9375rem;
      color: var(--color-text-secondary);
      margin: 0 0 1.5rem;
      line-height: 1.5;
    }

    .result-details {
      background: var(--color-bg-secondary);
      border-radius: 0.75rem;
      padding: 1rem;
      margin-bottom: 2rem;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 0;
      font-size: 0.875rem;
      color: var(--color-text-secondary);

      &:not(:last-child) {
        border-bottom: 1px solid var(--color-border);
      }
    }

    .detail-value {
      font-weight: 600;
      color: var(--color-text-primary);
    }

    .order-id {
      font-size: 0.75rem;
      font-family: monospace;
    }

    .result-actions {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.875rem 1.5rem;
      border-radius: 0.75rem;
      font-weight: 600;
      font-size: 0.9375rem;
      text-decoration: none;
      transition: all 0.2s;
      cursor: pointer;
    }

    .btn-primary {
      background: var(--color-brand-500);
      color: white;

      &:hover {
        background: var(--color-brand-600);
      }
    }

    .btn-outline {
      background: transparent;
      color: var(--color-text-secondary);
      border: 1px solid var(--color-border);

      &:hover {
        background: var(--color-bg-secondary);
      }
    }

    .spinner-lg {
      width: 48px;
      height: 48px;
      border: 3px solid var(--color-border);
      border-top-color: var(--color-brand-500);
      border-radius: 50%;
      margin: 0 auto 1.5rem;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    h2 {
      font-size: 1.125rem;
      color: var(--color-text-secondary);
      font-weight: 500;
    }

    @media (max-width: 480px) {
      .payment-result-page {
        padding: 1rem;
      }

      .result-card {
        padding: 2rem 1.25rem;
      }
    }
  `]
})
export class PaymentResultComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private auth = inject(AuthService);

  isLoading = signal(true);
  isSuccess = signal(false);
  amount = signal('');
  orderId = signal('');
  errorMessage = signal('К сожалению, платёж не был завершён. Средства не списаны. Попробуйте повторить оплату.');

  dashboardLink = signal('/master/dashboard');
  subscriptionLink = signal('/master/subscription');

  ngOnInit(): void {
    const user = this.auth.currentUser();
    const role = user?.role || 'master';
    this.dashboardLink.set(role === 'client' ? '/client' : '/master/dashboard');
    this.subscriptionLink.set(role === 'client' ? '/client/subscription' : '/master/subscription');

    // Read query params from T-Bank redirect
    const params = this.route.snapshot.queryParams;
    const success = params['Success'] || params['success'];
    const status = params['Status'] || params['status'];

    // T-Bank sends Success=true/false, or we check ?success=true from our own redirect
    if (success === 'true' || success === true || status === 'CONFIRMED') {
      this.isSuccess.set(true);
    } else if (success === 'false' || success === false || status === 'REJECTED' || status === 'DEADLINE_EXPIRED') {
      this.isSuccess.set(false);
      if (status === 'REJECTED') {
        this.errorMessage.set('Платёж отклонён банком. Проверьте данные карты и попробуйте снова.');
      } else if (status === 'DEADLINE_EXPIRED') {
        this.errorMessage.set('Время на оплату истекло. Попробуйте оформить подписку заново.');
      }
    } else {
      // Fallback: check if we came from a success redirect
      const urlSuccess = params['success'];
      this.isSuccess.set(urlSuccess === 'true');
    }

    if (params['Amount']) {
      const amountKopecks = parseInt(params['Amount'], 10);
      this.amount.set(isNaN(amountKopecks) ? '' : (amountKopecks / 100).toFixed(0));
    } else if (params['amount']) {
      this.amount.set(params['amount']);
    }

    this.orderId.set(params['OrderId'] || params['order_id'] || '');

    this.isLoading.set(false);
  }
}
