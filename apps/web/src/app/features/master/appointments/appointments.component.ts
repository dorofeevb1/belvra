import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, filter } from 'rxjs/operators';
import { AuthService, DataService, ApiService, NotificationService } from '../../../core/services';
import { Appointment, AppointmentStatus, APPOINTMENT_STATUS_LABELS, APPOINTMENT_STATUS_COLORS, BeautyService } from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';
import { RescheduleModalComponent } from './modals/reschedule-modal.component';
import { MaterialsModalComponent } from './modals/materials-modal.component';

interface ClientSearchResult {
  id: string;
  name: string;
  first_name: string;
  last_name: string;
  email: string;
  visits: number;
}

interface ManualBookingForm {
  client_id: string | null;
  client_name: string;
  client_surname: string;
  master_service_id: string;
  date: string;
  start_time: string;
  price: number | null;
  notes: string;
}

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
  private apiService = inject(ApiService);
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
    this.appointments().filter(a => a.status === 'pending' || a.status === 'confirmed')
  );

  pendingCount = computed(() => this.pendingAppointments().length);

  // Manual booking modal
  showManualModal = signal(false);
  manualSaving = signal(false);
  clientSearchResults = signal<ClientSearchResult[]>([]);
  selectedClient = signal<ClientSearchResult | null>(null);
  masterServices = signal<BeautyService[]>([]);
  selectedServiceDuration = signal<number | null>(null);
  showServiceDropdown = signal(false);
  clientSearchInput$ = new Subject<string>();
  clientSearchQuery = '';

  manualForm: ManualBookingForm = {
    client_id: null,
    client_name: '',
    client_surname: '',
    master_service_id: '',
    date: '',
    start_time: '',
    price: null,
    notes: ''
  };

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
    this.setupClientSearch();
  }

  private loadData(): void {
    this.dataService.getAppointments(undefined, 'master').subscribe(data => {
      this.appointments.set(data);
      this.isLoading.set(false);
    });
  }

  private setupClientSearch(): void {
    this.clientSearchInput$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      filter(query => query.length >= 2),
      switchMap(query =>
        this.apiService.get<ClientSearchResult[]>('/appointments/my-clients/', { search: query })
      )
    ).subscribe({
      next: results => this.clientSearchResults.set(results),
      error: () => this.clientSearchResults.set([])
    });
  }

  openManualModal(): void {
    this.resetManualForm();
    this.showManualModal.set(true);

    const masterId = this.authService.masterApiId();
    if (masterId) {
      this.dataService.getServices(masterId).subscribe({
        next: services => this.masterServices.set(services),
        error: () => this.notificationService.error('Не удалось загрузить услуги')
      });
    }
  }

  closeManualModal(): void {
    this.showManualModal.set(false);
    this.resetManualForm();
  }

  onClientSearch(query: string): void {
    this.clientSearchQuery = query;
    if (query.length >= 2) {
      this.clientSearchInput$.next(query);
    } else {
      this.clientSearchResults.set([]);
    }
  }

  selectClient(client: ClientSearchResult): void {
    this.selectedClient.set(client);
    this.manualForm.client_id = client.id;
    this.manualForm.client_name = client.first_name || client.name;
    this.manualForm.client_surname = client.last_name || '';
    this.clientSearchResults.set([]);
    this.clientSearchQuery = '';
  }

  clearClient(): void {
    this.selectedClient.set(null);
    this.manualForm.client_id = null;
    this.manualForm.client_name = '';
    this.manualForm.client_surname = '';
    this.clientSearchQuery = '';
  }

  getSelectedServiceName(): string {
    const service = this.masterServices().find(s => s.id === this.manualForm.master_service_id);
    return service?.name || '';
  }

  selectService(service: any): void {
    this.manualForm.master_service_id = service.id;
    this.manualForm.price = service.price;
    this.selectedServiceDuration.set(service.duration);
    this.showServiceDropdown.set(false);
  }

  onServiceChange(): void {
    const service = this.masterServices().find(s => s.id === this.manualForm.master_service_id);
    if (service) {
      this.manualForm.price = service.price;
      this.selectedServiceDuration.set(service.duration);
    } else {
      this.manualForm.price = null;
      this.selectedServiceDuration.set(null);
    }
  }

  saveManualBooking(): void {
    if (!this.manualForm.client_name || !this.manualForm.master_service_id || !this.manualForm.date || !this.manualForm.start_time) {
      this.notificationService.error('Заполните обязательные поля');
      return;
    }

    this.manualSaving.set(true);

    const body: any = {
      client_name: this.manualForm.client_name,
      master_service_id: this.manualForm.master_service_id,
      date: this.manualForm.date,
      start_time: this.manualForm.start_time
    };

    if (this.manualForm.client_id) body.client_id = this.manualForm.client_id;
    if (this.manualForm.client_surname) body.client_surname = this.manualForm.client_surname;
    if (this.manualForm.price !== null) body.price = this.manualForm.price;
    if (this.manualForm.notes) body.notes = this.manualForm.notes;

    this.apiService.post('/appointments/manual-create/', body).subscribe({
      next: () => {
        this.notificationService.success('Запись создана');
        this.closeManualModal();
        this.loadData();
      },
      error: () => {
        this.notificationService.error('Ошибка при создании записи');
        this.manualSaving.set(false);
      }
    });
  }

  private resetManualForm(): void {
    this.manualForm = {
      client_id: null,
      client_name: '',
      client_surname: '',
      master_service_id: '',
      date: '',
      start_time: '',
      price: null,
      notes: ''
    };
    this.selectedClient.set(null);
    this.selectedServiceDuration.set(null);
    this.clientSearchResults.set([]);
    this.clientSearchQuery = '';
    this.manualSaving.set(false);
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
    this.dataService.updateAppointmentStatus(apt.id, 'confirmed').subscribe({
      next: () => {
        this.appointments.update(list =>
          list.map(a => a.id === apt.id ? { ...a, status: 'confirmed' } : a)
        );
        this.notificationService.success('Запись подтверждена');
      },
      error: () => {
        this.notificationService.error('Ошибка при подтверждении записи');
      }
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

  /** Сохраняет материалы, мержит частичный ответ с существующей записью */
  onSaveMaterials(event: { materials: any[]; totalCost: number }): void {
    const apt = this.selectedAppointment();
    if (!apt) return;

    this.dataService.updateAppointmentMaterials(apt.id, event.materials, event.totalCost).subscribe(updated => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? { ...a, ...updated } : a)
      );
      this.showMaterialsModal.set(false);
      this.notificationService.success('Материалы сохранены');
    });
  }
}
