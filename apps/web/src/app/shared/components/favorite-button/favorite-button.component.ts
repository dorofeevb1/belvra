import { Component, inject, input, signal, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FavoritesService } from '../../../core/services/favorites.service';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-favorite-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (authService.isClient()) {
      <button
        class="favorite-btn"
        [class.is-favorite]="isFavorite()"
        [class.size-small]="size() === 'small'"
        [class.size-large]="size() === 'large'"
        [disabled]="isLoading()"
        (click)="toggleFavorite($event)"
        [title]="isFavorite() ? 'Удалить из избранного' : 'Добавить в избранное'"
      >
        @if (isLoading()) {
          <span class="spinner"></span>
        } @else {
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            [attr.fill]="isFavorite() ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
          </svg>
        }
        @if (showLabel()) {
          <span class="label">{{ isFavorite() ? 'В избранном' : 'В избранное' }}</span>
        }
      </button>
    }
  `,
  styles: [`
    .favorite-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
      border-radius: 10px;
      cursor: pointer;
      color: #a09bb0;
      transition: all 0.2s ease;
      font-size: 0.875rem;
      font-weight: 500;
    }

    .favorite-btn:hover:not(:disabled) {
      border-color: rgba(239, 68, 68, 0.3);
      color: #f87171;
      background: rgba(239, 68, 68, 0.06);
    }

    .favorite-btn.is-favorite {
      color: #f87171;
      border-color: rgba(239, 68, 68, 0.25);
      background: rgba(239, 68, 68, 0.08);
    }

    .favorite-btn:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }

    .favorite-btn svg {
      width: 20px;
      height: 20px;
    }

    .favorite-btn.size-small {
      padding: 6px 8px;
    }

    .favorite-btn.size-small svg {
      width: 16px;
      height: 16px;
    }

    .favorite-btn.size-large {
      padding: 10px 16px;
      font-size: 1rem;
    }

    .favorite-btn.size-large svg {
      width: 24px;
      height: 24px;
    }

    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.1);
      border-top-color: #f87171;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .label {
      white-space: nowrap;
    }
  `]
})
export class FavoriteButtonComponent implements OnInit, OnChanges {
  masterId = input.required<string>();
  size = input<'small' | 'medium' | 'large'>('medium');
  showLabel = input<boolean>(false);

  authService = inject(AuthService);
  private favoritesService = inject(FavoritesService);
  private notificationService = inject(NotificationService);

  isFavorite = signal(false);
  isLoading = signal(false);

  ngOnInit(): void {
    this.checkFavoriteStatus();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['masterId'] && !changes['masterId'].firstChange) {
      this.checkFavoriteStatus();
    }
  }

  private checkFavoriteStatus(): void {
    // First check from local cache
    if (this.favoritesService.isFavorite(this.masterId())) {
      this.isFavorite.set(true);
      return;
    }

    // Then verify with server
    this.favoritesService.checkFavorite(this.masterId()).subscribe(result => {
      this.isFavorite.set(result);
    });
  }

  toggleFavorite(event: Event): void {
    event.preventDefault();
    event.stopPropagation();

    if (this.isLoading()) return;

    this.isLoading.set(true);
    this.favoritesService.toggleFavorite(this.masterId()).subscribe({
      next: (response) => {
        this.isFavorite.set(response.is_favorite);
        this.notificationService.success(
          response.is_favorite ? 'Добавлено в избранное' : 'Удалено из избранного'
        );
        this.isLoading.set(false);
      },
      error: (error) => {
        this.notificationService.error(
          error.error?.detail || 'Не удалось обновить избранное'
        );
        this.isLoading.set(false);
      }
    });
  }
}
