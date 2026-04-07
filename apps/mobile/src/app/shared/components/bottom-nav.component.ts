import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

export interface BottomNavItem {
  label: string;
  icon: string;
  route?: string;
  action?: string;
  badge?: number;
  exact?: boolean;
}

@Component({
  selector: 'app-bottom-nav',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <nav class="bottom-nav">
      @for (item of items(); track item.label) {
        @if (item.route) {
          <a
            [routerLink]="item.route"
            routerLinkActive="active"
            [routerLinkActiveOptions]="{ exact: item.exact ?? false }"
            class="nav-tab"
          >
            <span class="nav-tab-icon" [innerHTML]="item.icon"></span>
            @if (item.badge && item.badge > 0) {
              <span class="nav-tab-badge">{{ item.badge > 99 ? '99+' : item.badge }}</span>
            }
            <span class="nav-tab-label">{{ item.label }}</span>
          </a>
        } @else {
          <button
            class="nav-tab"
            type="button"
            (click)="actionClick.emit(item.action!)"
          >
            <span class="nav-tab-icon" [innerHTML]="item.icon"></span>
            <span class="nav-tab-label">{{ item.label }}</span>
          </button>
        }
      }
    </nav>
  `,
  styles: [`
    :host {
      display: block;
    }

    .bottom-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 40;
      display: flex;
      align-items: stretch;
      justify-content: space-around;
      border-top: 1px solid var(--color-border-secondary);
      padding-bottom: var(--ion-safe-area-bottom, env(safe-area-inset-bottom, 0px));
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }

    :host-context(:not(.dark)) .bottom-nav {
      background: rgba(253, 252, 251, 0.92);
    }

    :host-context(.dark) .bottom-nav {
      background: rgba(24, 24, 27, 0.92);
    }

    .nav-tab {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      padding: 6px 4px 8px;
      min-height: 50px;
      text-decoration: none;
      border: none;
      background: none;
      color: var(--color-text-tertiary);
      transition: color 0.15s ease;
      position: relative;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }

    .nav-tab:active {
      opacity: 0.7;
    }

    .nav-tab.active {
      color: var(--color-brand-500);
    }

    :host-context(.dark) .nav-tab.active {
      color: var(--color-brand-400);
    }

    .nav-tab-icon {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }

    ::ng-deep .nav-tab-icon svg {
      width: 24px;
      height: 24px;
    }

    .nav-tab-badge {
      position: absolute;
      top: 2px;
      right: 50%;
      transform: translate(14px, -4px);
      min-width: 16px;
      height: 16px;
      padding: 0 4px;
      border-radius: 8px;
      background: var(--color-brand-500);
      color: white;
      font-size: 10px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      line-height: 1;
    }

    .nav-tab-label {
      font-size: 10px;
      font-weight: 500;
      line-height: 1.2;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 72px;
      text-align: center;
    }

    @media (min-width: 1024px) {
      :host {
        display: none;
      }
    }
  `]
})
export class BottomNavComponent {
  items = input<BottomNavItem[]>([]);
  actionClick = output<string>();
}
