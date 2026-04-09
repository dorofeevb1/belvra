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
    // Close menu on scroll
    if (this.mobileMenuOpen) {
      this.toggleMenu(false);
    }
  }

  toggleMenu(state?: boolean): void {
    this.mobileMenuOpen = state ?? !this.mobileMenuOpen;
    // Block body scroll when menu is open
    document.body.style.overflow = this.mobileMenuOpen ? 'hidden' : '';
  }

  scrollTo(id: string): void {
    this.toggleMenu(false);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  }
}
