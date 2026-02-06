import { Injectable } from '@angular/core';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import weekday from 'dayjs/plugin/weekday';
import isoWeek from 'dayjs/plugin/isoWeek';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(weekday);
dayjs.extend(isoWeek);
dayjs.extend(customParseFormat);
dayjs.locale('ru');

export interface CalendarDay {
  date: string;
  dayNum: number;
  isCurrentMonth: boolean;
  isPast: boolean;
  isToday: boolean;
}

export interface WeekDay {
  date: string;
  weekDay: string;
  dayNum: number;
  isToday: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class DateService {
  private weekDayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
  private monthNames = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

  today(): dayjs.Dayjs {
    return dayjs();
  }

  todayStr(): string {
    return dayjs().format('YYYY-MM-DD');
  }

  format(date: string | Date | dayjs.Dayjs, format: string = 'D MMMM YYYY'): string {
    return dayjs(date).format(format);
  }

  formatDateLong(dateStr: string): string {
    return dayjs(dateStr).format('D MMMM YYYY');
  }

  formatDateShort(dateStr: string): string {
    return dayjs(dateStr).format('D MMM');
  }

  formatTime(timeStr: string): string {
    return timeStr;
  }

  formatDateWithTime(dateStr: string, timeStr: string): string {
    return `${this.formatDateLong(dateStr)} в ${timeStr}`;
  }

  getWeekStart(date: Date | dayjs.Dayjs = dayjs()): dayjs.Dayjs {
    return dayjs(date).startOf('isoWeek');
  }

  getWeekDays(startDate: dayjs.Dayjs): WeekDay[] {
    const today = this.todayStr();
    const result: WeekDay[] = [];

    for (let i = 0; i < 7; i++) {
      const day = startDate.add(i, 'day');
      const dateStr = day.format('YYYY-MM-DD');
      result.push({
        date: dateStr,
        weekDay: this.weekDayNames[i],
        dayNum: day.date(),
        isToday: dateStr === today
      });
    }

    return result;
  }

  getWeekRangeText(startDate: dayjs.Dayjs): string {
    const endDate = startDate.add(6, 'day');

    if (startDate.month() === endDate.month()) {
      return `${startDate.date()} - ${endDate.date()} ${this.monthNames[startDate.month()]} ${startDate.year()}`;
    }
    return `${startDate.date()} ${this.monthNames[startDate.month()]} - ${endDate.date()} ${this.monthNames[endDate.month()]}`;
  }

  generateCalendarMonth(date: Date | dayjs.Dayjs = dayjs()): CalendarDay[] {
    const d = dayjs(date);
    const year = d.year();
    const month = d.month();

    const firstDay = d.startOf('month');
    const lastDay = d.endOf('month');

    const startDay = (firstDay.day() + 6) % 7; // Monday = 0
    const today = this.todayStr();
    const days: CalendarDay[] = [];

    // Previous month days
    for (let i = startDay - 1; i >= 0; i--) {
      const day = firstDay.subtract(i + 1, 'day');
      days.push({
        date: day.format('YYYY-MM-DD'),
        dayNum: day.date(),
        isCurrentMonth: false,
        isPast: true,
        isToday: false
      });
    }

    // Current month days
    for (let i = 1; i <= lastDay.date(); i++) {
      const day = dayjs(new Date(year, month, i));
      const dateStr = day.format('YYYY-MM-DD');
      days.push({
        date: dateStr,
        dayNum: i,
        isCurrentMonth: true,
        isPast: dateStr < today,
        isToday: dateStr === today
      });
    }

    // Next month days (fill to 42 = 6 weeks)
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
      const day = lastDay.add(i, 'day');
      days.push({
        date: day.format('YYYY-MM-DD'),
        dayNum: i,
        isCurrentMonth: false,
        isPast: false,
        isToday: false
      });
    }

    return days;
  }

  isPast(dateStr: string): boolean {
    return dateStr < this.todayStr();
  }

  isToday(dateStr: string): boolean {
    return dateStr === this.todayStr();
  }

  addTime(time: string, minutes: number): string {
    const [h, m] = time.split(':').map(Number);
    const totalMinutes = h * 60 + m + minutes;
    const newHours = Math.floor(totalMinutes / 60);
    const newMinutes = totalMinutes % 60;
    return `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
  }

  getHourFromTime(time: string): number {
    return parseInt(time.split(':')[0], 10);
  }

  getMinuteFromTime(time: string): number {
    return parseInt(time.split(':')[1], 10);
  }

  getShortWeekday(dateStr: string): string {
    const dayIndex = (dayjs(dateStr).day() + 6) % 7; // Monday = 0
    return this.weekDayNames[dayIndex];
  }

  getRelativeTime(date: Date | string): string {
    const d = dayjs(date);
    const now = dayjs();
    const diffMinutes = now.diff(d, 'minute');
    const diffHours = now.diff(d, 'hour');
    const diffDays = now.diff(d, 'day');

    if (diffMinutes < 1) return 'только что';
    if (diffMinutes < 60) return `${diffMinutes} мин назад`;
    if (diffHours < 24) return `${diffHours} ч назад`;
    if (diffDays < 7) return `${diffDays} дн назад`;
    return this.formatDateShort(d.format('YYYY-MM-DD'));
  }

  getGreeting(): string {
    const hour = dayjs().hour();
    if (hour < 12) return 'Доброе утро';
    if (hour < 17) return 'Добрый день';
    if (hour < 22) return 'Добрый вечер';
    return 'Доброй ночи';
  }

  /**
   * Check if a time slot is in the past for a given date.
   * Returns true if the slot has already passed.
   */
  isSlotPast(dateStr: string, timeStr: string): boolean {
    const now = dayjs();
    const slotDateTime = dayjs(`${dateStr} ${timeStr}`, 'YYYY-MM-DD HH:mm');
    return slotDateTime.isBefore(now);
  }

  /**
   * Filter out past time slots for a given date.
   * Returns only future slots.
   */
  filterPastSlots(dateStr: string, slots: string[]): string[] {
    if (dateStr !== this.todayStr()) {
      return slots; // For future dates, return all slots
    }
    return slots.filter(slot => !this.isSlotPast(dateStr, slot));
  }

  /**
   * Get current time as HH:mm string.
   */
  currentTime(): string {
    return dayjs().format('HH:mm');
  }
}
