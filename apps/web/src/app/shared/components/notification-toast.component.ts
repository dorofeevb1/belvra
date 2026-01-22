import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, Notification } from '../../core/services/notification.service';

@Component({
  selector: 'app-notification-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container">
      @for (notification of notificationService.notifications(); track notification.id) {
        <div class="toast animate-slideInRight" [class]="getTypeClass(notification.type)">
          <div class="toast-icon" [innerHTML]="getIcon(notification.type)"></div>
          <p class="toast-message">{{ notification.message }}</p>
          <button
            type="button"
            class="toast-close"
            (click)="notificationService.remove(notification.id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
          <div class="toast-progress" [class]="getProgressClass(notification.type)"></div>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 1.5rem;
      right: 1.5rem;
      z-index: 100;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      max-width: 24rem;
    }

    .toast {
      position: relative;
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 1rem;
      background: var(--color-bg-elevated);
      border: 1px solid var(--color-border-secondary);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-xl);
      overflow: hidden;
    }

    .toast-icon {
      flex-shrink: 0;
      width: 1.25rem;
      height: 1.25rem;
    }

    .toast-message {
      flex: 1;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-primary);
    }

    .toast-close {
      flex-shrink: 0;
      padding: 0.25rem;
      color: var(--color-text-tertiary);
      border-radius: var(--radius-md);
      transition: all 150ms ease;
    }

    .toast-close:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .toast-progress {
      position: absolute;
      bottom: 0;
      left: 0;
      height: 3px;
      animation: progress 4s linear forwards;
    }

    .toast-success .toast-icon { color: var(--color-success); }
    .toast-error .toast-icon { color: var(--color-error); }
    .toast-warning .toast-icon { color: var(--color-warning); }
    .toast-info .toast-icon { color: var(--color-info); }

    .progress-success { background: var(--color-success); }
    .progress-error { background: var(--color-error); }
    .progress-warning { background: var(--color-warning); }
    .progress-info { background: var(--color-info); }

    @keyframes progress {
      from { width: 100%; }
      to { width: 0%; }
    }

    @keyframes slideInRight {
      from {
        opacity: 0;
        transform: translateX(100%);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }

    .animate-slideInRight {
      animation: slideInRight 0.3s ease-out;
    }
  `]
})
export class NotificationToastComponent {
  notificationService = inject(NotificationService);

  getTypeClass(type: string): string {
    return `toast-${type}`;
  }

  getProgressClass(type: string): string {
    return `progress-${type}`;
  }

  getIcon(type: string): string {
    const icons: Record<string, string> = {
      success: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
      error: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
      warning: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
      info: '<svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
    };
    return icons[type] || icons['info'];
  }
}
