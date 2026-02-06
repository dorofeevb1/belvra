import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, DataService, NotificationService, ThemeService } from '../../../core/services';
import { SavedCard, NotificationSettings, Review } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-client-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, DateFormatPipe],
  templateUrl: './client-profile.component.html',
  styleUrl: './client-profile.component.scss'
})
export class ClientProfileComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private notificationService = inject(NotificationService);
  protected themeService = inject(ThemeService);

  isLoading = signal(true);
  isSaving = signal(false);
  activeTab = signal<'profile' | 'cards' | 'notifications' | 'reviews'>('profile');

  // Reviews
  reviews = signal<Review[]>([]);

  // Avatar
  avatarPreview = signal<string>('');

  // Forms
  profileForm!: FormGroup;
  notificationsForm!: FormGroup;

  // Saved cards
  savedCards = signal<SavedCard[]>([]);
  cardToDelete = signal<string | null>(null);

  // Add card modal
  isAddingCard = signal(false);
  newCardNumber = '';
  newCardExpiry = '';
  newCardCvv = '';

  ngOnInit(): void {
    this.initForms();
    this.loadData();
  }

  private initForms(): void {
    this.profileForm = this.fb.group({
      name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', Validators.pattern(/^\+?[0-9]{10,15}$/)]
    });

    this.notificationsForm = this.fb.group({
      emailNotifications: [true],
      smsNotifications: [false],
      pushNotifications: [true],
      reminderHours: [24]
    });
  }

  private loadData(): void {
    const client = this.authService.clientData();
    if (!client) {
      this.isLoading.set(false);
      return;
    }

    // Load avatar
    if (client.avatar) {
      this.avatarPreview.set(client.avatar);
    }

    // Load profile
    this.profileForm.patchValue({
      name: client.name,
      email: client.email,
      phone: client.phone || ''
    });

    // Load saved cards
    if (client.savedCards) {
      this.savedCards.set(client.savedCards);
    }

    // Load notifications
    if (client.notificationSettings) {
      this.notificationsForm.patchValue(client.notificationSettings);
    }

    // Load reviews
    this.dataService.getClientReviews(client.id).subscribe(reviews => {
      this.reviews.set(reviews);
    });

    this.isLoading.set(false);
  }

  setTab(tab: 'profile' | 'cards' | 'notifications' | 'reviews'): void {
    this.activeTab.set(tab);
  }

  // Avatar methods
  onAvatarSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      this.avatarPreview.set(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  removeAvatar(): void {
    this.avatarPreview.set('');
  }

  // Card methods
  getCardBrandIcon(brand: string): string {
    switch (brand) {
      case 'visa': return 'V';
      case 'mastercard': return 'M';
      case 'mir': return 'М';
      default: return '?';
    }
  }

  getCardBrandName(brand: string): string {
    switch (brand) {
      case 'visa': return 'Visa';
      case 'mastercard': return 'Mastercard';
      case 'mir': return 'Мир';
      default: return 'Карта';
    }
  }

  setDefaultCard(cardId: string): void {
    const cards = this.savedCards().map(c => ({
      ...c,
      isDefault: c.id === cardId
    }));
    this.savedCards.set(cards);
    this.saveCards();
    this.notificationService.success('Карта установлена как основная');
  }

  confirmDeleteCard(cardId: string): void {
    this.cardToDelete.set(cardId);
  }

  cancelDeleteCard(): void {
    this.cardToDelete.set(null);
  }

  deleteCard(cardId: string): void {
    const cards = this.savedCards().filter(c => c.id !== cardId);
    // If deleted card was default, set first as default
    if (cards.length > 0 && !cards.some(c => c.isDefault)) {
      cards[0].isDefault = true;
    }
    this.savedCards.set(cards);
    this.cardToDelete.set(null);
    this.saveCards();
    this.notificationService.success('Карта удалена');
  }

  // Add card modal
  openAddCard(): void {
    this.isAddingCard.set(true);
    this.newCardNumber = '';
    this.newCardExpiry = '';
    this.newCardCvv = '';
  }

  closeAddCard(): void {
    this.isAddingCard.set(false);
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

  canAddCard(): boolean {
    const cardNum = this.newCardNumber.replace(/\s/g, '');
    if (cardNum.length !== 16 || this.newCardExpiry.length !== 5 || this.newCardCvv.length < 3) {
      return false;
    }

    // Validate expiry date
    const [monthStr, yearStr] = this.newCardExpiry.split('/');
    const month = parseInt(monthStr);
    const year = 2000 + parseInt(yearStr);
    if (month < 1 || month > 12) return false;
    const now = new Date();
    const currentMonth = now.getMonth() + 1;
    const currentYear = now.getFullYear();
    if (year < currentYear || (year === currentYear && month < currentMonth)) return false;

    return true;
  }

  addCard(): void {
    if (!this.canAddCard()) return;

    const cardNum = this.newCardNumber.replace(/\s/g, '');
    const last4 = cardNum.slice(-4);
    const brand = this.detectCardBrand(cardNum);

    // Check for duplicate card
    const isDuplicate = this.savedCards().some(c => c.last4 === last4 && c.brand === brand);
    if (isDuplicate) {
      this.notificationService.error('Такая карта уже добавлена');
      return;
    }

    const newCard: SavedCard = {
      id: 'card_' + Date.now(),
      last4,
      brand,
      expMonth: parseInt(this.newCardExpiry.split('/')[0]),
      expYear: 2000 + parseInt(this.newCardExpiry.split('/')[1]),
      isDefault: this.savedCards().length === 0
    };

    const cards = [...this.savedCards(), newCard];
    this.savedCards.set(cards);
    this.saveCards();
    this.closeAddCard();
    this.notificationService.success('Карта добавлена');
  }

  private detectCardBrand(number: string): 'visa' | 'mastercard' | 'mir' {
    if (number.startsWith('22')) return 'mir';
    if (number.startsWith('4')) return 'visa';
    if (number.startsWith('5') || number.startsWith('2')) return 'mastercard';
    return 'visa';
  }

  private saveCards(): void {
    this.authService.updateClientProfile({
      savedCards: this.savedCards()
    }).subscribe();
  }

  // Save profile
  saveProfile(): void {
    if (!this.profileForm.valid) {
      this.notificationService.error('Проверьте заполнение полей');
      return;
    }

    this.isSaving.set(true);

    const notificationSettings: NotificationSettings = {
      emailNotifications: this.notificationsForm.get('emailNotifications')?.value,
      smsNotifications: this.notificationsForm.get('smsNotifications')?.value,
      pushNotifications: this.notificationsForm.get('pushNotifications')?.value,
      reminderHours: this.notificationsForm.get('reminderHours')?.value
    };

    this.authService.updateClientProfile({
      name: this.profileForm.get('name')?.value,
      email: this.profileForm.get('email')?.value,
      phone: this.profileForm.get('phone')?.value || undefined,
      avatar: this.avatarPreview() || undefined,
      notificationSettings
    }).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.notificationService.success('Профиль сохранён');
      },
      error: () => {
        this.isSaving.set(false);
        this.notificationService.error('Ошибка сохранения');
      }
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
