import { UsedMaterial } from './service.model';
import { PaymentMethodType } from './wallet.model';

export type AppointmentStatus = 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'rescheduled' | 'no_show';

export interface Appointment {
  id: string;
  masterId: string;
  clientId: string;
  serviceId: string;
  serviceName: string;
  clientName: string;
  clientPhone: string;
  date: string;
  startTime: string;
  endTime: string;
  duration: number;
  price: number;
  status: AppointmentStatus;
  notes?: string;
  usedMaterials?: UsedMaterial[];
  materialsCost?: number;
  // Payment
  prepaid?: number;
  paymentMethod?: PaymentMethodType;
  paymentStatus?: 'pending' | 'paid' | 'refunded';
  createdAt: Date;
  updatedAt: Date;
}

export interface TimeSlot {
  time: string;
  available: boolean;
}

export interface DayAppointments {
  date: string;
  appointments: Appointment[];
}

export const APPOINTMENT_STATUS_LABELS: Record<AppointmentStatus, string> = {
  pending: 'Ожидает подтверждения',
  confirmed: 'Подтверждена',
  in_progress: 'В процессе',
  completed: 'Завершена',
  cancelled: 'Отменена',
  rescheduled: 'Перенесена',
  no_show: 'Клиент не пришёл'
};

export const APPOINTMENT_STATUS_COLORS: Record<AppointmentStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  rescheduled: 'bg-orange-100 text-orange-800',
  no_show: 'bg-gray-100 text-gray-800'
};
