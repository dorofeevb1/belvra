import { Component, inject, OnInit, signal, computed, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, DataService, GeminiService } from '../../../core/services';
import { Chat, ChatMessage, AISuggestion } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DateFormatPipe],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private geminiService = inject(GeminiService);

  isLoading = signal(true);
  chats = signal<Chat[]>([]);
  selectedChat = signal<Chat | null>(null);
  messages = signal<ChatMessage[]>([]);
  aiSuggestions = signal<AISuggestion[]>([]);
  searchQuery = '';
  newMessage = '';
  private shouldScroll = false;

  filteredChats = computed(() => {
    const query = this.searchQuery.toLowerCase().trim();
    if (!query) return this.chats();
    return this.chats().filter(c =>
      c.clientName.toLowerCase().includes(query)
    );
  });

  ngOnInit(): void {
    this.loadChats();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private loadChats(): void {
    const masterId = this.authService.masterData()?.id;
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

    const suggestions = await this.geminiService.generateChatSuggestions(chatHistory, lastMessage);
    this.aiSuggestions.set(suggestions);
  }

  useSuggestion(text: string): void {
    this.newMessage = text;
    this.sendMessage();
  }

  sendMessage(): void {
    const chat = this.selectedChat();
    if (!chat || !this.newMessage.trim()) return;

    const masterId = this.authService.masterData()?.id;
    if (!masterId) return;

    this.dataService.sendMessage({
      chatId: chat.id,
      senderId: masterId,
      senderRole: 'master',
      content: this.newMessage.trim()
    }).subscribe(message => {
      this.messages.update(list => [...list, message]);
      this.newMessage = '';
      this.aiSuggestions.set([]);
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
    if (this.messagesContainer) {
      const el = this.messagesContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
  }
}
