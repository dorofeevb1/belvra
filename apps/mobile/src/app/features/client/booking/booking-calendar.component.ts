import { Component, inject, OnInit, signal, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService, DataService, DateService, NotificationService, WalletService } from '../../../core/services';
import { Master, BeautyService, SavedCard, PaymentMethodType } from '../../../core/models';
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
  private walletService = inject(WalletService);

  isLoading = signal(true);
  isLoadingSlots = signal(false);
  isSubmitting = signal(false);
  isProcessingPayment = signal(false);
  step = signal(1);

  master = signal<Master | null>(null);
  services = signal<BeautyService[]>([]);
  selectedService = signal<BeautyService | null>(null);
  selectedDate = signal<string>('');
  selectedTime = signal<string>('');
  availableSlots = signal<string[]>([]);
  calendarDays = signal<{ date: string; dayNum: number; isCurrentMonth: boolean; isPast: boolean; isToday: boolean }[]>([]);

  // Payment
  savedCards = signal<SavedCard[]>([]);
  selectedPaymentMethod = signal<PaymentMethodType>('card');
  selectedCardId = signal<string | null>(null);
  isAddingNewCard = signal(false);

  // New card form
  newCardNumber = '';
  newCardExpiry = '';
  newCardCvv = '';
  saveNewCard = true;

  weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  // Computed: check if payment step is needed
  // COMMENTED OUT: Online payment is disabled, cash only
  // readonly requiresPayment = computed(() => {
  //   const master = this.master();
  //   if (!master?.paymentSettings) return false;
  //   return master.paymentSettings.onlinePaymentsEnabled && master.paymentSettings.prepaymentRequired;
  // });
  readonly requiresPayment = computed(() => false); // Cash payment only

  // Computed: total steps
  readonly totalSteps = computed(() => this.requiresPayment() ? 4 : 3);

  // Computed: prepayment amount
  readonly prepaymentAmount = computed(() => {
    const master = this.master();
    const service = this.selectedService();
    if (!master?.paymentSettings || !service) return 0;

    const percent = master.paymentSettings.prepaymentPercent || 100;
    return Math.round(service.price * percent / 100);
  });

  // Computed: accepted payment methods
  readonly acceptedMethods = computed(() => {
    const master = this.master();
    if (!master?.paymentSettings) return { card: true, sbp: false, yoomoney: false };
    return master.paymentSettings.acceptedMethods;
  });

  ngOnInit(): void {
    this.calendarDays.set(this.dateService.generateCalendarMonth());
    this.loadData();
    this.loadSavedCards();
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

  private loadSavedCards(): void {
    const client = this.authService.clientData();
    if (client?.savedCards) {
      this.savedCards.set(client.savedCards);
      const defaultCard = client.savedCards.find(c => c.isDefault);
      if (defaultCard) {
        this.selectedCardId.set(defaultCard.id);
      }
    }
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
    this.dataService.getAvailableSlotsForService(masterId, service.id, date).subscribe(slots => {
      this.availableSlots.set(slots);
      this.isLoadingSlots.set(false);
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

  // Payment methods
  selectPaymentMethod(method: PaymentMethodType): void {
    this.selectedPaymentMethod.set(method);
    if (method !== 'card') {
      this.selectedCardId.set(null);
      this.isAddingNewCard.set(false);
    }
  }

  selectCard(cardId: string): void {
    this.selectedCardId.set(cardId);
    this.isAddingNewCard.set(false);
  }

  startAddNewCard(): void {
    this.isAddingNewCard.set(true);
    this.selectedCardId.set(null);
    this.newCardNumber = '';
    this.newCardExpiry = '';
    this.newCardCvv = '';
  }

  cancelAddNewCard(): void {
    this.isAddingNewCard.set(false);
    const cards = this.savedCards();
    if (cards.length > 0) {
      const defaultCard = cards.find(c => c.isDefault) || cards[0];
      this.selectedCardId.set(defaultCard.id);
    }
  }

  getCardBrandIcon(brand: string): string {
    switch (brand) {
      case 'visa': return 'V';
      case 'mastercard': return 'M';
      case 'mir': return 'М';
      default: return '?';
    }
  }

  getSelectedCardLast4(): string {
    const cardId = this.selectedCardId();
    if (!cardId) return '';
    const card = this.savedCards().find(c => c.id === cardId);
    return card?.last4 || '';
  }

  formatCardNumber(event: Event): void {
    const input = event.target as HTMLInputElement;
    let value = input.value.replace(/\D/g, '');
    value = value.substring(0, 16);
    const parts = value.match(/.{1,4}/g);
    this.newCardNumber = parts ? parts.join(' ') : value;
  }

  formatCardExpiry(event: Event): void {
    const input = event.target as HTMLInputElement;
    let value = input.value.replace(/\D/g, '');
    value = value.substring(0, 4);
    if (value.length >= 2) {
      this.newCardExpiry = value.substring(0, 2) + '/' + value.substring(2);
    } else {
      this.newCardExpiry = value;
    }
  }

  canProceedToPayment(): boolean {
    const method = this.selectedPaymentMethod();
    if (method !== 'card') return true;

    if (this.isAddingNewCard()) {
      const cardNum = this.newCardNumber.replace(/\s/g, '');
      return cardNum.length === 16 && this.newCardExpiry.length === 5 && this.newCardCvv.length >= 3;
    }

    return !!this.selectedCardId();
  }

  async processPayment(): Promise<void> {
    this.isProcessingPayment.set(true);

    // Simulate payment processing
    await new Promise(resolve => setTimeout(resolve, 2000));

    // If adding new card and save option checked
    if (this.isAddingNewCard() && this.saveNewCard) {
      const cardNum = this.newCardNumber.replace(/\s/g, '');
      const newCard: SavedCard = {
        id: 'card_' + Date.now(),
        last4: cardNum.slice(-4),
        brand: this.detectCardBrand(cardNum),
        expMonth: parseInt(this.newCardExpiry.split('/')[0]),
        expYear: 2000 + parseInt(this.newCardExpiry.split('/')[1]),
        isDefault: this.savedCards().length === 0
      };

      const updatedCards = [...this.savedCards(), newCard];
      this.savedCards.set(updatedCards);
      // In real app, save to backend
    }

    this.isProcessingPayment.set(false);
    this.confirmBooking();
  }

  private detectCardBrand(number: string): 'visa' | 'mastercard' | 'mir' {
    if (number.startsWith('4')) return 'visa';
    if (number.startsWith('5') || number.startsWith('2')) return 'mastercard';
    if (number.startsWith('22')) return 'mir';
    return 'visa';
  }

  confirmBooking(): void {
    const client = this.authService.clientData();
    const service = this.selectedService();
    const master = this.master();

    if (!client || !service || !master) return;

    this.isSubmitting.set(true);

    const endTime = this.dateService.addTime(this.selectedTime(), service.duration);
    const isPaid = this.requiresPayment();

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
      prepaid: isPaid ? this.prepaymentAmount() : 0,
      paymentMethod: isPaid ? this.selectedPaymentMethod() : undefined
    }).subscribe(() => {
      this.isSubmitting.set(false);

      if (isPaid) {
        this.notificationService.success(`Оплачено ${this.prepaymentAmount()} ₽. Запись отправлена!`);
      } else {
        this.notificationService.success('Заявка на запись отправлена!');
      }

      this.router.navigate(['/client/my-appointments']);
    });
  }
}
