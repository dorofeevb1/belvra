import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="verify-container">
      <div class="verify-card">
        @if (isLoading()) {
          <div class="loading-state">
            <div class="spinner"></div>
            <h2>Подтверждение email...</h2>
            <p>Пожалуйста, подождите</p>
          </div>
        } @else if (isSuccess()) {
          <div class="success-state">
            <div class="icon success-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <h2>Email подтверждён!</h2>
            <p>{{ message() }}</p>
            <a routerLink="/login" class="btn btn-primary">Войти в аккаунт</a>
          </div>
        } @else {
          <div class="error-state">
            <div class="icon error-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
            <h2>Ошибка подтверждения</h2>
            <p>{{ errorMessage() }}</p>
            <div class="actions">
              <a routerLink="/login" class="btn btn-secondary">Войти</a>
              <a routerLink="/register" class="btn btn-primary">Регистрация</a>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .verify-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .verify-card {
      background: white;
      border-radius: 16px;
      padding: 3rem;
      max-width: 400px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    }

    .loading-state, .success-state, .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    }

    .spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #e5e7eb;
      border-top-color: #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .icon {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .success-icon {
      background: #d1fae5;
      color: #059669;
    }

    .error-icon {
      background: #fee2e2;
      color: #dc2626;
    }

    h2 {
      margin: 0;
      font-size: 1.5rem;
      color: #111827;
    }

    p {
      margin: 0;
      color: #6b7280;
      line-height: 1.5;
    }

    .btn {
      display: inline-block;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 500;
      text-decoration: none;
      transition: all 0.2s;
      cursor: pointer;
      border: none;
    }

    .btn-primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .btn-secondary {
      background: #f3f4f6;
      color: #374151;
    }

    .btn-secondary:hover {
      background: #e5e7eb;
    }

    .actions {
      display: flex;
      gap: 1rem;
      margin-top: 0.5rem;
    }
  `]
})
export class VerifyEmailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);

  isLoading = signal(true);
  isSuccess = signal(false);
  message = signal('');
  errorMessage = signal('');

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.isLoading.set(false);
      this.errorMessage.set('Токен подтверждения не найден. Проверьте ссылку из письма.');
      return;
    }

    this.authService.verifyEmail(token).subscribe({
      next: (response) => {
        this.isLoading.set(false);
        this.isSuccess.set(true);
        this.message.set(response.detail || 'Ваш email успешно подтверждён. Теперь вы можете пользоваться всеми функциями.');
      },
      error: (error) => {
        this.isLoading.set(false);
        this.isSuccess.set(false);
        this.errorMessage.set(
          error.error?.detail ||
          'Не удалось подтвердить email. Возможно, ссылка устарела или уже была использована.'
        );
      }
    });
  }
}
