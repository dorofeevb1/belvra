import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

export interface NavItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
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
          <span class="logo-text">BeautyBook</span>
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
      </nav>

      <!-- Footer -->
      <div class="sidebar-footer">
        <div class="upgrade-card">
          <div class="upgrade-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
            </svg>
          </div>
          <p class="upgrade-title">BeautyBook Pro</p>
          <p class="upgrade-text">Расширьте возможности</p>
          <button class="upgrade-btn">Подробнее</button>
        </div>
        <span class="version">v2.0.0</span>
      </div>
    </aside>
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
      width: 256px;
      height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--color-bg-primary);
      border-right: 1px solid var(--color-border-secondary);
      transform: translateX(-100%);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .sidebar-open {
      transform: translateX(0);
    }

    @media (min-width: 1024px) {
      .sidebar {
        transform: translateX(0);
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
  `]
})
export class SidebarComponent {
  items = input<NavItem[]>([]);
  isOpen = input<boolean>(false);
  close = output<void>();
}
