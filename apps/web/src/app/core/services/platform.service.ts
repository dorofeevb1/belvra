import { Injectable, signal, computed } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { App, URLOpenListenerEvent } from '@capacitor/app';
import { StatusBar, Style } from '@capacitor/status-bar';
import { SplashScreen } from '@capacitor/splash-screen';
import { Keyboard } from '@capacitor/keyboard';
import { Network } from '@capacitor/network';
import { Router } from '@angular/router';

export type Platform = 'web' | 'ios' | 'android';

@Injectable({
  providedIn: 'root'
})
export class PlatformService {
  private readonly _platform = signal<Platform>(this.detectPlatform());
  private readonly _isOnline = signal<boolean>(true);
  private readonly _keyboardHeight = signal<number>(0);

  readonly platform = this._platform.asReadonly();
  readonly isOnline = this._isOnline.asReadonly();
  readonly keyboardHeight = this._keyboardHeight.asReadonly();

  readonly isNative = computed(() => this._platform() !== 'web');
  readonly isIOS = computed(() => this._platform() === 'ios');
  readonly isAndroid = computed(() => this._platform() === 'android');
  readonly isWeb = computed(() => this._platform() === 'web');

  constructor(private router: Router) {
    this.initializePlatform();
  }

  private detectPlatform(): Platform {
    const platform = Capacitor.getPlatform();
    if (platform === 'ios') return 'ios';
    if (platform === 'android') return 'android';
    return 'web';
  }

  private async initializePlatform(): Promise<void> {
    if (!this.isNative()) return;

    try {
      // Setup status bar
      await StatusBar.setStyle({ style: Style.Light });
      await StatusBar.setBackgroundColor({ color: '#ec4899' });

      // Hide splash screen after app is ready
      await SplashScreen.hide();

      // Setup deep links
      this.setupDeepLinks();

      // Setup network listener
      this.setupNetworkListener();

      // Setup keyboard listeners (for iOS/Android)
      this.setupKeyboardListeners();

      // Setup back button handler (Android)
      if (this.isAndroid()) {
        this.setupBackButton();
      }
    } catch (error) {
      console.error('Platform initialization error:', error);
    }
  }

  private setupDeepLinks(): void {
    App.addListener('appUrlOpen', (event: URLOpenListenerEvent) => {
      const url = new URL(event.url);
      const path = url.pathname;

      // Handle deep links
      // beautybook://master/123 -> /master/123
      // https://beautybook.app/booking/456 -> /booking/456
      if (path) {
        this.router.navigateByUrl(path);
      }
    });
  }

  private async setupNetworkListener(): Promise<void> {
    const status = await Network.getStatus();
    this._isOnline.set(status.connected);

    Network.addListener('networkStatusChange', (status) => {
      this._isOnline.set(status.connected);
    });
  }

  private setupKeyboardListeners(): void {
    Keyboard.addListener('keyboardWillShow', (info) => {
      this._keyboardHeight.set(info.keyboardHeight);
    });

    Keyboard.addListener('keyboardWillHide', () => {
      this._keyboardHeight.set(0);
    });
  }

  private setupBackButton(): void {
    App.addListener('backButton', ({ canGoBack }) => {
      if (canGoBack) {
        window.history.back();
      } else {
        App.exitApp();
      }
    });
  }

  async hideKeyboard(): Promise<void> {
    if (this.isNative()) {
      await Keyboard.hide();
    }
  }

  async showKeyboard(): Promise<void> {
    if (this.isNative()) {
      await Keyboard.show();
    }
  }
}
