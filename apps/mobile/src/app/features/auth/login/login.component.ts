import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ThemeService } from '../../../core/services/theme.service';
import { UserRole } from '../../../core/models';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);
  private router = inject(Router);
  themeService = inject(ThemeService);

  selectedRole = signal<UserRole>('master');
  email = '';
  password = '';
  showPassword = signal(false);
  isLoading = signal(false);
  errorMessage = signal('');
  useApiMode = signal(false);

  fillDemoCredentials(): void {
    const credentials = this.authService.getDemoCredentials(this.selectedRole());
    this.email = credentials.email;
    this.password = credentials.password;
    this.errorMessage.set('');
    this.useApiMode.set(false);
  }

  fillBackendCredentials(): void {
    // Fill with a test master from backend
    this.email = 'анна.петрова@beautystyle.ru';
    this.password = 'master123';
    this.errorMessage.set('');
    this.useApiMode.set(true);
  }

  async onSubmit(): Promise<void> {
    if (!this.email || !this.password) {
      this.errorMessage.set('Заполните все поля');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    // Try API login first
    try {
      const apiSuccess = await firstValueFrom(
        this.authService.loginWithApi(this.email, this.password)
      );

      if (apiSuccess) {
        this.notificationService.success('Добро пожаловать в BeautyBook!');
        const user = this.authService.currentUser();
        const route = user?.role === 'master' ? '/master' : '/client';
        this.router.navigate([route]);
        this.isLoading.set(false);
        return;
      }
    } catch {
      // API login failed, trying demo mode
    }

    // Fallback to demo mode
    const demoSuccess = this.authService.login({
      email: this.email,
      password: this.password,
      role: this.selectedRole()
    });

    if (demoSuccess) {
      this.notificationService.success('Добро пожаловать в BeautyBook! (демо-режим)');
      const route = this.selectedRole() === 'master' ? '/master' : '/client';
      this.router.navigate([route]);
    } else {
      this.errorMessage.set('Неверный email или пароль');
    }

    this.isLoading.set(false);
  }
}
