export type TransactionStatus = 'pending' | 'paid';

export interface Transaction {
  id: string;
  masterId: string;
  appointmentId: string;
  clientName: string;
  serviceName: string;
  date: string;
  income: number;
  materialsCost: number;
  platformFee: number;
  netProfit: number;
  status: TransactionStatus;
  createdAt: Date;
}

export interface FinancialSummary {
  totalProfit: number;
  pendingAmount: number;
  lastPayout: number;
  lastPayoutDate?: string;
}

export const PLATFORM_FEE_PERCENT = 10;

export function calculateNetProfit(income: number, materialsCost: number): {
  platformFee: number;
  netProfit: number;
} {
  const platformFee = income * (PLATFORM_FEE_PERCENT / 100);
  const netProfit = income - materialsCost - platformFee;
  return { platformFee, netProfit };
}

export const TRANSACTION_STATUS_LABELS: Record<TransactionStatus, string> = {
  pending: 'В ожидании',
  paid: 'Выплачено'
};

export const TRANSACTION_STATUS_COLORS: Record<TransactionStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-green-100 text-green-800'
};
