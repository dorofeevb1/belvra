import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { AuthService, DataService } from '../../../core/services';
import {
  Transaction,
  TRANSACTION_STATUS_LABELS
} from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

interface AnalyticsData {
  period: string;
  date_from: string;
  date_to: string;
  total_income: number;
  total_expenses: number;
  materials_cost: number;
  manual_expenses: number;
  net_profit: number;
  avg_check: number;
  appointments_count: number;
  comparison: { prev_income: number; change_percent: number };
  chart_data: { date: string; label?: string; income: number; expenses: number }[];
  top_services: { name: string; income: number; count: number }[];
  top_clients: { name: string; total_spent: number; visits: number }[];
  goal: {
    target: number;
    current: number;
    progress_percent: number;
    days_left: number;
    forecast: number;
    daily_needed: number;
  } | null;
  tax: {
    system: string;
    rate: number;
    amount: number;
    label: string;
  } | null;
  expense_breakdown: { category: string; total: number }[];
}

interface Expense {
  id?: number;
  amount: number;
  category: string;
  description: string;
  date: string;
  is_recurring: boolean;
}

const CATEGORY_ICONS: Record<string, string> = {
  rent: '🏠',
  materials: '🎨',
  tools: '🔧',
  education: '📚',
  transport: '🚗',
  other: '📦'
};

const CATEGORY_LABELS: Record<string, string> = {
  rent: 'Аренда',
  materials: 'Материалы',
  tools: 'Инструменты',
  education: 'Обучение',
  transport: 'Транспорт',
  other: 'Прочее'
};

const TAX_LABELS: Record<string, string> = {
  self_employed: 'Самозанятый',
  ip_usn: 'ИП (УСН)',
  ip_osn: 'ИП (ОСН)',
  ooo: 'ООО'
};

const MONTH_NAMES = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

@Component({
  selector: 'app-finances',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyRubPipe, DateFormatPipe],
  templateUrl: './finances.component.html',
  styleUrl: './finances.component.scss'
})
export class FinancesComponent implements OnInit {
  private api = inject(ApiService);
  private authService = inject(AuthService);
  private dataService = inject(DataService);

  isLoading = signal(true);
  activePeriod = signal<'week' | 'month' | 'year'>('month');
  analytics = signal<AnalyticsData | null>(null);
  transactions = signal<Transaction[]>([]);
  showExpenseModal = signal(false);
  expenseSaving = signal(false);
  animateReady = signal(false);

  // Expense form model
  newExpense: Expense = {
    amount: 0,
    category: 'materials',
    description: '',
    date: new Date().toISOString().slice(0, 10),
    is_recurring: false
  };

  readonly categoryIcons = CATEGORY_ICONS;
  readonly categoryLabels = CATEGORY_LABELS;
  readonly taxLabels = TAX_LABELS;
  readonly categories = Object.keys(CATEGORY_LABELS);

  headerTitle = computed(() => {
    const now = new Date();
    const period = this.activePeriod();
    if (period === 'month') {
      return `Финансы · ${MONTH_NAMES[now.getMonth()]} ${now.getFullYear()}`;
    } else if (period === 'week') {
      return `Финансы · Текущая неделя`;
    }
    return `Финансы · ${now.getFullYear()} год`;
  });

  // Chart computations
  chartMax = computed(() => {
    const data = this.analytics()?.chart_data ?? [];
    if (data.length === 0) return 1;
    return Math.max(...data.map(d => d.income), 1);
  });

  donutSegments = computed(() => {
    const services = this.analytics()?.top_services ?? [];
    const total = services.reduce((s, svc) => s + svc.income, 0);
    if (total === 0) return [];

    const colors = ['#7C3AED', '#A855F7', '#C084FC', '#DDD6FE', '#8B5CF6'];
    let cumulative = 0;
    return services.slice(0, 5).map((svc, i) => {
      const pct = svc.income / total;
      const startAngle = cumulative * 360;
      cumulative += pct;
      const endAngle = cumulative * 360;
      return {
        name: svc.name,
        income: svc.income,
        count: svc.count,
        percent: Math.round(pct * 100),
        color: colors[i % colors.length],
        startAngle,
        endAngle
      };
    });
  });

  // Transaction totals (kept for the transactions table)
  totals = computed(() => {
    const txs = this.transactions();
    return {
      income: txs.reduce((sum, t) => sum + t.income, 0),
      materials: txs.reduce((sum, t) => sum + t.materialsCost, 0),
      profit: txs.reduce((sum, t) => sum + t.netProfit, 0)
    };
  });

  ngOnInit(): void {
    this.loadData();
  }

  switchPeriod(period: 'week' | 'month' | 'year'): void {
    this.activePeriod.set(period);
    this.animateReady.set(false);
    this.isLoading.set(true);
    this.loadData();
  }

  openExpenseModal(): void {
    this.newExpense = {
      amount: 0,
      category: 'materials',
      description: '',
      date: new Date().toISOString().slice(0, 10),
      is_recurring: false
    };
    this.showExpenseModal.set(true);
  }

  closeExpenseModal(): void {
    this.showExpenseModal.set(false);
  }

  saveExpense(): void {
    if (!this.newExpense.amount || this.newExpense.amount <= 0) return;
    this.expenseSaving.set(true);

    this.api.post('/finances/expenses/', this.newExpense).subscribe({
      next: () => {
        this.expenseSaving.set(false);
        this.showExpenseModal.set(false);
        this.loadData();
      },
      error: () => {
        this.expenseSaving.set(false);
      }
    });
  }

  exportData(): void {
    const a = this.analytics();
    if (!a) return;

    const lines = [
      `Финансовый отчет (${a.date_from} — ${a.date_to})`,
      `Доход: ${a.total_income}`,
      `Расходы: ${a.total_expenses}`,
      `Чистая прибыль: ${a.net_profit}`,
      `Средний чек: ${a.avg_check}`,
      `Записей: ${a.appointments_count}`,
      '',
      'Топ услуги:',
      ...a.top_services.map(s => `  ${s.name}: ${s.income} ₽ (${s.count} раз)`),
      '',
      'Расходы по категориям:',
      ...a.expense_breakdown.map(e => `  ${CATEGORY_LABELS[e.category] || e.category}: ${e.total} ₽`)
    ];

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `finances_${a.date_from}_${a.date_to}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  getStatusLabel(status: string): string {
    return TRANSACTION_STATUS_LABELS[status as keyof typeof TRANSACTION_STATUS_LABELS] || status;
  }

  getBarHeight(income: number): number {
    const max = this.chartMax();
    return Math.max((income / max) * 100, 2);
  }

  getDonutPath(startAngle: number, endAngle: number): string {
    const cx = 80, cy = 80, r = 60;
    const rad = (deg: number) => (deg - 90) * Math.PI / 180;

    if (endAngle - startAngle >= 359.99) {
      // Full circle
      return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r} A ${r} ${r} 0 1 1 ${cx} ${cy - r}`;
    }

    const x1 = cx + r * Math.cos(rad(startAngle));
    const y1 = cy + r * Math.sin(rad(startAngle));
    const x2 = cx + r * Math.cos(rad(endAngle));
    const y2 = cy + r * Math.sin(rad(endAngle));
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;

    return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
  }

  getShortDate(dateStr: string): string {
    const d = new Date(dateStr);
    return `${d.getDate()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
  }

  private loadData(): void {
    const period = this.activePeriod();

    this.api.get<AnalyticsData>('/finances/analytics/', { period }).subscribe({
      next: (data) => {
        this.analytics.set(data);
        this.isLoading.set(false);
        // Trigger animations after a tick
        setTimeout(() => this.animateReady.set(true), 50);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });

    // Also load transactions for the table
    const masterId = this.authService.masterApiId();
    if (masterId) {
      this.dataService.getTransactions(masterId).subscribe(data => {
        this.transactions.set(data.sort((a, b) =>
          new Date(b.date).getTime() - new Date(a.date).getTime()
        ));
      });
    }
  }
}
