import { Component, inject, OnInit, signal, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, DataService, DateService, NotificationService } from '../../../core/services';
import { Master, BeautyService } from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';

@Component({
  selector: 'app-booking-calendar',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyRubPipe],
  templateUrl: './booking-calendar.component.html',
  styleUrl: './booking-calendar.component.scss'
})
export class BookingCalendarComponent implements OnInit {
  masterId = input<string>('');

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private dateService = inject(DateService);
  private notificationService = inject(NotificationService);

  isLoading = signal(true);
  isLoadingSlots = signal(false);
  isSubmitting = signal(false);
  step = signal(1);

  master = signal<Master | null>(null);
  services = signal<BeautyService[]>([]);
  selectedService = signal<BeautyService | null>(null);
  selectedDate = signal<string>('');
  selectedTime = signal<string>('');
  availableSlots = signal<string[]>([]);
  calendarDays = signal<{ date: string; dayNum: number; isCurrentMonth: boolean; isPast: boolean; isToday: boolean }[]>([]);

  weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  // 3 steps: service -> date/time -> confirm
  readonly totalSteps = computed(() => 3);

  ngOnInit(): void {
    this.calendarDays.set(this.dateService.generateCalendarMonth());
    this.loadData();
  }

  private loadData(): void {
    const masterId = this.masterId();
    if (!masterId) return;

    this.dataService.getMasterById(masterId).subscribe(master => {
      if (master) {
        this.master.set(master);
      }
    });

    this.dataService.getServices(masterId).subscribe(services => {
      this.services.set(services);

      const serviceId = this.route.snapshot.queryParams['serviceId'];
      if (serviceId) {
        const service = services.find(s => s.id === serviceId);
        if (service) {
          this.selectedService.set(service);
          this.step.set(2);
        }
      }

      this.isLoading.set(false);
    });
  }

  selectService(service: BeautyService): void {
    this.selectedService.set(service);
  }

  selectDate(date: string): void {
    this.selectedDate.set(date);
    this.selectedTime.set('');
    this.loadSlots(date);
  }

  private loadSlots(date: string): void {
    const masterId = this.masterId();
    const service = this.selectedService();
    if (!masterId || !service) return;

    this.isLoadingSlots.set(true);
    this.dataService.getAvailableSlotsForService(masterId, service.id, date).subscribe({
      next: (slots) => {
        const filteredSlots = this.dateService.filterPastSlots(date, slots);
        this.availableSlots.set(filteredSlots);
        this.isLoadingSlots.set(false);
      },
      error: () => {
        this.availableSlots.set([]);
        this.isLoadingSlots.set(false);
        this.notificationService.error('Не удалось загрузить доступные слоты');
      }
    });
  }

  nextStep(): void {
    const total = this.totalSteps();
    if (this.step() < total) {
      this.step.update(s => s + 1);
    }
  }

  prevStep(): void {
    if (this.step() > 1) {
      this.step.update(s => s - 1);
    }
  }

  goBack(): void {
    this.router.navigate(['/client/master', this.masterId()]);
  }

  formatDate(dateStr: string): string {
    return this.dateService.formatDateLong(dateStr);
  }

  confirmBooking(): void {
    const client = this.authService.clientData();
    const service = this.selectedService();
    const master = this.master();

    if (!client || !service || !master) return;

    this.isSubmitting.set(true);

    const endTime = this.dateService.addTime(this.selectedTime(), service.duration);

    this.dataService.createAppointment({
      masterId: master.id,
      clientId: client.id,
      serviceId: service.id,
      serviceName: service.name,
      clientName: client.name,
      clientPhone: client.phone || '',
      date: this.selectedDate(),
      startTime: this.selectedTime(),
      endTime,
      duration: service.duration,
      price: service.price,
      status: 'pending',
    }).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.notificationService.success('Заявка на запись отправлена!');
        this.router.navigate(['/client/my-appointments']);
      },
      error: (err) => {
        this.isSubmitting.set(false);
        const detail = err.error?.detail || err.error?.non_field_errors?.[0] || 'Не удалось создать запись';
        this.notificationService.error(typeof detail === 'string' ? detail : 'Не удалось создать запись');
      }
    });
  }
}
