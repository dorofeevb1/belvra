import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { CookieBannerComponent } from './shared/components/cookie-banner.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CookieBannerComponent],
  template: `<router-outlet /><app-cookie-banner />`
})
export class App {
  // Inject ThemeService to initialize theme on app start
  private themeService = inject(ThemeService);
}
