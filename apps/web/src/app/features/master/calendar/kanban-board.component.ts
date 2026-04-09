import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TodoItem, TodoStatus, TODO_STATUS_LABELS, TODO_PRIORITY_COLORS } from '../../../core/models';

@Component({
  selector: 'app-kanban-board',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="kanban-grid">
      @for (column of columns; track column.status) {
        <div
          class="kanban-column"
          (dragover)="onDragOver($event, column.status)"
          (dragleave)="onDragLeave()"
          (drop)="onDrop($event, column.status)"
          [class.drag-over]="dragOverColumn() === column.status"
        >
          <!-- Column Header -->
          <div class="column-header">
            <div class="column-title">
              <span class="column-dot" [ngClass]="column.color"></span>
              <h3>{{ column.label }}</h3>
              <span class="column-count">{{ getColumnTodos(column.status).length }}</span>
            </div>
            <button
              type="button"
              (click)="startAddingTo(column.status)"
              class="btn btn-ghost btn-icon-sm"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
            </button>
          </div>

          <!-- Add Form -->
          @if (addingToColumn() === column.status) {
            <div class="add-form animate-fadeIn">
              <input
                type="text"
                [(ngModel)]="newTodoTitle"
                (keyup.enter)="addTodo(column.status)"
                (keyup.escape)="cancelAdd()"
                placeholder="Введите задачу..."
                class="input"
                autofocus
              />
              <div class="add-form-actions">
                <button
                  type="button"
                  (click)="addTodo(column.status)"
                  class="btn btn-primary btn-sm"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                  </svg>
                  Добавить
                </button>
                <button
                  type="button"
                  (click)="cancelAdd()"
                  class="btn btn-ghost btn-sm"
                >
                  Отмена
                </button>
              </div>
            </div>
          }

          <!-- Tasks -->
          <div class="column-tasks">
            @for (todo of getColumnTodos(column.status); track todo.id) {
              <div
                draggable="true"
                (dragstart)="onDragStart($event, todo)"
                (dragend)="onDragEnd()"
                class="task-card"
                [class.dragging]="draggedTodo()?.id === todo.id"
              >
                <div class="task-header">
                  <p class="task-title">{{ todo.title }}</p>
                  <button
                    type="button"
                    (click)="todoDeleted.emit(todo.id)"
                    class="task-delete btn btn-ghost btn-icon-sm"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                  </button>
                </div>
                @if (todo.description) {
                  <p class="task-description">{{ todo.description }}</p>
                }
                <div class="task-footer">
                  <span class="priority-badge" [ngClass]="getPriorityColor(todo.priority)">
                    {{ getPriorityLabel(todo.priority) }}
                  </span>
                </div>
              </div>
            } @empty {
              <div class="empty-column">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                </svg>
                <p>Нет задач</p>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .kanban-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.25rem;
    }

    @media (max-width: 768px) {
      .kanban-grid {
        grid-template-columns: 1fr;
      }
    }

    .kanban-column {
      background: var(--color-surface-primary);
      border: 1px solid var(--color-border-secondary);
      border-radius: var(--radius-xl);
      padding: 1rem;
      min-height: 400px;
      transition: all 200ms ease;

      &.drag-over {
        border-color: var(--color-brand-400);
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15);
      }
    }

    .column-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--color-border-secondary);
    }

    .column-title {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      h3 {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--color-text-primary);
      }
    }

    .column-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }

    .column-count {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-text-tertiary);
      background: var(--color-surface-secondary);
      padding: 0.125rem 0.5rem;
      border-radius: var(--radius-full);
    }

    .add-form {
      background: var(--color-surface-secondary);
      border-radius: var(--radius-lg);
      padding: 0.75rem;
      margin-bottom: 0.75rem;
    }

    .add-form-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }

    .column-tasks {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .task-card {
      background: var(--color-surface-secondary);
      border-radius: var(--radius-lg);
      padding: 0.875rem;
      cursor: grab;
      transition: all 150ms ease;

      &:hover {
        box-shadow: var(--shadow-md);

        .task-delete {
          opacity: 1;
        }
      }

      &:active {
        cursor: grabbing;
      }

      &.dragging {
        opacity: 0.5;
        transform: rotate(2deg);
      }
    }

    .task-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.5rem;
    }

    .task-title {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-primary);
      flex: 1;
    }

    .task-delete {
      opacity: 0;
      transition: opacity 150ms ease;
      color: var(--color-text-tertiary);

      &:hover {
        color: var(--color-error);
      }
    }

    .task-description {
      font-size: 0.75rem;
      color: var(--color-text-tertiary);
      margin-top: 0.375rem;
    }

    .task-footer {
      margin-top: 0.625rem;
    }

    .priority-badge {
      font-size: 0.6875rem;
      font-weight: 600;
      padding: 0.25rem 0.5rem;
      border-radius: var(--radius-sm);
    }

    .empty-column {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem 1rem;
      color: var(--color-text-disabled);

      svg {
        width: 2rem;
        height: 2rem;
        max-width: 32px;
        max-height: 32px;
        margin-bottom: 0.5rem;
      }

      p {
        font-size: 0.875rem;
      }
    }

    /* Priority colors */
    .bg-green-100 {
      background: var(--color-success-bg);
      color: var(--color-success);
    }

    .bg-yellow-100 {
      background: var(--color-warning-bg);
      color: var(--color-warning);
    }

    .bg-red-100 {
      background: var(--color-error-bg);
      color: var(--color-error);
    }

    /* Column colors */
    .bg-slate-400 {
      background: #94a3b8;
    }

    .bg-blue-500 {
      background: #3b82f6;
    }

    .bg-green-500 {
      background: #22c55e;
    }

    /* Animation */
    .animate-fadeIn {
      animation: fadeIn 200ms ease-out;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    /* Mobile 320-767px */
    @media (max-width: 767px) {
      .kanban-grid {
        gap: 0.75rem;
      }

      .kanban-column {
        padding: 0.75rem;
        min-height: 200px;
      }

      .column-header {
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
      }

      .column-title {
        gap: 0.375rem;

        h3 {
          font-size: 0.8125rem;
        }
      }

      .column-dot {
        width: 8px;
        height: 8px;
      }

      .column-count {
        font-size: 0.6875rem;
        padding: 0.0625rem 0.375rem;
      }

      .add-form {
        padding: 0.5rem;
        margin-bottom: 0.5rem;
      }

      .task-card {
        padding: 0.625rem;
      }

      .task-title {
        font-size: 0.8125rem;
      }

      .task-description {
        font-size: 0.6875rem;
      }

      .task-footer {
        margin-top: 0.5rem;
      }

      .priority-badge {
        font-size: 0.625rem;
        padding: 0.1875rem 0.375rem;
      }

      .task-delete {
        opacity: 1;
      }

      .empty-column {
        padding: 1.5rem 0.75rem;

        svg {
          width: 1.5rem;
          height: 1.5rem;
          max-width: 24px;
          max-height: 24px;
        }

        p {
          font-size: 0.75rem;
        }
      }
    }
  `]
})
export class KanbanBoardComponent {
  todos = input<TodoItem[]>([]);
  todoUpdated = output<{ id: string; status: string }>();
  todoAdded = output<{ title: string; status: string }>();
  todoDeleted = output<string>();

  addingToColumn = signal<TodoStatus | null>(null);
  newTodoTitle = '';
  draggedTodo = signal<TodoItem | null>(null);
  dragOverColumn = signal<TodoStatus | null>(null);

  columns: { status: TodoStatus; label: string; color: string }[] = [
    { status: 'todo', label: 'К выполнению', color: 'bg-slate-400' },
    { status: 'in_progress', label: 'В процессе', color: 'bg-blue-500' },
    { status: 'done', label: 'Готово', color: 'bg-green-500' }
  ];

  getColumnTodos(status: TodoStatus): TodoItem[] {
    return this.todos().filter(t => t.status === status);
  }

  getPriorityColor(priority: string): string {
    return TODO_PRIORITY_COLORS[priority] || TODO_PRIORITY_COLORS['medium'];
  }

  getPriorityLabel(priority: string): string {
    const labels: Record<string, string> = {
      low: 'Низкий',
      medium: 'Средний',
      high: 'Высокий'
    };
    return labels[priority] || priority;
  }

  startAddingTo(status: TodoStatus): void {
    this.addingToColumn.set(status);
    this.newTodoTitle = '';
  }

  cancelAdd(): void {
    this.addingToColumn.set(null);
    this.newTodoTitle = '';
  }

  addTodo(status: TodoStatus): void {
    if (!this.newTodoTitle.trim()) return;

    this.todoAdded.emit({
      title: this.newTodoTitle.trim(),
      status
    });

    this.cancelAdd();
  }

  onDragStart(event: DragEvent, todo: TodoItem): void {
    // Prevent dragging todos without valid IDs
    if (!todo.id) {
      event.preventDefault();
      return;
    }
    this.draggedTodo.set(todo);
    event.dataTransfer?.setData('text/plain', todo.id);
    event.dataTransfer!.effectAllowed = 'move';
  }

  onDragEnd(): void {
    this.draggedTodo.set(null);
    this.dragOverColumn.set(null);
  }

  onDragOver(event: DragEvent, status: TodoStatus): void {
    event.preventDefault();
    event.dataTransfer!.dropEffect = 'move';
    this.dragOverColumn.set(status);
  }

  onDragLeave(): void {
    this.dragOverColumn.set(null);
  }

  onDrop(event: DragEvent, status: TodoStatus): void {
    event.preventDefault();
    const todoId = event.dataTransfer?.getData('text/plain');

    // Validate todoId before emitting update - prevent undefined/null/empty IDs
    if (todoId && todoId !== 'undefined' && todoId !== 'null' && this.draggedTodo()) {
      const todo = this.draggedTodo()!;
      if (todo.status !== status) {
        this.todoUpdated.emit({ id: todoId, status });
      }
    }

    this.draggedTodo.set(null);
    this.dragOverColumn.set(null);
  }
}
