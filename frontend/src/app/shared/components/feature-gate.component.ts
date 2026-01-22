import { Component, input, output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { SubscriptionService } from '../../core/services/subscription.service';

@Component({
  selector: 'app-feature-gate',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (isLocked()) {
      <div class="relative">
        <!-- Blurred/locked content -->
        <div class="opacity-50 pointer-events-none filter blur-[2px]">
          <ng-content select="[locked]"></ng-content>
        </div>

        <!-- Overlay with upgrade prompt -->
        <div class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm rounded-lg">
          <div class="text-center p-6 max-w-sm">
            <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <svg class="w-8 h-8 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/>
              </svg>
            </div>

            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              {{ title() }}
            </h3>

            <p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
              {{ description() }}
            </p>

            <button
              type="button"
              class="inline-flex items-center px-4 py-2 bg-gradient-to-r from-amber-400 to-amber-500 text-white font-medium rounded-lg hover:from-amber-500 hover:to-amber-600 transition-all shadow-sm"
              (click)="onUpgrade()"
            >
              <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clip-rule="evenodd"/>
              </svg>
              Перейти на PRO
            </button>
          </div>
        </div>
      </div>
    } @else {
      <!-- Unlocked content -->
      <ng-content></ng-content>
    }
  `
})
export class FeatureGateComponent {
  private router = inject(Router);
  private subscriptionService = inject(SubscriptionService);

  // Can be used to manually override the lock state
  locked = input<boolean | undefined>(undefined);
  title = input<string>('Функция доступна в PRO');
  description = input<string>('Оформите PRO подписку, чтобы разблокировать эту функцию');
  redirectUrl = input<string>('/subscription');

  upgrade = output<void>();

  isLocked(): boolean {
    // If explicitly set, use that value
    const explicitLock = this.locked();
    if (explicitLock !== undefined) {
      return explicitLock;
    }
    // Otherwise, check if user is NOT pro
    return !this.subscriptionService.isPro();
  }

  onUpgrade(): void {
    this.upgrade.emit();
    this.router.navigate([this.redirectUrl()]);
  }
}
