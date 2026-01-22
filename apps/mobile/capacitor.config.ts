import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.beautybook.app',
  appName: 'BeautyBook',
  webDir: 'dist/mobile/browser',

  // Server configuration for development
  server: {
    // For development, use your local backend
    // url: 'http://localhost:4200',
    cleartext: true,
    androidScheme: 'https'
  },

  // iOS specific configuration
  ios: {
    contentInset: 'automatic',
    preferredContentMode: 'mobile',
    scheme: 'beautybook'
  },

  // Android specific configuration
  android: {
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true
  },

  // Plugin configurations
  plugins: {
    // Push Notifications
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert']
    },

    // Splash Screen
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#ec4899',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
      splashFullScreen: true,
      splashImmersive: true
    },

    // Status Bar - defaults for light theme, updated dynamically by ThemeService
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#f9f7f5',
      overlaysWebView: false
    },

    // Keyboard
    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true
    },

    // Camera for portfolio photos
    Camera: {
      quality: 90,
      allowEditing: true,
      resultType: 'uri'
    },

    // App deep links
    App: {
      links: [
        { scheme: 'beautybook' },
        { scheme: 'https', host: 'beautybook.app' },
        { scheme: 'https', host: 'www.beautybook.app' }
      ]
    }
  }
};

export default config;
