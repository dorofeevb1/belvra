import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FavoritesService, FavoriteMaster } from '../../../core/services/favorites.service';
import { FavoriteButtonComponent } from '../../../shared/components/favorite-button/favorite-button.component';

@Component({
  selector: 'app-favorites',
  standalone: true,
  imports: [CommonModule, RouterLink, FavoriteButtonComponent],
  template: `
    <div class="favorites-page">
      <header class="page-header">
        <h1>Избранные мастера</h1>
        <p class="subtitle">Мастера, которых вы добавили в избранное</p>
      </header>

      @if (isLoading()) {
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Загрузка...</p>
        </div>
      } @else if (favorites().length === 0) {
        <div class="empty-state">
          <div class="empty-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
          </div>
          <h2>Нет избранных мастеров</h2>
          <p>Добавляйте понравившихся мастеров в избранное, чтобы легко их найти</p>
          <a routerLink="/client" class="btn-primary">Найти мастера</a>
        </div>
      } @else {
        <div class="masters-grid">
          @for (favorite of favorites(); track favorite.id) {
            <div class="master-card">
              <div class="card-header">
                <div class="avatar">
                  @if (favorite.master.user.avatar) {
                    <img [src]="favorite.master.user.avatar" [alt]="favorite.master.user.full_name" />
                  } @else {
                    <span class="avatar-text">{{ favorite.master.user.full_name.charAt(0) }}</span>
                  }
                </div>
                <app-favorite-button [masterId]="favorite.master.id" size="small" />
              </div>

              <div class="card-body">
                <h3>{{ favorite.master.user.full_name }}</h3>
                <p class="specialization">{{ favorite.master.specialization || 'Мастер красоты' }}</p>

                <div class="rating">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="#fbbf24" stroke="#fbbf24" stroke-width="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  <span>{{ favorite.master.rating }}</span>
                  <span class="reviews">({{ favorite.master.reviews_count }} отзывов)</span>
                </div>

                @if (favorite.master.bio) {
                  <p class="bio">{{ favorite.master.bio | slice:0:100 }}{{ favorite.master.bio.length > 100 ? '...' : '' }}</p>
                }

                <div class="card-footer">
                  <span class="experience">{{ favorite.master.experience_years }} лет опыта</span>
                  @if (favorite.master.is_available) {
                    <span class="status available">Доступен</span>
                  } @else {
                    <span class="status unavailable">Недоступен</span>
                  }
                </div>
              </div>

              <div class="card-actions">
                <a [routerLink]="['/client/master', favorite.master.id]" class="btn-secondary">
                  Профиль
                </a>
                <a [routerLink]="['/client/booking', favorite.master.id]" class="btn-primary" [class.disabled]="!favorite.master.is_available">
                  Записаться
                </a>
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .favorites-page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem;
    }

    .page-header {
      margin-bottom: 2rem;
    }

    .page-header h1 {
      margin: 0 0 0.5rem;
      font-size: 1.75rem;
      font-weight: 700;
      color: #111827;
    }

    .subtitle {
      margin: 0;
      color: #6b7280;
    }

    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 2rem;
      text-align: center;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid #e5e7eb;
      border-top-color: #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 1rem;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .empty-icon {
      width: 100px;
      height: 100px;
      border-radius: 50%;
      background: #f3f4f6;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1.5rem;
      color: #9ca3af;
    }

    .empty-state h2 {
      margin: 0 0 0.5rem;
      font-size: 1.25rem;
      color: #111827;
    }

    .empty-state p {
      margin: 0 0 1.5rem;
      color: #6b7280;
      max-width: 300px;
    }

    .btn-primary {
      display: inline-block;
      padding: 0.75rem 1.5rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .btn-primary.disabled {
      opacity: 0.5;
      pointer-events: none;
    }

    .btn-secondary {
      display: inline-block;
      padding: 0.75rem 1.5rem;
      background: #f3f4f6;
      color: #374151;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .btn-secondary:hover {
      background: #e5e7eb;
    }

    .masters-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.5rem;
    }

    .master-card {
      background: white;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      transition: all 0.2s;
    }

    .master-card:hover {
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
      transform: translateY(-4px);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 1.25rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .avatar {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: white;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 3px solid rgba(255, 255, 255, 0.3);
    }

    .avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .avatar-text {
      font-size: 1.5rem;
      font-weight: 600;
      color: #667eea;
    }

    .card-body {
      padding: 1.25rem;
    }

    .card-body h3 {
      margin: 0 0 0.25rem;
      font-size: 1.125rem;
      font-weight: 600;
      color: #111827;
    }

    .specialization {
      margin: 0 0 0.75rem;
      color: #6b7280;
      font-size: 0.875rem;
    }

    .rating {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 0.75rem;
      font-size: 0.875rem;
      font-weight: 500;
    }

    .reviews {
      color: #9ca3af;
      font-weight: normal;
    }

    .bio {
      margin: 0 0 0.75rem;
      font-size: 0.875rem;
      color: #6b7280;
      line-height: 1.5;
    }

    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .experience {
      font-size: 0.75rem;
      color: #9ca3af;
    }

    .status {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 500;
    }

    .status.available {
      background: #d1fae5;
      color: #059669;
    }

    .status.unavailable {
      background: #fee2e2;
      color: #dc2626;
    }

    .card-actions {
      display: flex;
      gap: 0.5rem;
      padding: 1rem 1.25rem;
      border-top: 1px solid #f3f4f6;
    }

    .card-actions a {
      flex: 1;
      text-align: center;
    }
  `]
})
export class FavoritesComponent implements OnInit {
  private favoritesService = inject(FavoritesService);

  favorites = this.favoritesService.favorites;
  isLoading = this.favoritesService.isLoading;

  ngOnInit(): void {
    this.favoritesService.fetchFavorites().subscribe();
  }
}
