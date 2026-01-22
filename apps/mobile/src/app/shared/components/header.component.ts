import { Component, inject, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService, ThemeService } from '../../core/services';
import { NotificationBellComponent } from './notification-bell/notification-bell.component';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, NotificationBellComponent],
  template: `
    <header class="header">
      <div class="header-content">
        <!-- Left Section -->
        <div class="header-left">
          <!-- Mobile menu button -->
          <button
            (click)="menuToggle.emit()"
            class="menu-btn"
            type="button"
            aria-label="Открыть меню"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
          </button>

          <!-- Logo -->
          <div class="logo">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
              </svg>
            </div>
            <span class="logo-text">BeautyBook</span>
          </div>
        </div>

        <!-- Right Section -->
        <div class="header-right">
          <!-- Notifications -->
          <app-notification-bell />

          <!-- User Menu -->
          @if (authService.currentUser(); as user) {
            <div class="user-menu">
              <div class="user-info">
                <span class="user-name">{{ user.name }}</span>
                <span class="user-role">{{ user.role === 'master' ? 'Мастер' : 'Клиент' }}</span>
              </div>
            </div>
          }
        </div>
      </div>
    </header>
  `,
  styles: [`
    :host {
      display: block;
    }

    .header {
      position: sticky;
      top: 0;
      z-index: 40;
      background: var(--color-surface-primary);
      border-bottom: 1px solid var(--color-border-secondary);
    }

    .header-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 56px;
      padding: 0 12px;
    }

    @media (min-width: 1024px) {
      .header-content {
        height: 64px;
        padding: 0 24px;
      }
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    @media (min-width: 640px) {
      .header-right {
        gap: 12px;
      }
    }

    .menu-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border: none;
      background: var(--color-surface-secondary);
      color: var(--color-text-secondary);
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .menu-btn:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .menu-btn svg {
      width: 20px;
      height: 20px;
    }

    @media (min-width: 1024px) {
      .menu-btn {
        display: none;
      }
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .logo-icon {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      border-radius: 8px;
    }

    @media (min-width: 640px) {
      .logo-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
      }
    }

    .logo-icon svg {
      width: 18px;
      height: 18px;
      color: white;
    }

    @media (min-width: 640px) {
      .logo-icon svg {
        width: 20px;
        height: 20px;
      }
    }

    .logo-text {
      font-size: 16px;
      font-weight: 700;
      color: var(--color-text-primary);
      letter-spacing: -0.025em;
    }

    @media (min-width: 640px) {
      .logo-text {
        font-size: 18px;
      }
    }

    .user-menu {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .user-info {
      display: none;
      flex-direction: column;
      align-items: flex-end;
    }

    @media (min-width: 640px) {
      .user-info {
        display: flex;
      }
    }

    .user-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text-primary);
      max-width: 120px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-role {
      font-size: 11px;
      color: var(--color-text-tertiary);
    }
  `]
})
export class HeaderComponent {
  authService = inject(AuthService);
  themeService = inject(ThemeService);
  menuToggle = output<void>();
}
