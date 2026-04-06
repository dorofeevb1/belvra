import { ApplicationConfig, provideBrowserGlobalErrorListeners, APP_INITIALIZER, inject, isDevMode } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { provideIonicAngular } from '@ionic/angular/standalone';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { AppInitializerService } from './core/services/app-initializer.service';

function initializeApp(): () => Promise<void> {
  const appInitializer = inject(AppInitializerService);
  return () => appInitializer.initialize();
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    provideIonicAngular({
      mode: 'md', // Use Material Design style for consistency
      animated: true
    }),
    {
      provide: APP_INITIALIZER,
      useFactory: initializeApp,
      multi: true
    },
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
};
