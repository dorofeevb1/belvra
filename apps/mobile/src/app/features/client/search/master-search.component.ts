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

  filteredMasters = computed(() => {
    const ids = this.rankedMasterIds();
    const masters = this.allMasters();

    if (ids.length === 0) return masters;

    return ids
      .map(id => masters.find(m => m.id === id))
      .filter((m): m is Master => !!m);
  });

  constructor() {
    // Watch for view mode changes to initialize map
    effect(() => {
      const mode = this.viewMode();
      const masters = this.allMasters();

      if (mode === 'map' && masters.length > 0) {
        // Small delay to ensure DOM is ready
        setTimeout(() => this.initMap(), 50);
      }
    });
  }

  ngOnInit(): void {
    this.loadMasters();
  }

  ngOnDestroy(): void {
    this.destroyMap();
  }

  private loadMasters(): void {
    this.dataService.getAllMasters().subscribe(data => {
      this.allMasters.set(data);
      this.rankedMasterIds.set(data.map(m => m.id));
      this.isLoading.set(false);
    });
  }

  async search(): Promise<void> {
    if (!this.searchQuery.trim()) {
      this.rankedMasterIds.set(this.allMasters().map(m => m.id));
      return;
    }

    this.isSearching.set(true);

    try {
      const rankedIds = await this.aiService.searchMasters(
        this.searchQuery,
        this.allMasters()
      );
      this.rankedMasterIds.set(rankedIds);
    } catch (error) {
      console.error('Search error:', error);
    }

    this.isSearching.set(false);
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

    // Destroy existing map if any
    this.destroyMap();

    ymaps.ready(() => {
      // Clear container before initializing
      const container = document.getElementById('search-map');
      if (container) {
        container.innerHTML = '';
      }

      // Calculate center based on masters with coordinates
      const mastersWithCoords = this.filteredMasters().filter(m => m.coordinates);
      let center = [55.76, 37.64]; // Default: Moscow

      if (mastersWithCoords.length > 0) {
        const avgLat = mastersWithCoords.reduce((sum, m) => sum + m.coordinates!.lat, 0) / mastersWithCoords.length;
        const avgLng = mastersWithCoords.reduce((sum, m) => sum + m.coordinates!.lng, 0) / mastersWithCoords.length;
        center = [avgLat, avgLng];
      }

      this.map = new ymaps.Map('search-map', {
        center,
        zoom: 11,
        controls: ['zoomControl', 'geolocationControl']
      });

      // Add placemarks for each master
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

        placemark.events.add('click', () => {
          // Open balloon on click
        });

        this.map.geoObjects.add(placemark);
      });

      // Fit bounds to show all markers
      if (mastersWithCoords.length > 1) {
        this.map.setBounds(this.map.geoObjects.getBounds(), {
          checkZoomRange: true,
          zoomMargin: 50
        });
      }
    });
  }
}
