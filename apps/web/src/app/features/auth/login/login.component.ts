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

  async onSubmit(): Promise<void> {
    if (!this.email || !this.password) {
      this.errorMessage.set('Заполните все поля');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    try {
      const success = await firstValueFrom(
        this.authService.login(this.email, this.password, this.selectedRole())
      );

      if (success) {
        const user = this.authService.currentUser();
        if (!user?.isVerified) {
          this.router.navigate(['/verify-email'], {
            queryParams: { email: user?.email }
          });
        } else {
          this.notificationService.success('Добро пожаловать в BeautyBook!');
          const route = user?.role === 'master' ? '/master' : '/client';
          this.router.navigate([route]);
        }
      } else {
        this.errorMessage.set('Неверный email или пароль');
      }
    } catch {
      this.errorMessage.set('Ошибка входа. Попробуйте позже.');
    }

    this.isLoading.set(false);
  }
}
