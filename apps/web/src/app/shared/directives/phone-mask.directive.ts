import { Directive, ElementRef, HostListener, forwardRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

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
    const value = this.el.nativeElement.value;
    const formatted = this.formatPhone(value);
    this.el.nativeElement.value = formatted;
    // Store clean number for the form
    this.onChange(this.cleanPhone(formatted));
  }

  @HostListener('blur')
  onBlur(): void {
    this.onTouched();
  }

  @HostListener('focus')
  onFocus(): void {
    // If empty, pre-fill with +7
    if (!this.el.nativeElement.value) {
      this.el.nativeElement.value = '+7 (';
      this.onChange('+7');
    }
  }

  private formatPhone(value: string): string {
    if (!value) return '';

    // Remove all non-digits
    let digits = value.replace(/\D/g, '');

    // If starts with 8, replace with 7
    if (digits.startsWith('8') && digits.length > 1) {
      digits = '7' + digits.slice(1);
    }

    // If starts with 9 (user typed 9...), prepend 7
    if (digits.startsWith('9')) {
      digits = '7' + digits;
    }

    // If doesn't start with 7, prepend it
    if (digits.length > 0 && !digits.startsWith('7')) {
      digits = '7' + digits;
    }

    // Limit to 11 digits (7 + 10 digits)
    digits = digits.slice(0, 11);

    // Format: +7 (XXX) XXX-XX-XX
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
    // Return just the digits with + prefix
    const digits = formatted.replace(/\D/g, '');
    return digits ? '+' + digits : '';
  }
}
