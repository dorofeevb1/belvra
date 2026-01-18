import { Injectable, signal, effect } from '@angular/core';

export type Theme = 'light' | 'dark';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private themeSignal = signal<Theme>(this.getInitialTheme());

  readonly theme = this.themeSignal.asReadonly();
  readonly isDark = () => this.themeSignal() === 'dark';

  constructor() {
    effect(() => {
      const theme = this.themeSignal();
      this.applyTheme(theme);
      localStorage.setItem('beautybook_theme', theme);
    });
  }

  private getInitialTheme(): Theme {
    const stored = localStorage.getItem('beautybook_theme') as Theme | null;
    if (stored) return stored;

    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  private applyTheme(theme: Theme): void {
    const html = document.documentElement;
    if (theme === 'dark') {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  }

  toggleTheme(): void {
    this.themeSignal.update(current => current === 'light' ? 'dark' : 'light');
  }

  setTheme(theme: Theme): void {
    this.themeSignal.set(theme);
  }
}
