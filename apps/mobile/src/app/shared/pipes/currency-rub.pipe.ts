import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'currencyRub',
  standalone: true
})
export class CurrencyRubPipe implements PipeTransform {
  transform(value: number | null | undefined, showSymbol: boolean = true): string {
    if (value === null || value === undefined) {
      return showSymbol ? '0 ₽' : '0';
    }

    const formatted = new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);

    return showSymbol ? `${formatted} ₽` : formatted;
  }
}
