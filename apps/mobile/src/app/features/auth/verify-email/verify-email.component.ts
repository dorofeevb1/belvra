import { Component, OnInit, OnDestroy, inject, signal, ViewChildren, QueryList, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="verify-container">
      <div class="verify-card">
        @if (isSuccess()) {
          <div class="success-state">
            <div class="icon success-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
            <h2>Email подтверждён!</h2>
            <p>Ваш email успешно подтверждён.</p>
            <button class="btn btn-primary" (click)="goToHome()">Продолжить</button>
          </div>
        } @else {
          <div class="code-form">
            <div class="icon email-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect width="20" height="16" x="2" y="4" rx="2"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
            </div>
            <h2>Подтверждение email</h2>
            <p>Код отправлен на <strong>{{ email() }}</strong></p>

            <div class="code-inputs">
              @for (digit of digits; track $index) {
                <input
                  #codeInput
                  type="text"
                  inputmode="numeric"
                  maxlength="1"
                  [value]="digit"
                  (input)="onDigitInput($event, $index)"
                  (keydown)="onKeyDown($event, $index)"
                  (paste)="onPaste($event)"
                  [class.filled]="digit !== ''"
                  [disabled]="isLoading()"
                />
              }
            </div>

            @if (errorMessage()) {
              <div class="error-message">{{ errorMessage() }}</div>
            }

            <button
              class="btn btn-primary btn-full"
              (click)="submitCode()"
              [disabled]="isLoading() || !isCodeComplete()"
            >
              @if (isLoading()) {
                <span class="btn-spinner"></span> Проверка...
              } @else {
                Подтвердить
              }
            </button>

            <div class="resend-section">
              @if (resendCountdown() > 0) {
                <p class="resend-timer">Отправить повторно через {{ resendCountdown() }} сек</p>
              } @else {
                <button class="btn btn-link" (click)="resendCode()" [disabled]="isResending()">
                  @if (isResending()) {
                    Отправка...
                  } @else {
                    Отправить код повторно
                  }
                </button>
              }
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
      padding: 2.5rem;
      max-width: 420px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    }

    .code-form, .success-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    }

    .icon {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .email-icon {
      background: #ede9fe;
      color: #7c3aed;
    }

    .success-icon {
      background: #d1fae5;
      color: #059669;
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

    p strong {
      color: #111827;
    }

    .code-inputs {
      display: flex;
      gap: 8px;
      margin: 0.5rem 0;
    }

    .code-inputs input {
      width: 48px;
      height: 56px;
      text-align: center;
      font-size: 24px;
      font-weight: 700;
      border: 2px solid #d1d5db;
      border-radius: 12px;
      outline: none;
      transition: all 0.2s;
      color: #111827;
      background: #f9fafb;
    }

    .code-inputs input:focus {
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
      background: white;
    }

    .code-inputs input.filled {
      border-color: #667eea;
      background: white;
    }

    .error-message {
      color: #dc2626;
      font-size: 0.875rem;
      background: #fef2f2;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      width: 100%;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 500;
      font-size: 1rem;
      text-decoration: none;
      transition: all 0.2s;
      cursor: pointer;
      border: none;
    }

    .btn-full {
      width: 100%;
    }

    .btn-primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    .btn-primary:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-link {
      background: none;
      color: #667eea;
      padding: 0.5rem;
      font-weight: 500;
    }

    .btn-link:hover:not(:disabled) {
      text-decoration: underline;
    }

    .btn-link:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .resend-section {
      margin-top: 0.5rem;
    }

    .resend-timer {
      color: #9ca3af;
      font-size: 0.875rem;
    }
  `]
})
export class VerifyEmailComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChildren('codeInput') codeInputs!: QueryList<ElementRef<HTMLInputElement>>;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);

  email = signal('');
  digits: string[] = ['', '', '', '', '', ''];
  isLoading = signal(false);
  isSuccess = signal(false);
  errorMessage = signal('');
  resendCountdown = signal(0);
  isResending = signal(false);

  private countdownInterval: any = null;

  ngOnInit(): void {
    const emailParam = this.route.snapshot.queryParamMap.get('email');
    if (emailParam) {
      this.email.set(emailParam);
    }
    this.startCountdown();
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      const inputs = this.codeInputs.toArray();
      if (inputs.length > 0) {
        inputs[0].nativeElement.focus();
      }
    });
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
  }

  onDigitInput(event: Event, index: number): void {
    const input = event.target as HTMLInputElement;
    const value = input.value.replace(/\D/g, '');

    if (value.length > 0) {
      this.digits[index] = value[0];
      input.value = value[0];

      // Auto-focus next input
      if (index < 5) {
        const inputs = this.codeInputs.toArray();
        inputs[index + 1].nativeElement.focus();
      }
    } else {
      this.digits[index] = '';
    }

    this.errorMessage.set('');
  }

  onKeyDown(event: KeyboardEvent, index: number): void {
    if (event.key === 'Backspace') {
      if (this.digits[index] === '' && index > 0) {
        const inputs = this.codeInputs.toArray();
        this.digits[index - 1] = '';
        inputs[index - 1].nativeElement.value = '';
        inputs[index - 1].nativeElement.focus();
        event.preventDefault();
      } else {
        this.digits[index] = '';
      }
    }
  }

  onPaste(event: ClipboardEvent): void {
    event.preventDefault();
    const pastedData = event.clipboardData?.getData('text')?.replace(/\D/g, '') || '';
    if (pastedData.length === 6) {
      const inputs = this.codeInputs.toArray();
      for (let i = 0; i < 6; i++) {
        this.digits[i] = pastedData[i];
        inputs[i].nativeElement.value = pastedData[i];
      }
      inputs[5].nativeElement.focus();
    }
  }

  isCodeComplete(): boolean {
    return this.digits.every(d => d !== '');
  }

  submitCode(): void {
    const code = this.digits.join('');
    if (code.length !== 6) return;

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.authService.verifyEmail(this.email(), code).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.isSuccess.set(true);
      },
      error: (error) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          error.error?.detail || 'Не удалось подтвердить email. Попробуйте ещё раз.'
        );
      }
    });
  }

  resendCode(): void {
    this.isResending.set(true);
    this.errorMessage.set('');

    this.authService.resendVerificationEmail().subscribe({
      next: () => {
        this.isResending.set(false);
        this.startCountdown();
      },
      error: (error) => {
        this.isResending.set(false);
        this.errorMessage.set(
          error.error?.detail || 'Не удалось отправить код. Попробуйте позже.'
        );
      }
    });
  }

  goToHome(): void {
    const user = this.authService.currentUser();
    const route = user?.role === 'master' ? '/master' : '/client';
    this.router.navigate([route]);
  }

  private startCountdown(): void {
    this.resendCountdown.set(60);
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
    this.countdownInterval = setInterval(() => {
      const current = this.resendCountdown();
      if (current <= 1) {
        this.resendCountdown.set(0);
        clearInterval(this.countdownInterval);
        this.countdownInterval = null;
      } else {
        this.resendCountdown.set(current - 1);
      }
    }, 1000);
  }
}
