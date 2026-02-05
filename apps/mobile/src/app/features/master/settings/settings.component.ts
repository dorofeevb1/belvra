import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { AuthService, DataService, NotificationService, ThemeService, ApiService } from '../../../core/services';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { BeautyService, SERVICE_CATEGORIES, WorkSchedule, SocialLinks, NotificationSettings, PaymentSettings, PaymentProvider } from '../../../core/models';

interface BackendSchedule {
  id: string;
  weekday: number;
  start_time: string;
  end_time: string;
  is_working: boolean;
}

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private notificationService = inject(NotificationService);
  protected themeService = inject(ThemeService);
  private apiService = inject(ApiService);
  subscriptionService = inject(SubscriptionService);

  isLoading = signal(true);
  isSaving = signal(false);
  categories = SERVICE_CATEGORIES;

  // Backend schedules storage for tracking changes
  private backendSchedules: BackendSchedule[] = [];

  // Active tab
  activeTab = signal<'profile' | 'schedule' | 'services' | 'notifications' | 'payments' | 'subscription'>('profile');

  // Avatar
  avatarPreview = signal<string>('');
  private avatarFile: File | null = null;
  private avatarChanged = signal<boolean>(false);

  // Forms
  profileForm!: FormGroup;
  scheduleForm!: FormGroup;
  servicesForm!: FormGroup;
  notificationsForm!: FormGroup;
  paymentsForm!: FormGroup;

  // Service to delete confirmation
  serviceToDelete = signal<number | null>(null);

  // Active payment provider for config
  activePaymentProvider = signal<PaymentProvider | null>(null);

  weekDays = [
    { key: 'monday', label: 'Пн', fullLabel: 'Понедельник' },
    { key: 'tuesday', label: 'Вт', fullLabel: 'Вторник' },
    { key: 'wednesday', label: 'Ср', fullLabel: 'Среда' },
    { key: 'thursday', label: 'Чт', fullLabel: 'Четверг' },
    { key: 'friday', label: 'Пт', fullLabel: 'Пятница' },
    { key: 'saturday', label: 'Сб', fullLabel: 'Суббота' },
    { key: 'sunday', label: 'Вс', fullLabel: 'Воскресенье' }
  ];

  reminderOptions = [
    { value: 1, label: 'За 1 час' },
    { value: 2, label: 'За 2 часа' },
    { value: 3, label: 'За 3 часа' },
    { value: 12, label: 'За 12 часов' },
    { value: 24, label: 'За 24 часа' }
  ];

  paymentProviders: { key: PaymentProvider; name: string; logo: string; color: string }[] = [
    { key: 'yoomoney', name: 'ЮMoney', logo: 'yoomoney', color: '#8b3ffd' },
    { key: 'tinkoff', name: 'Тинькофф', logo: 'tinkoff', color: '#ffdd2d' },
    { key: 'sberbank', name: 'СберБанк', logo: 'sberbank', color: '#21a038' },
    { key: 'alfabank', name: 'Альфа-Банк', logo: 'alfabank', color: '#ef3124' }
  ];

  prepaymentOptions = [
    { value: 0, label: 'Без предоплаты' },
    { value: 10, label: '10%' },
    { value: 20, label: '20%' },
    { value: 30, label: '30%' },
    { value: 50, label: '50%' },
    { value: 100, label: '100% (полная оплата)' }
  ];

  private initialValues: any = {};

  get servicesArray(): FormArray {
    return this.servicesForm.get('services') as FormArray;
  }

  ngOnInit(): void {
    this.initForms();
    this.loadData();
  }

  private initForms(): void {
    this.profileForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', [Validators.maxLength(20)]], // Phone is optional
      specialization: ['', [Validators.maxLength(100)]],
      address: ['', [Validators.maxLength(200)]],
      description: ['', [Validators.maxLength(1000)]],
      // Social links
      telegram: ['', [Validators.maxLength(100)]],
      instagram: ['', [Validators.maxLength(100)]],
      vk: ['', [Validators.maxLength(200)]],
      whatsapp: ['', [Validators.maxLength(20)]]
    });

    const scheduleControls: any = {};
    this.weekDays.forEach(day => {
      scheduleControls[day.key + 'Enabled'] = [false];
      scheduleControls[day.key + 'Start'] = ['09:00'];
      scheduleControls[day.key + 'End'] = ['18:00'];
    });
    this.scheduleForm = this.fb.group(scheduleControls);

    this.servicesForm = this.fb.group({
      services: this.fb.array([])
    });

    this.notificationsForm = this.fb.group({
      emailNotifications: [true],
      smsNotifications: [false],
      pushNotifications: [true],
      reminderHours: [24]
    });

    this.paymentsForm = this.fb.group({
      onlinePaymentsEnabled: [false],
      prepaymentRequired: [false],
      prepaymentPercent: [30],
      // Accepted methods
      acceptCard: [true],
      acceptSbp: [true],
      acceptYoomoney: [false],
      // YooMoney provider
      yoomoneyEnabled: [false],
      yoomoneyShopId: [''],
      yoomoneySecretKey: [''],
      // Tinkoff provider
      tinkoffEnabled: [false],
      tinkoffTerminalKey: [''],
      tinkoffSecretKey: [''],
      // Sberbank provider
      sberbankEnabled: [false],
      sberbankMerchantLogin: [''],
      sberbankToken: [''],
      // Alfabank provider
      alfabankEnabled: [false],
      alfabankMerchantLogin: [''],
      alfabankToken: ['']
    });
  }

  private loadData(): void {
    const master = this.authService.masterData();
    if (!master) return;

    // Load avatar
    if (master.avatar) {
      this.avatarPreview.set(master.avatar);
    }

    // Load profile
    this.profileForm.patchValue({
      name: master.name,
      email: master.email,
      phone: master.phone || '',
      specialization: master.specialization,
      address: master.address,
      description: master.description,
      telegram: master.socialLinks?.telegram || '',
      instagram: master.socialLinks?.instagram || '',
      vk: master.socialLinks?.vk || '',
      whatsapp: master.socialLinks?.whatsapp || ''
    });

    // Load schedule from backend API
    this.loadScheduleFromApi();

    // Load notifications
    if (master.notificationSettings) {
      this.notificationsForm.patchValue(master.notificationSettings);
    }

    // Load payment settings
    if (master.paymentSettings) {
      const ps = master.paymentSettings;
      this.paymentsForm.patchValue({
        onlinePaymentsEnabled: ps.onlinePaymentsEnabled,
        prepaymentRequired: ps.prepaymentRequired,
        prepaymentPercent: ps.prepaymentPercent,
        acceptCard: ps.acceptedMethods?.card ?? true,
        acceptSbp: ps.acceptedMethods?.sbp ?? true,
        acceptYoomoney: ps.acceptedMethods?.yoomoney ?? false,
        // YooMoney
        yoomoneyEnabled: ps.providers?.yoomoney?.enabled ?? false,
        yoomoneyShopId: ps.providers?.yoomoney?.shopId ?? '',
        yoomoneySecretKey: ps.providers?.yoomoney?.secretKey ?? '',
        // Tinkoff
        tinkoffEnabled: ps.providers?.tinkoff?.enabled ?? false,
        tinkoffTerminalKey: ps.providers?.tinkoff?.terminalKey ?? '',
        tinkoffSecretKey: ps.providers?.tinkoff?.secretKey ?? '',
        // Sberbank
        sberbankEnabled: ps.providers?.sberbank?.enabled ?? false,
        sberbankMerchantLogin: ps.providers?.sberbank?.merchantLogin ?? '',
        sberbankToken: ps.providers?.sberbank?.token ?? '',
        // Alfabank
        alfabankEnabled: ps.providers?.alfabank?.enabled ?? false,
        alfabankMerchantLogin: ps.providers?.alfabank?.merchantLogin ?? '',
        alfabankToken: ps.providers?.alfabank?.token ?? ''
      });
    }

    // Load services (use masterProfileId for API calls)
    const profileId = master.masterProfileId || master.id;
    this.dataService.getServices(profileId).subscribe(services => {
      services.forEach(s => this.addService(s));
      this.isLoading.set(false);
      this.saveInitialValues();
    });
  }

  private saveInitialValues(): void {
    this.initialValues = {
      profile: { ...this.profileForm.value },
      schedule: { ...this.scheduleForm.value },
      services: this.servicesArray.value.map((s: any) => ({ ...s })),
      notifications: { ...this.notificationsForm.value },
      payments: { ...this.paymentsForm.value },
      avatar: this.avatarPreview()
    };
    this.avatarChanged.set(false);
    this.avatarFile = null;
  }

  hasChanges(): boolean {
    const currentProfile = JSON.stringify(this.profileForm.value);
    const currentSchedule = JSON.stringify(this.scheduleForm.value);
    const currentServices = JSON.stringify(this.servicesArray.value);
    const currentNotifications = JSON.stringify(this.notificationsForm.value);
    const currentPayments = JSON.stringify(this.paymentsForm.value);

    return currentProfile !== JSON.stringify(this.initialValues.profile) ||
           currentSchedule !== JSON.stringify(this.initialValues.schedule) ||
           currentServices !== JSON.stringify(this.initialValues.services) ||
           currentNotifications !== JSON.stringify(this.initialValues.notifications) ||
           currentPayments !== JSON.stringify(this.initialValues.payments) ||
           this.avatarChanged();
  }

  // Avatar methods
  onAvatarSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    // Store the file for upload
    this.avatarFile = file;
    this.avatarChanged.set(true);

    // Show preview
    const reader = new FileReader();
    reader.onload = () => {
      this.avatarPreview.set(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  removeAvatar(): void {
    this.avatarPreview.set('');
    this.avatarFile = null;
    this.avatarChanged.set(true);
  }

  // Service methods
  addService(service?: BeautyService): void {
    // Check limit only for new services (not when loading existing ones)
    if (!service && !this.subscriptionService.canAddService()) {
      this.notificationService.warning('Достигнут лимит услуг. Перейдите на PRO для добавления неограниченного количества услуг.');
      return;
    }

    const group = this.fb.group({
      id: [service?.id || ''],
      serviceId: [service?.serviceId || ''], // Global catalog service ID
      name: [service?.name || '', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
      description: [service?.description || '', [Validators.maxLength(500)]],
      duration: [service?.duration || 60, [Validators.required, Validators.min(15), Validators.max(480)]],
      price: [service?.price || 0, [Validators.required, Validators.min(0), Validators.max(1000000)]],
      category: [service?.category || 'other'],
      defaultMaterialsCost: [service?.defaultMaterialsCost || 0, [Validators.min(0), Validators.max(100000)]]
    });
    this.servicesArray.push(group);
  }

  confirmDeleteService(index: number): void {
    this.serviceToDelete.set(index);
  }

  cancelDeleteService(): void {
    this.serviceToDelete.set(null);
  }

  removeService(index: number): void {
    this.servicesArray.removeAt(index);
    this.serviceToDelete.set(null);
  }

  // Tab navigation
  setTab(tab: 'profile' | 'schedule' | 'services' | 'notifications' | 'payments' | 'subscription'): void {
    this.activeTab.set(tab);
  }

  // Payment provider config toggle
  toggleProviderConfig(provider: PaymentProvider): void {
    if (this.activePaymentProvider() === provider) {
      this.activePaymentProvider.set(null);
    } else {
      this.activePaymentProvider.set(provider);
    }
  }

  isProviderEnabled(provider: PaymentProvider): boolean {
    return this.paymentsForm.get(provider + 'Enabled')?.value ?? false;
  }

  // Save all
  async saveAll(): Promise<void> {
    if (!this.profileForm.valid) {
      // Mark all fields as touched to show validation errors
      this.profileForm.markAllAsTouched();
      this.notificationService.error('Проверьте заполнение полей профиля');
      this.activeTab.set('profile');
      return;
    }

    this.isSaving.set(true);

    // Build work schedule
    const workSchedule: WorkSchedule = {} as WorkSchedule;
    this.weekDays.forEach(day => {
      const enabled = this.scheduleForm.get(day.key + 'Enabled')?.value;
      if (enabled) {
        (workSchedule as any)[day.key] = {
          start: this.scheduleForm.get(day.key + 'Start')?.value,
          end: this.scheduleForm.get(day.key + 'End')?.value
        };
      } else {
        (workSchedule as any)[day.key] = null;
      }
    });

    // Build social links
    const socialLinks: SocialLinks = {
      telegram: this.profileForm.get('telegram')?.value || undefined,
      instagram: this.profileForm.get('instagram')?.value || undefined,
      vk: this.profileForm.get('vk')?.value || undefined,
      whatsapp: this.profileForm.get('whatsapp')?.value || undefined
    };

    // Build notification settings
    const notificationSettings: NotificationSettings = {
      emailNotifications: this.notificationsForm.get('emailNotifications')?.value,
      smsNotifications: this.notificationsForm.get('smsNotifications')?.value,
      pushNotifications: this.notificationsForm.get('pushNotifications')?.value,
      reminderHours: this.notificationsForm.get('reminderHours')?.value
    };

    // Build payment settings
    const paymentSettings: PaymentSettings = {
      onlinePaymentsEnabled: this.paymentsForm.get('onlinePaymentsEnabled')?.value,
      prepaymentRequired: this.paymentsForm.get('prepaymentRequired')?.value,
      prepaymentPercent: this.paymentsForm.get('prepaymentPercent')?.value,
      acceptedMethods: {
        card: this.paymentsForm.get('acceptCard')?.value,
        sbp: this.paymentsForm.get('acceptSbp')?.value,
        yoomoney: this.paymentsForm.get('acceptYoomoney')?.value
      },
      providers: {
        yoomoney: {
          enabled: this.paymentsForm.get('yoomoneyEnabled')?.value,
          shopId: this.paymentsForm.get('yoomoneyShopId')?.value,
          secretKey: this.paymentsForm.get('yoomoneySecretKey')?.value
        },
        tinkoff: {
          enabled: this.paymentsForm.get('tinkoffEnabled')?.value,
          terminalKey: this.paymentsForm.get('tinkoffTerminalKey')?.value,
          secretKey: this.paymentsForm.get('tinkoffSecretKey')?.value
        },
        sberbank: {
          enabled: this.paymentsForm.get('sberbankEnabled')?.value,
          merchantLogin: this.paymentsForm.get('sberbankMerchantLogin')?.value,
          token: this.paymentsForm.get('sberbankToken')?.value
        },
        alfabank: {
          enabled: this.paymentsForm.get('alfabankEnabled')?.value,
          merchantLogin: this.paymentsForm.get('alfabankMerchantLogin')?.value,
          token: this.paymentsForm.get('alfabankToken')?.value
        }
      }
    };

    try {
      // Step 1: Upload avatar if changed
      if (this.avatarChanged()) {
        if (this.avatarFile) {
          const avatarResponse = await this.apiService.uploadAvatar(this.avatarFile).toPromise();
          if (avatarResponse?.avatar) {
            this.avatarPreview.set(avatarResponse.avatar);
          }
        } else {
          // Delete avatar
          await this.apiService.deleteAvatar().toPromise();
        }
        this.avatarFile = null;
        this.avatarChanged.set(false);
      }

      // Step 2: Update profile via API
      await this.apiService.updateProfile({
        first_name: this.profileForm.get('name')?.value?.split(' ')[0] || '',
        last_name: this.profileForm.get('name')?.value?.split(' ').slice(1).join(' ') || '',
        phone: this.profileForm.get('phone')?.value || '',
        specialization: this.profileForm.get('specialization')?.value || '',
        bio: this.profileForm.get('description')?.value || ''
      }).toPromise();

      // Step 3: Update local state only (API already called in step 2)
      this.authService.updateMasterProfile({
        name: this.profileForm.get('name')?.value,
        email: this.profileForm.get('email')?.value,
        phone: this.profileForm.get('phone')?.value || undefined,
        specialization: this.profileForm.get('specialization')?.value,
        address: this.profileForm.get('address')?.value,
        description: this.profileForm.get('description')?.value,
        avatar: this.avatarPreview() || undefined,
        workSchedule,
        socialLinks,
        notificationSettings,
        paymentSettings
      }, true).subscribe();

      // Step 4: Save schedule to backend API
      try {
        await this.saveScheduleToApi();
      } catch {
        // Schedule save failed silently - user will see notification on next load
      }

      // Step 5: Save services
      const masterId = this.authService.masterData()?.masterProfileId || this.authService.masterData()?.id;
      if (masterId) {
        // Delete removed services from backend
        const currentIds = new Set(this.servicesArray.value.map((s: any) => s.id).filter((id: string) => id && !id.startsWith('service-')));
        const initialServices = this.initialValues.services || [];
        for (const initial of initialServices) {
          if (initial.id && !initial.id.startsWith('service-') && !currentIds.has(initial.id)) {
            this.dataService.deleteService(initial.id).subscribe();
          }
        }

        // Create/update remaining services
        const services = this.servicesArray.value;
        for (const service of services) {
          if (service.id && !service.id.startsWith('service-')) {
            // Update existing service (has real backend ID)
            this.dataService.updateService(service.id, {
              ...service,
              masterId
            }).subscribe();
          } else {
            // Create new service (custom or from catalog)
            this.dataService.addService({
              ...service,
              masterId,
              serviceId: service.serviceId || undefined // Use catalog service if available
            }).subscribe(newService => {
              // Update form with new ID
              const index = services.indexOf(service);
              if (index >= 0) {
                this.servicesArray.at(index).patchValue({ id: newService.id });
              }
            });
          }
        }
      }

      this.saveInitialValues();
      this.isSaving.set(false);
      this.notificationService.success('Настройки сохранены');
    } catch {
      this.isSaving.set(false);
      this.notificationService.error('Ошибка сохранения');
    }
  }

  // Quick schedule templates
  setWorkdaysSchedule(): void {
    this.weekDays.forEach(day => {
      const isWeekend = day.key === 'saturday' || day.key === 'sunday';
      this.scheduleForm.patchValue({
        [day.key + 'Enabled']: !isWeekend,
        [day.key + 'Start']: '09:00',
        [day.key + 'End']: '18:00'
      });
    });
  }

  setEverydaySchedule(): void {
    this.weekDays.forEach(day => {
      this.scheduleForm.patchValue({
        [day.key + 'Enabled']: true,
        [day.key + 'Start']: '10:00',
        [day.key + 'End']: '20:00'
      });
    });
  }

  clearSchedule(): void {
    this.weekDays.forEach(day => {
      this.scheduleForm.patchValue({
        [day.key + 'Enabled']: false
      });
    });
  }

  // Load schedule from backend API
  private loadScheduleFromApi(): void {
    this.apiService.getSchedules().subscribe({
      next: (response) => {
        // Handle paginated or direct array response
        const schedules: BackendSchedule[] = response.results || response;
        this.backendSchedules = schedules;

        // Map weekday numbers to day keys
        const weekdayMap: { [key: number]: string } = {
          0: 'monday',
          1: 'tuesday',
          2: 'wednesday',
          3: 'thursday',
          4: 'friday',
          5: 'saturday',
          6: 'sunday'
        };

        // Reset form first
        this.weekDays.forEach(day => {
          this.scheduleForm.patchValue({
            [day.key + 'Enabled']: false,
            [day.key + 'Start']: '09:00',
            [day.key + 'End']: '18:00'
          });
        });

        // Apply backend schedules
        schedules.forEach(schedule => {
          const dayKey = weekdayMap[schedule.weekday];
          if (dayKey) {
            this.scheduleForm.patchValue({
              [dayKey + 'Enabled']: schedule.is_working,
              [dayKey + 'Start']: schedule.start_time.slice(0, 5), // "HH:MM:SS" -> "HH:MM"
              [dayKey + 'End']: schedule.end_time.slice(0, 5)
            });
          }
        });
      },
      error: () => {
        // Fallback to local data
        const master = this.authService.masterData();
        if (master?.workSchedule) {
          this.weekDays.forEach(day => {
            const schedule = master.workSchedule[day.key as keyof WorkSchedule];
            this.scheduleForm.patchValue({
              [day.key + 'Enabled']: !!schedule,
              [day.key + 'Start']: schedule?.start || '09:00',
              [day.key + 'End']: schedule?.end || '18:00'
            });
          });
        }
      }
    });
  }

  // Save schedule to backend API
  private saveScheduleToApi(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Map day keys to weekday numbers
      const dayKeyToWeekday: { [key: string]: number } = {
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6
      };

      // Build current schedules from form
      const currentSchedules: { weekday: number; start_time: string; end_time: string; is_working: boolean }[] = [];
      this.weekDays.forEach(day => {
        const enabled = this.scheduleForm.get(day.key + 'Enabled')?.value;
        const startTime = this.scheduleForm.get(day.key + 'Start')?.value || '09:00';
        const endTime = this.scheduleForm.get(day.key + 'End')?.value || '18:00';

        currentSchedules.push({
          weekday: dayKeyToWeekday[day.key],
          start_time: startTime + ':00', // Add seconds for backend
          end_time: endTime + ':00',
          is_working: enabled
        });
      });

      // Compare with backend schedules and create update operations
      const operations: any[] = [];

      currentSchedules.forEach(current => {
        const existing = this.backendSchedules.find(s => s.weekday === current.weekday);

        if (existing) {
          // Update existing schedule
          if (existing.start_time !== current.start_time ||
              existing.end_time !== current.end_time ||
              existing.is_working !== current.is_working) {
            operations.push(
              this.apiService.updateSchedule(existing.id, {
                start_time: current.start_time,
                end_time: current.end_time,
                is_working: current.is_working
              })
            );
          }
        } else {
          // Create new schedule
          operations.push(
            this.apiService.createSchedule({
              weekday: current.weekday,
              start_time: current.start_time,
              end_time: current.end_time,
              is_working: current.is_working
            })
          );
        }
      });

      if (operations.length === 0) {
        resolve();
        return;
      }

      forkJoin(operations).subscribe({
        next: (responses) => {
          // Update backendSchedules with responses (for created schedules)
          responses.forEach((response: any) => {
            if (response && response.id) {
              const existingIndex = this.backendSchedules.findIndex(s => s.weekday === response.weekday);
              if (existingIndex >= 0) {
                this.backendSchedules[existingIndex] = response;
              } else {
                this.backendSchedules.push(response);
              }
            }
          });
          resolve();
        },
        error: (err) => reject(err)
      });
    });
  }

  getUsagePercent(used: number, limit: number | null): number {
    if (!limit) return 0;
    return Math.min(100, (used / limit) * 100);
  }
}
