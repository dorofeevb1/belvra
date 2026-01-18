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

          <!-- Logo (mobile only) -->
          <div class="logo mobile-only">
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
          <!-- Theme Toggle -->
          <button
            (click)="themeService.toggleTheme()"
            class="icon-btn"
            type="button"
            [attr.aria-label]="themeService.isDark() ? 'Светлая тема' : 'Темная тема'"
          >
            @if (themeService.isDark()) {
              <svg class="sun-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path>
              </svg>
            } @else {
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
              </svg>
            }
          </button>

          <!-- Notifications -->
          <app-notification-bell />

          <!-- Divider -->
          <div class="divider desktop-only"></div>

          <!-- User Menu -->
          @if (authService.currentUser(); as user) {
            <div class="user-menu">
              <div class="user-info desktop-only">
                <span class="user-name">{{ user.name }}</span>
                <span class="user-role">{{ user.role === 'master' ? 'Мастер' : 'Клиент' }}</span>
              </div>

              <!-- Avatar -->
              <div class="avatar">
                @if (user.avatar) {
                  <img [src]="user.avatar" [alt]="user.name" />
                } @else {
                  <span class="avatar-text">{{ user.name.charAt(0) }}</span>
                }
                <span class="avatar-status"></span>
              </div>
            </div>
          }

          <!-- Logout -->
          <button
            (click)="authService.logout()"
            class="icon-btn logout-btn"
            type="button"
            title="Выйти"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
            </svg>
          </button>
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
      background: var(--color-bg-primary);
      border-bottom: 1px solid var(--color-border-secondary);
    }

    .header-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
      padding: 0 16px;
    }

    @media (min-width: 1024px) {
      .header-content {
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

    .menu-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border: none;
      background: transparent;
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

    .mobile-only {
      display: flex;
    }

    @media (min-width: 1024px) {
      .mobile-only {
        display: none;
      }
    }

    .desktop-only {
      display: none;
    }

    @media (min-width: 640px) {
      .desktop-only {
        display: flex;
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

    .icon-btn {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border: none;
      background: transparent;
      color: var(--color-text-secondary);
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .icon-btn:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .icon-btn svg {
      width: 20px;
      height: 20px;
    }

    .sun-icon {
      color: #fbbf24;
    }

    .divider {
      width: 1px;
      height: 24px;
      background: var(--color-border-primary);
      margin: 0 8px;
    }

    .user-menu {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .user-info {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }

    .user-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text-primary);
    }

    .user-role {
      font-size: 12px;
      color: var(--color-text-tertiary);
    }

    .avatar {
      position: relative;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--color-brand-100);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .avatar-text {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-brand-600);
    }

    .avatar-status {
      position: absolute;
      bottom: 0;
      right: 0;
      width: 12px;
      height: 12px;
      background: var(--color-success);
      border: 2px solid var(--color-bg-primary);
      border-radius: 50%;
    }

    .logout-btn:hover {
      color: var(--color-error);
    }
  `]
})
export class HeaderComponent {
  authService = inject(AuthService);
  themeService = inject(ThemeService);
  menuToggle = output<void>();
}
