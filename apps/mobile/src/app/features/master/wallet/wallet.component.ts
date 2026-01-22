import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WalletService } from '../../../core/services';
import {
  Wallet,
  PaymentTransaction,
  WithdrawalRequest,
  WithdrawalMethod,
  WithdrawalDestination,
  EarningsSummary
} from '../../../core/models';

type TabType = 'overview' | 'transactions' | 'withdrawals';

@Component({
  selector: 'app-wallet',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './wallet.component.html',
  styleUrl: './wallet.component.scss'
})
export class WalletComponent implements OnInit {
  readonly walletService = inject(WalletService);

  // Data from service
  readonly wallet = this.walletService.wallet;
  readonly transactions = this.walletService.transactions;
  readonly withdrawals = this.walletService.withdrawals;
  readonly payoutDestinations = this.walletService.payoutDestinations;
  readonly loading = this.walletService.loading;
  readonly error = this.walletService.error;

  // UI state
  readonly activeTab = signal<TabType>('transactions');
  readonly selectedPeriod = signal<'day' | 'week' | 'month' | 'year'>('month');
  readonly summary = signal<EarningsSummary | null>(null);

  // Withdrawal modal
  readonly showWithdrawModal = signal(false);
  readonly withdrawStep = signal(1);
  readonly withdrawMethod = signal<WithdrawalMethod>('card');
  readonly selectedDestinationId = signal<string | null>(null);
  readonly isWithdrawing = signal(false);
  readonly showAddDestination = signal(false);

  // Form data
  withdrawAmount = 0;
  cardNumber = '';
  cardHolder = '';
  yoomoneyAccount = '';
  bankName = '';
  bik = '';
  accountNumber = '';
  saveDestination = true;

  readonly periods = [
    { value: 'day' as const, label: 'День' },
    { value: 'week' as const, label: 'Неделя' },
    { value: 'month' as const, label: 'Месяц' },
    { value: 'year' as const, label: 'Год' }
  ];

  readonly withdrawMethods = [
    { value: 'card' as WithdrawalMethod, label: 'Банковская карта', icon: 'credit-card' },
    { value: 'yoomoney' as WithdrawalMethod, label: 'ЮMoney', icon: 'wallet' },
    { value: 'bank_account' as WithdrawalMethod, label: 'Расчётный счёт', icon: 'landmark' }
  ];

  readonly calculatedFee = computed(() => {
    if (this.withdrawAmount <= 0) return 0;
    return this.walletService.calculateWithdrawalFee(this.withdrawAmount, this.withdrawMethod());
  });

  readonly filteredDestinations = computed(() => {
    const method = this.withdrawMethod();
    return this.payoutDestinations().filter(d => d.destination_type === method);
  });

  readonly hasDestinations = computed(() => {
    return this.filteredDestinations().length > 0;
  });

  ngOnInit(): void {
    // Load all wallet data
    this.walletService.loadWalletData();
    this.loadSummary();
  }

  selectPeriod(period: 'day' | 'week' | 'month' | 'year'): void {
    this.selectedPeriod.set(period);
    this.loadSummary();
  }

  loadSummary(): void {
    this.walletService.getEarningsSummary(this.selectedPeriod()).subscribe(s => {
      this.summary.set(s);
    });
  }

  formatMoney(amount: number): string {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  }

  formatDate(date: Date): string {
    return new Date(date).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getTransactionIconClass(tx: PaymentTransaction): string {
    return `type-${tx.type}`;
  }

  getPaymentMethodLabel(method: string): string {
    const labels: Record<string, string> = {
      card: 'Карта',
      sbp: 'СБП',
      yoomoney: 'ЮMoney',
      cash: 'Наличные'
    };
    return labels[method] || method;
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Ожидает',
      processing: 'В обработке',
      succeeded: 'Успешно',
      failed: 'Ошибка',
      refunded: 'Возврат',
      cancelled: 'Отменён'
    };
    return labels[status] || status;
  }

  getWithdrawalMethodLabel(method: WithdrawalMethod): string {
    const labels: Record<WithdrawalMethod, string> = {
      card: 'На карту',
      yoomoney: 'ЮMoney',
      bank_account: 'На счёт'
    };
    return labels[method];
  }

  getWithdrawalStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Создан',
      processing: 'В обработке',
      completed: 'Выполнен',
      rejected: 'Отклонён',
      failed: 'Ошибка'
    };
    return labels[status] || status;
  }

  getDestinationLabel(dest: WithdrawalDestination): string {
    if (dest.cardNumber) return dest.cardNumber;
    if (dest.yoomoneyAccount) return `ЮMoney ${dest.yoomoneyAccount}`;
    if (dest.accountNumber) return `${dest.bankName} *${dest.accountNumber.slice(-4)}`;
    return 'Не указано';
  }

  getMethodFeeLabel(method: WithdrawalMethod): string {
    const fees = this.walletService.commissionSettings().withdrawalFees;
    switch (method) {
      case 'card':
        return fees.cardPercent > 0
          ? `${fees.cardPercent}%`
          : fees.card > 0 ? `${fees.card} ₽` : 'Бесплатно';
      case 'yoomoney':
        return fees.yoomoneyPercent > 0
          ? `${fees.yoomoneyPercent}%`
          : fees.yoomoney > 0 ? `${fees.yoomoney} ₽` : 'Бесплатно';
      case 'bank_account':
        return fees.bank_accountPercent > 0
          ? `${fees.bank_accountPercent}%`
          : fees.bank_account > 0 ? `${fees.bank_account} ₽` : 'Бесплатно';
    }
  }

  openWithdrawModal(): void {
    this.withdrawStep.set(1);
    this.withdrawAmount = this.wallet()?.availableBalance || 0;
    this.withdrawMethod.set('card');
    this.selectedDestinationId.set(null);
    this.showAddDestination.set(false);
    this.cardNumber = '';
    this.cardHolder = '';
    this.yoomoneyAccount = '';
    this.bankName = '';
    this.bik = '';
    this.accountNumber = '';
    this.saveDestination = true;
    this.showWithdrawModal.set(true);

    // Select default destination if exists
    const defaultDest = this.filteredDestinations().find(d => d.is_default);
    if (defaultDest) {
      this.selectedDestinationId.set(defaultDest.id);
    }
  }

  closeWithdrawModal(): void {
    this.showWithdrawModal.set(false);
  }

  onMethodChange(): void {
    this.selectedDestinationId.set(null);
    this.showAddDestination.set(false);

    // Auto-select default destination for new method
    const defaultDest = this.filteredDestinations().find(d => d.is_default);
    if (defaultDest) {
      this.selectedDestinationId.set(defaultDest.id);
    }
  }

  canProceedToStep2(): boolean {
    const settings = this.walletService.commissionSettings();
    const wallet = this.wallet();
    return (
      this.withdrawAmount >= settings.minWithdrawalAmount &&
      this.withdrawAmount <= (wallet?.availableBalance || 0)
    );
  }

  canSubmitWithdraw(): boolean {
    // If using existing destination
    if (this.selectedDestinationId()) {
      return true;
    }

    // If adding new destination
    if (this.showAddDestination()) {
      return this.canAddDestination();
    }

    return false;
  }

  canAddDestination(): boolean {
    const method = this.withdrawMethod();

    switch (method) {
      case 'card':
        return this.cardNumber.replace(/\s/g, '').length >= 16 && this.cardHolder.length >= 3;
      case 'yoomoney':
        return this.yoomoneyAccount.length >= 11;
      case 'bank_account':
        return this.bankName.length >= 2 && this.bik.length === 9 && this.accountNumber.length === 20;
    }
  }

  selectDestination(id: string): void {
    this.selectedDestinationId.set(id);
    this.showAddDestination.set(false);
  }

  toggleAddDestination(): void {
    this.showAddDestination.update(v => !v);
    if (this.showAddDestination()) {
      this.selectedDestinationId.set(null);
    }
  }

  async submitWithdraw(): Promise<void> {
    if (!this.canSubmitWithdraw()) return;

    this.isWithdrawing.set(true);

    try {
      let destinationId = this.selectedDestinationId();

      // If adding new destination first
      if (this.showAddDestination() && !destinationId) {
        const method = this.withdrawMethod();
        const destData: any = {
          destination_type: method,
          is_default: this.saveDestination
        };

        switch (method) {
          case 'card':
            destData.card_number = this.cardNumber.replace(/\s/g, '');
            break;
          case 'yoomoney':
            destData.yoomoney_account = this.yoomoneyAccount;
            break;
          case 'bank_account':
            destData.bank_name = this.bankName;
            destData.bik = this.bik;
            destData.account_number = this.accountNumber;
            break;
        }

        // Create destination first
        const newDest = await this.walletService.addPayoutDestination(destData).toPromise();
        if (newDest) {
          destinationId = newDest.id;
        }
      }

      if (!destinationId) {
        throw new Error('Не выбран способ вывода');
      }

      // Create withdrawal request
      await this.walletService.requestWithdrawal(this.withdrawAmount, destinationId).toPromise();

      this.isWithdrawing.set(false);
      this.closeWithdrawModal();
    } catch (err: any) {
      this.isWithdrawing.set(false);
      alert(err.message || err.error?.detail || 'Ошибка при создании запроса на вывод');
    }
  }

  async removeDestination(id: string, event: Event): Promise<void> {
    event.stopPropagation();
    if (!confirm('Удалить этот способ вывода?')) return;

    try {
      await this.walletService.removePayoutDestination(id).toPromise();
      if (this.selectedDestinationId() === id) {
        this.selectedDestinationId.set(null);
      }
    } catch (err: any) {
      alert(err.message || 'Ошибка удаления');
    }
  }

  async setDefaultDestination(id: string, event: Event): Promise<void> {
    event.stopPropagation();
    try {
      await this.walletService.setDefaultDestination(id).toPromise();
    } catch (err: any) {
      alert(err.message || 'Ошибка установки по умолчанию');
    }
  }

  cancelWithdrawal(withdrawalId: string): void {
    if (!confirm('Отменить запрос на вывод?')) return;

    this.walletService.cancelWithdrawal(withdrawalId).subscribe({
      error: (err) => alert(err.message || 'Ошибка отмены')
    });
  }

  refreshData(): void {
    this.walletService.loadWalletData();
    this.loadSummary();
  }
}
