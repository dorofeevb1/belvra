import { Component, inject, OnInit, signal, computed, effect, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DataService, AIService } from '../../../core/services';
import { Master } from '../../../core/models';
import { FavoriteButtonComponent } from '../../../shared/components/favorite-button/favorite-button.component';

declare const ymaps: any;

@Component({
  selector: 'app-master-search',
  standalone: true,
  imports: [CommonModule, FormsModule, FavoriteButtonComponent],
  templateUrl: './master-search.component.html',
  styleUrl: './master-search.component.scss'
})
export class MasterSearchComponent implements OnInit, OnDestroy {
  private dataService = inject(DataService);
  private aiService = inject(AIService);
  private router = inject(Router);

  private map: any = null;

  isLoading = signal(true);
  isSearching = signal(false);
  searchQuery = '';
  viewMode = signal<'list' | 'map'>('list');
  allMasters = signal<Master[]>([]);
  rankedMasterIds = signal<string[]>([]);
  userLocation = signal<{ lat: number; lng: number } | null>(null);
  geoEnabled = signal(false);
  geoError = signal('');

  filteredMasters = computed(() => {
    const ids = this.rankedMasterIds();
    const masters = this.allMasters();

    if (ids.length === 0) return masters;

    return ids
      .map(id => masters.find(m => m.id === id))
      .filter((m): m is Master => !!m);
  });

  constructor() {
    effect(() => {
      const mode = this.viewMode();
      const masters = this.allMasters();

      if (mode === 'map' && masters.length > 0) {
        setTimeout(() => this.initMap(), 50);
      }
    });
  }

  ngOnInit(): void {
    this.detectLocation();
    this.loadMasters();
  }

  ngOnDestroy(): void {
    this.destroyMap();
  }

  /** Detect user's geolocation */
  detectLocation(): void {
    if (!navigator.geolocation) {
      this.geoError.set('Геолокация не поддерживается');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.userLocation.set({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude
        });
        this.geoEnabled.set(true);
      },
      () => {
        this.geoError.set('Нет доступа к геолокации');
      },
      { timeout: 5000, maximumAge: 300000 }
    );
  }

  private loadMasters(): void {
    this.dataService.getAllMasters().subscribe(data => {
      this.allMasters.set(data);
      this.rankedMasterIds.set(data.map(m => m.id));
      this.isLoading.set(false);
    });
  }

  /** Main search — text + geo, then AI ranking as bonus */
  async search(): Promise<void> {
    const query = this.searchQuery.trim();

    if (!query) {
      // Reset to all masters
      this.loadMasters();
      return;
    }

    this.isSearching.set(true);

    try {
      // Build search params for backend
      const params: any = {};

      // Text search
      if (query) {
        params.q = query;
      }

      // Geo search: if user typed "рядом" / "поблизости" or geo is enabled
      const geoKeywords = ['рядом', 'поблизости', 'близко', 'около', 'недалеко'];
      const wantsGeo = geoKeywords.some(kw => query.toLowerCase().includes(kw));

      if (wantsGeo || this.geoEnabled()) {
        const loc = this.userLocation();
        if (loc) {
          params.lat = loc.lat;
          params.lng = loc.lng;
          params.radius_km = wantsGeo ? 5 : 15;
        }
      }

      // Fetch from backend with filters
      const masters = await this.dataService.searchMasters(params).toPromise() || [];
      this.allMasters.set(masters);

      // Try AI ranking as bonus (non-blocking)
      if (masters.length > 1) {
        try {
          const rankedIds = await this.aiService.searchMasters(query, masters);
          if (rankedIds.length > 0) {
            this.rankedMasterIds.set(rankedIds);
          } else {
            this.rankedMasterIds.set(masters.map(m => m.id));
          }
        } catch {
          // AI failed — just use backend order
          this.rankedMasterIds.set(masters.map(m => m.id));
        }
      } else {
        this.rankedMasterIds.set(masters.map(m => m.id));
      }
    } catch (error) {
      console.error('Search error:', error);
    }

    this.isSearching.set(false);
  }

  /** Search nearby masters */
  searchNearby(): void {
    const loc = this.userLocation();
    if (!loc) {
      this.detectLocation();
      return;
    }

    this.searchQuery = 'Мастера рядом';
    this.search();
  }

  openMasterProfile(masterId: string): void {
    this.router.navigate(['/client/master', masterId]);
  }

  private destroyMap(): void {
    if (this.map) {
      this.map.destroy();
      this.map = null;
    }
  }

  private initMap(): void {
    if (typeof ymaps === 'undefined') {
      console.warn('Yandex Maps API not loaded');
      return;
    }

    const container = document.getElementById('search-map');
    if (!container) return;

    this.destroyMap();

    ymaps.ready(() => {
      const container = document.getElementById('search-map');
      if (container) {
        container.innerHTML = '';
      }

      const mastersWithCoords = this.filteredMasters().filter(m => m.coordinates);
      const loc = this.userLocation();
      let center = loc ? [loc.lat, loc.lng] : [55.76, 37.64];

      if (!loc && mastersWithCoords.length > 0) {
        const avgLat = mastersWithCoords.reduce((sum, m) => sum + m.coordinates!.lat, 0) / mastersWithCoords.length;
        const avgLng = mastersWithCoords.reduce((sum, m) => sum + m.coordinates!.lng, 0) / mastersWithCoords.length;
        center = [avgLat, avgLng];
      }

      this.map = new ymaps.Map('search-map', {
        center,
        zoom: 11,
        controls: ['zoomControl', 'geolocationControl']
      });

      mastersWithCoords.forEach(master => {
        const placemark = new ymaps.Placemark(
          [master.coordinates!.lat, master.coordinates!.lng],
          {
            balloonContentHeader: `<strong>${master.name}</strong>`,
            balloonContentBody: `
              <div style="font-size: 13px; line-height: 1.4;">
                <div style="color: #666;">${master.specialization}</div>
                <div style="margin-top: 4px;">
                  <span style="color: #f59e0b;">★</span> ${master.rating} (${master.reviewsCount} отзывов)
                </div>
                <div style="margin-top: 4px; color: #888;">${master.address}</div>
              </div>
            `,
            balloonContentFooter: `<a href="/client/master/${master.id}" style="color: #ec4899;">Открыть профиль</a>`,
            hintContent: master.name
          },
          {
            preset: 'islands#pinkDotIcon',
            balloonPanelMaxMapArea: 0
          }
        );

        this.map.geoObjects.add(placemark);
      });

      if (mastersWithCoords.length > 1) {
        this.map.setBounds(this.map.geoObjects.getBounds(), {
          checkZoomRange: true,
          zoomMargin: 50
        });
      }
    });
  }
}
