import { Component, inject, output, signal, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
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
            <span class="logo-text">Belvra</span>
          </div>
        </div>

        <!-- Right Section -->
        <div class="header-right">
          <!-- Notifications -->
          <app-notification-bell />

          <!-- User Menu -->
          @if (authService.currentUser(); as user) {
            <div class="user-menu-wrapper">
              <button class="user-menu-btn" (click)="toggleDropdown($event)">
                <div class="user-avatar">
                  <span>{{ getInitials(user.name) }}</span>
                </div>
                <div class="user-info">
                  <span class="user-name">{{ user.name }}</span>
                  <span class="user-role">{{ user.role === 'master' ? 'Мастер' : 'Клиент' }}</span>
                </div>
                <svg class="chevron" [class.chevron-open]="dropdownOpen()" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
                </svg>
              </button>

              <!-- Dropdown Menu -->
              @if (dropdownOpen()) {
                <div class="dropdown-menu">
                  <div class="dropdown-header">
                    <div class="dropdown-avatar">
                      <span>{{ getInitials(user.name) }}</span>
                    </div>
                    <div class="dropdown-user-info">
                      <span class="dropdown-user-name">{{ user.name }}</span>
                      <span class="dropdown-user-email">{{ user.email }}</span>
                    </div>
                  </div>

                  <div class="dropdown-divider"></div>

                  <!-- Role switch -->
                  @if (user.role === 'master') {
                    <button class="dropdown-item dropdown-item-switch" (click)="switchToClient()">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                      </svg>
                      <span>Режим клиента</span>
                    </button>
                  } @else if (authService.hasMasterProfile()) {
                    <button class="dropdown-item dropdown-item-switch" (click)="switchToMaster()">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" />
                      </svg>
                      <span>Режим мастера</span>
                    </button>
                  } @else {
                    <button class="dropdown-item dropdown-item-switch" (click)="becomeMaster()">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                      </svg>
                      <span>Стать мастером</span>
                    </button>
                  }

                  <button class="dropdown-item" (click)="goToSettings()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.506-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z" />
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>Настройки</span>
                  </button>

                  <div class="dropdown-divider"></div>

                  <button class="dropdown-item dropdown-item-danger" (click)="logout()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                    </svg>
                    <span>Выйти</span>
                  </button>
                </div>
              }
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

    /* User Menu */
    .user-menu-wrapper {
      position: relative;
    }

    .user-menu-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 8px 4px 4px;
      border: 1px solid transparent;
      background: transparent;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .user-menu-btn:hover {
      background: var(--color-surface-secondary);
    }

    .user-menu-btn:active,
    .user-menu-btn[aria-expanded="true"] {
      background: var(--color-surface-hover);
      border-color: var(--color-border-secondary);
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 10px;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.025em;
      flex-shrink: 0;
    }

    .user-info {
      display: none;
      flex-direction: column;
      align-items: flex-start;
      gap: 1px;
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
      line-height: 1.2;
    }

    .user-role {
      font-size: 11px;
      color: var(--color-text-tertiary);
      line-height: 1.2;
    }

    .chevron {
      width: 16px;
      height: 16px;
      color: var(--color-text-tertiary);
      transition: transform 0.2s ease;
      flex-shrink: 0;
      display: none;
    }

    @media (min-width: 640px) {
      .chevron {
        display: block;
      }
    }

    .chevron-open {
      transform: rotate(180deg);
    }

    /* Dropdown */
    .dropdown-menu {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      width: 260px;
      background: var(--color-surface-primary);
      border: 1px solid var(--color-border-secondary);
      border-radius: 16px;
      box-shadow: 0 10px 40px -4px rgba(0, 0, 0, 0.12), 0 4px 12px -2px rgba(0, 0, 0, 0.06);
      padding: 6px;
      z-index: 50;
      animation: dropdownIn 0.15s ease;
    }

    :host-context(.dark) .dropdown-menu {
      box-shadow: 0 10px 40px -4px rgba(0, 0, 0, 0.4), 0 4px 12px -2px rgba(0, 0, 0, 0.2);
    }

    @keyframes dropdownIn {
      from {
        opacity: 0;
        transform: translateY(-4px) scale(0.98);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    .dropdown-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
    }

    .dropdown-avatar {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, var(--color-brand-500), var(--color-brand-600));
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 700;
      flex-shrink: 0;
    }

    .dropdown-user-info {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .dropdown-user-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .dropdown-user-email {
      font-size: 12px;
      color: var(--color-text-tertiary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .dropdown-divider {
      height: 1px;
      background: var(--color-border-secondary);
      margin: 4px 8px;
    }

    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      padding: 10px;
      border: none;
      background: transparent;
      border-radius: 10px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      color: var(--color-text-secondary);
      transition: all 0.12s ease;
      text-align: left;
    }

    .dropdown-item:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .dropdown-item svg {
      width: 18px;
      height: 18px;
      flex-shrink: 0;
    }

    .dropdown-item-switch {
      color: var(--color-brand-600);
    }

    .dropdown-item-switch:hover {
      background: rgba(var(--color-brand-rgb, 139, 92, 246), 0.08);
      color: var(--color-brand-700);
    }

    :host-context(.dark) .dropdown-item-switch:hover {
      background: rgba(var(--color-brand-rgb, 139, 92, 246), 0.15);
      color: var(--color-brand-400);
    }

    .dropdown-item-danger {
      color: #ef4444;
    }

    .dropdown-item-danger:hover {
      background: rgba(239, 68, 68, 0.08);
      color: #dc2626;
    }

    :host-context(.dark) .dropdown-item-danger:hover {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
    }
  `]
})
export class HeaderComponent {
  private elRef = inject(ElementRef);
  private router = inject(Router);

  authService = inject(AuthService);
  themeService = inject(ThemeService);
  menuToggle = output<void>();
  dropdownOpen = signal(false);

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event) {
    if (!this.elRef.nativeElement.contains(event.target)) {
      this.dropdownOpen.set(false);
    }
  }

  toggleDropdown(event: Event) {
    event.stopPropagation();
    this.dropdownOpen.update(v => !v);
  }

  getInitials(name: string): string {
    return name
      .split(' ')
      .map(part => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase();
  }

  goToSettings() {
    this.dropdownOpen.set(false);
    const route = this.authService.isMaster() ? '/master/settings' : '/client/profile';
    this.router.navigate([route]);
  }

  switchToClient() {
    this.dropdownOpen.set(false);
    this.authService.switchRole('client').subscribe();
  }

  switchToMaster() {
    this.dropdownOpen.set(false);
    this.authService.switchRole('master').subscribe();
  }

  becomeMaster() {
    this.dropdownOpen.set(false);
    this.authService.becomeMaster().subscribe();
  }

  toggleTheme() {
    this.themeService.toggleTheme();
  }

  logout() {
    this.dropdownOpen.set(false);
    this.authService.logout();
  }
}
