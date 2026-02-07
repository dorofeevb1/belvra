import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ThemeService } from '../../../core/services/theme.service';
import { UserRole } from '../../../core/models';

interface RegisterForm {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  password: string;
  passwordConfirm: string;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss'
})
export class RegisterComponent {
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);
  private router = inject(Router);
  themeService = inject(ThemeService);

  selectedRole = signal<UserRole>('client');
  showPassword = signal(false);
  showPasswordConfirm = signal(false);
  isLoading = signal(false);
  errorMessage = signal('');
  currentStep = signal(1);

  form: RegisterForm = {
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    password: '',
    passwordConfirm: ''
  };

  // Validation errors
  errors = signal<Partial<Record<keyof RegisterForm, string>>>({});

  validateStep1(): boolean {
    const newErrors: Partial<Record<keyof RegisterForm, string>> = {};

    if (!this.form.firstName.trim()) {
      newErrors.firstName = 'Введите имя';
    }

    if (!this.form.lastName.trim()) {
      newErrors.lastName = 'Введите фамилию';
    }

    if (!this.form.email.trim()) {
      newErrors.email = 'Введите email';
    } else if (!this.isValidEmail(this.form.email)) {
      newErrors.email = 'Некорректный email';
    }

    if (this.form.phone && !this.isValidPhone(this.form.phone)) {
      newErrors.phone = 'Некорректный номер телефона';
    }

    this.errors.set(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  validateStep2(): boolean {
    const newErrors: Partial<Record<keyof RegisterForm, string>> = {};

    if (!this.form.password) {
      newErrors.password = 'Введите пароль';
    } else if (this.form.password.length < 8) {
      newErrors.password = 'Минимум 8 символов';
    } else if (!/[A-Za-z]/.test(this.form.password) || !/[0-9]/.test(this.form.password)) {
      newErrors.password = 'Пароль должен содержать буквы и цифры';
    }

    if (!this.form.passwordConfirm) {
      newErrors.passwordConfirm = 'Подтвердите пароль';
    } else if (this.form.password !== this.form.passwordConfirm) {
      newErrors.passwordConfirm = 'Пароли не совпадают';
    }

    this.errors.set(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  nextStep(): void {
    if (this.currentStep() === 1 && this.validateStep1()) {
      this.currentStep.set(2);
      this.errorMessage.set('');
    }
  }

  prevStep(): void {
    if (this.currentStep() === 2) {
      this.currentStep.set(1);
      this.errors.set({});
      this.errorMessage.set('');
    }
  }

  async onSubmit(): Promise<void> {
    if (!this.validateStep2()) {
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    try {
      const success = await firstValueFrom(
        this.authService.registerWithRole({
          email: this.form.email.trim(),
          password: this.form.password,
          password_confirm: this.form.passwordConfirm,
          first_name: this.form.firstName.trim(),
          last_name: this.form.lastName.trim(),
          phone: this.form.phone.trim() || undefined,
          role: this.selectedRole()
        })
      );

      if (success) {
        this.notificationService.success('Регистрация успешна! Подтвердите email.');
        this.router.navigate(['/verify-email'], {
          queryParams: { email: this.form.email.trim() }
        });
      } else {
        this.errorMessage.set('Ошибка регистрации. Возможно, email уже используется.');
      }
    } catch (error: any) {
      console.error('Registration error:', error);
      if (error?.error?.email) {
        this.errorMessage.set('Пользователь с таким email уже существует');
      } else if (error?.error?.detail) {
        this.errorMessage.set(error.error.detail);
      } else {
        this.errorMessage.set('Произошла ошибка. Попробуйте позже.');
      }
    }

    this.isLoading.set(false);
  }

  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  private isValidPhone(phone: string): boolean {
    const cleaned = phone.replace(/[\s\-\(\)]/g, '');
    return /^\+?[0-9]{10,15}$/.test(cleaned);
  }

  formatPhone(event: Event): void {
    const input = event.target as HTMLInputElement;
    let value = input.value.replace(/\D/g, '');

    if (value.startsWith('8')) {
      value = '7' + value.slice(1);
    }

    if (value.length > 0) {
      if (value.length <= 1) {
        value = '+7 (' + value;
      } else if (value.length <= 4) {
        value = '+7 (' + value.slice(1);
      } else if (value.length <= 7) {
        value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4);
      } else if (value.length <= 9) {
        value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4, 7) + '-' + value.slice(7);
      } else {
        value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4, 7) + '-' + value.slice(7, 9) + '-' + value.slice(9, 11);
      }
    }

    this.form.phone = value;
  }

  getPasswordStrength(): { level: number; text: string; color: string } {
    const password = this.form.password;
    let score = 0;

    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (score <= 1) return { level: 1, text: 'Слабый', color: 'error' };
    if (score <= 2) return { level: 2, text: 'Средний', color: 'warning' };
    if (score <= 3) return { level: 3, text: 'Хороший', color: 'info' };
    return { level: 4, text: 'Надежный', color: 'success' };
  }
}
