import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="loading-wrapper" [class.fullscreen]="fullScreen()">
      <div class="spinner" [class]="sizeClass()"></div>
      @if (showText()) {
        <span class="loading-text">Загрузка...</span>
      }
    </div>
  `,
  styles: [`
    .loading-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      padding: 2rem;
    }

    .loading-wrapper.fullscreen {
      position: fixed;
      inset: 0;
      z-index: 50;
      background: var(--color-bg-overlay);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
    }

    .spinner {
      border: 2px solid var(--color-border-primary);
      border-top-color: var(--color-brand-500);
      border-radius: 9999px;
      animation: spin 0.7s linear infinite;
    }

    .spinner-sm {
      width: 1rem;
      height: 1rem;
      border-width: 1.5px;
    }

    .spinner-md {
      width: 1.5rem;
      height: 1.5rem;
      border-width: 2px;
    }

    .spinner-lg {
      width: 2rem;
      height: 2rem;
      border-width: 2.5px;
    }

    .loading-text {
      font-size: 0.875rem;
      color: var(--color-text-tertiary);
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `]
})
export class LoadingSpinnerComponent {
  size = input<'sm' | 'md' | 'lg'>('md');
  fullScreen = input<boolean>(false);
  showText = input<boolean>(false);

  sizeClass(): string {
    const sizes: Record<string, string> = {
      sm: 'spinner-sm',
      md: 'spinner-md',
      lg: 'spinner-lg'
    };
    return sizes[this.size()];
  }
}
