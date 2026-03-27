import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, DataService, NotificationService } from '../../../core/services';
import { Appointment, APPOINTMENT_STATUS_LABELS } from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-my-appointments',
  standalone: true,
  imports: [CommonModule, FormsModule, CurrencyRubPipe, DateFormatPipe],
  templateUrl: './my-appointments.component.html',
  styleUrl: './my-appointments.component.scss'
})
export class MyAppointmentsComponent implements OnInit {
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private notificationService = inject(NotificationService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  isLoading = signal(true);
  activeTab = signal<'upcoming' | 'past'>('upcoming');
  appointments = signal<Appointment[]>([]);
  reviewedAppointments = signal<Set<string>>(new Set());

  // Review modal
  showReviewModal = signal(false);
  selectedAppointment = signal<Appointment | null>(null);
  reviewRating = signal(0);
  reviewComment = '';

  upcomingAppointments = computed(() => {
    const today = new Date().toISOString().split('T')[0];
    return this.appointments()
      .filter(a => a.date >= today && a.status !== 'cancelled' && a.status !== 'completed')
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  });

  pastAppointments = computed(() => {
    const today = new Date().toISOString().split('T')[0];
    return this.appointments()
      .filter(a => {
        if (a.status === 'cancelled') return true;
        if (a.status === 'completed') return true;
        if (a.date < today) return true;
        return false;
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  });

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    const clientId = this.authService.clientData()?.id;
    if (!clientId) return;

    this.dataService.getClientAppointments(clientId).subscribe(data => {
      this.appointments.set(data);
      this.isLoading.set(false);
    });
  }

  getStatusLabel(status: string): string {
    return APPOINTMENT_STATUS_LABELS[status as keyof typeof APPOINTMENT_STATUS_LABELS] || status;
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      pending: 'badge-warning',
      confirmed: 'badge-info',
      completed: 'badge-success',
      cancelled: 'badge-error'
    };
    return classes[status] || 'badge-info';
  }

  hasReview(appointmentId: string): boolean {
    return this.reviewedAppointments().has(appointmentId);
  }

  cancelAppointment(apt: Appointment): void {
    if (!confirm('Отменить запись?')) return;

    this.dataService.updateAppointmentStatus(apt.id, 'cancelled').subscribe(() => {
      this.appointments.update(list =>
        list.map(a => a.id === apt.id ? { ...a, status: 'cancelled' } : a)
      );
      this.notificationService.info('Запись отменена');
    });
  }

  // ========== Review Modal ==========

  openReviewModal(apt: Appointment): void {
    this.selectedAppointment.set(apt);
    this.reviewRating.set(0);
    this.reviewComment = '';
    this.showReviewModal.set(true);
  }

  submitReview(): void {
    const apt = this.selectedAppointment();
    const client = this.authService.clientData();
    if (!apt || !client || this.reviewRating() === 0) return;

    this.dataService.addReview({
      masterId: apt.masterId,
      clientId: client.id,
      clientName: client.name,
      clientAvatar: client.avatar,
      appointmentId: apt.id,
      rating: this.reviewRating(),
      comment: this.reviewComment.trim()
    }).subscribe({
      next: () => {
        this.reviewedAppointments.update(set => new Set([...set, apt.id]));
        this.showReviewModal.set(false);
        this.notificationService.success('Отзыв отправлен!');
      },
      error: (err) => {
        this.notificationService.error(err.error?.detail || 'Ошибка отправки отзыва');
      }
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
}
