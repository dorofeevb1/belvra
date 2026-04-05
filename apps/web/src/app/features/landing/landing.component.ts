import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingPageComponent {
  mobileMenuOpen = false;
  headerSolid = false;

  @HostListener('window:scroll')
  onScroll(): void {
    this.headerSolid = window.scrollY > 50;
  }

  scrollTo(id: string): void {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    this.mobileMenuOpen = false;
  }
}
