import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (isOpen()) {
      <div class="modal-overlay" (click)="onBackdropClick($event)">
        <div class="modal" [class]="sizeClass()" role="dialog" aria-modal="true">
          @if (title()) {
            <div class="modal-header">
              <h2 class="modal-title">{{ title() }}</h2>
              <button
                type="button"
                class="btn btn-ghost btn-icon-sm"
                (click)="closeModal.emit()"
                aria-label="Закрыть"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          }

          <div class="modal-body">
            <ng-content></ng-content>
          </div>

          <ng-content select="[modal-footer]"></ng-content>
        </div>
      </div>
    }
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      inset: 0;
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      background: var(--color-bg-overlay);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      animation: fadeIn 0.15s ease-out;
    }

    @media (max-width: 640px) {
      .modal-overlay {
        align-items: flex-end;
        padding: 0;
      }
    }

    .modal {
      position: relative;
      width: 100%;
      max-height: calc(100vh - 2rem);
      display: flex;
      flex-direction: column;
      background: var(--color-bg-elevated);
      border-radius: var(--radius-2xl);
      box-shadow: var(--shadow-2xl);
      animation: scaleIn 0.2s ease-out;
    }

    @media (max-width: 640px) {
      .modal {
        max-height: 90vh;
        border-radius: var(--radius-2xl) var(--radius-2xl) 0 0;
        animation: slideUp 0.25s ease-out;
      }
    }

    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateY(100%);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .modal-sm { max-width: 24rem; }
    .modal-md { max-width: 32rem; }
    .modal-lg { max-width: 40rem; }
    .modal-xl { max-width: 48rem; }
    .modal-full { max-width: 64rem; }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--color-border-secondary);
    }

    .modal-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--color-text-primary);
    }

    .modal-body {
      flex: 1;
      padding: 1.5rem;
      overflow-y: auto;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes scaleIn {
      from {
        opacity: 0;
        transform: scale(0.95);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }

    :host {
      display: contents;
    }
  `]
})
export class ModalComponent {
  isOpen = input<boolean>(false);
  title = input<string>('');
  size = input<'sm' | 'md' | 'lg' | 'xl' | 'full'>('md');
  closeOnBackdrop = input<boolean>(true);
  closeModal = output<void>();

  sizeClass(): string {
    const sizes: Record<string, string> = {
      sm: 'modal-sm',
      md: 'modal-md',
      lg: 'modal-lg',
      xl: 'modal-xl',
      full: 'modal-full'
    };
    return sizes[this.size()];
  }

  onBackdropClick(event: MouseEvent): void {
    if (this.closeOnBackdrop() && event.target === event.currentTarget) {
      this.closeModal.emit();
    }
  }
}
