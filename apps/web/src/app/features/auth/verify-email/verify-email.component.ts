import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  inject,
  signal,
  ViewChildren,
  QueryList,
  ElementRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

/** Количество цифр в коде подтверждения */
const CODE_LENGTH = 6;

/** Время до повторной отправки кода (секунды) */
const RESEND_COOLDOWN = 60;

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './verify-email.component.html',
  styleUrl: './verify-email.component.scss'
})
export class VerifyEmailComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChildren('codeInput') codeInputs!: QueryList<ElementRef<HTMLInputElement>>;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);

  /** Email пользователя, на который отправлен код */
  email = signal('');

  /** Массив из 6 цифр — текущее значение кода */
  digits: string[] = Array(CODE_LENGTH).fill('');

  isLoading = signal(false);
  isSuccess = signal(false);
  errorMessage = signal('');
  resendCountdown = signal(0);
  isResending = signal(false);

  private countdownTimer: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    const emailParam = this.route.snapshot.queryParamMap.get('email');
    if (emailParam) {
      this.email.set(emailParam);
    }
    this.startCountdown();
  }

  /** Автофокус на первое поле ввода при загрузке */
  ngAfterViewInit(): void {
    setTimeout(() => {
      const inputs = this.codeInputs.toArray();
      if (inputs.length > 0) {
        inputs[0].nativeElement.focus();
      }
    });
  }

  ngOnDestroy(): void {
    this.clearCountdown();
  }

  /**
   * Обработка ввода цифры — записывает только первую цифру
   * и автоматически переводит фокус на следующее поле
   */
  onDigitInput(event: Event, index: number): void {
    const input = event.target as HTMLInputElement;
    const value = input.value.replace(/\D/g, '');

    if (value.length > 0) {
      this.digits[index] = value[0];
      input.value = value[0];

      if (index < CODE_LENGTH - 1) {
        this.codeInputs.toArray()[index + 1].nativeElement.focus();
      }
    } else {
      this.digits[index] = '';
    }

    this.errorMessage.set('');
  }

  /**
   * Обработка Backspace — при пустом поле переходит
   * на предыдущее поле и очищает его
   */
  onKeyDown(event: KeyboardEvent, index: number): void {
    if (event.key !== 'Backspace') return;

    if (this.digits[index] === '' && index > 0) {
      const prevInput = this.codeInputs.toArray()[index - 1];
      this.digits[index - 1] = '';
      prevInput.nativeElement.value = '';
      prevInput.nativeElement.focus();
      event.preventDefault();
    } else {
      this.digits[index] = '';
    }
  }

  /** Вставка 6-значного кода из буфера обмена — заполняет все поля сразу */
  onPaste(event: ClipboardEvent): void {
    event.preventDefault();
    const pastedData = event.clipboardData?.getData('text')?.replace(/\D/g, '') || '';

    if (pastedData.length !== CODE_LENGTH) return;

    const inputs = this.codeInputs.toArray();
    for (let i = 0; i < CODE_LENGTH; i++) {
      this.digits[i] = pastedData[i];
      inputs[i].nativeElement.value = pastedData[i];
    }
    inputs[CODE_LENGTH - 1].nativeElement.focus();
  }

  /** Проверяет, что все 6 цифр заполнены */
  isCodeComplete(): boolean {
    return this.digits.every(d => d !== '');
  }

  /** Отправляет введённый код на сервер для верификации email */
  submitCode(): void {
    const code = this.digits.join('');
    if (code.length !== CODE_LENGTH) return;

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.authService.verifyEmail(this.email(), code).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.isSuccess.set(true);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          err.error?.detail || 'Не удалось подтвердить email. Попробуйте ещё раз.'
        );
      }
    });
  }

  /** Запрашивает повторную отправку кода и запускает таймер ожидания */
  resendCode(): void {
    this.isResending.set(true);
    this.errorMessage.set('');

    this.authService.resendVerificationEmail().subscribe({
      next: () => {
        this.isResending.set(false);
        this.startCountdown();
      },
      error: (err) => {
        this.isResending.set(false);
        this.errorMessage.set(
          err.error?.detail || 'Не удалось отправить код. Попробуйте позже.'
        );
      }
    });
  }

  /** Перенаправляет на главную страницу в зависимости от роли пользователя */
  goToHome(): void {
    const user = this.authService.currentUser();
    const route = user?.role === 'master' ? '/master' : '/client';
    this.router.navigate([route]);
  }

  /** Запускает обратный отсчёт для кнопки повторной отправки кода */
  private startCountdown(): void {
    this.clearCountdown();
    this.resendCountdown.set(RESEND_COOLDOWN);

    this.countdownTimer = setInterval(() => {
      const current = this.resendCountdown();
      if (current <= 1) {
        this.resendCountdown.set(0);
        this.clearCountdown();
      } else {
        this.resendCountdown.set(current - 1);
      }
    }, 1000);
  }

  private clearCountdown(): void {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
  }
}
