import { Injectable, inject } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';
import { SplashScreen } from '@capacitor/splash-screen';
import { PlatformService } from './platform.service';
import { PushNotificationsService } from './push-notifications.service';

const STORAGE_KEYS = [
  'belvra_access_token',
  'belvra_refresh_token',
  'belvra_user'
];

@Injectable({
  providedIn: 'root'
})
export class AppInitializerService {
  private platform = inject(PlatformService);
  private pushService = inject(PushNotificationsService);

  async initialize(): Promise<void> {
    if (Capacitor.isNativePlatform()) {
      // Sync Preferences to localStorage for compatibility
      await this.syncStorageToLocalStorage();

      // Initialize push notifications after user login
      // This will be called from auth service after successful login

      // Hide splash screen
      await SplashScreen.hide();
    }

    // Setup localStorage change listener to sync back to Preferences
    if (Capacitor.isNativePlatform()) {
      this.setupStorageSync();
    }
  }

  private async syncStorageToLocalStorage(): Promise<void> {
    for (const key of STORAGE_KEYS) {
      const result = await Preferences.get({ key });
      if (result.value) {
        localStorage.setItem(key, result.value);
      }
    }
  }

  private setupStorageSync(): void {
    // Override localStorage.setItem to also save to Preferences
    const originalSetItem = localStorage.setItem.bind(localStorage);
    localStorage.setItem = (key: string, value: string) => {
      originalSetItem(key, value);
      if (STORAGE_KEYS.includes(key)) {
        Preferences.set({ key, value }).catch(console.error);
      }
    };

    // Override localStorage.removeItem to also remove from Preferences
    const originalRemoveItem = localStorage.removeItem.bind(localStorage);
    localStorage.removeItem = (key: string) => {
      originalRemoveItem(key);
      if (STORAGE_KEYS.includes(key)) {
        Preferences.remove({ key }).catch(console.error);
      }
    };
  }

  async initializePushNotifications(): Promise<void> {
    if (Capacitor.isNativePlatform()) {
      await this.pushService.initialize();
    }
  }
}
