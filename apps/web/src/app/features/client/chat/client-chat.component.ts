import 'emoji-picker-element';
import { Component, inject, OnInit, OnDestroy, signal, computed, ViewChild, ElementRef, AfterViewChecked, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { AuthService, DataService } from '../../../core/services';
import { Chat, ChatMessage, Master } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-client-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DateFormatPipe],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './client-chat.component.html',
  styleUrls: ['./client-chat.component.scss']
})
export class ClientChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private route = inject(ActivatedRoute);

  isLoading = signal(true);
  chats = signal<Chat[]>([]);
  selectedChat = signal<Chat | null>(null);
  messages = signal<ChatMessage[]>([]);
  searchQuery = '';
  newMessage = '';
  currentUserId = computed(() => this.authService.currentUser()?.id || '');
  selectedFile = signal<File | null>(null);
  selectedFilePreview = signal<string | null>(null);
  showEmojiPanel = signal(false);
  private shouldScroll = false;

  // New chat modal
  showNewChatModal = signal(false);
  masters = signal<Master[]>([]);
  mastersLoading = signal(false);
  masterSearchQuery = '';
  private chatPollInterval: ReturnType<typeof setInterval> | null = null;

  filteredChats = computed(() => {
    const query = this.searchQuery.toLowerCase().trim();
    let result = this.chats();
    if (query) {
      result = result.filter(c =>
        c.masterName?.toLowerCase().includes(query)
      );
    }
    return [...result].sort((a, b) => {
      const timeA = a.lastMessageTime ? new Date(a.lastMessageTime).getTime() : 0;
      const timeB = b.lastMessageTime ? new Date(b.lastMessageTime).getTime() : 0;
      return timeB - timeA;
    });
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
    this.chatPollInterval = setInterval(() => this.loadChats(), 30000);
  }

  ngOnDestroy(): void {
    if (this.chatPollInterval) {
      clearInterval(this.chatPollInterval);
    }
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
      });
    }
  }

  private loadMessages(chatId: string): void {
    this.dataService.getMessages(chatId).subscribe(data => {
      this.messages.set(data);
      this.shouldScroll = true;

      // Принудительный скролл после рендеринга DOM
      setTimeout(() => this.scrollToBottom(), 50);
    });
  }

  onFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      alert('Файл слишком большой (макс. 10 МБ)');
      return;
    }
    this.selectedFile.set(file);
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = e => this.selectedFilePreview.set(e.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      this.selectedFilePreview.set(null);
    }
  }

  removeSelectedFile(): void {
    this.selectedFile.set(null);
    this.selectedFilePreview.set(null);
    if (this.fileInput) this.fileInput.nativeElement.value = '';
  }

  sendMessage(): void {
    const chat = this.selectedChat();
    const file = this.selectedFile();
    if (!chat || (!this.newMessage.trim() && !file)) return;

    const userId = this.authService.currentUser()?.id;
    if (!userId) return;

    this.dataService.sendMessage({
      chatId: chat.id,
      senderId: userId,
      senderRole: 'client',
      content: this.newMessage.trim()
    }, file ?? undefined).subscribe(message => {
      this.messages.update(list => [...list, message]);
      this.newMessage = '';
      this.selectedFile.set(null);
      this.selectedFilePreview.set(null);
      if (this.fileInput) this.fileInput.nativeElement.value = '';
      this.shouldScroll = true;

      this.chats.update(list =>
        list.map(c => c.id === chat.id ? {
          ...c,
          lastMessage: message.content || '📎 Файл',
          lastMessageTime: message.timestamp || new Date()
        } : c)
      );
    });
  }

  openImageFullscreen(url: string): void {
    window.open(url, '_blank');
  }

  toggleEmojiPanel(): void {
    this.showEmojiPanel.update(v => !v);
  }

  onEmojiClick(event: Event): void {
    const detail = (event as CustomEvent).detail;
    this.newMessage += detail?.unicode ?? '';
    this.showEmojiPanel.set(false);
  }

  private scrollToBottom(): void {
    if (this.messagesContainer) {
      const el = this.messagesContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
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

  shouldShowDateSeparator(index: number): boolean {
    const msgs = this.messages();
    if (index === 0) return true;

    const current = new Date(msgs[index].timestamp);
    const prev = new Date(msgs[index - 1].timestamp);

    return current.toDateString() !== prev.toDateString();
  }
}
