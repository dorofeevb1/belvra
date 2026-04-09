import { Component, ViewEncapsulation, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
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
  encapsulation: ViewEncapsulation.None,
  template: `
    <nav class="belvra-bottom-nav">
      @for (item of items(); track item.label) {
        @if (item.route) {
          <a
            [routerLink]="item.route"
            routerLinkActive="active"
            [routerLinkActiveOptions]="{ exact: item.exact ?? false }"
            class="belvra-bottom-nav__tab"
          >
            <span class="belvra-bottom-nav__icon" [innerHTML]="safeIcon(item.icon)"></span>
            @if (item.badge && item.badge > 0) {
              <span class="belvra-bottom-nav__badge">{{ item.badge > 99 ? '99+' : item.badge }}</span>
            }
            <span class="belvra-bottom-nav__label">{{ item.label }}</span>
          </a>
        } @else {
          <button
            class="belvra-bottom-nav__tab"
            type="button"
            (click)="actionClick.emit(item.action!)"
          >
            <span class="belvra-bottom-nav__icon" [innerHTML]="safeIcon(item.icon)"></span>
            <span class="belvra-bottom-nav__label">{{ item.label }}</span>
          </button>
        }
      }
    </nav>
  `,
  styles: [`
    .belvra-bottom-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 40;
      display: flex;
      align-items: stretch;
      justify-content: space-around;
      height: 60px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      padding-bottom: var(--ion-safe-area-bottom, env(safe-area-inset-bottom, 0px));
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      background: rgba(15, 10, 30, 0.95);
    }

    .belvra-bottom-nav__tab {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      padding: 6px 4px 8px;
      min-height: 50px;
      text-decoration: none;
      border: none;
      background: none;
      color: #71717a;
      transition: color 0.2s ease;
      position: relative;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }

    .belvra-bottom-nav__tab:active {
      opacity: 0.7;
    }

    .belvra-bottom-nav__tab.active {
      color: #7C3AED;
    }

    .belvra-bottom-nav__tab.active::after {
      content: '';
      position: absolute;
      top: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 24px;
      height: 2px;
      background: #7C3AED;
      border-radius: 0 0 2px 2px;
    }

    .belvra-bottom-nav__icon {
      width: 22px;
      height: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }

    .belvra-bottom-nav__icon svg {
      width: 22px;
      height: 22px;
    }

    .belvra-bottom-nav__badge {
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

    .belvra-bottom-nav__label {
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.2px;
      line-height: 1.2;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 72px;
      text-align: center;
    }

    @media (min-width: 1024px) {
      .belvra-bottom-nav {
        display: none;
      }
    }
  `]
})
export class BottomNavComponent {
  private sanitizer = inject(DomSanitizer);
  items = input<BottomNavItem[]>([]);
  actionClick = output<string>();

  safeIcon(icon: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(icon);
  }
}
