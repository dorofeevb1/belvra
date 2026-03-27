import { Injectable, signal, inject } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import {
  PushNotifications,
  PushNotificationSchema,
  ActionPerformed,
  Token
} from '@capacitor/push-notifications';
import { Router } from '@angular/router';
import { ApiService } from './api.service';

export interface PushNotificationData {
  type: string;
  appointmentId?: string;
  chatId?: string;
  masterId?: string;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root'
})
export class PushNotificationsService {
  private readonly _token = signal<string | null>(null);
  private readonly _hasPermission = signal<boolean>(false);

  readonly token = this._token.asReadonly();
  readonly hasPermission = this._hasPermission.asReadonly();

  private router = inject(Router);
  private api = inject(ApiService);

  async initialize(): Promise<void> {
    if (!Capacitor.isNativePlatform()) {
      console.log('Push notifications not available on web');
      return;
    }

    try {
      // Request permission
      const permStatus = await PushNotifications.checkPermissions();

      if (permStatus.receive === 'prompt') {
        const result = await PushNotifications.requestPermissions();
        this._hasPermission.set(result.receive === 'granted');
      } else {
        this._hasPermission.set(permStatus.receive === 'granted');
      }

      if (!this._hasPermission()) {
        console.log('Push notification permission not granted');
        return;
      }

      // Register for push notifications
      await PushNotifications.register();

      // Setup listeners
      this.setupListeners();
    } catch (error) {
      console.error('Push notification initialization error:', error);
    }
  }

  private setupListeners(): void {
    // On registration success
    PushNotifications.addListener('registration', async (token: Token) => {
      console.log('Push registration success, token: ', token.value);
      this._token.set(token.value);

      // Send token to backend
      await this.registerTokenWithBackend(token.value);
    });

    // On registration error
    PushNotifications.addListener('registrationError', (error) => {
      console.error('Push registration error:', error);
    });

    // On push notification received (app is in foreground)
    PushNotifications.addListener('pushNotificationReceived', (notification: PushNotificationSchema) => {
      console.log('Push notification received:', notification);
      // Handle foreground notification - show in-app notification
      this.handleForegroundNotification(notification);
    });

    // On push notification action performed (user tapped notification)
    PushNotifications.addListener('pushNotificationActionPerformed', (action: ActionPerformed) => {
      console.log('Push notification action performed:', action);
      const data = action.notification.data as PushNotificationData;
      this.handleNotificationTap(data);
    });
  }

  private async registerTokenWithBackend(token: string): Promise<void> {
    try {
      const platform = Capacitor.getPlatform();
      await this.api.post('/notifications/device/', {
        token,
        platform,
        active: true
      }).toPromise();
    } catch (error) {
      console.error('Failed to register push token with backend:', error);
    }
  }

  private handleForegroundNotification(notification: PushNotificationSchema): void {
    // You can show an in-app notification toast here
    // For now, we'll just log it
    console.log('Foreground notification:', notification.title, notification.body);
  }

  private handleNotificationTap(data: PushNotificationData): void {
    // Navigate based on notification type
    switch (data.type) {
      case 'appointment_confirmed':
      case 'appointment_cancelled':
      case 'appointment_reminder':
        if (data.appointmentId) {
          this.router.navigate(['/appointments', data.appointmentId]);
        }
        break;

      case 'new_message':
        if (data.chatId) {
          this.router.navigate(['/chat', data.chatId]);
        }
        break;

      case 'new_review':
        this.router.navigate(['/master/reviews']);
        break;

      case 'payment_received':
        this.router.navigate(['/master/finances']);
        break;

      default:
        this.router.navigate(['/']);
    }
  }

  async unregister(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    try {
      // Unregister from backend
      if (this._token()) {
        await this.api.delete(`/notifications/device/${this._token()}/`).toPromise();
      }

      // Remove all listeners
      await PushNotifications.removeAllListeners();

      this._token.set(null);
    } catch (error) {
      console.error('Push notification unregister error:', error);
    }
  }
}
