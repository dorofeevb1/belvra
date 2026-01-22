import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ProBadgeSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-pro-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      [class]="badgeClasses()"
      [attr.title]="showTooltip() ? 'PRO подписка активна' : null"
    >
      @if (showIcon()) {
        <svg
          class="inline-block"
          [class.w-3]="size() === 'sm'"
          [class.h-3]="size() === 'sm'"
          [class.w-4]="size() === 'md'"
          [class.h-4]="size() === 'md'"
          [class.w-5]="size() === 'lg'"
          [class.h-5]="size() === 'lg'"
          [class.mr-0.5]="size() === 'sm'"
          [class.mr-1]="size() !== 'sm'"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clip-rule="evenodd"/>
        </svg>
      }
      PRO
    </span>
  `
})
export class ProBadgeComponent {
  size = input<ProBadgeSize>('md');
  variant = input<'default' | 'outline' | 'subtle'>('default');
  showIcon = input<boolean>(true);
  showTooltip = input<boolean>(true);

  badgeClasses(): string {
    const baseClasses = 'inline-flex items-center font-bold uppercase tracking-wide';

    // Size classes
    const sizeClasses = {
      sm: 'text-[10px] px-1.5 py-0.5 rounded',
      md: 'text-xs px-2 py-0.5 rounded-md',
      lg: 'text-sm px-2.5 py-1 rounded-md'
    };

    // Variant classes
    const variantClasses = {
      default: 'bg-gradient-to-r from-amber-400 to-amber-500 text-white shadow-sm',
      outline: 'border-2 border-amber-400 text-amber-500 bg-transparent',
      subtle: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
    };

    return `${baseClasses} ${sizeClasses[this.size()]} ${variantClasses[this.variant()]}`;
  }
}
