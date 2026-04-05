import { Component, inject, signal, OnInit, OnDestroy, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { InAppNotificationService, InAppNotification } from '../../../core/services/in-app-notification.service';

@Component({
  selector: 'app-notification-bell',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="notification-container">
      <button class="bell-button" (click)="toggleDropdown()" [class.has-unread]="notificationService.unreadCount() > 0">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        @if (notificationService.unreadCount() > 0) {
          <span class="badge">{{ notificationService.unreadCount() > 99 ? '99+' : notificationService.unreadCount() }}</span>
        }
      </button>

      @if (isOpen()) {
        <div class="dropdown">
          <div class="dropdown-header">
            <h3>Уведомления</h3>
            @if (notificationService.unreadCount() > 0) {
              <button class="mark-all-btn" (click)="markAllAsRead()">Прочитать все</button>
            }
          </div>

          <div class="dropdown-content">
            @if (notificationService.isLoading()) {
              <div class="loading">
                <div class="spinner"></div>
                <span>Загрузка...</span>
              </div>
            } @else if (notificationService.notifications().length === 0) {
              <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <p>Нет уведомлений</p>
              </div>
            } @else {
              @for (notification of notificationService.notifications(); track notification.id) {
                <div
                  class="notification-item"
                  [class.unread]="!notification.is_read"
                  (click)="onNotificationClick(notification)"
                >
                  <div class="notification-icon" [style.backgroundColor]="notificationService.getNotificationColor(notification.notification_type) + '20'" [style.color]="notificationService.getNotificationColor(notification.notification_type)">
                    @switch (notification.notification_type) {
                      @case ('appointment_new') {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                          <line x1="16" y1="2" x2="16" y2="6"/>
                          <line x1="8" y1="2" x2="8" y2="6"/>
                          <line x1="3" y1="10" x2="21" y2="10"/>
                          <line x1="12" y1="14" x2="12" y2="18"/>
                          <line x1="10" y1="16" x2="14" y2="16"/>
                        </svg>
                      }
                      @case ('appointment_confirmed') {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                          <line x1="16" y1="2" x2="16" y2="6"/>
                          <line x1="8" y1="2" x2="8" y2="6"/>
                          <line x1="3" y1="10" x2="21" y2="10"/>
                          <polyline points="9 16 12 18 16 14"/>
                        </svg>
                      }
                      @case ('appointment_cancelled') {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                          <line x1="16" y1="2" x2="16" y2="6"/>
                          <line x1="8" y1="2" x2="8" y2="6"/>
                          <line x1="3" y1="10" x2="21" y2="10"/>
                          <line x1="10" y1="14" x2="14" y2="18"/>
                          <line x1="14" y1="14" x2="10" y2="18"/>
                        </svg>
                      }
                      @case ('review_new') {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1">
                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                        </svg>
                      }
                      @case ('payment_received') {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
                          <line x1="1" y1="10" x2="23" y2="10"/>
                        </svg>
                      }
                      @case ('chat_message') {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                      }
                      @default {
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                        </svg>
                      }
                    }
                  </div>
                  <div class="notification-content">
                    <h4>{{ notification.title }}</h4>
                    <p>{{ notification.message }}</p>
                    <span class="time">{{ formatTime(notification.created_at) }}</span>
                  </div>
                  <button class="delete-btn" (click)="deleteNotification($event, notification.id)" title="Удалить">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                </div>
              }
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .notification-container {
      position: relative;
    }

    .bell-button {
      position: relative;
      background: none;
      border: none;
      padding: 8px;
      cursor: pointer;
      color: #6b7280;
      border-radius: 8px;
      transition: all 0.2s;
    }

    .bell-button:hover {
      background: #f3f4f6;
      color: #374151;
    }

    .bell-button.has-unread {
      color: #667eea;
    }

    .badge {
      position: absolute;
      top: 2px;
      right: 2px;
      background: #ef4444;
      color: white;
      font-size: 10px;
      font-weight: 600;
      padding: 2px 5px;
      border-radius: 10px;
      min-width: 16px;
      text-align: center;
    }

    .dropdown {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      width: 380px;
      max-width: calc(100vw - 2rem);
      background: white;
      border-radius: 12px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
      z-index: 1000;
      overflow: hidden;
    }

    @media (max-width: 767px) {
      .dropdown {
        position: fixed;
        top: 60px;
        right: 0.5rem;
        left: 0.5rem;
        width: auto;
        max-width: none;
        max-height: calc(100vh - 80px);
      }
    }

    .dropdown-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid #e5e7eb;
    }

    .dropdown-header h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
      color: #111827;
    }

    .mark-all-btn {
      background: none;
      border: none;
      color: #667eea;
      font-size: 0.875rem;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
    }

    .mark-all-btn:hover {
      background: #f3f4f6;
    }

    .dropdown-content {
      max-height: 400px;
      overflow-y: auto;
    }

    .loading, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
      color: #9ca3af;
    }

    .spinner {
      width: 24px;
      height: 24px;
      border: 2px solid #e5e7eb;
      border-top-color: #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 8px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .empty-state svg {
      margin-bottom: 12px;
      opacity: 0.5;
    }

    .empty-state p {
      margin: 0;
      font-size: 0.875rem;
    }

    .notification-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px 16px;
      cursor: pointer;
      transition: background 0.2s;
      border-bottom: 1px solid #f3f4f6;
      position: relative;
    }

    .notification-item:last-child {
      border-bottom: none;
    }

    .notification-item:hover {
      background: #f9fafb;
    }

    .notification-item.unread {
      background: #f0f4ff;
    }

    .notification-item.unread:hover {
      background: #e8edff;
    }

    .notification-icon {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .notification-content {
      flex: 1;
      min-width: 0;
    }

    .notification-content h4 {
      margin: 0 0 4px;
      font-size: 0.875rem;
      font-weight: 600;
      color: #111827;
    }

    .notification-content p {
      margin: 0 0 4px;
      font-size: 0.8125rem;
      color: #6b7280;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .notification-content .time {
      font-size: 0.75rem;
      color: #9ca3af;
    }

    .delete-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      background: none;
      border: none;
      padding: 4px;
      cursor: pointer;
      color: #9ca3af;
      border-radius: 4px;
      opacity: 0;
      transition: all 0.2s;
    }

    .notification-item:hover .delete-btn {
      opacity: 1;
    }

    .delete-btn:hover {
      background: #fee2e2;
      color: #ef4444;
    }
  `]
})
export class NotificationBellComponent implements OnInit, OnDestroy {
  private elementRef = inject(ElementRef);
  private router = inject(Router);

  notificationService = inject(InAppNotificationService);
  isOpen = signal(false);

  ngOnInit(): void {
    this.notificationService.startPolling();
  }

  ngOnDestroy(): void {
    this.notificationService.stopPolling();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen.set(false);
    }
  }

  toggleDropdown(): void {
    const wasOpen = this.isOpen();
    this.isOpen.set(!wasOpen);

    if (!wasOpen) {
      this.notificationService.fetchNotifications().subscribe();
    }
  }

  onNotificationClick(notification: InAppNotification): void {
    if (!notification.is_read) {
      this.notificationService.markAsRead(notification.id).subscribe();
    }

    if (notification.link) {
      this.router.navigateByUrl(notification.link);
      this.isOpen.set(false);
    }
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead().subscribe();
  }

  deleteNotification(event: Event, id: string): void {
    event.stopPropagation();
    this.notificationService.deleteNotification(id).subscribe();
  }

  formatTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Только что';
    if (minutes < 60) return `${minutes} мин. назад`;
    if (hours < 24) return `${hours} ч. назад`;
    if (days < 7) return `${days} дн. назад`;

    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short'
    });
  }
}
