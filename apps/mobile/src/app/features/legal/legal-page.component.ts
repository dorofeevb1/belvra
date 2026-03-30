import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-legal-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="legal-page">
      <button
        (click)="themeService.toggleTheme()"
        class="theme-toggle btn btn-ghost btn-icon"
        type="button"
      >
        @if (themeService.isDark()) {
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path>
          </svg>
        } @else {
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
          </svg>
        }
      </button>

      <div class="legal-container">
        <div class="legal-header">
          <a routerLink="/register" class="back-link">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
            Назад
          </a>
          <h1>{{ title() }}</h1>
          @if (version()) {
            <p class="version">Версия {{ version() }} от {{ effectiveDate() }}</p>
          }
        </div>

        <div class="legal-card card">
          @if (isLoading()) {
            <div class="loading">
              <div class="spinner"></div>
              <span>Загрузка...</span>
            </div>
          } @else {
            <div class="legal-content" [innerHTML]="formattedContent()"></div>
          }
        </div>

        <div class="legal-footer">
          <p>Belvra © 2025</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .legal-page {
      min-height: 100vh;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 2rem 1.5rem;
      background-color: var(--color-bg-secondary);
    }

    .theme-toggle {
      position: fixed;
      top: 1.5rem;
      right: 1.5rem;
      z-index: 50;
    }

    .legal-container {
      width: 100%;
      max-width: 720px;
    }

    .legal-header {
      margin-bottom: 1.5rem;

      h1 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--color-text-primary);
        margin: 0.75rem 0 0.25rem;
      }

      .version {
        font-size: 0.8125rem;
        color: var(--color-text-tertiary);
      }
    }

    .back-link {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.875rem;
      color: var(--color-brand-500);
      text-decoration: none;

      &:hover {
        color: var(--color-brand-600);
      }
    }

    .legal-card {
      padding: 2rem;
    }

    .legal-content {
      font-size: 0.875rem;
      line-height: 1.7;
      color: var(--color-text-secondary);
      white-space: pre-line;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      padding: 3rem;
      color: var(--color-text-tertiary);
    }

    .legal-footer {
      text-align: center;
      margin-top: 2rem;

      p {
        font-size: 0.75rem;
        color: var(--color-text-tertiary);
      }
    }

    @media (max-width: 480px) {
      .legal-page {
        padding: 1rem;
      }

      .legal-card {
        padding: 1.25rem;
      }

      .legal-header h1 {
        font-size: 1.25rem;
      }
    }
  `]
})
export class LegalPageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api = inject(ApiService);
  themeService = inject(ThemeService);

  title = signal('');
  version = signal('');
  effectiveDate = signal('');
  formattedContent = signal('');
  isLoading = signal(true);

  private docType: 'privacy' | 'terms' = 'privacy';

  ngOnInit(): void {
    const path = this.route.snapshot.routeConfig?.path;
    this.docType = path === 'terms' ? 'terms' : 'privacy';

    this.api.get(`/auth/legal/`, { type: this.docType }).subscribe({
      next: (data: any) => {
        this.title.set(data.title);
        this.version.set(data.version);
        this.effectiveDate.set(data.effective_date);
        this.formattedContent.set(data.content);
        this.isLoading.set(false);
      },
      error: () => {
        this.title.set(this.docType === 'privacy' ? 'Политика конфиденциальности' : 'Пользовательское соглашение');
        this.formattedContent.set('Не удалось загрузить документ. Попробуйте позже.');
        this.isLoading.set(false);
      }
    });
  }
}
