import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'dateFormat',
  standalone: true
})
export class DateFormatPipe implements PipeTransform {
  private months = [
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
  ];

  private shortMonths = [
    'янв', 'фев', 'мар', 'апр', 'май', 'июн',
    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'
  ];

  private weekDays = [
    'воскресенье', 'понедельник', 'вторник', 'среда',
    'четверг', 'пятница', 'суббота'
  ];

  private shortWeekDays = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];

  transform(
    value: string | Date | null | undefined,
    format: 'full' | 'short' | 'date' | 'time' | 'weekday' | 'relative' = 'full'
  ): string {
    if (!value) return '';

    const date = value instanceof Date ? value : new Date(value);

    if (isNaN(date.getTime())) return '';

    switch (format) {
      case 'full':
        return `${date.getDate()} ${this.months[date.getMonth()]} ${date.getFullYear()}`;

      case 'short':
        return `${date.getDate()} ${this.shortMonths[date.getMonth()]}`;

      case 'date':
        return `${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}.${date.getFullYear()}`;

      case 'time':
        return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

      case 'weekday':
        return this.weekDays[date.getDay()];

      case 'relative':
        return this.getRelativeTime(date);

      default:
        return date.toLocaleDateString('ru-RU');
    }
  }

  private getRelativeTime(date: Date): string {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'только что';
    if (diffMins < 60) return `${diffMins} мин. назад`;
    if (diffHours < 24) return `${diffHours} ч. назад`;
    if (diffDays === 1) return 'вчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;

    return `${date.getDate()} ${this.shortMonths[date.getMonth()]}`;
  }
}
