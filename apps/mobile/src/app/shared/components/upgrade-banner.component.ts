import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-upgrade-banner',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div
      class="relative overflow-hidden rounded-xl p-4 sm:p-6"
      [class]="variant() === 'gradient' ? 'bg-gradient-to-r from-amber-400 via-amber-500 to-orange-500' : 'bg-slate-100 dark:bg-slate-800 border border-amber-200 dark:border-amber-800'"
    >
      @if (dismissible()) {
        <button
          type="button"
          class="absolute top-2 right-2 p-1 rounded-full hover:bg-black/10 transition-colors"
          [class.text-white]="variant() === 'gradient'"
          [class.text-slate-500]="variant() !== 'gradient'"
          (click)="onDismiss.emit()"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      }

      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <!-- Icon -->
        <div
          class="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center"
          [class.bg-white/20]="variant() === 'gradient'"
          [class.bg-amber-100]="variant() !== 'gradient'"
          [class.dark:bg-amber-900/30]="variant() !== 'gradient'"
        >
          <svg
            class="w-6 h-6"
            [class.text-white]="variant() === 'gradient'"
            [class.text-amber-600]="variant() !== 'gradient'"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clip-rule="evenodd"/>
          </svg>
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <h3
            class="text-lg font-semibold"
            [class.text-white]="variant() === 'gradient'"
            [class.text-slate-900]="variant() !== 'gradient'"
            [class.dark:text-white]="variant() !== 'gradient'"
          >
            {{ title() }}
          </h3>
          <p
            class="text-sm mt-0.5"
            [class.text-white/90]="variant() === 'gradient'"
            [class.text-slate-600]="variant() !== 'gradient'"
            [class.dark:text-slate-400]="variant() !== 'gradient'"
          >
            {{ description() }}
          </p>
        </div>

        <!-- CTA Button -->
        <a
          [routerLink]="ctaLink()"
          class="flex-shrink-0 px-4 py-2 rounded-lg font-medium text-sm transition-all"
          [class.bg-white]="variant() === 'gradient'"
          [class.text-amber-600]="variant() === 'gradient'"
          [class.hover:bg-amber-50]="variant() === 'gradient'"
          [class.bg-amber-500]="variant() !== 'gradient'"
          [class.text-white]="variant() !== 'gradient'"
          [class.hover:bg-amber-600]="variant() !== 'gradient'"
        >
          {{ ctaText() }}
        </a>
      </div>

      @if (showFeatures()) {
        <div
          class="mt-4 pt-4 border-t grid grid-cols-2 sm:grid-cols-3 gap-2"
          [class.border-white/20]="variant() === 'gradient'"
          [class.border-slate-200]="variant() !== 'gradient'"
          [class.dark:border-slate-700]="variant() !== 'gradient'"
        >
          @for (feature of features(); track feature) {
            <div class="flex items-center gap-1.5 text-sm">
              <svg
                class="w-4 h-4 flex-shrink-0"
                [class.text-white]="variant() === 'gradient'"
                [class.text-amber-500]="variant() !== 'gradient'"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <span
                [class.text-white/90]="variant() === 'gradient'"
                [class.text-slate-700]="variant() !== 'gradient'"
                [class.dark:text-slate-300]="variant() !== 'gradient'"
              >
                {{ feature }}
              </span>
            </div>
          }
        </div>
      }
    </div>
  `
})
export class UpgradeBannerComponent {
  variant = input<'gradient' | 'subtle'>('gradient');
  title = input<string>('Перейдите на PRO');
  description = input<string>('Разблокируйте все возможности платформы');
  ctaText = input<string>('Подробнее');
  ctaLink = input<string>('/subscription');
  dismissible = input<boolean>(false);
  showFeatures = input<boolean>(false);
  features = input<string[]>([
    'Безлимит записей/услуг/портфолио',
    'PRO-бейдж',
    'Буст в поиске',
    'Расширенная аналитика'
  ]);

  onDismiss = output<void>();
}
