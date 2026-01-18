import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ThemeService } from '../../../core/services/theme.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss'
})
export class ResetPasswordComponent implements OnInit {
  private apiService = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  themeService = inject(ThemeService);

  token = '';
  newPassword = '';
  confirmPassword = '';
  showPassword = signal(false);
  showConfirmPassword = signal(false);

  isLoading = signal(false);
  isValidating = signal(true);
  isTokenValid = signal(false);
  isSuccess = signal(false);
  errorMessage = signal('');

  ngOnInit(): void {
    this.token = this.route.snapshot.queryParamMap.get('token') || '';
    if (this.token) {
      this.validateToken();
    } else {
      this.isValidating.set(false);
      this.errorMessage.set('Токен сброса пароля не найден');
    }
  }

  private validateToken(): void {
    this.apiService.validateResetToken(this.token).subscribe({
      next: (response) => {
        this.isValidating.set(false);
        this.isTokenValid.set(response.valid);
        if (!response.valid) {
          this.errorMessage.set('Недействительный или истёкший токен');
        }
      },
      error: () => {
        this.isValidating.set(false);
        this.isTokenValid.set(false);
        this.errorMessage.set('Недействительный или истёкший токен');
      }
    });
  }

  async onSubmit(): Promise<void> {
    this.errorMessage.set('');

    if (!this.newPassword) {
      this.errorMessage.set('Введите новый пароль');
      return;
    }

    if (this.newPassword.length < 8) {
      this.errorMessage.set('Пароль должен содержать минимум 8 символов');
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.errorMessage.set('Пароли не совпадают');
      return;
    }

    this.isLoading.set(true);

    this.apiService.confirmPasswordReset(this.token, this.newPassword).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.isSuccess.set(true);
      },
      error: (error) => {
        this.isLoading.set(false);
        this.errorMessage.set(error.error?.detail || 'Ошибка при сбросе пароля');
      }
    });
  }

  getPasswordStrength(): number {
    if (!this.newPassword) return 0;
    let strength = 0;
    if (this.newPassword.length >= 8) strength++;
    if (/[a-z]/.test(this.newPassword) && /[A-Z]/.test(this.newPassword)) strength++;
    if (/\d/.test(this.newPassword)) strength++;
    if (/[^a-zA-Z0-9]/.test(this.newPassword)) strength++;
    return strength;
  }

  getPasswordStrengthText(): string {
    const strength = this.getPasswordStrength();
    switch (strength) {
      case 0:
      case 1:
        return 'Слабый';
      case 2:
        return 'Средний';
      case 3:
        return 'Хороший';
      case 4:
        return 'Отличный';
      default:
        return '';
    }
  }

  getPasswordStrengthColor(): string {
    const strength = this.getPasswordStrength();
    switch (strength) {
      case 0:
      case 1:
        return '#ef4444';
      case 2:
        return '#f59e0b';
      case 3:
        return '#10b981';
      case 4:
        return '#22c55e';
      default:
        return '#e5e7eb';
    }
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}
