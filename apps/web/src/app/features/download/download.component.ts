import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-download',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './download.component.html',
  styleUrl: './download.component.scss'
})
export class DownloadComponent {
  selected: 'ios' | 'android' | null = null;

  selectPlatform(platform: 'ios' | 'android'): void {
    this.selected = platform;
  }

  back(): void {
    this.selected = null;
  }
}
