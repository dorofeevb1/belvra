import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent, SidebarComponent, NavItem } from '../../shared/components';
import { NotificationToastComponent } from '../../shared/components/notification-toast.component';
import { DataService } from '../../core/services';

@Component({
  selector: 'app-client-view',
  standalone: true,
  imports: [CommonModule, RouterOutlet, HeaderComponent, SidebarComponent, NotificationToastComponent],
  templateUrl: './client-view.component.html',
  styleUrl: './client-view.component.scss'
})
export class ClientViewComponent implements OnInit {
  private dataService = inject(DataService);
  sidebarOpen = signal(false);

  navItems: NavItem[] = [
    {
      label: 'Поиск мастеров',
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>',
      route: '/client'
    },
    {
      label: 'Мои записи',
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>',
      route: '/client/my-appointments'
    },
    {
      label: 'Чаты',
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>',
      route: '/client/chat'
    },
    {
      label: 'Избранное',
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>',
      route: '/client/favorites'
    },
    {
      label: 'Профиль',
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>',
      route: '/client/profile'
    }
  ];

  ngOnInit(): void {
    this.loadUnreadCount();
  }

  private loadUnreadCount(): void {
    this.dataService.getAllChats().subscribe(chats => {
      const total = chats.reduce((sum, c) => sum + c.unreadCount, 0);
      const chatItem = this.navItems.find(i => i.route === '/client/chat');
      if (chatItem) chatItem.badge = total;
    });
  }
}
