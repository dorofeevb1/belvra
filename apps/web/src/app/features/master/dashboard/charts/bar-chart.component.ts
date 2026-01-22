import { Component, input, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DateService } from '../../../../core/services';

@Component({
  selector: 'app-bar-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="bar-chart">
      @for (item of chartData(); track item.date) {
        <div class="bar-column">
          <div class="bar-area">
            <span class="bar-value">{{ item.count }}</span>
            <div
              class="bar-fill"
              [style.height.%]="item.heightPercent"
              [class.bar-highlight]="item.isToday"
            ></div>
          </div>
          <span class="bar-label" [class.label-highlight]="item.isToday">{{ item.label }}</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .bar-chart {
      height: 12rem;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 0.5rem;
    }

    .bar-column {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
    }

    .bar-area {
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      height: 9rem;
    }

    .bar-value {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-text-secondary);
      margin-bottom: 0.25rem;
    }

    .bar-fill {
      width: 100%;
      max-width: 2rem;
      background: linear-gradient(180deg, var(--color-brand-400) 0%, var(--color-brand-600) 100%);
      border-radius: var(--radius-md) var(--radius-md) 0 0;
      transition: height 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
      min-height: 4px;
    }

    .bar-fill.bar-highlight {
      background: linear-gradient(180deg, var(--color-brand-300) 0%, var(--color-brand-500) 100%);
      box-shadow: 0 0 12px var(--color-brand-400);
    }

    .bar-label {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--color-text-tertiary);
    }

    .label-highlight {
      color: var(--color-brand-500);
      font-weight: 600;
    }
  `]
})
export class BarChartComponent {
  private dateService = inject(DateService);

  data = input<{ date: string; count: number }[]>([]);

  chartData = computed(() => {
    const items = this.data();
    const maxCount = Math.max(...items.map(i => i.count), 1);
    const today = this.dateService.todayStr();

    return items.map(item => ({
      ...item,
      label: this.dateService.getShortWeekday(item.date),
      heightPercent: Math.max((item.count / maxCount) * 100, 3),
      isToday: item.date === today
    }));
  });
}
