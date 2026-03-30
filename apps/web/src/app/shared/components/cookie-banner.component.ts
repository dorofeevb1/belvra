import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-cookie-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (visible()) {
      <div class="cookie-banner">
        <div class="cookie-content">
          <p>
            Мы используем только технические файлы cookie для работы аутентификации.
            Рекламные и аналитические cookie не используются.
            <a href="/privacy-policy" target="_blank">Подробнее</a>
          </p>
          <button type="button" class="cookie-accept" (click)="accept()">Понятно</button>
        </div>
      </div>
    }
  `,
  styles: [`
    .cookie-banner {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 9999;
      background: var(--color-surface-primary);
      border-top: 1px solid var(--color-border);
      box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.1);
      padding: 1rem 1.5rem;
      animation: slideUp 0.3s ease;
    }

    .cookie-content {
      max-width: 64rem;
      margin: 0 auto;
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
    }

    p {
      flex: 1;
      font-size: 0.8125rem;
      line-height: 1.5;
      color: var(--color-text-secondary);
      margin: 0;
      min-width: 200px;

      a {
        color: var(--color-brand-500);
        text-decoration: none;
        &:hover { text-decoration: underline; }
      }
    }

    .cookie-accept {
      padding: 0.5rem 1.25rem;
      font-size: 0.8125rem;
      font-weight: 600;
      color: white;
      background: var(--color-brand-500);
      border: none;
      border-radius: 0.5rem;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s;

      &:hover {
        background: var(--color-brand-600);
      }
    }

    @keyframes slideUp {
      from { transform: translateY(100%); }
      to { transform: translateY(0); }
    }

    @media (max-width: 480px) {
      .cookie-content {
        flex-direction: column;
        text-align: center;
      }
      .cookie-accept {
        width: 100%;
      }
    }
  `]
})
export class CookieBannerComponent {
  visible = signal(!localStorage.getItem('cookie_consent'));

  accept(): void {
    localStorage.setItem('cookie_consent', 'accepted');
    this.visible.set(false);
  }
}
