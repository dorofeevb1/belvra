import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService, DataService } from '../../../core/services';
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

  isLoading = signal(true);
  transactions = signal<Transaction[]>([]);

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
    const paidTxs = this.transactions().filter(t => t.status === 'paid');
    return {
      income: paidTxs.reduce((sum, t) => sum + t.income, 0),
      materials: paidTxs.reduce((sum, t) => sum + t.materialsCost, 0),
      profit: paidTxs.reduce((sum, t) => sum + t.netProfit, 0)
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
