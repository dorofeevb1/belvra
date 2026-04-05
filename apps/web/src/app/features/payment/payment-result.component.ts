import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-payment-result',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page" [class.page--success]="isSuccess()" [class.page--error]="!isLoading() && !isSuccess()">
      <!-- Animated background particles -->
      <div class="particles">
        @for (p of particles; track p.id) {
          <div class="particle" [style.--x]="p.x" [style.--y]="p.y" [style.--size]="p.size" [style.--delay]="p.delay" [style.--duration]="p.duration"></div>
        }
      </div>

      <!-- Confetti for success -->
      @if (isSuccess() && !isLoading()) {
        <div class="confetti-container">
          @for (c of confetti; track c.id) {
            <div class="confetti-piece" [style.--x]="c.x" [style.--delay]="c.delay" [style.--color]="c.color" [style.--rotation]="c.rotation" [style.--duration]="c.duration"></div>
          }
        </div>
      }

      @if (isLoading()) {
        <div class="content fade-in">
          <div class="loader">
            <div class="loader-ring"></div>
            <div class="loader-ring"></div>
            <div class="loader-ring"></div>
          </div>
          <p class="loader-text">Проверяем оплату</p>
        </div>
      } @else if (isSuccess()) {
        <div class="content stagger-in">
          <!-- Animated checkmark -->
          <div class="icon-wrap icon-wrap--success">
            <svg class="checkmark" viewBox="0 0 52 52">
              <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
              <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
            </svg>
          </div>

          <h1 class="title">Оплата прошла успешно</h1>
          <p class="subtitle">Добро пожаловать в <span class="pro-badge">PRO</span></p>

          <div class="features">
            <div class="feature">
              <div class="feature-icon">&#8734;</div>
              <span>Безлимитные записи</span>
            </div>
            <div class="feature">
              <div class="feature-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
                </svg>
              </div>
              <span>PRO-бейдж</span>
            </div>
            <div class="feature">
              <div class="feature-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                </svg>
              </div>
              <span>Продвижение в поиске</span>
            </div>
          </div>

          @if (amount()) {
            <div class="amount-badge">
              <span class="amount-label">Оплачено</span>
              <span class="amount-value">{{ amount() }} &#8381;</span>
            </div>
          }

          <div class="actions">
            <a [routerLink]="dashboardLink()" class="btn btn-primary">
              <span>Перейти в кабинет</span>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
              </svg>
            </a>
            <a [routerLink]="subscriptionLink()" class="btn btn-ghost">Моя подписка</a>
          </div>
        </div>
      } @else {
        <div class="content stagger-in">
          <!-- Animated X mark -->
          <div class="icon-wrap icon-wrap--error">
            <svg class="xmark" viewBox="0 0 52 52">
              <circle class="xmark-circle" cx="26" cy="26" r="25" fill="none"/>
              <path class="xmark-x" fill="none" d="M16 16 36 36 M36 16 16 36"/>
            </svg>
          </div>

          <h1 class="title">Оплата не прошла</h1>
          <p class="subtitle error-msg">{{ errorMessage() }}</p>

          <div class="actions">
            <a [routerLink]="subscriptionLink()" class="btn btn-primary">
              <span>Попробовать снова</span>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
            </a>
            <a [routerLink]="dashboardLink()" class="btn btn-ghost">Вернуться в кабинет</a>
          </div>
        </div>
      }

      <div class="footer fade-in-delayed">Belvra &copy; 2025</div>
    </div>
  `,
  styles: [`
    /* ===== BASE ===== */
    .page {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      padding: 2rem;
      background: #0a0a0f;
      transition: background 0.6s ease;
    }

    .page--success {
      background: radial-gradient(ellipse at 50% 0%, rgba(124, 58, 237, 0.15) 0%, #0a0a0f 70%);
    }

    .page--error {
      background: radial-gradient(ellipse at 50% 0%, rgba(239, 68, 68, 0.1) 0%, #0a0a0f 70%);
    }

    /* ===== PARTICLES ===== */
    .particles {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }

    .particle {
      position: absolute;
      left: calc(var(--x) * 1%);
      top: calc(var(--y) * 1%);
      width: calc(var(--size) * 1px);
      height: calc(var(--size) * 1px);
      background: rgba(124, 58, 237, 0.3);
      border-radius: 50%;
      animation: float calc(var(--duration) * 1s) ease-in-out calc(var(--delay) * 1s) infinite alternate;
    }

    @keyframes float {
      from { transform: translateY(0) scale(1); opacity: 0.2; }
      to { transform: translateY(-30px) scale(1.5); opacity: 0.6; }
    }

    /* ===== CONFETTI ===== */
    .confetti-container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 10;
    }

    .confetti-piece {
      position: absolute;
      top: -10px;
      left: calc(var(--x) * 1%);
      width: 10px;
      height: 10px;
      background: var(--color);
      transform: rotate(calc(var(--rotation) * 1deg));
      animation: confetti-fall calc(var(--duration) * 1s) ease-in calc(var(--delay) * 1s) forwards;
      border-radius: 2px;
    }

    @keyframes confetti-fall {
      0% { top: -10px; opacity: 1; transform: rotate(0deg) scale(1); }
      100% { top: 110vh; opacity: 0; transform: rotate(720deg) scale(0.3); }
    }

    /* ===== CONTENT ===== */
    .content {
      position: relative;
      z-index: 5;
      text-align: center;
      max-width: 440px;
      width: 100%;
    }

    /* ===== ANIMATED CHECKMARK ===== */
    .icon-wrap {
      width: 100px;
      height: 100px;
      margin: 0 auto 2rem;
    }

    .checkmark, .xmark {
      width: 100px;
      height: 100px;
    }

    .checkmark-circle {
      stroke: #22c55e;
      stroke-width: 2;
      stroke-dasharray: 166;
      stroke-dashoffset: 166;
      animation: circle-draw 0.6s ease-in-out 0.3s forwards;
    }

    .checkmark-check {
      stroke: #22c55e;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-dasharray: 48;
      stroke-dashoffset: 48;
      animation: check-draw 0.4s ease-in-out 0.8s forwards;
    }

    .xmark-circle {
      stroke: #ef4444;
      stroke-width: 2;
      stroke-dasharray: 166;
      stroke-dashoffset: 166;
      animation: circle-draw 0.6s ease-in-out 0.3s forwards;
    }

    .xmark-x {
      stroke: #ef4444;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-dasharray: 56;
      stroke-dashoffset: 56;
      animation: check-draw 0.4s ease-in-out 0.8s forwards;
    }

    @keyframes circle-draw {
      to { stroke-dashoffset: 0; }
    }

    @keyframes check-draw {
      to { stroke-dashoffset: 0; }
    }

    /* ===== TYPOGRAPHY ===== */
    .title {
      font-size: 2.25rem;
      font-weight: 800;
      color: #fff;
      margin: 0 0 0.75rem;
      letter-spacing: -0.02em;
      animation: slide-up 0.6s ease-out 0.5s both;
    }

    .subtitle {
      font-size: 1.125rem;
      color: rgba(255, 255, 255, 0.6);
      margin: 0 0 2.5rem;
      line-height: 1.6;
      animation: slide-up 0.6s ease-out 0.65s both;
    }

    .error-msg {
      max-width: 340px;
      margin-left: auto;
      margin-right: auto;
    }

    .pro-badge {
      display: inline-block;
      background: linear-gradient(135deg, #7c3aed, #a855f7);
      color: white;
      padding: 0.15em 0.6em;
      border-radius: 0.375em;
      font-weight: 700;
      font-size: 0.9em;
    }

    /* ===== FEATURES ===== */
    .features {
      display: flex;
      gap: 1rem;
      justify-content: center;
      margin-bottom: 2rem;
      animation: slide-up 0.6s ease-out 0.8s both;
    }

    .feature {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 1rem;
      min-width: 120px;
      backdrop-filter: blur(10px);
      transition: transform 0.3s, border-color 0.3s;

      &:hover {
        transform: translateY(-4px);
        border-color: rgba(124, 58, 237, 0.3);
      }

      span {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
        text-align: center;
      }
    }

    .feature-icon {
      font-size: 1.25rem;
      font-weight: 800;
      color: #a855f7;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background: rgba(124, 58, 237, 0.15);
      border-radius: 0.75rem;

      svg { color: #a855f7; }
    }

    /* ===== AMOUNT ===== */
    .amount-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 100px;
      padding: 0.625rem 1.25rem;
      margin-bottom: 2.5rem;
      animation: slide-up 0.6s ease-out 0.95s both;
    }

    .amount-label {
      font-size: 0.8125rem;
      color: rgba(255, 255, 255, 0.4);
    }

    .amount-value {
      font-size: 1.125rem;
      font-weight: 700;
      color: #fff;
    }

    /* ===== BUTTONS ===== */
    .actions {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      animation: slide-up 0.6s ease-out 1.1s both;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 1rem 2rem;
      border-radius: 100px;
      font-weight: 600;
      font-size: 1rem;
      text-decoration: none;
      cursor: pointer;
      border: none;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
    }

    .btn-primary {
      background: linear-gradient(135deg, #7c3aed, #a855f7);
      color: white;
      box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(124, 58, 237, 0.5);
      }

      &:active {
        transform: translateY(0);
      }
    }

    .page--error .btn-primary {
      background: linear-gradient(135deg, #dc2626, #ef4444);
      box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);

      &:hover {
        box-shadow: 0 8px 30px rgba(239, 68, 68, 0.4);
      }
    }

    .btn-ghost {
      background: transparent;
      color: rgba(255, 255, 255, 0.5);
      padding: 0.75rem 2rem;

      &:hover {
        color: rgba(255, 255, 255, 0.8);
      }
    }

    /* ===== LOADER ===== */
    .loader {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      margin-bottom: 1.5rem;
    }

    .loader-ring {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #7c3aed;
      animation: pulse-loader 1.2s ease-in-out infinite;

      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
    }

    @keyframes pulse-loader {
      0%, 100% { transform: scale(0.5); opacity: 0.3; }
      50% { transform: scale(1.2); opacity: 1; }
    }

    .loader-text {
      font-size: 1rem;
      color: rgba(255, 255, 255, 0.5);
      letter-spacing: 0.05em;
    }

    /* ===== FOOTER ===== */
    .footer {
      position: absolute;
      bottom: 2rem;
      font-size: 0.75rem;
      color: rgba(255, 255, 255, 0.2);
    }

    /* ===== ANIMATIONS ===== */
    @keyframes slide-up {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
      animation: slide-up 0.6s ease-out both;
    }

    .fade-in-delayed {
      animation: slide-up 0.6s ease-out 1.5s both;
    }

    .stagger-in {
      animation: slide-up 0.5s ease-out 0.2s both;
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 480px) {
      .page { padding: 1.5rem 1rem; }

      .title { font-size: 1.75rem; }

      .features {
        flex-direction: column;
        align-items: center;

        .feature {
          flex-direction: row;
          width: 100%;
          min-width: 0;
          padding: 0.75rem 1rem;
        }
      }

      .icon-wrap { width: 80px; height: 80px; }
      .checkmark, .xmark { width: 80px; height: 80px; }
    }
  `]
})
export class PaymentResultComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private auth = inject(AuthService);
  private api = inject(ApiService);

  isLoading = signal(true);
  isSuccess = signal(false);
  amount = signal('');
  orderId = signal('');
  errorMessage = signal('К сожалению, платёж не был завершён. Средства не списаны. Попробуйте повторить оплату.');

  dashboardLink = signal('/master/dashboard');
  subscriptionLink = signal('/master/subscription');

  // Background particles
  particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    x: `${Math.random() * 100}`,
    y: `${Math.random() * 100}`,
    size: `${Math.random() * 4 + 2}`,
    delay: `${Math.random() * 3}`,
    duration: `${Math.random() * 3 + 3}`
  }));

  // Confetti pieces
  confetti = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    x: `${Math.random() * 100}`,
    delay: `${Math.random() * 1.5 + 0.5}`,
    color: ['#7c3aed', '#a855f7', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4', '#fff'][Math.floor(Math.random() * 7)],
    rotation: `${Math.random() * 360}`,
    duration: `${Math.random() * 2 + 2.5}`
  }));

  ngOnInit(): void {
    const user = this.auth.currentUser();
    const role = user?.role || 'master';
    this.dashboardLink.set(role === 'client' ? '/client' : '/master/dashboard');
    this.subscriptionLink.set(role === 'client' ? '/client/subscription' : '/master/subscription');

    const params = this.route.snapshot.queryParams;

    if (params['Amount']) {
      const amountKopecks = parseInt(params['Amount'], 10);
      this.amount.set(isNaN(amountKopecks) ? '' : (amountKopecks / 100).toFixed(0));
    } else if (params['amount']) {
      this.amount.set(params['amount']);
    }
    this.orderId.set(params['OrderId'] || params['order_id'] || '');

    // Check real subscription status from API instead of trusting query params
    this.api.getSubscription().subscribe({
      next: (sub: any) => {
        if (sub && sub.status === 'active' && sub.plan?.tier === 'pro') {
          this.isSuccess.set(true);
        } else {
          this.isSuccess.set(false);
        }
        this.isLoading.set(false);
      },
      error: () => {
        // Fallback to query params if API fails
        const success = params['Success'] || params['success'];
        const status = params['Status'] || params['status'];

        if (success === 'false' || status === 'REJECTED' || status === 'DEADLINE_EXPIRED') {
          this.isSuccess.set(false);
          if (status === 'REJECTED') {
            this.errorMessage.set('Платёж отклонён банком. Проверьте данные карты и попробуйте снова.');
          } else if (status === 'DEADLINE_EXPIRED') {
            this.errorMessage.set('Время на оплату истекло. Попробуйте оформить подписку заново.');
          }
        } else {
          this.isSuccess.set(success === 'true');
        }
        this.isLoading.set(false);
      }
    });
  }
}
