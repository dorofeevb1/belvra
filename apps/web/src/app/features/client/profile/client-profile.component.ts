import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService, NotificationService, ThemeService } from '../../../core/services';
import { ApiService } from '../../../core/services/api.service';
import { NotificationSettings } from '../../../core/models';

@Component({
  selector: 'app-client-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, RouterLink],
  templateUrl: './client-profile.component.html',
  styleUrl: './client-profile.component.scss'
})
export class ClientProfileComponent implements OnInit {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);
  protected themeService = inject(ThemeService);

  isLoading = signal(true);
  isSaving = signal(false);
  activeTab = signal<'profile' | 'notifications'>('profile');

  // Avatar
  avatarPreview = signal<string>('');

  // Forms
  profileForm!: FormGroup;
  notificationsForm!: FormGroup;

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

    // Load notifications
    if (client.notificationSettings) {
      this.notificationsForm.patchValue(client.notificationSettings);
    }

    this.isLoading.set(false);
  }

  setTab(tab: 'profile' | 'notifications'): void {
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

  // Delete account
  private api = inject(ApiService);
  showDeleteConfirm = signal(false);
  isDeletingAccount = signal(false);
  deleteError = signal('');
  deletePassword = '';

  deleteAccount(): void {
    if (!this.deletePassword) {
      this.deleteError.set('Введите пароль');
      return;
    }

    this.isDeletingAccount.set(true);
    this.deleteError.set('');

    this.api.deleteAccount(this.deletePassword).subscribe({
      next: () => {
        this.authService.logout();
        this.router.navigate(['/login']);
        this.notificationService.success('Аккаунт и все данные удалены');
      },
      error: (err: any) => {
        this.isDeletingAccount.set(false);
        this.deleteError.set(err?.error?.detail || 'Ошибка удаления аккаунта');
      }
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
