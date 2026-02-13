import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, DataService, NotificationService, WalletService } from '../../../core/services';
import { Appointment, APPOINTMENT_STATUS_LABELS, PaymentType, Review } from '../../../core/models';
import { CurrencyRubPipe } from '../../../shared/pipes/currency-rub.pipe';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';
import { environment } from '../../../../environments/environment';

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
  private walletService = inject(WalletService);
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
  isEditingReview = signal(false);
  editingReviewId = signal<string | null>(null);

  // Client reviews map: appointmentId -> Review
  clientReviews = signal<Map<string, Review>>(new Map());

  // Payment modal
  showPaymentModal = signal(false);
  paymentAppointment = signal<Appointment | null>(null);
  paymentType = signal<PaymentType>('full_payment');
  paymentMethod = signal<'bank_card' | 'sbp'>('bank_card');
  paymentAmount = signal(0);
  isProcessingPayment = signal(false);
  paymentUrl = signal<string | null>(null);

  upcomingAppointments = computed(() => {
    const today = new Date().toISOString().split('T')[0];
    return this.appointments()
      .filter(a => a.date >= today && a.status !== 'cancelled' && a.status !== 'completed')
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  });

  pastAppointments = computed(() => {
    const today = new Date().toISOString().split('T')[0];
    return this.appointments()
      .filter(a => a.date < today || a.status === 'completed' || a.status === 'cancelled')
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  });

  ngOnInit(): void {
    this.loadData();
    this.handlePaymentReturn();
  }

  private handlePaymentReturn(): void {
    this.route.queryParams.subscribe(params => {
      const paymentStatus = params['payment'];
      const testPayment = params['test_payment'];
      const paymentId = params['payment_id'];

      if (paymentStatus === 'success' && testPayment && paymentId) {
        // Confirm test payment
        this.walletService.confirmTestPayment(paymentId).subscribe({
          next: () => {
            this.notificationService.success('Платёж подтверждён!');
            this.loadData();
            // Clear query params
            this.router.navigate([], {
              relativeTo: this.route,
              queryParams: {},
              replaceUrl: true
            });
          },
          error: () => {
            this.notificationService.error('Ошибка подтверждения платежа');
            this.router.navigate([], {
              relativeTo: this.route,
              queryParams: {},
              replaceUrl: true
            });
          }
        });
      } else if (paymentStatus === 'success') {
        this.notificationService.success('Платёж обрабатывается');
        this.loadData();
        // Clear query params
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {},
          replaceUrl: true
        });
      }
    });
  }

  private loadData(): void {
    const clientId = this.authService.clientData()?.id;
    if (!clientId) return;

    this.dataService.getClientAppointments(clientId).subscribe(data => {
      this.appointments.set(data);
      this.isLoading.set(false);
    });

    this.dataService.getClientReviews().subscribe(reviews => {
      const reviewMap = new Map<string, Review>();
      reviews.forEach(r => reviewMap.set(r.appointmentId, r));
      this.clientReviews.set(reviewMap);
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

  getPaymentStatusLabel(apt: Appointment): string {
    if (apt.paymentStatus === 'paid') return 'Оплачено';
    if (apt.paymentStatus === 'refunded') return 'Возврат';
    if (apt.prepaid && apt.prepaid > 0) return `Предоплата ${apt.prepaid} ₽`;
    return 'Не оплачено';
  }

  getPaymentStatusClass(apt: Appointment): string {
    if (apt.paymentStatus === 'paid') return 'payment-paid';
    if (apt.paymentStatus === 'refunded') return 'payment-refunded';
    if (apt.prepaid && apt.prepaid > 0) return 'payment-partial';
    return 'payment-pending';
  }

  canPay(apt: Appointment): boolean {
    return (
      (apt.status === 'pending' || apt.status === 'confirmed') &&
      apt.paymentStatus !== 'paid'
    );
  }

  getRemainingAmount(apt: Appointment): number {
    const prepaid = apt.prepaid || 0;
    return apt.price - prepaid;
  }

  hasReview(appointmentId: string): boolean {
    return this.reviewedAppointments().has(appointmentId) || this.clientReviews().has(appointmentId);
  }

  getReview(appointmentId: string): Review | undefined {
    return this.clientReviews().get(appointmentId);
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
    this.isEditingReview.set(false);
    this.editingReviewId.set(null);
    this.showReviewModal.set(true);
  }

  submitReview(): void {
    const apt = this.selectedAppointment();
    const client = this.authService.clientData();
    if (!apt || !client || this.reviewRating() === 0) return;

    if (this.isEditingReview() && this.editingReviewId()) {
      this.dataService.updateReview(this.editingReviewId()!, {
        rating: this.reviewRating(),
        comment: this.reviewComment.trim()
      }).subscribe(() => {
        this.showReviewModal.set(false);
        this.isEditingReview.set(false);
        this.editingReviewId.set(null);
        this.notificationService.success('Отзыв обновлён!');
        this.loadData();
      });
      return;
    }

    this.dataService.addReview({
      masterId: apt.masterId,
      clientId: client.id,
      clientName: client.name,
      clientAvatar: client.avatar,
      appointmentId: apt.id,
      rating: this.reviewRating(),
      comment: this.reviewComment.trim()
    }).subscribe(() => {
      this.reviewedAppointments.update(set => new Set([...set, apt.id]));
      this.showReviewModal.set(false);
      this.notificationService.success('Отзыв отправлен!');
      this.loadData();
    });
  }

  editReview(apt: Appointment): void {
    const review = this.getReview(apt.id);
    if (!review) return;

    this.selectedAppointment.set(apt);
    this.reviewRating.set(review.rating);
    this.reviewComment = review.comment;
    this.isEditingReview.set(true);
    this.editingReviewId.set(review.id);
    this.showReviewModal.set(true);
  }

  deleteReview(apt: Appointment): void {
    const review = this.getReview(apt.id);
    if (!review) return;
    if (!confirm('Удалить отзыв?')) return;

    this.dataService.deleteReview(review.id).subscribe(() => {
      this.clientReviews.update(map => {
        const newMap = new Map(map);
        newMap.delete(apt.id);
        return newMap;
      });
      this.notificationService.success('Отзыв удалён');
    });
  }

  // ========== Payment Modal ==========

  openPaymentModal(apt: Appointment): void {
    this.paymentAppointment.set(apt);
    this.paymentUrl.set(null);
    this.paymentMethod.set('bank_card');

    const remaining = this.getRemainingAmount(apt);

    // Если уже была предоплата, показываем доплату
    if (apt.prepaid && apt.prepaid > 0) {
      this.paymentType.set('remaining');
      this.paymentAmount.set(remaining);
    } else {
      // Иначе предлагаем полную оплату по умолчанию
      this.paymentType.set('full_payment');
      this.paymentAmount.set(apt.price);
    }

    this.showPaymentModal.set(true);
  }

  closePaymentModal(): void {
    this.showPaymentModal.set(false);
    this.paymentAppointment.set(null);
    this.paymentUrl.set(null);
  }

  onPaymentTypeChange(): void {
    const apt = this.paymentAppointment();
    if (!apt) return;

    const type = this.paymentType();
    const remaining = this.getRemainingAmount(apt);

    if (type === 'full_payment') {
      this.paymentAmount.set(remaining);
    } else if (type === 'prepayment') {
      // 20% предоплата
      this.paymentAmount.set(Math.round(remaining * 0.2));
    } else if (type === 'remaining') {
      this.paymentAmount.set(remaining);
    }
  }

  processPayment(): void {
    const apt = this.paymentAppointment();
    if (!apt || this.paymentAmount() <= 0) return;

    this.isProcessingPayment.set(true);

    const returnUrl = `${window.location.origin}/client/my-appointments?payment=success&appointment=${apt.id}`;

    this.walletService.createPayment(
      apt.id,
      this.paymentType(),
      this.paymentAmount(),
      returnUrl,
      this.paymentMethod()
    ).subscribe({
      next: (payment) => {
        this.isProcessingPayment.set(false);

        if (payment.confirmationUrl) {
          this.paymentUrl.set(payment.confirmationUrl);
          this.notificationService.success('Платёж создан! Перейдите по ссылке для оплаты.');
        } else {
          this.notificationService.info('Платёж создан, ожидает обработки');
          this.closePaymentModal();
        }
      },
      error: (err) => {
        this.isProcessingPayment.set(false);
        this.notificationService.error(err.error?.detail || 'Ошибка создания платежа');
      }
    });
  }

  goToPayment(): void {
    const url = this.paymentUrl();
    if (url) {
      window.open(url, '_blank');
      this.closePaymentModal();
    }
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
