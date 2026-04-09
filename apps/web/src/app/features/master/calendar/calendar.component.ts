import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, DataService, DateService, ApiService } from '../../../core/services';
import { Appointment, TodoItem, APPOINTMENT_STATUS_COLORS, APPOINTMENT_STATUS_LABELS } from '../../../core/models';
import { KanbanBoardComponent } from './kanban-board.component';
import { ModalComponent } from '../../../shared/components/modal.component';
import dayjs from 'dayjs';

@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [CommonModule, FormsModule, KanbanBoardComponent, ModalComponent],
  templateUrl: './calendar.component.html',
  styleUrl: './calendar.component.scss'
})
export class CalendarComponent implements OnInit, OnDestroy {
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private dateService = inject(DateService);
  private apiService = inject(ApiService);
  private timeInterval: ReturnType<typeof setInterval> | null = null;

  viewMode = signal<'calendar' | 'kanban'>('calendar');
  mobileViewMode = signal<'week' | 'day'>('day');
  selectedDayIndex = signal(new Date().getDay() === 0 ? 6 : new Date().getDay() - 1);
  currentWeekStart = signal(this.dateService.getWeekStart());
  appointments = signal<Appointment[]>([]);
  allTodos = signal<TodoItem[]>([]);
  showQuickAdd = signal(false);
  newTodoTitle = '';
  currentTime = signal(dayjs());

  // Modal state
  showAppointmentModal = signal(false);
  showCreateModal = signal(false);
  showRescheduleModal = signal(false);
  selectedAppointment = signal<Appointment | null>(null);
  createSlot = signal<{ date: string; hour: number } | null>(null);

  // Reschedule state
  rescheduleDate = signal('');
  rescheduleTime = signal('');

  // Reminder form state
  reminderTitle = signal('');
  reminderTime = signal('');
  reminderPriority = signal<'low' | 'medium' | 'high'>('medium');
  isSavingReminder = signal(false);

  // Reminder detail/edit modal state
  showReminderModal = signal(false);
  showRescheduleReminderModal = signal(false);
  showSlotRemindersModal = signal(false);
  selectedReminder = signal<TodoItem | null>(null);
  selectedSlot = signal<{ date: string; hour: number } | null>(null);
  reminderNewDate = signal('');
  reminderNewTime = signal('');
  isReschedulingReminder = signal(false);
  isRescheduling = signal(false);

  // Dynamic time slots based on schedule (default 8-23, updated from API)
  private _startHour = 8;
  private _endHour = 23;
  timeSlots = Array.from({ length: 15 }, (_, i) => i + 8);
  availableTimeSlots = this.generateTimeSlots(8, 23);

  weekDays = computed(() => {
    const start = this.currentWeekStart();
    return this.dateService.getWeekDays(start);
  });

  weekRangeText = computed(() => {
    return this.dateService.getWeekRangeText(this.currentWeekStart());
  });

  selectedDay = computed(() => {
    const days = this.weekDays();
    return days[this.selectedDayIndex()] || days[0];
  });

  todayTodos = computed(() => {
    const today = this.dateService.todayStr();
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return this.allTodos()
      .filter(t => t.date === today)
      .sort((a, b) => {
        // Sort by priority first (high > medium > low)
        const priorityDiff = (priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1);
        if (priorityDiff !== 0) return priorityDiff;
        // Then by time if available
        if (a.time && b.time) return a.time.localeCompare(b.time);
        if (a.time) return -1;
        if (b.time) return 1;
        return 0;
      });
  });

  completedTodosCount = computed(() => {
    return this.todayTodos().filter(t => t.status === 'done').length;
  });

  isCurrentWeek = computed(() => {
    const now = dayjs();
    const weekStart = this.currentWeekStart();
    const weekEnd = weekStart.add(6, 'day');
    return now.isAfter(weekStart.subtract(1, 'day')) && now.isBefore(weekEnd.add(1, 'day'));
  });

  currentTimePosition = computed(() => {
    const now = this.currentTime();
    const hour = now.hour();
    const minute = now.minute();

    if (hour < this._startHour || hour >= this._endHour) return null;

    const rowIndex = hour - this._startHour;
    const pixelOffset = (minute / 60) * 64;
    return rowIndex * 64 + pixelOffset;
  });

  todayColumnIndex = computed(() => {
    const today = this.dateService.todayStr();
    const days = this.weekDays();
    return days.findIndex(d => d.date === today);
  });

  ngOnInit(): void {
    this.loadData();
    this.startTimeUpdater();
    // Set selected day to today if it's in current week
    const todayIdx = this.todayColumnIndex();
    if (todayIdx >= 0) {
      this.selectedDayIndex.set(todayIdx);
    }
  }

  ngOnDestroy(): void {
    if (this.timeInterval) {
      clearInterval(this.timeInterval);
    }
  }

  private startTimeUpdater(): void {
    this.timeInterval = setInterval(() => {
      this.currentTime.set(dayjs());
    }, 60000);
  }

  private generateTimeSlots(startHour: number, endHour: number): string[] {
    const slots: string[] = [];
    for (let h = startHour; h < endHour; h++) {
      slots.push(`${h.toString().padStart(2, '0')}:00`);
      slots.push(`${h.toString().padStart(2, '0')}:30`);
    }
    slots.push(`${endHour.toString().padStart(2, '0')}:00`);
    return slots;
  }

  private loadData(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    /** Показываем все активные записи: pending, confirmed, in_progress и completed */
    this.dataService.getAppointments(masterId).subscribe(data => {
      this.appointments.set(data.filter(a =>
        a.status === 'pending' || a.status === 'confirmed' ||
        a.status === 'in_progress' || a.status === 'completed'
      ));
    });

    this.dataService.getTodos(masterId).subscribe(data => {
      this.allTodos.set(data);
    });

    // Load schedules to determine time range
    this.apiService.get<any[]>('/appointments/schedules/').subscribe((schedules: any[]) => {
      if (schedules && schedules.length > 0) {
        const working = schedules.filter((s: any) => s.is_working);
        if (working.length > 0) {
          const minHour = Math.min(...working.map((s: any) => parseInt(s.start_time?.split(':')[0] || '9', 10)));
          const maxHour = Math.max(...working.map((s: any) => parseInt(s.end_time?.split(':')[0] || '20', 10)));
          this._startHour = minHour;
          this._endHour = maxHour;
          this.timeSlots = Array.from({ length: maxHour - minHour }, (_, i) => i + minHour);
          this.availableTimeSlots = this.generateTimeSlots(minHour, maxHour);
        }
      }
    });
  }

  navigateWeek(direction: number): void {
    const current = this.currentWeekStart();
    this.currentWeekStart.set(current.add(direction * 7, 'day'));
  }

  goToToday(): void {
    this.currentWeekStart.set(this.dateService.getWeekStart());
    const todayIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;
    this.selectedDayIndex.set(todayIdx);
  }

  selectDay(index: number): void {
    this.selectedDayIndex.set(index);
  }

  navigateDay(direction: number): void {
    const current = this.selectedDayIndex();
    const newIndex = current + direction;

    if (newIndex < 0) {
      this.navigateWeek(-1);
      this.selectedDayIndex.set(6);
    } else if (newIndex > 6) {
      this.navigateWeek(1);
      this.selectedDayIndex.set(0);
    } else {
      this.selectedDayIndex.set(newIndex);
    }
  }

  getAppointmentsForSlot(date: string, hour: number): Appointment[] {
    return this.appointments().filter(apt => {
      if (apt.date !== date) return false;
      const aptHour = this.dateService.getHourFromTime(apt.startTime);
      return aptHour === hour;
    });
  }

  getRemindersForSlot(date: string, hour: number): TodoItem[] {
    return this.allTodos().filter(todo => {
      if (todo.date !== date || !todo.time) return false;
      const todoHour = this.dateService.getHourFromTime(todo.time);
      return todoHour === hour;
    });
  }

  getRemindersForDay(date: string): TodoItem[] {
    return this.allTodos()
      .filter(todo => todo.date === date && todo.time)
      .sort((a, b) => (a.time || '').localeCompare(b.time || ''));
  }

  getAppointmentsForDay(date: string): Appointment[] {
    return this.appointments()
      .filter(apt => apt.date === date)
      .sort((a, b) => a.startTime.localeCompare(b.startTime));
  }

  getAppointmentTop(startTime: string, hour: number): number {
    const h = this.dateService.getHourFromTime(startTime);
    const m = this.dateService.getMinuteFromTime(startTime);
    if (h !== hour) return 0;
    return (m / 60) * 64;
  }

  getAppointmentHeight(duration: number): number {
    return (duration / 60) * 64;
  }

  // Get positioning for overlapping items in the same slot
  getAppointmentStyle(apt: Appointment, date: string, hour: number): { [key: string]: string } {
    const appointments = this.getAppointmentsForSlot(date, hour);

    // Group by start time
    const sameTimeApts = appointments.filter(a => a.startTime === apt.startTime);
    const idx = sameTimeApts.findIndex(a => a.id === apt.id);
    const total = sameTimeApts.length;

    const top = this.getAppointmentTop(apt.startTime, hour);
    const height = this.getAppointmentHeight(apt.duration);

    if (total <= 1) {
      return {
        'top': `${top}px`,
        'height': `${height}px`,
        'left': '3px',
        'right': '3px'
      };
    }

    // Split horizontally for multiple appointments
    const widthPercent = (100 - 6) / total;
    const leftOffset = 3 + idx * widthPercent;

    return {
      'top': `${top}px`,
      'height': `${height}px`,
      'left': `calc(${leftOffset}%)`,
      'width': `calc(${widthPercent}% - 2px)`
    };
  }

  getReminderStyle(reminder: TodoItem, date: string, hour: number): { [key: string]: string } | null {
    const appointments = this.getAppointmentsForSlot(date, hour);
    const reminders = this.getRemindersForSlot(date, hour);

    // Group reminders by time
    const sameTimeReminders = reminders.filter(r => r.time === reminder.time);
    const idx = sameTimeReminders.findIndex(r => r.id === reminder.id);

    const top = this.getAppointmentTop(reminder.time!, hour);

    // Check if there's an appointment at the same time
    const hasAppointmentAtSameTime = appointments.some(a => a.startTime === reminder.time);

    // Calculate available space (64px per hour slot)
    const slotHeight = 64;
    const reminderHeight = 22;
    let startY = top;

    if (hasAppointmentAtSameTime) {
      startY = top + 28;
    }

    const positionY = startY + idx * reminderHeight;

    // Check if this reminder would overflow the slot
    if (positionY + reminderHeight > slotHeight) {
      return null; // Don't render this reminder
    }

    return {
      'top': `${positionY}px`,
      'left': '3px',
      'right': '3px'
    };
  }

  // Get count of hidden reminders for a slot
  getHiddenRemindersCount(date: string, hour: number): number {
    const appointments = this.getAppointmentsForSlot(date, hour);
    const reminders = this.getRemindersForSlot(date, hour);

    if (reminders.length === 0) return 0;

    const slotHeight = 64;
    const reminderHeight = 22;

    // Group by time and count visible
    let hiddenCount = 0;

    const timeGroups = new Map<string, TodoItem[]>();
    reminders.forEach(r => {
      const time = r.time || '';
      if (!timeGroups.has(time)) {
        timeGroups.set(time, []);
      }
      timeGroups.get(time)!.push(r);
    });

    timeGroups.forEach((groupReminders, time) => {
      const top = this.getAppointmentTop(time, hour);
      const hasAppointmentAtSameTime = appointments.some(a => a.startTime === time);
      let startY = hasAppointmentAtSameTime ? top + 28 : top;

      groupReminders.forEach((_, idx) => {
        const positionY = startY + idx * reminderHeight;
        if (positionY + reminderHeight > slotHeight) {
          hiddenCount++;
        }
      });
    });

    return hiddenCount;
  }

  // Get all reminders for a slot (for modal)
  getAllRemindersForSlot(date: string, hour: number): TodoItem[] {
    return this.getRemindersForSlot(date, hour);
  }

  // Show all reminders for a slot in modal
  showAllSlotReminders(date: string, hour: number, event: Event): void {
    event.stopPropagation();
    this.selectedSlot.set({ date, hour });
    this.showSlotRemindersModal.set(true);
  }

  closeSlotRemindersModal(): void {
    this.showSlotRemindersModal.set(false);
    this.selectedSlot.set(null);
  }

  getSelectedSlotReminders(): TodoItem[] {
    const slot = this.selectedSlot();
    if (!slot) return [];
    return this.getRemindersForSlot(slot.date, slot.hour);
  }

  getAppointmentColor(status: string): string {
    return APPOINTMENT_STATUS_COLORS[status as keyof typeof APPOINTMENT_STATUS_COLORS] || 'bg-slate-100';
  }

  getStatusLabel(status: string): string {
    return APPOINTMENT_STATUS_LABELS[status as keyof typeof APPOINTMENT_STATUS_LABELS] || status;
  }

  // Appointment interactions
  onAppointmentClick(appointment: Appointment, event: Event): void {
    event.stopPropagation();
    this.selectedAppointment.set(appointment);
    this.showAppointmentModal.set(true);
  }

  onCellClick(date: string, hour: number): void {
    this.createSlot.set({ date, hour });
    this.reminderTime.set(`${hour.toString().padStart(2, '0')}:00`);
    this.reminderTitle.set('');
    this.reminderPriority.set('medium');
    this.showCreateModal.set(true);
  }

  closeAppointmentModal(): void {
    this.showAppointmentModal.set(false);
    this.selectedAppointment.set(null);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
    this.createSlot.set(null);
    this.reminderTitle.set('');
    this.reminderTime.set('');
    this.reminderPriority.set('medium');
  }

  saveReminder(): void {
    const slot = this.createSlot();
    const title = this.reminderTitle().trim();
    const time = this.reminderTime();

    if (!slot || !title) return;

    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.isSavingReminder.set(true);

    this.dataService.addTodo({
      masterId,
      title,
      date: slot.date,
      time,
      status: 'todo',
      priority: this.reminderPriority()
    }).subscribe({
      next: (newTodo) => {
        this.allTodos.update(todos => [...todos, newTodo]);
        this.isSavingReminder.set(false);
        this.closeCreateModal();
      },
      error: () => {
        this.isSavingReminder.set(false);
      }
    });
  }

  // Reschedule methods
  openRescheduleModal(): void {
    const apt = this.selectedAppointment();
    if (apt) {
      this.rescheduleDate.set(apt.date);
      this.rescheduleTime.set(apt.startTime);
      this.showAppointmentModal.set(false);
      this.showRescheduleModal.set(true);
    }
  }

  closeRescheduleModal(): void {
    this.showRescheduleModal.set(false);
    this.rescheduleDate.set('');
    this.rescheduleTime.set('');
  }

  confirmReschedule(): void {
    const apt = this.selectedAppointment();
    const newDate = this.rescheduleDate();
    const newTime = this.rescheduleTime();

    if (!apt || !newDate || !newTime) return;

    this.isRescheduling.set(true);

    this.dataService.rescheduleAppointment(apt.id, newDate, newTime).subscribe({
      next: (updated) => {
        this.appointments.update(appointments =>
          appointments.map(a => a.id === apt.id ? updated : a)
        );
        this.isRescheduling.set(false);
        this.closeRescheduleModal();
        this.selectedAppointment.set(null);
      },
      error: () => {
        this.isRescheduling.set(false);
      }
    });
  }

  getMinDate(): string {
    return dayjs().format('YYYY-MM-DD');
  }

  formatDate(dateStr: string): string {
    return dayjs(dateStr).format('D MMMM YYYY');
  }

  formatEndTime(startTime: string, duration: number): string {
    const [h, m] = startTime.split(':').map(Number);
    const totalMinutes = h * 60 + m + duration;
    const endH = Math.floor(totalMinutes / 60);
    const endM = totalMinutes % 60;
    return `${endH.toString().padStart(2, '0')}:${endM.toString().padStart(2, '0')}`;
  }

  // Todo methods
  addQuickTodo(): void {
    this.showQuickAdd.set(true);
  }

  saveQuickTodo(): void {
    if (!this.newTodoTitle.trim()) return;

    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.dataService.addTodo({
      masterId,
      title: this.newTodoTitle.trim(),
      date: this.dateService.todayStr(),
      status: 'todo',
      priority: 'medium'
    }).subscribe(newTodo => {
      this.allTodos.update(todos => [...todos, newTodo]);
      this.newTodoTitle = '';
      this.showQuickAdd.set(false);
    });
  }

  toggleTodo(todo: TodoItem): void {
    const newStatus = todo.status === 'done' ? 'todo' : 'done';
    this.dataService.updateTodoStatus(todo.id, newStatus).subscribe(() => {
      this.allTodos.update(todos =>
        todos.map(t => t.id === todo.id ? { ...t, status: newStatus } : t)
      );
    });
  }

  deleteTodo(id: string): void {
    this.dataService.deleteTodo(id).subscribe(() => {
      this.allTodos.update(todos => todos.filter(t => t.id !== id));
    });
  }

  // Reminder modal methods
  onReminderClick(reminder: TodoItem, event: Event): void {
    event.stopPropagation();
    this.selectedReminder.set(reminder);
    this.showReminderModal.set(true);
  }

  closeReminderModal(): void {
    this.showReminderModal.set(false);
    this.selectedReminder.set(null);
  }

  deleteReminder(): void {
    const reminder = this.selectedReminder();
    if (!reminder) return;

    this.dataService.deleteTodo(reminder.id).subscribe(() => {
      this.allTodos.update(todos => todos.filter(t => t.id !== reminder.id));
      this.closeReminderModal();
    });
  }

  openRescheduleReminderModal(): void {
    const reminder = this.selectedReminder();
    if (reminder) {
      this.reminderNewDate.set(reminder.date);
      this.reminderNewTime.set(reminder.time || '');
      this.showReminderModal.set(false);
      this.showRescheduleReminderModal.set(true);
    }
  }

  closeRescheduleReminderModal(): void {
    this.showRescheduleReminderModal.set(false);
    this.reminderNewDate.set('');
    this.reminderNewTime.set('');
  }

  confirmRescheduleReminder(): void {
    const reminder = this.selectedReminder();
    const newDate = this.reminderNewDate();
    const newTime = this.reminderNewTime();

    if (!reminder || !newDate || !newTime) return;

    this.isReschedulingReminder.set(true);

    // Update todo with new date and time
    this.dataService.updateTodo(reminder.id, { date: newDate, time: newTime }).subscribe({
      next: () => {
        this.allTodos.update(todos =>
          todos.map(t => t.id === reminder.id ? { ...t, date: newDate, time: newTime } : t)
        );
        this.isReschedulingReminder.set(false);
        this.closeRescheduleReminderModal();
        this.selectedReminder.set(null);
      },
      error: () => {
        this.isReschedulingReminder.set(false);
      }
    });
  }

  isOverdue(todo: TodoItem): boolean {
    if (todo.status === 'done') return false;
    const now = dayjs();
    if (todo.time) {
      return dayjs(`${todo.date} ${todo.time}`).isBefore(now);
    }
    return dayjs(todo.date).endOf('day').isBefore(now);
  }

  onTodoUpdated(event: { id: string; status: string }): void {
    this.dataService.updateTodoStatus(event.id, event.status as any).subscribe(() => {
      this.allTodos.update(todos =>
        todos.map(t => t.id === event.id ? { ...t, status: event.status as any } : t)
      );
    });
  }

  onTodoAdded(event: { title: string; status: string }): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.dataService.addTodo({
      masterId,
      title: event.title,
      date: this.dateService.todayStr(),
      status: event.status as any,
      priority: 'medium'
    }).subscribe(newTodo => {
      this.allTodos.update(todos => [...todos, newTodo]);
    });
  }
}
