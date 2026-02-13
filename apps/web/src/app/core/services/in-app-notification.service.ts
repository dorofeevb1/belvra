import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap, interval, switchMap, of, catchError } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

export interface InAppNotification {
  id: string;
  notification_type: string;
  notification_type_display: string;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class InAppNotificationService {
  private api = inject(ApiService);
  private auth = inject(AuthService);

  private notificationsSignal = signal<InAppNotification[]>([]);
  private unreadCountSignal = signal<number>(0);
  private isLoadingSignal = signal<boolean>(false);

  readonly notifications = this.notificationsSignal.asReadonly();
  readonly unreadCount = this.unreadCountSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();

  private pollingSubscription: any = null;

  startPolling(): void {
    if (this.pollingSubscription) return;

    // Опрос каждые 10 секунд для более быстрого обновления уведомлений
    this.pollingSubscription = interval(10000).pipe(
      switchMap(() => {
        if (this.auth.isAuthenticated()) {
          return this.fetchUnreadCount();
        }
        return of(null);
      }),
      catchError(() => of(null))
    ).subscribe();

    // Initial fetch
    if (this.auth.isAuthenticated()) {
      this.fetchUnreadCount().subscribe();
    }
  }

  stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
      this.pollingSubscription = null;
    }
  }

  fetchNotifications(): Observable<InAppNotification[]> {
    this.isLoadingSignal.set(true);
    return this.api.getNotifications().pipe(
      tap((response: any) => {
        const notifications = response.results || response || [];
        this.notificationsSignal.set(notifications);
        this.updateUnreadCount(notifications);
        this.isLoadingSignal.set(false);
      }),
      catchError(error => {
        this.isLoadingSignal.set(false);
        console.error('Failed to fetch notifications:', error);
        return of([]);
      })
    );
  }

  fetchUnreadCount(): Observable<{ count: number }> {
    return this.api.getUnreadNotificationsCount().pipe(
      tap((response: { count: number }) => {
        this.unreadCountSignal.set(response.count);
      }),
      catchError(() => {
        return of({ count: 0 });
      })
    );
  }

  markAsRead(notificationId: string): Observable<InAppNotification> {
    return this.api.markNotificationRead(notificationId).pipe(
      tap((updatedNotification: InAppNotification) => {
        const notifications = this.notificationsSignal().map(n =>
          n.id === notificationId ? { ...n, is_read: true } : n
        );
        this.notificationsSignal.set(notifications);
        this.updateUnreadCount(notifications);
      })
    );
  }

  markAllAsRead(): Observable<any> {
    return this.api.markNotificationsRead().pipe(
      tap(() => {
        const notifications = this.notificationsSignal().map(n => ({ ...n, is_read: true }));
        this.notificationsSignal.set(notifications);
        this.unreadCountSignal.set(0);
      })
    );
  }

  deleteNotification(notificationId: string): Observable<any> {
    return this.api.deleteNotification(notificationId).pipe(
      tap(() => {
        const notifications = this.notificationsSignal().filter(n => n.id !== notificationId);
        this.notificationsSignal.set(notifications);
        this.updateUnreadCount(notifications);
      })
    );
  }

  clearReadNotifications(): Observable<any> {
    return this.api.clearReadNotifications().pipe(
      tap(() => {
        const notifications = this.notificationsSignal().filter(n => !n.is_read);
        this.notificationsSignal.set(notifications);
      })
    );
  }

  private updateUnreadCount(notifications: InAppNotification[]): void {
    const count = notifications.filter(n => !n.is_read).length;
    this.unreadCountSignal.set(count);
  }

  getNotificationIcon(type: string): string {
    const icons: Record<string, string> = {
      'appointment_new': 'calendar-plus',
      'appointment_confirmed': 'calendar-check',
      'appointment_cancelled': 'calendar-x',
      'appointment_reminder': 'bell',
      'appointment_completed': 'check-circle',
      'review_new': 'star',
      'payment_received': 'credit-card',
      'payment_refunded': 'rotate-ccw',
      'system': 'info'
    };
    return icons[type] || 'bell';
  }

  getNotificationColor(type: string): string {
    const colors: Record<string, string> = {
      'appointment_new': '#3b82f6',
      'appointment_confirmed': '#22c55e',
      'appointment_cancelled': '#ef4444',
      'appointment_reminder': '#f59e0b',
      'appointment_completed': '#10b981',
      'review_new': '#eab308',
      'payment_received': '#22c55e',
      'payment_refunded': '#6366f1',
      'chat_message': '#ec4899',
      'system': '#6b7280'
    };
    return colors[type] || '#6b7280';
  }
}
