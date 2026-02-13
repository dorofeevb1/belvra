import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService, DataService } from '../../../core/services';
import { SubscriptionService } from '../../../core/services/subscription.service';
import {
  Transaction,
  TRANSACTION_STATUS_LABELS
} from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-finances',
  standalone: true,
  imports: [CommonModule, CurrencyRubPipe, DateFormatPipe],
  templateUrl: './finances.component.html',
  styleUrl: './finances.component.scss'
})
export class FinancesComponent implements OnInit {
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private subscriptionService = inject(SubscriptionService);

  isLoading = signal(true);
  transactions = signal<Transaction[]>([]);
  platformFee = computed(() => this.subscriptionService.limits().commissionPercent);

  /** Общая прибыль считается только по выплаченным транзакциям, pending отображаются отдельно */
  summary = computed(() => {
    const txs = this.transactions();
    const paidTxs = txs.filter(t => t.status === 'paid');
    const totalProfit = paidTxs.reduce((sum, t) => sum + t.netProfit, 0);
    const pendingAmount = txs
      .filter(t => t.status === 'pending')
      .reduce((sum, t) => sum + t.netProfit, 0);
    const lastPayout = paidTxs.length > 0
      ? paidTxs[paidTxs.length - 1].netProfit
      : 0;

    return { totalProfit, pendingAmount, lastPayout };
  });

  totals = computed(() => {
    const txs = this.transactions();
    return {
      income: txs.reduce((sum, t) => sum + t.income, 0),
      materials: txs.reduce((sum, t) => sum + t.materialsCost, 0),
      fees: txs.reduce((sum, t) => sum + t.platformFee, 0),
      profit: txs.reduce((sum, t) => sum + t.netProfit, 0)
    };
  });

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    const masterId = this.authService.masterData()?.id;
    if (!masterId) return;

    this.dataService.getTransactions(masterId).subscribe(data => {
      this.transactions.set(data.sort((a, b) =>
        new Date(b.date).getTime() - new Date(a.date).getTime()
      ));
      this.isLoading.set(false);
    });
  }

  getStatusLabel(status: string): string {
    return TRANSACTION_STATUS_LABELS[status as keyof typeof TRANSACTION_STATUS_LABELS] || status;
  }
}
