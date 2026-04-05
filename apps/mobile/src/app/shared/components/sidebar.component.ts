import { Component, input, output, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { SubscriptionService } from '../../core/services/subscription.service';
import { AuthService } from '../../core/services/auth.service';
import { ProBadgeComponent } from './pro-badge.component';

export interface NavItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, ProBadgeComponent],
  template: `
    <!-- Overlay for mobile -->
    @if (isOpen()) {
      <div class="sidebar-overlay" (click)="close.emit()"></div>
    }

    <aside class="sidebar" [class.sidebar-open]="isOpen()">
      <!-- Logo Section (Desktop) -->
      <div class="sidebar-logo">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
            </svg>
          </div>
          <span class="logo-text">Belvra</span>
        </div>
        <button class="close-btn" (click)="close.emit()" type="button" aria-label="Закрыть меню">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <div class="nav-section">
          <span class="nav-section-title">Меню</span>
          @for (item of items(); track item.route) {
            <a
              [routerLink]="item.route"
              routerLinkActive="active"
              [routerLinkActiveOptions]="{ exact: item.route === '/master' || item.route === '/client' }"
              class="nav-item"
              (click)="close.emit()"
            >
              <span class="nav-item-icon" [innerHTML]="item.icon"></span>
              <span class="nav-item-label">{{ item.label }}</span>
            </a>
          }
        </div>

        <!-- Support Link -->
        <div class="nav-section" style="margin-top: auto; padding-top: 8px;">
          <a
            href="https://t.me/Dorof_hanzo"
            target="_blank"
            rel="noopener noreferrer"
            class="nav-item"
            style="opacity: 0.7;"
          >
            <span class="nav-item-icon">
              <svg viewBox="0 0 24 24" fill="currentColor" style="width: 20px; height: 20px;">
                <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
              </svg>
            </span>
            <span class="nav-item-label">Поддержка</span>
          </a>
        </div>
      </nav>

      <!-- Footer -->
      <div class="sidebar-footer">
        @if (subscriptionService.isPro()) {
          <!-- PRO Status Card -->
          <div class="pro-status-card" (click)="navigateToSubscription()">
            <div class="pro-status-header">
              <app-pro-badge [size]="'md'" [showIcon]="true" />
              <span class="pro-status-active">Активна</span>
            </div>
            <p class="pro-status-text">
              @if (subscriptionService.daysUntilExpiry() !== null) {
                {{ subscriptionService.daysUntilExpiry() }} дн. до продления
              } @else {
                Управление подпиской
              }
            </p>
          </div>
        } @else {
          <!-- Upgrade Card -->
          <div class="upgrade-card">
            <div class="upgrade-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
            <p class="upgrade-title">Belvra Pro</p>
            <p class="upgrade-text">Расширьте возможности</p>
            <button class="upgrade-btn" (click)="navigateToSubscription()">Подробнее</button>
          </div>
        }
        <span class="version">v2.0.0</span>
      </div>
    </aside>

    <!-- Pro Modal -->
    @if (showProModal()) {
      <div class="pro-modal-overlay" (click)="showProModal.set(false)">
        <div class="pro-modal" (click)="$event.stopPropagation()">
          <button class="pro-modal-close" (click)="showProModal.set(false)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>

          <div class="pro-modal-header">
            <div class="pro-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
            <h2 class="pro-modal-title">Belvra Pro</h2>
            <span class="pro-status">В разработке</span>
          </div>

          <div class="pro-pricing">
            <span class="pro-price">299</span>
            <span class="pro-currency">руб/мес</span>
          </div>

          <ul class="pro-features">
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>Неограниченное количество услуг</span>
            </li>
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>Расширенная аналитика и отчёты</span>
            </li>
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>Автоматические напоминания клиентам</span>
            </li>
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>Интеграция с социальными сетями</span>
            </li>
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>Приоритетная поддержка 24/7</span>
            </li>
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>Продвижение в топе поиска</span>
            </li>
            <li>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>
              <span>PRO-бейдж в профиле</span>
            </li>
          </ul>

          <button class="pro-subscribe-btn" disabled>
            Скоро будет доступно
          </button>

          <p class="pro-note">Мы сообщим вам, когда Pro-версия станет доступна</p>
        </div>
      </div>
    }
  `,
  styles: [`
    :host {
      display: contents;
    }

    .sidebar-overlay {
      position: fixed;
      inset: 0;
      z-index: 45;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      animation: fadeIn 0.2s ease;
    }

    @media (min-width: 1024px) {
      .sidebar-overlay {
        display: none;
      }
    }

    .sidebar {
      position: fixed;
      top: 0;
      left: 0;
      z-index: 50;
      width: 280px;
      height: 100vh;
      height: 100dvh;
      display: flex;
      flex-direction: column;
      background: var(--color-bg-primary);
      border-right: 1px solid var(--color-border-secondary);
      transform: translateX(-100%);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      padding-top: var(--ion-safe-area-top, env(safe-area-inset-top));
      padding-bottom: var(--ion-safe-area-bottom, env(safe-area-inset-bottom));
    }

    .sidebar-open {
      transform: translateX(0);
    }

    @media (min-width: 1024px) {
      .sidebar {
        transform: translateX(0);
        width: 260px;
      }
    }

    .sidebar-logo {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid var(--color-border-secondary);
    }

    .close-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border: none;
      background: transparent;
      color: var(--color-text-secondary);
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .close-btn:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .close-btn svg {
      width: 20px;
      height: 20px;
    }

    @media (min-width: 1024px) {
      .close-btn {
        display: none;
      }
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      border-radius: 10px;
    }

    .logo-icon svg {
      width: 20px;
      height: 20px;
      color: white;
    }

    .logo-text {
      font-size: 18px;
      font-weight: 700;
      color: var(--color-text-primary);
      letter-spacing: -0.025em;
    }

    .sidebar-nav {
      flex: 1;
      overflow-y: auto;
      padding: 16px 12px;
    }

    .nav-section {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .nav-section-title {
      padding: 8px 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--color-text-tertiary);
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      font-size: 14px;
      font-weight: 500;
      color: var(--color-text-secondary);
      border-radius: 10px;
      text-decoration: none;
      transition: all 0.15s ease;
    }

    .nav-item:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .nav-item.active {
      background: var(--color-brand-50);
      color: var(--color-brand-600);
    }

    :host-context(.dark) .nav-item.active {
      background: rgba(236, 72, 153, 0.15);
      color: var(--color-brand-400);
    }

    .nav-item-icon {
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .nav-item-icon :deep(svg) {
      width: 20px;
      height: 20px;
    }

    .nav-item-label {
      white-space: nowrap;
    }

    .sidebar-footer {
      padding: 16px;
      border-top: 1px solid var(--color-border-secondary);
    }

    .upgrade-card {
      padding: 16px;
      background: var(--color-surface-secondary);
      border-radius: 14px;
      text-align: center;
    }

    .upgrade-icon {
      width: 40px;
      height: 40px;
      margin: 0 auto 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--color-brand-50);
      color: var(--color-brand-500);
      border-radius: 10px;
    }

    :host-context(.dark) .upgrade-icon {
      background: rgba(236, 72, 153, 0.15);
    }

    .upgrade-icon svg {
      width: 20px;
      height: 20px;
    }

    .upgrade-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text-primary);
      margin: 0 0 4px 0;
    }

    .upgrade-text {
      font-size: 12px;
      color: var(--color-text-tertiary);
      margin: 0 0 12px 0;
    }

    .upgrade-btn {
      width: 100%;
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 500;
      color: white;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      border: none;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .upgrade-btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(236, 72, 153, 0.35);
    }

    /* PRO Status Card */
    .pro-status-card {
      padding: 16px;
      background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.1));
      border: 1px solid rgba(251, 191, 36, 0.3);
      border-radius: 14px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .pro-status-card:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(251, 191, 36, 0.2);
    }

    :host-context(.dark) .pro-status-card {
      background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(245, 158, 11, 0.15));
      border-color: rgba(251, 191, 36, 0.3);
    }

    .pro-status-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .pro-status-active {
      font-size: 11px;
      font-weight: 600;
      color: #16a34a;
      background: rgba(22, 163, 74, 0.1);
      padding: 2px 8px;
      border-radius: 10px;
    }

    :host-context(.dark) .pro-status-active {
      background: rgba(22, 163, 74, 0.2);
      color: #4ade80;
    }

    .pro-status-text {
      margin: 0;
      font-size: 12px;
      color: var(--color-text-secondary);
    }

    .version {
      display: block;
      text-align: center;
      margin-top: 12px;
      font-size: 11px;
      color: var(--color-text-tertiary);
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    /* Pro Modal Styles */
    .pro-modal-overlay {
      position: fixed;
      inset: 0;
      z-index: 100;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      animation: fadeIn 0.2s ease;
    }

    .pro-modal {
      position: relative;
      width: 100%;
      max-width: 400px;
      background: var(--color-surface-primary);
      border-radius: 20px;
      padding: 2rem;
      text-align: center;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }

    .pro-modal-close {
      position: absolute;
      top: 1rem;
      right: 1rem;
      width: 2rem;
      height: 2rem;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      color: var(--color-text-tertiary);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .pro-modal-close:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .pro-modal-close svg {
      width: 1.25rem;
      height: 1.25rem;
    }

    .pro-modal-header {
      margin-bottom: 1.5rem;
    }

    .pro-badge {
      width: 4rem;
      height: 4rem;
      margin: 0 auto 1rem;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      border-radius: 16px;
      color: white;
    }

    .pro-badge svg {
      width: 2rem;
      height: 2rem;
    }

    .pro-modal-title {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--color-text-primary);
      margin: 0 0 0.5rem 0;
    }

    .pro-status {
      display: inline-block;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-brand-600);
      background: var(--color-brand-50);
      border-radius: 20px;
    }

    :host-context(.dark) .pro-status {
      background: rgba(236, 72, 153, 0.15);
      color: var(--color-brand-400);
    }

    .pro-pricing {
      margin-bottom: 1.5rem;
    }

    .pro-price {
      font-size: 3rem;
      font-weight: 800;
      color: var(--color-text-primary);
      line-height: 1;
    }

    .pro-currency {
      font-size: 1rem;
      font-weight: 500;
      color: var(--color-text-tertiary);
      margin-left: 0.25rem;
    }

    .pro-features {
      list-style: none;
      padding: 0;
      margin: 0 0 1.5rem 0;
      text-align: left;
    }

    .pro-features li {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem 0;
      font-size: 0.9375rem;
      color: var(--color-text-secondary);
    }

    .pro-features li svg {
      width: 1.25rem;
      height: 1.25rem;
      color: var(--color-brand-500);
      flex-shrink: 0;
    }

    .pro-subscribe-btn {
      width: 100%;
      padding: 0.875rem 1.5rem;
      font-size: 1rem;
      font-weight: 600;
      color: white;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      border: none;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .pro-subscribe-btn:not(:disabled):hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(236, 72, 153, 0.4);
    }

    .pro-subscribe-btn:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .pro-note {
      margin: 1rem 0 0 0;
      font-size: 0.8125rem;
      color: var(--color-text-tertiary);
    }
  `]
})
export class SidebarComponent {
  private router = inject(Router);
  private authService = inject(AuthService);
  subscriptionService = inject(SubscriptionService);

  items = input<NavItem[]>([]);
  isOpen = input<boolean>(false);
  close = output<void>();
  showProModal = signal(false);

  navigateToSubscription(): void {
    this.close.emit();
    const route = this.authService.isMaster() ? '/master/subscription' : '/client/subscription';
    this.router.navigate([route]);
  }
}
