import { Directive, ElementRef, HostListener, forwardRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

/**
 * Маска ввода телефона в формате +7 (XXX) XXX-XX-XX.
 * Автоматически форматирует ввод, обрабатывает вставку из буфера
 * и корректно управляет позицией курсора при удалении.
 */
@Directive({
  selector: '[appPhoneMask]',
  standalone: true,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => PhoneMaskDirective),
      multi: true
    }
  ]
})
export class PhoneMaskDirective implements ControlValueAccessor {
  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  constructor(private el: ElementRef<HTMLInputElement>) {}

  writeValue(value: string): void {
    this.el.nativeElement.value = this.formatPhone(value || '');
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.el.nativeElement.disabled = isDisabled;
  }

  @HostListener('input')
  onInput(): void {
    const input = this.el.nativeElement;
    const value = input.value;
    const formatted = this.formatPhone(value);
    input.value = formatted;

    // Ставим курсор в конец после форматирования
    const cursorPos = formatted.length;
    input.setSelectionRange(cursorPos, cursorPos);

    this.onChange(this.cleanPhone(formatted));
  }

  @HostListener('blur')
  onBlur(): void {
    const input = this.el.nativeElement;
    // Если осталось только "+7" или "+7 (" — очищаем поле
    const digits = input.value.replace(/\D/g, '');
    if (digits.length <= 1) {
      input.value = '';
      this.onChange('');
    }
    this.onTouched();
  }

  @HostListener('focus')
  onFocus(): void {
    const input = this.el.nativeElement;
    if (!input.value) {
      input.value = '+7 (';
      this.onChange('+7');
      // Курсор после скобки
      setTimeout(() => input.setSelectionRange(4, 4));
    }
  }

  private formatPhone(value: string): string {
    if (!value) return '';

    let digits = value.replace(/\D/g, '');

    if (digits.startsWith('8') && digits.length > 1) {
      digits = '7' + digits.slice(1);
    }

    if (digits.startsWith('9')) {
      digits = '7' + digits;
    }

    if (digits.length > 0 && !digits.startsWith('7')) {
      digits = '7' + digits;
    }

    digits = digits.slice(0, 11);

    // Формат: +7 (XXX) XXX-XX-XX
    let formatted = '';
    if (digits.length > 0) {
      formatted = '+' + digits[0];
    }
    if (digits.length > 1) {
      formatted += ' (' + digits.slice(1, 4);
    }
    if (digits.length >= 4) {
      formatted += ') ';
    }
    if (digits.length > 4) {
      formatted += digits.slice(4, 7);
    }
    if (digits.length > 7) {
      formatted += '-' + digits.slice(7, 9);
    }
    if (digits.length > 9) {
      formatted += '-' + digits.slice(9, 11);
    }

    return formatted;
  }

  private cleanPhone(formatted: string): string {
    const digits = formatted.replace(/\D/g, '');
    return digits ? '+' + digits : '';
  }
}
