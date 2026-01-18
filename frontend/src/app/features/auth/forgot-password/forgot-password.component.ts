import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ThemeService } from '../../../core/services/theme.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent {
  private apiService = inject(ApiService);
  themeService = inject(ThemeService);

  email = '';
  isLoading = signal(false);
  isSubmitted = signal(false);
  errorMessage = signal('');

  async onSubmit(): Promise<void> {
    if (!this.email) {
      this.errorMessage.set('Введите email');
      return;
    }

    if (!this.isValidEmail(this.email)) {
      this.errorMessage.set('Введите корректный email');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.apiService.requestPasswordReset(this.email).subscribe({
      next: () => {
        this.isSubmitted.set(true);
        this.isLoading.set(false);
      },
      error: () => {
        // Don't show error - for security reasons we show success message anyway
        this.isSubmitted.set(true);
        this.isLoading.set(false);
      }
    });
  }

  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
}
