/**
 * Wallet & Payment System Models
 *
 * Flow:
 * 1. Client books appointment and pays
 * 2. Payment goes through provider (YooMoney/Tinkoff/etc)
 * 3. Platform takes commission
 * 4. Net amount added to master's wallet (pending -> available after holdPeriod)
 * 5. Master can withdraw available balance
 */

// Master's wallet
export interface Wallet {
  masterId: string;

  // Balances (in rubles, kopecks as decimals)
  availableBalance: number;    // Can withdraw now
  pendingBalance: number;      // Waiting for hold period
  holdBalance: number;         // Frozen (disputed/refund pending)

  // Statistics
  totalEarned: number;         // All time earnings
  totalWithdrawn: number;      // All time withdrawals
  totalCommissionPaid: number; // All time commission to platform

  // Settings
  autoWithdraw: boolean;       // Auto withdraw when balance > threshold
  autoWithdrawThreshold: number;
  autoWithdrawMethod?: WithdrawalMethod;

  updatedAt: Date;
}

// Payment from client for appointment
export interface PaymentTransaction {
  id: string;

  // References
  masterId: string;
  clientId: string;
  appointmentId: string;

  // Type
  type: PaymentType;
  status: PaymentStatus;

  // Amounts
  amount: number;              // Full amount paid by client
  commission: number;          // Platform commission
  providerFee: number;         // Payment provider fee
  netAmount: number;           // amount - commission - providerFee (goes to master)

  // Payment details
  paymentMethod: PaymentMethodType;
  paymentProvider: PaymentProviderType;

  // External IDs
  externalPaymentId?: string;  // ID from payment provider

  // Dates
  createdAt: Date;
  paidAt?: Date;
  availableAt?: Date;          // When funds become available (after hold)

  // Meta
  description: string;
  receiptUrl?: string;
  refundedAmount?: number;
  refundReason?: string;
}

export type PaymentType =
  | 'prepayment'    // Предоплата при записи
  | 'full_payment'  // Полная оплата
  | 'remaining'     // Доплата после услуги
  | 'tip';          // Чаевые

export type PaymentStatus =
  | 'pending'       // Ожидает оплаты
  | 'processing'    // В обработке
  | 'succeeded'     // Успешно
  | 'failed'        // Ошибка
  | 'refunded'      // Возвращено
  | 'partially_refunded' // Частично возвращено
  | 'cancelled';    // Отменено

export type PaymentMethodType =
  | 'card'          // Банковская карта
  | 'sbp'           // СБП
  | 'yoomoney'      // Кошелёк ЮMoney
  | 'cash';         // Наличные (учёт вручную)

export type PaymentProviderType =
  | 'yoomoney'
  | 'tinkoff'
  | 'sberbank'
  | 'alfabank'
  | 'manual';       // Ручной ввод (наличные)

// Withdrawal request
export interface WithdrawalRequest {
  id: string;
  masterId: string;

  // Amount
  amount: number;
  fee: number;                 // Withdrawal fee
  netAmount: number;           // amount - fee

  // Method
  method: WithdrawalMethod;

  // Destination
  destination: WithdrawalDestination;

  // Status
  status: WithdrawalStatus;

  // Dates
  createdAt: Date;
  processedAt?: Date;
  completedAt?: Date;

  // Error info
  errorMessage?: string;

  // External
  externalTransactionId?: string;
}

export type WithdrawalMethod =
  | 'card'          // На банковскую карту
  | 'yoomoney'      // На кошелёк ЮMoney
  | 'bank_account'; // На расчётный счёт

export interface WithdrawalDestination {
  type: WithdrawalMethod;

  // For card
  cardNumber?: string;         // Masked: **** **** **** 1234
  cardHolder?: string;

  // For YooMoney
  yoomoneyAccount?: string;

  // For bank account
  bankName?: string;
  bik?: string;
  accountNumber?: string;
  corrAccount?: string;
}

export type WithdrawalStatus =
  | 'pending'       // Создан, ожидает обработки
  | 'processing'    // В обработке
  | 'completed'     // Выполнен
  | 'rejected'      // Отклонён
  | 'failed';       // Ошибка

// Platform commission settings
export interface CommissionSettings {
  // Base commission (% from each payment)
  baseCommissionPercent: number;  // e.g., 5%

  // Minimum commission per transaction
  minCommission: number;          // e.g., 10 rubles

  // Withdrawal fees
  withdrawalFees: {
    card: number;                 // Fixed fee for card withdrawal
    cardPercent: number;          // % fee for card
    yoomoney: number;             // Fixed fee for YooMoney
    yoomoneyPercent: number;      // % fee for YooMoney
    bank_account: number;         // Fixed fee for bank
    bank_accountPercent: number;  // % fee for bank
  };

  // Hold period (days) before funds become available
  holdPeriodDays: number;         // e.g., 3 days

  // Minimum withdrawal amount
  minWithdrawalAmount: number;    // e.g., 100 rubles
}

// Saved payment method (for quick checkout)
export interface SavedPaymentMethod {
  id: string;
  clientId: string;

  type: PaymentMethodType;

  // Card details (masked)
  cardLast4?: string;
  cardBrand?: string;             // Visa, Mastercard, МИР
  cardExpMonth?: number;
  cardExpYear?: number;

  // Token for recurring payments
  paymentToken?: string;

  isDefault: boolean;
  createdAt: Date;
}

// Payment link for client
export interface PaymentLink {
  id: string;
  appointmentId: string;

  amount: number;
  description: string;

  // Generated URL
  paymentUrl: string;

  // Expiration
  expiresAt: Date;

  // Status
  status: 'active' | 'paid' | 'expired' | 'cancelled';

  createdAt: Date;
}

// Daily/monthly earnings summary
export interface EarningsSummary {
  period: 'day' | 'week' | 'month' | 'year';
  startDate: Date;
  endDate: Date;

  // Totals
  grossEarnings: number;          // Before commission
  commission: number;
  netEarnings: number;            // After commission

  // Breakdown
  appointmentsCount: number;
  tipsAmount: number;
  refundsAmount: number;

  // By payment method
  byMethod: {
    card: number;
    sbp: number;
    yoomoney: number;
    cash: number;
  };
}

// Default commission settings
export const DEFAULT_COMMISSION_SETTINGS: CommissionSettings = {
  baseCommissionPercent: 5,
  minCommission: 10,
  withdrawalFees: {
    card: 50,
    cardPercent: 0,
    yoomoney: 0,
    yoomoneyPercent: 3,
    bank_account: 0,
    bank_accountPercent: 1
  },
  holdPeriodDays: 3,
  minWithdrawalAmount: 100
};
