import { Injectable, inject, Renderer2, RendererFactory2 } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private renderer: Renderer2;
  private isDarkMode = new BehaviorSubject<boolean>(false);
  isDarkMode$ = this.isDarkMode.asObservable();

  constructor(rendererFactory: RendererFactory2) {
    this.renderer = rendererFactory.createRenderer(null, null);
    this.loadTheme();
  }

  toggleTheme() {
    const newMode = !this.isDarkMode.value;
    this.isDarkMode.next(newMode);
    this.applyTheme(newMode);
    localStorage.setItem('theme', newMode ? 'dark' : 'light');
  }

  private applyTheme(isDark: boolean) {
    const body = document.body;
    if (isDark) {
      this.renderer.setAttribute(body, 'data-theme', 'dark');
    } else {
      this.renderer.removeAttribute(body, 'data-theme');
    }
  }

  private loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    const isDark = savedTheme === 'dark';
    this.isDarkMode.next(isDark);
    this.applyTheme(isDark);
  }

  getCurrentTheme(): boolean {
    return this.isDarkMode.value;
  }
}