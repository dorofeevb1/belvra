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
  styleUrl: './favorites.component.scss'
})
export class FavoritesComponent implements OnInit {
  private favoritesService = inject(FavoritesService);

  favorites = this.favoritesService.favorites;
  isLoading = this.favoritesService.isLoading;

  ngOnInit(): void {
    this.favoritesService.fetchFavorites().subscribe();
  }
}
