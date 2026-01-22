import { Component, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-donut-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="donut-chart">
      <!-- SVG Donut -->
      <div class="donut-visual">
        <svg viewBox="0 0 36 36" class="donut-svg">
          @for (segment of chartSegments(); track segment.name; let i = $index) {
            <circle
              cx="18"
              cy="18"
              r="15.9155"
              fill="none"
              [attr.stroke]="segment.color"
              stroke-width="3"
              [attr.stroke-dasharray]="segment.dashArray"
              [attr.stroke-dashoffset]="segment.offset"
              class="donut-segment"
            />
          }
          <!-- Background circle when no data -->
          @if (chartSegments().length === 0) {
            <circle
              cx="18"
              cy="18"
              r="15.9155"
              fill="none"
              stroke="var(--color-border-secondary)"
              stroke-width="3"
            />
          }
        </svg>
        <div class="donut-center">
          <span class="donut-total">{{ total() }}</span>
          <span class="donut-label">записей</span>
        </div>
      </div>

      <!-- Legend -->
      <div class="donut-legend">
        @for (segment of chartSegments(); track segment.name) {
          <div class="legend-item">
            <div class="legend-dot" [style.backgroundColor]="segment.color"></div>
            <span class="legend-name">{{ segment.name }}</span>
            <span class="legend-count">{{ segment.count }}</span>
          </div>
        } @empty {
          <p class="legend-empty">Нет данных</p>
        }
      </div>
    </div>
  `,
  styles: [`
    .donut-chart {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .donut-visual {
      position: relative;
      width: 8rem;
      height: 8rem;
      flex-shrink: 0;
    }

    .donut-svg {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
    }

    .donut-segment {
      transition: stroke-dasharray 500ms cubic-bezier(0.34, 1.56, 0.64, 1),
                  stroke-dashoffset 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .donut-center {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .donut-total {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--color-text-primary);
      line-height: 1;
    }

    .donut-label {
      font-size: 0.6875rem;
      font-weight: 500;
      color: var(--color-text-tertiary);
      margin-top: 0.125rem;
    }

    .donut-legend {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      min-width: 0;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .legend-dot {
      width: 0.625rem;
      height: 0.625rem;
      border-radius: var(--radius-full);
      flex-shrink: 0;
    }

    .legend-name {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .legend-count {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--color-text-primary);
    }

    .legend-empty {
      font-size: 0.875rem;
      color: var(--color-text-tertiary);
    }

    @media (max-width: 640px) {
      .donut-chart {
        flex-direction: column;
        align-items: stretch;
      }

      .donut-visual {
        margin: 0 auto;
      }
    }
  `]
})
export class DonutChartComponent {
  data = input<{ serviceName: string; count: number }[]>([]);

  private colors = [
    'var(--color-brand-500)',
    '#8b5cf6',
    '#3b82f6',
    '#10b981',
    '#f59e0b',
    '#ef4444',
    '#06b6d4',
  ];

  total = computed(() => this.data().reduce((sum, item) => sum + item.count, 0));

  chartSegments = computed(() => {
    const items = this.data();
    const totalValue = this.total();
    if (totalValue === 0) return [];

    const circumference = 100;
    let currentOffset = 0;

    return items.map((item, index) => {
      const percentage = (item.count / totalValue) * circumference;
      const segment = {
        name: item.serviceName,
        count: item.count,
        color: this.colors[index % this.colors.length],
        dashArray: `${percentage} ${circumference - percentage}`,
        offset: -currentOffset
      };
      currentOffset += percentage;
      return segment;
    });
  });
}
