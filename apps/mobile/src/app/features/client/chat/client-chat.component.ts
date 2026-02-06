import { Component, inject, OnInit, signal, computed, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { AuthService, DataService } from '../../../core/services';
import { InAppNotificationService } from '../../../core/services/in-app-notification.service';
import { Chat, ChatMessage, Master } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-client-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DateFormatPipe],
  templateUrl: './client-chat.component.html',
  styleUrls: ['./client-chat.component.scss']
})
export class ClientChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private route = inject(ActivatedRoute);
  private notificationService = inject(InAppNotificationService);

  isLoading = signal(true);
  chats = signal<Chat[]>([]);
  selectedChat = signal<Chat | null>(null);
  messages = signal<ChatMessage[]>([]);
  searchQuery = '';
  newMessage = '';
  private shouldScroll = false;

  // New chat modal
  showNewChatModal = signal(false);
  masters = signal<Master[]>([]);
  mastersLoading = signal(false);
  masterSearchQuery = '';

  filteredChats = computed(() => {
    const query = this.searchQuery.toLowerCase().trim();
    if (!query) return this.chats();
    return this.chats().filter(c =>
      c.masterName?.toLowerCase().includes(query)
    );
  });

  filteredMasters = computed(() => {
    const query = this.masterSearchQuery.toLowerCase().trim();
    if (!query) return this.masters();
    return this.masters().filter(m =>
      m.name.toLowerCase().includes(query) ||
      m.specialization?.toLowerCase().includes(query)
    );
  });

  ngOnInit(): void {
    this.loadChats();
    this.handleQueryParams();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private handleQueryParams(): void {
    this.route.queryParams.subscribe(params => {
      const masterId = params['masterId'];
      if (masterId) {
        this.openChatWithMaster(masterId);
      }
    });
  }

  private openChatWithMaster(masterId: string): void {
    this.dataService.getChatWithMaster(masterId).subscribe(chat => {
      // Add to list if not already there
      this.chats.update(list => {
        const exists = list.find(c => c.id === chat.id);
        if (!exists) {
          return [chat, ...list];
        }
        return list;
      });
      this.selectChat(chat);
      this.isLoading.set(false);
    });
  }

  private loadChats(): void {
    this.dataService.getAllChats().subscribe(data => {
      this.chats.set(data);
      this.isLoading.set(false);
    });
  }

  selectChat(chat: Chat): void {
    this.selectedChat.set(chat);
    this.loadMessages(chat.id);

    if (chat.unreadCount > 0) {
      this.dataService.markMessagesAsRead(chat.id).subscribe(() => {
        this.chats.update(list =>
          list.map(c => c.id === chat.id ? { ...c, unreadCount: 0 } : c)
        );
        // Refresh notification badge count
        this.notificationService.refreshUnreadCount();
      });
    }
  }

  private loadMessages(chatId: string): void {
    this.dataService.getMessages(chatId).subscribe(data => {
      this.messages.set(data);
      this.shouldScroll = true;
      // Force scroll after DOM update
      setTimeout(() => this.scrollToBottom(), 0);
    });
  }

  sendMessage(): void {
    const chat = this.selectedChat();
    if (!chat || !this.newMessage.trim()) return;

    const userId = this.authService.currentUser()?.id;
    if (!userId) return;

    this.dataService.sendMessage({
      chatId: chat.id,
      senderId: userId,
      senderRole: 'client',
      content: this.newMessage.trim()
    }).subscribe(message => {
      this.messages.update(list => [...list, message]);
      this.newMessage = '';
      this.shouldScroll = true;

      this.chats.update(list =>
        list.map(c => c.id === chat.id ? {
          ...c,
          lastMessage: message.content,
          lastMessageTime: message.timestamp
        } : c)
      );
    });
  }

  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        const el = this.messagesContainer.nativeElement;
        // Use smooth: auto for instant scroll
        el.scrollTo({ top: el.scrollHeight, behavior: 'auto' });
      }
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  openNewChatModal(): void {
    this.showNewChatModal.set(true);
    this.masterSearchQuery = '';
    if (this.masters().length === 0) {
      this.mastersLoading.set(true);
      this.dataService.getAllMasters().subscribe(data => {
        this.masters.set(data);
        this.mastersLoading.set(false);
      });
    }
  }

  closeNewChatModal(): void {
    this.showNewChatModal.set(false);
    this.masterSearchQuery = '';
  }

  selectMaster(master: Master): void {
    this.closeNewChatModal();
    this.openChatWithMaster(master.id);
  }
}
