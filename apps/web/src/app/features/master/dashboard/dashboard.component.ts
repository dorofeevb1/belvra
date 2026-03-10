import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService, DataService, DateService } from '../../../core/services';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { BarChartComponent } from './charts/bar-chart.component';
import { DonutChartComponent } from './charts/donut-chart.component';
import { ProBadgeComponent } from '../../../shared/components/pro-badge.component';

declare const ymaps: any;

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    CurrencyRubPipe,
    BarChartComponent,
    DonutChartComponent,
    ProBadgeComponent
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit, OnDestroy {
  authService = inject(AuthService);
  subscriptionService = inject(SubscriptionService);
  private dataService = inject(DataService);
  private dateService = inject(DateService);
  router = inject(Router);

  private map: any = null;
  isLoading = signal(true);
  mapLoaded = signal(false);
  mapError = signal<string | null>(null);
  stats = signal({ totalProfit: 0, upcomingAppointments: 0, newClients: 0, averageRating: 0 });
  weeklyTrend = signal<{ date: string; count: number }[]>([]);
  servicesPopularity = signal<{ serviceName: string; count: number }[]>([]);
  activityFeed = signal<{
    id: string;
    type: string;
    title: string;
    description: string;
    time: Date;
    iconType: 'appointment' | 'review' | 'message';
    data?: unknown;
  }[]>([]);

  get greeting(): string {
    return this.dateService.getGreeting();
  }

  getMasterFirstName(): string {
    const name = this.authService.masterData()?.name;
    return name?.split(' ')[0] ?? 'Мастер';
  }

  getRelativeTime(date: Date): string {
    return this.dateService.getRelativeTime(date);
  }

  ngOnInit(): void {
    // Load subscription usage stats
    this.subscriptionService.loadUsageStats().subscribe();

    // Refresh profile to get latest data (including coordinates)
    this.authService.refreshProfile().subscribe(() => {
      this.loadData();
    });
  }

  ngOnDestroy(): void {
    if (this.map) {
      this.map.destroy();
      this.map = null;
    }
  }

  private loadData(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    forkJoin({
      stats: this.dataService.getDashboardStats(masterId),
      weeklyTrend: this.dataService.getWeeklyAppointmentsTrend(masterId),
      servicesPopularity: this.dataService.getServicesPopularity(masterId),
      appointments: this.dataService.getAppointments(masterId),
      reviews: this.dataService.getReviews(masterId),
      chats: this.dataService.getChats(masterId),
    }).subscribe({
      next: ({ stats, weeklyTrend, servicesPopularity, appointments, reviews, chats }) => {
        this.stats.set(stats);
        this.weeklyTrend.set(weeklyTrend);
        this.servicesPopularity.set(servicesPopularity);
        this.buildActivityFeed(appointments, reviews, chats);
        this.isLoading.set(false);
        this.initMap();
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }

  private buildActivityFeed(appointments: any[], reviews: any[], chats: any[]): void {
    type Activity = typeof this.activityFeed extends () => infer T ? T : never;
    const activities: Activity[number][] = [];

    appointments.filter(a => a.status === 'pending').forEach(apt => {
      activities.push({
        id: apt.id,
        type: 'appointment',
        title: 'Новая заявка на запись',
        description: `${apt.clientName} - ${apt.serviceName}`,
        time: apt.createdAt,
        iconType: 'appointment',
        data: apt
      });
    });

    reviews.slice(0, 3).forEach(review => {
      activities.push({
        id: review.id,
        type: 'review',
        title: 'Новый отзыв',
        description: `${review.clientName} - ${'★'.repeat(review.rating)}`,
        time: review.createdAt,
        iconType: 'review',
        data: review
      });
    });

    chats.filter(c => c.unreadCount > 0).forEach(chat => {
      activities.push({
        id: chat.id,
        type: 'message',
        title: 'Новое сообщение',
        description: `${chat.clientName}: ${chat.lastMessage}`,
        time: chat.lastMessageTime || new Date(),
        iconType: 'message',
        data: chat
      });
    });

    activities.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
    this.activityFeed.set(activities.slice(0, 10));
  }

  private initMap(retryCount = 0): void {
    const master = this.authService.masterData();

    if (!master?.coordinates) {
      console.warn('No coordinates available for map. User may need to re-login.');
      this.mapError.set('Координаты не указаны. Перезайдите в аккаунт для обновления данных.');
      return;
    }

    // Wait for ymaps to be available (retry up to 20 times = 10 seconds)
    if (typeof ymaps === 'undefined') {
      if (retryCount < 20) {
        setTimeout(() => this.initMap(retryCount + 1), 500);
      } else {
        console.error('Yandex Maps API failed to load');
        this.mapError.set('Не удалось загрузить карту. Проверьте подключение к интернету.');
      }
      return;
    }

    const container = document.getElementById('yandex-map');
    if (!container) return;

    ymaps.ready(() => {
      try {
        this.map = new ymaps.Map('yandex-map', {
          center: [master.coordinates!.lat, master.coordinates!.lng],
          zoom: 15,
          controls: ['zoomControl']
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
        this.mapLoaded.set(true);
      } catch (e) {
        console.error('Error initializing map:', e);
        this.mapError.set('Ошибка инициализации карты');
      }
    });
  }

  onActivityClick(activity: { type: string; data?: unknown }): void {
    switch (activity.type) {
      case 'appointment':
        this.router.navigate(['/master/appointments']);
        break;
      case 'message':
        this.router.navigate(['/master/chat']);
        break;
      case 'review':
        break;
    }
  }

  // Subscription usage helpers
  getUsagePercent(used: number, limit: number | null): number {
    if (!limit) return 0;
    return Math.min(100, (used / limit) * 100);
  }

  getUsageClass(percent: number): string {
    if (percent >= 100) return 'usage-critical';
    if (percent >= 80) return 'usage-warning';
    return 'usage-normal';
  }
}
