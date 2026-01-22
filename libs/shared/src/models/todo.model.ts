export type TodoStatus = 'todo' | 'in_progress' | 'done';

export interface TodoItem {
  id: string;
  masterId: string;
  title: string;
  description?: string;
  date: string;
  time?: string;
  status: TodoStatus;
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  updatedAt: Date;
}

export const TODO_STATUS_LABELS: Record<TodoStatus, string> = {
  todo: 'К выполнению',
  in_progress: 'В процессе',
  done: 'Готово'
};

export const TODO_PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-700'
};
