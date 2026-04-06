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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
              </svg>
            </div>
            <span class="logo-text">Belvra</span>
          </div>
        </div>

        <!-- Right Section -->
        <div class="header-right">
          <!-- Notifications -->
          <app-notification-bell />

          <!-- User Menu -->
          @if (authService.currentUser(); as user) {
            <div class="user-menu">
              <div class="user-avatar">
                {{ user.name.charAt(0).toUpperCase() }}
              </div>
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
      padding-top: max(var(--ion-safe-area-top, env(safe-area-inset-top, 0px)), 24px);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }

    /* Glass effect for light mode */
    :host-context(:not(.dark)) .header {
      background: rgba(253, 252, 251, 0.85);
    }

    /* Glass effect for dark mode */
    :host-context(.dark) .header {
      background: rgba(24, 24, 27, 0.85);
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
      gap: 8px;
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
      width: 40px;
      height: 40px;
      border: none;
      background: var(--color-surface-secondary);
      color: var(--color-text-secondary);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .menu-btn:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .menu-btn:active {
      transform: scale(0.95);
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
      gap: 10px;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(145deg, var(--color-brand-500), var(--color-brand-600));
      border-radius: 10px;
      box-shadow: 0 4px 12px -2px rgba(236, 72, 153, 0.4);
    }

    @media (min-width: 640px) {
      .logo-icon {
        width: 40px;
        height: 40px;
        border-radius: 12px;
      }
    }

    .logo-icon svg {
      width: 20px;
      height: 20px;
      color: white;
    }

    @media (min-width: 640px) {
      .logo-icon svg {
        width: 22px;
        height: 22px;
      }
    }

    .logo-text {
      font-size: 17px;
      font-weight: 700;
      color: var(--color-text-primary);
      letter-spacing: -0.02em;
    }

    @media (min-width: 640px) {
      .logo-text {
        font-size: 19px;
      }
    }

    .theme-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border: none;
      background: var(--color-surface-secondary);
      color: var(--color-text-secondary);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .theme-btn:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .theme-btn:active {
      transform: scale(0.95);
    }

    .theme-btn svg {
      width: 18px;
      height: 18px;
    }

    .user-menu {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 4px 8px 4px 4px;
      background: var(--color-surface-secondary);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .user-menu:hover {
      background: var(--color-surface-hover);
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, var(--color-brand-400), var(--color-brand-600));
      color: white;
      font-size: 13px;
      font-weight: 600;
      border-radius: 8px;
    }

    .user-info {
      display: none;
      flex-direction: column;
      align-items: flex-start;
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
      max-width: 100px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.2;
    }

    .user-role {
      font-size: 11px;
      color: var(--color-text-tertiary);
      line-height: 1.2;
    }
  `]
})
export class HeaderComponent {
  authService = inject(AuthService);
  themeService = inject(ThemeService);
  menuToggle = output<void>();
}
