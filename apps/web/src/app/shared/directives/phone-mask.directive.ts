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
  private previousValue: string = '';

  constructor(private el: ElementRef<HTMLInputElement>) {}

  writeValue(value: string): void {
    const formatted = this.formatPhone(value || '');
    this.el.nativeElement.value = formatted;
    this.previousValue = formatted;
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

  @HostListener('input', ['$event'])
  onInput(event: Event): void {
    const input = this.el.nativeElement;
    const cursorPosition = input.selectionStart || 0;
    const oldValue = this.previousValue;
    const newValue = input.value;

    const isDeleting = newValue.length < oldValue.length;

    if (!newValue || newValue.replace(/\D/g, '') === '') {
      input.value = '';
      this.previousValue = '';
      this.onChange('');
      return;
    }

    const formatted = this.formatPhone(newValue);
    input.value = formatted;
    this.previousValue = formatted;

    let newCursorPosition = cursorPosition;

    if (isDeleting) {
      const charAtCursor = formatted[cursorPosition - 1];
      if (charAtCursor && /[\s()-]/.test(charAtCursor)) {
        newCursorPosition = cursorPosition - 1;
      } else {
        newCursorPosition = cursorPosition;
      }
    } else {
      const digitsBeforeCursor = newValue.slice(0, cursorPosition).replace(/\D/g, '').length;
      let digitCount = 0;
      for (let i = 0; i < formatted.length; i++) {
        if (/\d/.test(formatted[i])) {
          digitCount++;
        }
        if (digitCount === digitsBeforeCursor) {
          newCursorPosition = i + 1;
          break;
        }
      }
    }

    input.setSelectionRange(newCursorPosition, newCursorPosition);
    this.onChange(this.cleanPhone(formatted));
  }

  @HostListener('blur')
  onBlur(): void {
    const input = this.el.nativeElement;
    const digits = input.value.replace(/\D/g, '');
    if (digits.length <= 1) {
      input.value = '';
      this.previousValue = '';
      this.onChange('');
    }
    this.onTouched();
  }

  @HostListener('focus')
  onFocus(): void {
    const input = this.el.nativeElement;
    if (!input.value) {
      input.value = '+7 (';
      this.previousValue = '+7 (';
      this.onChange('+7');
      setTimeout(() => input.setSelectionRange(4, 4));
    }
  }

  @HostListener('keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    const input = this.el.nativeElement;
    const cursorPosition = input.selectionStart || 0;
    const value = input.value;

    if (event.key === 'Backspace' && cursorPosition > 0) {
      const charBefore = value[cursorPosition - 1];
      if (/[\s()-]/.test(charBefore)) {
        event.preventDefault();
        const newValue = value.slice(0, cursorPosition - 1) + value.slice(cursorPosition);
        this.el.nativeElement.value = newValue;
        const inputEvent = new Event('input', { bubbles: true });
        this.el.nativeElement.dispatchEvent(inputEvent);
      }
    }

    if (event.key === 'Delete' && cursorPosition < value.length) {
      const charAfter = value[cursorPosition];
      if (/[\s()-]/.test(charAfter)) {
        event.preventDefault();
        const newValue = value.slice(0, cursorPosition) + value.slice(cursorPosition + 1);
        this.el.nativeElement.value = newValue;
        const inputEvent = new Event('input', { bubbles: true });
        this.el.nativeElement.dispatchEvent(inputEvent);
      }
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
