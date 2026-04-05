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
      padding: 2rem 1rem;
      background: var(--color-bg-overlay);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      animation: fadeIn 0.15s ease-out;
      overflow-y: auto;
    }

    .modal {
      position: relative;
      width: 100%;
      max-height: calc(100vh - 4rem);
      display: flex;
      flex-direction: column;
      background: var(--color-bg-elevated);
      border-radius: var(--radius-2xl);
      box-shadow: var(--shadow-2xl);
      animation: scaleIn 0.2s ease-out;
      margin: auto;
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
      min-height: 0;
    }

    ::ng-deep .modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 0.75rem;
      padding: 1rem 1.5rem;
      border-top: 1px solid var(--color-border-secondary);
      flex-shrink: 0;
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

    @media (max-width: 767px) {
      .modal-overlay {
        padding: 0;
        align-items: stretch;
      }

      .modal {
        max-height: 100vh;
        min-height: 100vh;
        border-radius: 0;
        margin: 0;
      }

      .modal-sm,
      .modal-md,
      .modal-lg,
      .modal-xl,
      .modal-full {
        max-width: 100%;
      }

      .modal-header {
        padding: 1rem;
      }

      .modal-body {
        padding: 1rem;
      }

      ::ng-deep .modal-footer {
        padding: 0.75rem 1rem;
      }

      ::ng-deep .modal-footer .btn {
        flex: 1;
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
