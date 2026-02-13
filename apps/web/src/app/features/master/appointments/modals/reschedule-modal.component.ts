import { Component, input, output, inject, signal, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ModalComponent } from '../../../../shared/components/modal.component';
import { AuthService, DataService, DateService } from '../../../../core/services';
import { Appointment } from '../../../../core/models';

@Component({
  selector: 'app-reschedule-modal',
  standalone: true,
  imports: [CommonModule, ModalComponent],
  template: `
    <app-modal
      [isOpen]="isOpen()"
      title="Перенести запись"
      size="md"
      (closeModal)="close.emit()"
    >
      @if (appointment()) {
        <ng-container>
          <div class="modal-content">
            <!-- Current Info -->
            <div class="info-card">
              <div class="info-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">Текущая дата:</span>
                <span class="info-value">{{ formatDate(appointment()!.date) }} в {{ appointment()!.startTime }}</span>
              </div>
            </div>

            <!-- Calendar -->
            <div class="calendar-section">
              <label class="section-label">Выберите новую дату</label>
              <div class="mini-calendar">
                <div class="calendar-weekdays">
                  @for (day of weekDays; track day) {
                    <span class="weekday">{{ day }}</span>
                  }
                </div>
                <div class="calendar-days">
                  @for (day of calendarDays(); track day.date) {
                    <button
                      type="button"
                      (click)="selectDate(day.date)"
                      [disabled]="day.isPast"
                      class="calendar-day"
                      [class.selected]="selectedDate() === day.date"
                      [class.today]="day.date === todayStr"
                      [class.disabled]="day.isPast"
                      [class.other-month]="!day.isCurrentMonth"
                    >
                      {{ day.dayNum }}
                    </button>
                  }
                </div>
              </div>
            </div>

            <!-- Time Slots -->
            @if (selectedDate()) {
              <div class="time-section">
                <label class="section-label">Выберите время</label>
                @if (isLoadingSlots()) {
                  <div class="loading-slots">
                    <div class="spinner"></div>
                  </div>
                } @else if (availableSlots().length === 0) {
                  <div class="empty-slots">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <span>Нет свободных слотов на эту дату</span>
                  </div>
                } @else {
                  <div class="time-grid">
                    @for (slot of availableSlots(); track slot) {
                      <button
                        type="button"
                        (click)="selectedTime.set(slot)"
                        class="time-slot"
                        [class.selected]="selectedTime() === slot"
                      >
                        {{ slot }}
                      </button>
                    }
                  </div>
                }
              </div>
            }
          </div>
        </ng-container>
      }

      <div modal-footer class="modal-actions">
        <button type="button" (click)="close.emit()" class="btn btn-secondary">
          Отмена
        </button>
        <button
          type="button"
          (click)="onReschedule()"
          [disabled]="!selectedDate() || !selectedTime()"
          class="btn btn-primary"
        >
          Перенести
        </button>
      </div>
    </app-modal>
  `,
  styles: [`
    .modal-content {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .info-card {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1rem;
      background: var(--color-surface-secondary);
      border-radius: var(--radius-lg);
    }

    .info-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--color-brand-50);
      color: var(--color-brand-500);
      border-radius: var(--radius-md);
      flex-shrink: 0;
    }

    :host-context(.dark) .info-icon {
      background: rgba(236, 72, 153, 0.15);
    }

    .info-icon svg {
      width: 20px;
      height: 20px;
    }

    .info-content {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    .info-label {
      font-size: 0.75rem;
      color: var(--color-text-tertiary);
    }

    .info-value {
      font-size: 0.9375rem;
      font-weight: 500;
      color: var(--color-text-primary);
    }

    .section-label {
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-secondary);
      margin-bottom: 0.75rem;
    }

    /* Mini Calendar */
    .mini-calendar {
      background: var(--color-surface-primary);
      border: 1px solid var(--color-border-secondary);
      border-radius: var(--radius-lg);
      padding: 0.75rem;
    }

    .calendar-weekdays {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 0.25rem;
      margin-bottom: 0.5rem;
    }

    .weekday {
      font-size: 0.6875rem;
      font-weight: 600;
      color: var(--color-text-tertiary);
      text-align: center;
      padding: 0.25rem;
      text-transform: uppercase;
    }

    .calendar-days {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 0.25rem;
    }

    .calendar-day {
      aspect-ratio: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-text-primary);
      background: transparent;
      border: none;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .calendar-day:hover:not(.disabled):not(.selected) {
      background: var(--color-surface-hover);
    }

    .calendar-day.today:not(.selected) {
      background: var(--color-brand-50);
      color: var(--color-brand-600);
    }

    :host-context(.dark) .calendar-day.today:not(.selected) {
      background: rgba(236, 72, 153, 0.15);
      color: var(--color-brand-400);
    }

    .calendar-day.selected {
      background: var(--color-brand-500);
      color: white;
    }

    .calendar-day.disabled {
      color: var(--color-text-tertiary);
      opacity: 0.4;
      cursor: not-allowed;
    }

    .calendar-day.other-month:not(.disabled) {
      color: var(--color-text-tertiary);
    }

    /* Time Section */
    .time-section {
      padding-top: 0.25rem;
    }

    .loading-slots {
      display: flex;
      justify-content: center;
      padding: 1.5rem 0;
    }

    .spinner {
      width: 24px;
      height: 24px;
      border: 2px solid var(--color-border-primary);
      border-top-color: var(--color-brand-500);
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .empty-slots {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 1.5rem;
      color: var(--color-text-tertiary);
      font-size: 0.875rem;
    }

    .empty-slots svg {
      width: 32px;
      height: 32px;
      opacity: 0.5;
    }

    .time-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.5rem;
    }

    @media (max-width: 480px) {
      .time-grid {
        grid-template-columns: repeat(3, 1fr);
      }
    }

    .time-slot {
      padding: 0.625rem 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-primary);
      background: var(--color-surface-primary);
      border: 1px solid var(--color-border-primary);
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .time-slot:hover:not(.selected) {
      border-color: var(--color-brand-300);
    }

    .time-slot.selected {
      background: var(--color-brand-50);
      border-color: var(--color-brand-500);
      color: var(--color-brand-600);
    }

    :host-context(.dark) .time-slot.selected {
      background: rgba(236, 72, 153, 0.15);
      color: var(--color-brand-400);
    }

    /* Modal Actions */
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      padding: 1rem 1.5rem;
      border-top: 1px solid var(--color-border-secondary);
      flex-shrink: 0;
    }
  `]
})
export class RescheduleModalComponent implements OnChanges {
  isOpen = input<boolean>(false);
  appointment = input<Appointment | null>(null);
  close = output<void>();
  reschedule = output<{ date: string; time: string }>();

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  dateService = inject(DateService);

  selectedDate = signal<string>('');
  selectedTime = signal<string>('');
  availableSlots = signal<string[]>([]);
  isLoadingSlots = signal(false);
  todayStr = this.dateService.todayStr();

  weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  calendarDays = signal<{
    date: string;
    dayNum: number;
    isCurrentMonth: boolean;
    isPast: boolean;
    isToday: boolean;
  }[]>([]);

  ngOnChanges(): void {
    if (this.isOpen()) {
      this.calendarDays.set(this.dateService.generateCalendarMonth());
      this.selectedDate.set('');
      this.selectedTime.set('');
    }
  }

  selectDate(date: string): void {
    this.selectedDate.set(date);
    this.selectedTime.set('');
    this.loadSlots(date);
  }

  /** Загружает доступные слоты и фильтрует прошедшие, если выбран сегодняшний день */
  private loadSlots(date: string): void {
    const apt = this.appointment();
    const masterId = this.authService.masterData()?.id;
    if (!apt || !masterId) return;

    this.isLoadingSlots.set(true);
    this.dataService.getAvailableSlots(masterId, date, apt.duration).subscribe(slots => {
      const filtered = this.dateService.filterPastSlots(date, slots);
      this.availableSlots.set(filtered);
      this.isLoadingSlots.set(false);
    });
  }

  formatDate(dateStr: string): string {
    return this.dateService.formatDateLong(dateStr);
  }

  onReschedule(): void {
    if (this.selectedDate() && this.selectedTime()) {
      this.reschedule.emit({
        date: this.selectedDate(),
        time: this.selectedTime()
      });
    }
  }
}
