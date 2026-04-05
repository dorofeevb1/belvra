import { Component, inject, OnInit, OnDestroy, signal, input, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DataService } from '../../../core/services';
import { Master, BeautyService, PortfolioItem, Review } from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';
import { FavoriteButtonComponent } from '../../../shared/components/favorite-button/favorite-button.component';

declare const ymaps: any;

@Component({
  selector: 'app-master-profile',
  standalone: true,
  imports: [CommonModule, CurrencyRubPipe, DateFormatPipe, FavoriteButtonComponent],
  templateUrl: './master-profile.component.html',
  styleUrl: './master-profile.component.scss'
})
export class MasterProfileComponent implements OnInit, OnDestroy {
  id = input<string>('');

  private dataService = inject(DataService);
  private router = inject(Router);

  private map: any = null;
  isLoading = signal(true);
  master = signal<Master | null>(null);
  services = signal<BeautyService[]>([]);
  portfolio = signal<PortfolioItem[]>([]);
  reviews = signal<Review[]>([]);
  activeTab = signal<'services' | 'portfolio' | 'reviews' | 'location'>('services');

  constructor() {
    // Initialize map when location tab is active
    effect(() => {
      const tab = this.activeTab();
      const currentMaster = this.master();

      if (tab === 'location' && currentMaster?.coordinates) {
        setTimeout(() => this.initMap(currentMaster), 50);
      }
    });
  }

  ngOnInit(): void {
    this.loadData();
  }

  ngOnDestroy(): void {
    if (this.map) {
      this.map.destroy();
      this.map = null;
    }
  }

  private loadData(): void {
    const masterId = this.id();
    if (!masterId) return;

    this.dataService.getMasterById(masterId).subscribe(master => {
      if (master) {
        this.master.set(master);
        this.loadAdditionalData(masterId);
      }
      this.isLoading.set(false);
    });
  }

  private loadAdditionalData(masterId: string): void {
    this.dataService.getServices(masterId).subscribe(data => this.services.set(data));
    this.dataService.getPortfolio(masterId).subscribe(data => this.portfolio.set(data));
    this.dataService.getReviews(masterId).subscribe(data => this.reviews.set(data));
  }

  goBack(): void {
    this.router.navigate(['/client']);
  }

  startBooking(): void {
    if (this.services().length > 0) {
      this.bookService(this.services()[0]);
    }
  }

  bookService(service: BeautyService): void {
    this.router.navigate(['/client/booking', this.id()], {
      queryParams: { serviceId: service.id }
    });
  }

  startChat(): void {
    const masterId = this.id();
    if (!masterId) return;

    // Navigate to client chat with this master
    this.router.navigate(['/client/chat'], {
      queryParams: { masterId }
    });
  }

  private initMap(master: Master): void {
    if (typeof ymaps === 'undefined' || !master.coordinates) {
      return;
    }

    const container = document.getElementById('master-location-map');
    if (!container) return;

    // Destroy existing map if any
    if (this.map) {
      this.map.destroy();
      this.map = null;
    }

    ymaps.ready(() => {
      // Clear container before initializing
      const container = document.getElementById('master-location-map');
      if (container) {
        container.innerHTML = '';
      }

      this.map = new ymaps.Map('master-location-map', {
        center: [master.coordinates!.lat, master.coordinates!.lng],
        zoom: 15,
        controls: ['zoomControl', 'geolocationControl']
      });

      const placemark = new ymaps.Placemark(
        [master.coordinates!.lat, master.coordinates!.lng],
        {
          balloonContentHeader: `<strong>${master.name}</strong>`,
          balloonContentBody: `
            <div style="font-size: 13px; line-height: 1.4;">
              <div style="color: #666;">${master.specialization}</div>
              <div style="margin-top: 8px; color: #888;">${master.address}</div>
            </div>
          `,
          hintContent: master.name
        },
        {
          preset: 'islands#pinkDotIcon',
          balloonPanelMaxMapArea: 0
        }
      );

      this.map.geoObjects.add(placemark);
    });
  }
}
