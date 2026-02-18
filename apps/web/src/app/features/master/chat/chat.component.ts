import 'emoji-picker-element';
import { Component, inject, OnInit, OnDestroy, signal, computed, ViewChild, ElementRef, AfterViewChecked, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, DataService, AIService } from '../../../core/services';
import { Chat, ChatMessage, AISuggestion } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DateFormatPipe],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private aiService = inject(AIService);

  isLoading = signal(true);
  chats = signal<Chat[]>([]);
  selectedChat = signal<Chat | null>(null);
  messages = signal<ChatMessage[]>([]);
  aiSuggestions = signal<AISuggestion[]>([]);
  currentUserId = computed(() => this.authService.currentUser()?.id || '');
  searchQuery = '';
  newMessage = '';
  selectedFile = signal<File | null>(null);
  selectedFilePreview = signal<string | null>(null);
  showEmojiPanel = signal(false);
  private shouldScroll = false;
  private chatPollInterval: ReturnType<typeof setInterval> | null = null;

  filteredChats = computed(() => {
    const query = this.searchQuery.toLowerCase().trim();
    let result = this.chats();
    if (query) {
      result = result.filter(c =>
        c.clientName.toLowerCase().includes(query)
      );
    }
    return [...result].sort((a, b) => {
      const timeA = a.lastMessageTime ? new Date(a.lastMessageTime).getTime() : 0;
      const timeB = b.lastMessageTime ? new Date(b.lastMessageTime).getTime() : 0;
      return timeB - timeA;
    });
  });

  ngOnInit(): void {
    this.loadChats();
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

  private loadChats(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.dataService.getChats(masterId).subscribe(data => {
      this.chats.set(data);
      this.isLoading.set(false);
    });
  }

  selectChat(chat: Chat): void {
    this.selectedChat.set(chat);
    this.aiSuggestions.set([]);
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

      const lastClientMsg = [...data].reverse().find(m => m.senderRole === 'client');
      if (lastClientMsg && !lastClientMsg.isRead) {
        this.generateAISuggestions(data, lastClientMsg.content);
      }
    });
  }

  private async generateAISuggestions(history: ChatMessage[], lastMessage: string): Promise<void> {
    const chatHistory = history.map(m => ({
      role: m.senderRole,
      content: m.content
    }));

    const suggestions = await this.aiService.generateChatSuggestions(chatHistory, lastMessage);
    this.aiSuggestions.set(suggestions);
  }

  useSuggestion(text: string): void {
    this.newMessage = text;
    this.sendMessage();
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

    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.dataService.sendMessage({
      chatId: chat.id,
      senderId: masterId,
      senderRole: 'master',
      content: this.newMessage.trim()
    }, file ?? undefined).subscribe(message => {
      this.messages.update(list => [...list, message]);
      this.newMessage = '';
      this.selectedFile.set(null);
      this.selectedFilePreview.set(null);
      if (this.fileInput) this.fileInput.nativeElement.value = '';
      this.aiSuggestions.set([]);
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

  shouldShowDateSeparator(index: number): boolean {
    const msgs = this.messages();
    if (index === 0) return true;

    const current = new Date(msgs[index].timestamp);
    const prev = new Date(msgs[index - 1].timestamp);

    return current.toDateString() !== prev.toDateString();
  }
}
