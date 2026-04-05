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

export function calculateNetProfit(income: number, materialsCost: number): number {
  return income - materialsCost;
}

export const TRANSACTION_STATUS_LABELS: Record<TransactionStatus, string> = {
  pending: 'В ожидании',
  paid: 'Выплачено'
};

export const TRANSACTION_STATUS_COLORS: Record<TransactionStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-green-100 text-green-800'
};
