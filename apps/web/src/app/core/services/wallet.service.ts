import { Injectable, inject, signal, computed } from '@angular/core';
import { Observable, map, tap, catchError, of, throwError } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import {
  Wallet,
  PaymentTransaction,
  WithdrawalRequest,
  WithdrawalMethod,
  WithdrawalDestination,
  EarningsSummary,
  CommissionSettings,
  DEFAULT_COMMISSION_SETTINGS,
  PaymentLink,
  PaymentStatus,
  PaymentType,
  PaymentMethodType,
  PaymentProviderType,
  WithdrawalStatus
} from '../models';

// API Response interfaces (snake_case from backend)
interface WalletResponse {
  id: string;
  master_name: string;
  available_balance: string;
  pending_balance: string;
  hold_balance: string;
  total_balance: string;
  total_earned: string;
  total_withdrawn: string;
  total_commission_paid: string;
  auto_withdraw: boolean;
  updated_at: string;
}

interface PaymentResponse {
  id: string;
  appointment: string;
  client: string;
  client_name: string;
  master: string;
  master_name: string;
  service_name: string;
  payment_type: string;
  payment_type_display: string;
  status: string;
  status_display: string;
  payment_method: string | null;
  payment_method_display: string | null;
  payment_provider: string;
  amount: string;
  commission: string;
  provider_fee: string;
  net_amount: string;
  refunded_amount: string;
  external_payment_id: string | null;
  confirmation_url: string | null;
  description: string;
  paid_at: string | null;
  available_at: string | null;
  refunded_at: string | null;
  created_at: string;
}

interface WithdrawalResponse {
  id: string;
  amount: string;
  fee: string;
  net_amount: string;
  method: string;
  method_display: string;
  status: string;
  status_display: string;
  card_last_four: string | null;
  destination_account: string | null;
  processed_at: string | null;
  completed_at: string | null;
  rejection_reason: string;
  created_at: string;
}

interface PayoutDestinationResponse {
  id: string;
  destination_type: string;
  destination_type_display: string;
  display_name: string;
  is_default: boolean;
  is_verified: boolean;
  card_last_four: string | null;
  card_type: string | null;
  yoomoney_account: string | null;
  bank_name: string | null;
  created_at: string;
}

interface WalletStatsResponse {
  period: string;
  total_earnings: string;
  total_payments: number;
  average_payment: string;
  commission_paid: string;
  net_earnings: string;
}

@Injectable({
  providedIn: 'root'
})
export class WalletService {
  private api = inject(ApiService);
  private authService = inject(AuthService);

  // Commission settings
  readonly commissionSettings = signal<CommissionSettings>(DEFAULT_COMMISSION_SETTINGS);

  // Master's wallet data
  private walletData = signal<Wallet | null>(null);
  private transactionsData = signal<PaymentTransaction[]>([]);
  private withdrawalsData = signal<WithdrawalRequest[]>([]);
  private payoutDestinationsData = signal<PayoutDestinationResponse[]>([]);

  // Loading states
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  // Public signals
  readonly wallet = this.walletData.asReadonly();
  readonly transactions = this.transactionsData.asReadonly();
  readonly withdrawals = this.withdrawalsData.asReadonly();
  readonly payoutDestinations = this.payoutDestinationsData.asReadonly();

  // Computed
  readonly totalBalance = computed(() => {
    const w = this.walletData();
    return w ? w.availableBalance + w.pendingBalance : 0;
  });

  readonly canWithdraw = computed(() => {
    const w = this.walletData();
    const settings = this.commissionSettings();
    return w ? w.availableBalance >= settings.minWithdrawalAmount : false;
  });

  readonly defaultPayoutDestination = computed(() => {
    return this.payoutDestinationsData().find(d => d.is_default) || null;
  });

  // ============ Wallet Methods ============

  getWallet(): Observable<Wallet | null> {
    this.loading.set(true);
    this.error.set(null);

    return this.api.getWallet().pipe(
      map((response: WalletResponse) => this.mapWalletResponse(response)),
      tap(wallet => {
        this.walletData.set(wallet);
        this.loading.set(false);
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка загрузки кошелька');
        this.loading.set(false);
        return of(null);
      })
    );
  }

  updateAutoWithdraw(enabled: boolean): Observable<Wallet | null> {
    return this.api.updateWallet({ auto_withdraw: enabled }).pipe(
      map((response: WalletResponse) => this.mapWalletResponse(response)),
      tap(wallet => this.walletData.set(wallet)),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка обновления настроек');
        return throwError(() => err);
      })
    );
  }

  private mapWalletResponse(response: WalletResponse): Wallet {
    return {
      masterId: response.id,
      availableBalance: parseFloat(response.available_balance),
      pendingBalance: parseFloat(response.pending_balance),
      holdBalance: parseFloat(response.hold_balance),
      totalEarned: parseFloat(response.total_earned),
      totalWithdrawn: parseFloat(response.total_withdrawn),
      totalCommissionPaid: parseFloat(response.total_commission_paid),
      autoWithdraw: response.auto_withdraw,
      autoWithdrawThreshold: 10000, // Default, can be added to backend later
      updatedAt: new Date(response.updated_at)
    };
  }

  // ============ Transactions Methods ============

  getTransactions(params?: {
    status?: PaymentStatus;
    payment_type?: PaymentType;
    date_from?: string;
    date_to?: string;
    limit?: number;
  }): Observable<PaymentTransaction[]> {
    this.loading.set(true);

    return this.api.getMasterPayments(params).pipe(
      map((response: { results: PaymentResponse[] }) =>
        (response.results || response).map((p: PaymentResponse) => this.mapPaymentResponse(p))
      ),
      tap(transactions => {
        this.transactionsData.set(transactions);
        this.loading.set(false);
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка загрузки транзакций');
        this.loading.set(false);
        return of([]);
      })
    );
  }

  private mapPaymentResponse(response: PaymentResponse): PaymentTransaction {
    return {
      id: response.id,
      masterId: response.master,
      clientId: response.client,
      appointmentId: response.appointment,
      type: response.payment_type as PaymentType,
      status: response.status as PaymentStatus,
      amount: parseFloat(response.amount),
      commission: parseFloat(response.commission),
      providerFee: parseFloat(response.provider_fee),
      netAmount: parseFloat(response.net_amount),
      paymentMethod: (response.payment_method as PaymentMethodType) || 'card',
      paymentProvider: response.payment_provider as PaymentProviderType,
      externalPaymentId: response.external_payment_id || undefined,
      createdAt: new Date(response.created_at),
      paidAt: response.paid_at ? new Date(response.paid_at) : undefined,
      availableAt: response.available_at ? new Date(response.available_at) : undefined,
      description: response.description || response.service_name,
      refundedAmount: parseFloat(response.refunded_amount) || undefined
    };
  }

  // ============ Withdrawals Methods ============

  getWithdrawals(params?: {
    status?: WithdrawalStatus;
    method?: WithdrawalMethod;
    date_from?: string;
    date_to?: string;
  }): Observable<WithdrawalRequest[]> {
    this.loading.set(true);

    return this.api.getWithdrawals(params).pipe(
      map((response: { results: WithdrawalResponse[] }) =>
        (response.results || response).map((w: WithdrawalResponse) => this.mapWithdrawalResponse(w))
      ),
      tap(withdrawals => {
        this.withdrawalsData.set(withdrawals);
        this.loading.set(false);
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка загрузки выводов');
        this.loading.set(false);
        return of([]);
      })
    );
  }

  requestWithdrawal(amount: number, destinationId: string): Observable<WithdrawalRequest> {
    const wallet = this.walletData();
    const settings = this.commissionSettings();

    // Client-side validation
    if (!wallet) {
      return throwError(() => new Error('Кошелёк не найден'));
    }
    if (amount < settings.minWithdrawalAmount) {
      return throwError(() => new Error(`Минимальная сумма вывода: ${settings.minWithdrawalAmount} ₽`));
    }
    if (amount > wallet.availableBalance) {
      return throwError(() => new Error('Недостаточно средств'));
    }

    this.loading.set(true);

    return this.api.createWithdrawal({ amount, destination_id: destinationId }).pipe(
      map((response: WithdrawalResponse) => this.mapWithdrawalResponse(response)),
      tap(withdrawal => {
        // Add to list
        this.withdrawalsData.update(list => [withdrawal, ...list]);
        // Update wallet balance
        this.walletData.update(w => w ? {
          ...w,
          availableBalance: w.availableBalance - amount,
          holdBalance: w.holdBalance + amount,
          updatedAt: new Date()
        } : null);
        this.loading.set(false);
      }),
      catchError(err => {
        this.error.set(err.error?.detail || err.error?.amount?.[0] || 'Ошибка создания запроса');
        this.loading.set(false);
        return throwError(() => err);
      })
    );
  }

  cancelWithdrawal(withdrawalId: string): Observable<WithdrawalRequest> {
    return this.api.cancelWithdrawal(withdrawalId).pipe(
      map((response: WithdrawalResponse) => this.mapWithdrawalResponse(response)),
      tap(withdrawal => {
        // Get original data BEFORE updating list
        const original = this.withdrawalsData().find(w => w.id === withdrawalId);
        // Update in list
        this.withdrawalsData.update(list =>
          list.map(w => w.id === withdrawalId ? withdrawal : w)
        );
        // Return funds to available balance using original amount
        if (original) {
          this.walletData.update(w => w ? {
            ...w,
            availableBalance: w.availableBalance + original.amount,
            holdBalance: w.holdBalance - original.amount,
            updatedAt: new Date()
          } : null);
        }
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка отмены запроса');
        return throwError(() => err);
      })
    );
  }

  private mapWithdrawalResponse(response: WithdrawalResponse): WithdrawalRequest {
    return {
      id: response.id,
      masterId: '', // Not provided by API, can be derived from wallet
      amount: parseFloat(response.amount),
      fee: parseFloat(response.fee),
      netAmount: parseFloat(response.net_amount),
      method: response.method as WithdrawalMethod,
      destination: {
        type: response.method as WithdrawalMethod,
        cardNumber: response.card_last_four ? `**** **** **** ${response.card_last_four}` : undefined,
        yoomoneyAccount: response.destination_account || undefined
      },
      status: response.status as WithdrawalStatus,
      createdAt: new Date(response.created_at),
      processedAt: response.processed_at ? new Date(response.processed_at) : undefined,
      completedAt: response.completed_at ? new Date(response.completed_at) : undefined,
      errorMessage: response.rejection_reason || undefined
    };
  }

  // ============ Payout Destinations Methods ============

  getPayoutDestinations(): Observable<PayoutDestinationResponse[]> {
    return this.api.getPayoutDestinations().pipe(
      map((response: { results: PayoutDestinationResponse[] }) => response.results || response),
      tap(destinations => this.payoutDestinationsData.set(destinations)),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка загрузки способов вывода');
        return of([]);
      })
    );
  }

  addPayoutDestination(data: {
    destination_type: WithdrawalMethod;
    is_default?: boolean;
    card_number?: string;
    yoomoney_account?: string;
    bank_name?: string;
    bik?: string;
    account_number?: string;
  }): Observable<PayoutDestinationResponse> {
    return this.api.createPayoutDestination(data).pipe(
      tap(destination => {
        this.payoutDestinationsData.update(list => [...list, destination]);
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка добавления способа вывода');
        return throwError(() => err);
      })
    );
  }

  removePayoutDestination(id: string): Observable<void> {
    return this.api.deletePayoutDestination(id).pipe(
      tap(() => {
        this.payoutDestinationsData.update(list => list.filter(d => d.id !== id));
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка удаления способа вывода');
        return throwError(() => err);
      })
    );
  }

  setDefaultDestination(id: string): Observable<PayoutDestinationResponse> {
    return this.api.setDefaultPayoutDestination(id).pipe(
      tap(destination => {
        this.payoutDestinationsData.update(list =>
          list.map(d => ({
            ...d,
            is_default: d.id === id
          }))
        );
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка установки способа по умолчанию');
        return throwError(() => err);
      })
    );
  }

  // ============ Payments Methods ============

  createPayment(
    appointmentId: string,
    paymentType: PaymentType = 'full_payment',
    amount?: number,
    returnUrl?: string,
    paymentMethod?: 'bank_card' | 'sbp'
  ): Observable<PaymentTransaction & { confirmationUrl?: string }> {
    const data: any = {
      appointment_id: appointmentId,
      payment_type: paymentType
    };
    if (amount) data.amount = amount;
    if (returnUrl) data.return_url = returnUrl;
    if (paymentMethod) data.payment_method = paymentMethod;

    return this.api.createPayment(data).pipe(
      map((response: PaymentResponse) => ({
        ...this.mapPaymentResponse(response),
        confirmationUrl: response.confirmation_url || undefined
      })),
      tap(payment => {
        this.transactionsData.update(list => [payment, ...list]);
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка создания платежа');
        return throwError(() => err);
      })
    );
  }

  getPaymentStatus(paymentId: string): Observable<any> {
    return this.api.getPaymentStatus(paymentId);
  }

  refundPayment(paymentId: string, amount?: number, reason?: string): Observable<PaymentTransaction> {
    return this.api.refundPayment(paymentId, { amount, reason }).pipe(
      map((response: PaymentResponse) => this.mapPaymentResponse(response)),
      tap(payment => {
        this.transactionsData.update(list =>
          list.map(p => p.id === paymentId ? payment : p)
        );
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка возврата платежа');
        return throwError(() => err);
      })
    );
  }

  confirmTestPayment(paymentId: string): Observable<PaymentTransaction> {
    return this.api.confirmTestPayment(paymentId).pipe(
      map((response: PaymentResponse) => this.mapPaymentResponse(response)),
      tap(payment => {
        this.transactionsData.update(list =>
          list.map(p => p.id === paymentId ? payment : p)
        );
      }),
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка подтверждения платежа');
        return throwError(() => err);
      })
    );
  }

  // ============ Statistics Methods ============

  getWalletStats(): Observable<WalletStatsResponse[]> {
    return this.api.getWalletStats().pipe(
      catchError(err => {
        this.error.set(err.error?.detail || 'Ошибка загрузки статистики');
        return of([]);
      })
    );
  }

  getEarningsSummary(period: 'day' | 'week' | 'month' | 'year'): Observable<EarningsSummary> {
    return this.getWalletStats().pipe(
      map(stats => {
        const periodMap: Record<string, string> = {
          'day': 'today',
          'week': 'week',
          'month': 'month',
          'year': 'year'
        };
        const stat = stats.find(s => s.period === periodMap[period]) || stats[0];

        const now = new Date();
        let startDate: Date;
        switch (period) {
          case 'day':
            startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            break;
          case 'week':
            startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            break;
          case 'month':
            startDate = new Date(now.getFullYear(), now.getMonth(), 1);
            break;
          case 'year':
            startDate = new Date(now.getFullYear(), 0, 1);
            break;
        }

        return {
          period,
          startDate,
          endDate: now,
          grossEarnings: parseFloat(stat?.total_earnings || '0'),
          commission: parseFloat(stat?.commission_paid || '0'),
          netEarnings: parseFloat(stat?.net_earnings || '0'),
          appointmentsCount: stat?.total_payments || 0,
          tipsAmount: 0,
          refundsAmount: 0,
          byMethod: {
            card: 0,
            sbp: 0,
            yoomoney: 0,
            cash: 0
          }
        };
      })
    );
  }

  // ============ Helper Methods ============

  calculateWithdrawalFee(amount: number, method: WithdrawalMethod): number {
    const settings = this.commissionSettings();
    const fees = settings.withdrawalFees;

    let fixedFee = 0;
    let percentFee = 0;

    switch (method) {
      case 'card':
        fixedFee = fees.card;
        percentFee = (amount * fees.cardPercent) / 100;
        break;
      case 'yoomoney':
        fixedFee = fees.yoomoney;
        percentFee = (amount * fees.yoomoneyPercent) / 100;
        break;
      case 'bank_account':
        fixedFee = fees.bank_account;
        percentFee = (amount * fees.bank_accountPercent) / 100;
        break;
    }

    return Math.round((fixedFee + percentFee) * 100) / 100;
  }

  // Load all wallet data at once
  loadWalletData(): void {
    this.getWallet().subscribe();
    this.getTransactions().subscribe();
    this.getWithdrawals().subscribe();
    this.getPayoutDestinations().subscribe();
  }

  // Clear wallet data (on logout)
  clearWalletData(): void {
    this.walletData.set(null);
    this.transactionsData.set([]);
    this.withdrawalsData.set([]);
    this.payoutDestinationsData.set([]);
    this.error.set(null);
  }
}
