import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, DataService, NotificationService } from '../../../core/services';
import { Appointment, AppointmentStatus, APPOINTMENT_STATUS_LABELS, APPOINTMENT_STATUS_COLORS } from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';
import { RescheduleModalComponent } from './modals/reschedule-modal.component';
import { MaterialsModalComponent } from './modals/materials-modal.component';

@Component({
  selector: 'app-appointments',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CurrencyRubPipe,
    DateFormatPipe,
    RescheduleModalComponent,
    MaterialsModalComponent
  ],
  templateUrl: './appointments.component.html',
  styleUrl: './appointments.component.scss'
})
export class AppointmentsComponent implements OnInit {
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private notificationService = inject(NotificationService);

  isLoading = signal(true);
  activeTab = signal<'pending' | 'history'>('pending');
  appointments = signal<Appointment[]>([]);
  showRescheduleModal = signal(false);
  showMaterialsModal = signal(false);
  selectedAppointment = signal<Appointment | null>(null);

  filterMonth = '';
  filterYear = '';

  months = [
    { value: '01', label: 'Январь' }, { value: '02', label: 'Февраль' },
    { value: '03', label: 'Март' }, { value: '04', label: 'Апрель' },
    { value: '05', label: 'Май' }, { value: '06', label: 'Июнь' },
    { value: '07', label: 'Июль' }, { value: '08', label: 'Август' },
    { value: '09', label: 'Сентябрь' }, { value: '10', label: 'Октябрь' },
    { value: '11', label: 'Ноябрь' }, { value: '12', label: 'Декабрь' }
  ];

  years = [2024, 2025, 2026];

  pendingAppointments = computed(() =>
    this.appointments().filter(a => a.status === 'pending')
  );

  pendingCount = computed(() => this.pendingAppointments().length);

  historyAppointments = computed(() =>
    this.appointments().filter(a => a.status !== 'pending')
  );

  filteredHistory = computed(() => {
    let result = this.historyAppointments();

    if (this.filterMonth) {
      result = result.filter(a => a.date.substring(5, 7) === this.filterMonth);
    }

    if (this.filterYear) {
      result = result.filter(a => a.date.substring(0, 4) === this.filterYear);
    }

    return result.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  });

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    this.dataService.getAppointments().subscribe(data => {
      this.appointments.set(data);
      this.isLoading.set(false);
    });
  }

  getStatusLabel(status: AppointmentStatus): string {
    return APPOINTMENT_STATUS_LABELS[status];
  }

  getStatusColor(status: AppointmentStatus): string {
    const colors: Record<string, string> = {
      pending: 'badge-warning',
      confirmed: 'badge-info',
      completed: 'badge-success',
      cancelled: 'badge-error',
      in_progress: 'badge-info'
    };
    return colors[status] || '';
  }

  confirmAppointment(apt: Appointment): void {
    this.dataService.updateAppointmentStatus(apt.id, 'confirmed').subscribe(() => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? { ...a, status: 'confirmed' } : a)
      );
      this.notificationService.success('Запись подтверждена');
    });
  }

  cancelAppointment(apt: Appointment): void {
    this.dataService.updateAppointmentStatus(apt.id, 'cancelled').subscribe(() => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? { ...a, status: 'cancelled' } : a)
      );
      this.notificationService.info('Запись отклонена');
    });
  }

  completeAppointment(apt: Appointment): void {
    this.dataService.updateAppointmentStatus(apt.id, 'completed').subscribe(() => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? { ...a, status: 'completed' } : a)
      );
      this.notificationService.success('Запись завершена');
    });
  }

  openReschedule(apt: Appointment): void {
    this.selectedAppointment.set(apt);
    this.showRescheduleModal.set(true);
  }

  openMaterials(apt: Appointment): void {
    this.selectedAppointment.set(apt);
    this.showMaterialsModal.set(true);
  }

  onReschedule(event: { date: string; time: string }): void {
    const apt = this.selectedAppointment();
    if (!apt) return;

    this.dataService.rescheduleAppointment(apt.id, event.date, event.time).subscribe(updated => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? updated : a)
      );
      this.showRescheduleModal.set(false);
      this.notificationService.success('Запись перенесена');
    });
  }

  onSaveMaterials(event: { materials: any[]; totalCost: number }): void {
    const apt = this.selectedAppointment();
    if (!apt) return;

    this.dataService.updateAppointmentMaterials(apt.id, event.materials, event.totalCost).subscribe(updated => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? updated : a)
      );
      this.showMaterialsModal.set(false);
      this.notificationService.success('Материалы сохранены');
    });
  }
}
