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

    // Check if user is deleting (backspace or delete key)
    const isDeleting = newValue.length < oldValue.length;

    // If completely empty, clear everything
    if (!newValue || newValue.replace(/\D/g, '') === '') {
      input.value = '';
      this.previousValue = '';
      this.onChange('');
      return;
    }

    const formatted = this.formatPhone(newValue);
    input.value = formatted;
    this.previousValue = formatted;

    // Adjust cursor position
    let newCursorPosition = cursorPosition;

    if (isDeleting) {
      // When deleting, move cursor back if we're on a formatting character
      const charAtCursor = formatted[cursorPosition - 1];
      if (charAtCursor && /[\s()-]/.test(charAtCursor)) {
        newCursorPosition = cursorPosition - 1;
      } else {
        newCursorPosition = cursorPosition;
      }
    } else {
      // When adding, skip over formatting characters
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

    // Set cursor position
    input.setSelectionRange(newCursorPosition, newCursorPosition);

    // Store clean number for the form
    this.onChange(this.cleanPhone(formatted));
  }

  @HostListener('blur')
  onBlur(): void {
    this.onTouched();
  }

  @HostListener('keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    const input = this.el.nativeElement;
    const cursorPosition = input.selectionStart || 0;
    const value = input.value;

    // Handle backspace on formatting characters
    if (event.key === 'Backspace' && cursorPosition > 0) {
      const charBefore = value[cursorPosition - 1];
      // If cursor is after a formatting character, delete the digit before it
      if (/[\s()-]/.test(charBefore)) {
        event.preventDefault();
        const newValue = value.slice(0, cursorPosition - 1) + value.slice(cursorPosition);
        this.el.nativeElement.value = newValue;
        const inputEvent = new Event('input', { bubbles: true });
        this.el.nativeElement.dispatchEvent(inputEvent);
      }
    }

    // Handle delete on formatting characters
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
