import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap, of, catchError, map } from 'rxjs';
import { ApiService } from './api.service';

export interface FavoriteMaster {
  id: string;
  master: {
    id: string;
    user: {
      id: string;
      email: string;
      full_name: string;
      avatar?: string;
    };
    bio: string;
    experience_years: number;
    specialization: string;
    rating: string;
    reviews_count: number;
    is_available: boolean;
  };
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class FavoritesService {
  private api = inject(ApiService);

  private favoritesSignal = signal<FavoriteMaster[]>([]);
  private favoriteIdsSignal = signal<Set<string>>(new Set());
  private isLoadingSignal = signal<boolean>(false);

  readonly favorites = this.favoritesSignal.asReadonly();
  readonly favoriteIds = this.favoriteIdsSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();

  fetchFavorites(): Observable<FavoriteMaster[]> {
    this.isLoadingSignal.set(true);
    return this.api.getFavorites().pipe(
      tap((response: any) => {
        const favorites = response.results || response || [];
        this.favoritesSignal.set(favorites);
        this.updateFavoriteIds(favorites);
        this.isLoadingSignal.set(false);
      }),
      map((response: any) => response.results || response || []),
      catchError(error => {
        this.isLoadingSignal.set(false);
        console.error('Failed to fetch favorites:', error);
        return of([]);
      })
    );
  }

  isFavorite(masterId: string): boolean {
    return this.favoriteIdsSignal().has(masterId);
  }

  checkFavorite(masterId: string): Observable<boolean> {
    return this.api.checkFavorite(masterId).pipe(
      map((response: { is_favorite: boolean }) => response.is_favorite),
      catchError(() => of(false))
    );
  }

  toggleFavorite(masterId: string): Observable<{ is_favorite: boolean }> {
    return this.api.toggleFavorite(masterId).pipe(
      tap((response: { is_favorite: boolean }) => {
        const currentIds = new Set(this.favoriteIdsSignal());
        if (response.is_favorite) {
          currentIds.add(masterId);
        } else {
          currentIds.delete(masterId);
          // Remove from favorites list
          const currentFavorites = this.favoritesSignal().filter(f => f.master.id !== masterId);
          this.favoritesSignal.set(currentFavorites);
        }
        this.favoriteIdsSignal.set(currentIds);
      })
    );
  }

  addToFavorites(masterId: string): Observable<FavoriteMaster> {
    return this.api.addToFavorites(masterId).pipe(
      tap((favorite: FavoriteMaster) => {
        const currentFavorites = [...this.favoritesSignal(), favorite];
        this.favoritesSignal.set(currentFavorites);
        this.updateFavoriteIds(currentFavorites);
      })
    );
  }

  removeFromFavorites(favoriteId: string, masterId: string): Observable<any> {
    return this.api.removeFromFavorites(favoriteId).pipe(
      tap(() => {
        const currentFavorites = this.favoritesSignal().filter(f => f.id !== favoriteId);
        this.favoritesSignal.set(currentFavorites);

        const currentIds = new Set(this.favoriteIdsSignal());
        currentIds.delete(masterId);
        this.favoriteIdsSignal.set(currentIds);
      })
    );
  }

  private updateFavoriteIds(favorites: FavoriteMaster[]): void {
    const ids = new Set(favorites.map(f => f.master.id));
    this.favoriteIdsSignal.set(ids);
  }

  getFavoritesCount(): number {
    return this.favoritesSignal().length;
  }
}
