import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { CookieBannerComponent } from './shared/components/cookie-banner.component';
import { SupportComponent } from './shared/components/support/support.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CookieBannerComponent, SupportComponent],
  template: `<router-outlet /><app-cookie-banner /><app-support />`
})
export class App {
  // Inject ThemeService to initialize theme on app start
  private themeService = inject(ThemeService);
}
