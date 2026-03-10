import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import customParseFormat from 'dayjs/plugin/customParseFormat';

dayjs.extend(customParseFormat);
dayjs.locale('ru');

import { DateService, CalendarDay } from './date.service';

/**
 * Create DateService without Angular DI (it has no injected dependencies).
 */
function createService(): DateService {
  const svc = Object.create(DateService.prototype) as DateService;
  // Reinitialise private fields that are set in the class body
  (svc as any).weekDayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
  (svc as any).monthNames = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  return svc;
}

describe('DateService', () => {
  let service: DateService;

  beforeEach(() => {
    service = createService();
  });

  // ---------- generateCalendarMonth ----------

  describe('generateCalendarMonth', () => {
    it('always returns exactly 42 days (6 weeks)', () => {
      // Test several different months
      const months = [
        new Date(2026, 0, 1),  // January 2026
        new Date(2026, 1, 1),  // February 2026
        new Date(2026, 2, 1),  // March 2026
        new Date(2026, 5, 1),  // June 2026
        new Date(2026, 11, 1), // December 2026
      ];

      for (const month of months) {
        const days = service.generateCalendarMonth(month);
        expect(days).toHaveLength(42);
      }
    });

    it('marks current month days with isCurrentMonth=true', () => {
      const days = service.generateCalendarMonth(new Date(2026, 2, 1)); // March 2026
      const marchDays = days.filter(d => d.isCurrentMonth);
      expect(marchDays).toHaveLength(31); // March has 31 days
    });

    it('includes previous and next month padding days', () => {
      const days = service.generateCalendarMonth(new Date(2026, 2, 1)); // March 2026
      const nonCurrentMonth = days.filter(d => !d.isCurrentMonth);
      expect(nonCurrentMonth.length).toBe(42 - 31); // 11 padding days
    });

    it('February 2026 (non-leap year) has 28 current-month days', () => {
      const days = service.generateCalendarMonth(new Date(2026, 1, 1));
      const febDays = days.filter(d => d.isCurrentMonth);
      expect(febDays).toHaveLength(28);
    });

    it('each day has correct date format (YYYY-MM-DD)', () => {
      const days = service.generateCalendarMonth(new Date(2026, 0, 1));
      for (const day of days) {
        expect(day.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    });
  });

  // ---------- filterPastSlots ----------

  describe('filterPastSlots', () => {
    it('returns all slots for a future date', () => {
      const futureDate = dayjs().add(5, 'day').format('YYYY-MM-DD');
      const slots = ['09:00', '10:00', '11:00', '14:00'];
      const filtered = service.filterPastSlots(futureDate, slots);
      expect(filtered).toEqual(slots);
    });

    it('filters past slots for today', () => {
      const today = service.todayStr();
      const now = dayjs();
      // Create slots: some in the past, some in the future
      const pastSlot = now.subtract(2, 'hour').format('HH:mm');
      const futureSlot = now.add(2, 'hour').format('HH:mm');

      const slots = [pastSlot, futureSlot];
      const filtered = service.filterPastSlots(today, slots);

      expect(filtered).toContain(futureSlot);
      expect(filtered).not.toContain(pastSlot);
    });

    it('returns empty array when all slots are past for today', () => {
      const today = service.todayStr();
      // Slots far in the past
      const slots = ['00:01', '00:02'];
      const filtered = service.filterPastSlots(today, slots);
      expect(filtered).toEqual([]);
    });
  });

  // ---------- formatDateLong ----------

  describe('formatDateLong', () => {
    it('formats date correctly using dayjs Russian locale', () => {
      const result = service.formatDateLong('2026-03-15');
      // dayjs with Russian locale: "15 марта 2026"
      expect(result).toContain('15');
      expect(result).toContain('2026');
      // Should contain Russian month name (марта)
      expect(result.toLowerCase()).toContain('март');
    });

    it('formats another date correctly', () => {
      const result = service.formatDateLong('2026-01-01');
      expect(result).toContain('1');
      expect(result).toContain('2026');
    });
  });

  // ---------- addTime ----------

  describe('addTime', () => {
    it('adds minutes correctly', () => {
      expect(service.addTime('10:00', 30)).toBe('10:30');
      expect(service.addTime('10:30', 30)).toBe('11:00');
      expect(service.addTime('23:30', 60)).toBe('24:30');
    });
  });

  // ---------- todayStr ----------

  describe('todayStr', () => {
    it('returns today in YYYY-MM-DD format', () => {
      const result = service.todayStr();
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(result).toBe(dayjs().format('YYYY-MM-DD'));
    });
  });
});
