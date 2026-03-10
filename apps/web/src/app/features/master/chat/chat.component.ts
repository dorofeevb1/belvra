import {
  Component, inject, OnInit, OnDestroy, signal, computed,
  ViewChild, ElementRef, AfterViewChecked, HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PickerComponent } from '@ctrl/ngx-emoji-mart';
import { Subject, debounceTime, takeUntil } from 'rxjs';
import { AuthService, DataService, AIService } from '../../../core/services';
import { InAppNotificationService } from '../../../core/services/in-app-notification.service';
import { Chat, ChatMessage, AISuggestion, ReplyPreview } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

const PAGE_SIZE = 40;

const TEMPLATES = [
  { label: 'Приветствие', text: 'Добрый день! Чем могу помочь? 😊' },
  { label: 'Запись', text: 'Вы записаны! Ждём вас в назначенное время.' },
  { label: 'Перенос', text: 'Ваша запись перенесена. Удобное для вас время?' },
  { label: 'Напоминание', text: 'Напоминаем о вашей записи завтра. Всё в силе? ✅' },
  { label: 'Спасибо', text: 'Спасибо, что выбрали нас! Будем рады видеть снова 💖' },
  { label: 'Цена', text: 'Стоимость услуги уточните, пожалуйста, у нас на сайте или напишите интересующую услугу.' },
  { label: 'Подтверждение', text: 'Запись подтверждена! Ждём вас 🎉' },
  { label: 'Отмена', text: 'Запись отменена. Если передумаете — пишите, запишем заново!' },
];

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DateFormatPipe, PickerComponent],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('msgInput') msgInput!: ElementRef<HTMLInputElement>;

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private aiService = inject(AIService);
  private inAppNotifications = inject(InAppNotificationService);

  // ── Core state
  isLoading = signal(true);
  chats = signal<Chat[]>([]);
  selectedChat = signal<Chat | null>(null);
  messages = signal<ChatMessage[]>([]);
  aiSuggestions = signal<AISuggestion[]>([]);
  currentUserId = computed(() => this.authService.currentUser()?.id || '');

  // ── Input
  newMessage = '';
  selectedFile = signal<File | null>(null);
  selectedFilePreview = signal<string | null>(null);

  // ── UI panels
  showEmojiPanel = signal(false);
  showTemplates = signal(false);
  showSearch = signal(false);

  // ── Search
  searchQuery = '';
  messageSearchQuery = signal('');
  private messageSearchSubject = new Subject<string>();

  // ── Reply
  replyToMessage = signal<ChatMessage | null>(null);

  // ── Lightbox
  lightboxUrl = signal<string | null>(null);

  // ── Scroll-to-bottom
  showScrollBtn = signal(false);
  newMessagesBelow = signal(0);

  // ── Pagination
  isLoadingMore = signal(false);
  hasMore = signal(false);
  totalMessages = signal(0);
  private messagesOffset = 0;

  // ── Typing
  isTypingOther = signal(false);
  private typingSubject = new Subject<void>();
  private typingPollInterval: ReturnType<typeof setInterval> | null = null;

  // ── Recording
  readonly isRecordingSupported = typeof window !== 'undefined' && window.isSecureContext && !!navigator.mediaDevices;
  isRecording = signal(false);
  recordingSeconds = signal(0);
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private recordingTimer: ReturnType<typeof setInterval> | null = null;

  // ── Booking modal
  showBookingModal = signal(false);
  bookingDate = '';
  bookingTime = '';
  bookingService = '';
  bookingNote = '';

  // ── Internal
  private shouldScroll = false;
  private isAtBottom = true;
  private chatPollInterval: ReturnType<typeof setInterval> | null = null;
  private destroy$ = new Subject<void>();

  readonly templates = TEMPLATES;

  filteredChats = computed(() => {
    const query = this.searchQuery.toLowerCase().trim();
    let result = this.chats();
    if (query) result = result.filter(c => c.clientName.toLowerCase().includes(query));
    return [...result].sort((a, b) => {
      const tA = a.lastMessageTime ? new Date(a.lastMessageTime).getTime() : 0;
      const tB = b.lastMessageTime ? new Date(b.lastMessageTime).getTime() : 0;
      return tB - tA;
    });
  });

  ngOnInit(): void {
    this.loadChats();
    this.chatPollInterval = setInterval(() => this.pollChats(), 30000);

    // Debounced message search
    this.messageSearchSubject.pipe(debounceTime(400), takeUntil(this.destroy$)).subscribe(q => {
      this.messageSearchQuery.set(q);
      const chat = this.selectedChat();
      if (chat) this.loadMessages(chat.id, true, q || undefined);
    });

    // Debounced typing send
    this.typingSubject.pipe(debounceTime(300), takeUntil(this.destroy$)).subscribe(() => {
      const chat = this.selectedChat();
      if (chat) this.dataService.sendTyping(chat.id).subscribe();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.chatPollInterval) clearInterval(this.chatPollInterval);
    if (this.typingPollInterval) clearInterval(this.typingPollInterval);
    this.cancelRecording();
    this.messageSearchSubject.complete();
    this.typingSubject.complete();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  // ── Chat list
  private loadChats(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;
    this.dataService.getChats(masterId).subscribe(data => {
      this.chats.set(data);
      this.isLoading.set(false);
    });
  }

  private pollChats(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;
    this.dataService.getChats(masterId).subscribe(data => {
      const cur = this.selectedChat();
      this.chats.set(data);
      // If selected chat got new messages, reload
      if (cur) {
        const updated = data.find(c => c.id === cur.id);
        if (updated && updated.unreadCount > 0) {
          this.loadMessages(cur.id);
        }
      }
    });
  }

  selectChat(chat: Chat): void {
    this.selectedChat.set(chat);
    this.aiSuggestions.set([]);
    this.replyToMessage.set(null);
    this.showSearch.set(false);
    this.messageSearchQuery.set('');
    this.searchQuery = '';
    this.messagesOffset = 0;
    this.loadMessages(chat.id, true);

    if (chat.unreadCount > 0) {
      this.dataService.markMessagesAsRead(chat.id).subscribe(() => {
        this.chats.update(list => list.map(c => c.id === chat.id ? { ...c, unreadCount: 0 } : c));
        this.inAppNotifications.fetchUnreadCount().subscribe();
      });
    }

    // Start typing poll
    if (this.typingPollInterval) clearInterval(this.typingPollInterval);
    this.typingPollInterval = setInterval(() => {
      this.dataService.getWhoIsTyping(chat.id).subscribe(t => this.isTypingOther.set(t));
    }, 3000);
  }

  // ── Messages / pagination
  private loadMessages(chatId: string, reset = true, search?: string): void {
    if (reset) {
      this.messagesOffset = 0;
      this.hasMore.set(false);
    }

    this.dataService.getMessages(chatId, { limit: PAGE_SIZE, offset: this.messagesOffset, search }).subscribe(
      ({ messages, count }) => {
        this.totalMessages.set(count);

        if (reset) {
          this.messages.set(messages);
          this.shouldScroll = true;
          setTimeout(() => this.scrollToBottom(), 50);
        } else {
          // Prepend older messages
          this.messages.update(existing => [...messages, ...existing]);
        }

        this.hasMore.set(this.messagesOffset + PAGE_SIZE < count);

        const cur = this.messages();
        const lastClient = [...cur].reverse().find(m => m.senderRole === 'client');
        if (lastClient && !lastClient.isRead && reset) {
          this.generateAISuggestions(cur, lastClient.content);
        }
      }
    );
  }

  loadMore(): void {
    const chat = this.selectedChat();
    if (!chat || this.isLoadingMore() || !this.hasMore()) return;
    this.isLoadingMore.set(true);
    this.messagesOffset += PAGE_SIZE;
    const search = this.messageSearchQuery() || undefined;
    this.dataService.getMessages(chat.id, { limit: PAGE_SIZE, offset: this.messagesOffset, search }).subscribe(
      ({ messages, count }) => {
        this.messages.update(existing => [...messages, ...existing]);
        this.hasMore.set(this.messagesOffset + PAGE_SIZE < count);
        this.isLoadingMore.set(false);
      }
    );
  }

  // ── AI
  private async generateAISuggestions(history: ChatMessage[], lastMessage: string): Promise<void> {
    const chatHistory = history.map(m => ({ role: m.senderRole, content: m.content }));
    const suggestions = await this.aiService.generateChatSuggestions(chatHistory, lastMessage);
    this.aiSuggestions.set(suggestions);
  }

  useSuggestion(text: string): void {
    this.newMessage = text;
    this.sendMessage();
  }

  // ── Reply
  setReply(msg: ChatMessage): void {
    this.replyToMessage.set(msg);
    this.msgInput?.nativeElement.focus();
  }

  cancelReply(): void {
    this.replyToMessage.set(null);
  }

  // ── Lightbox
  openLightbox(url: string): void {
    this.lightboxUrl.set(url);
  }

  closeLightbox(): void {
    this.lightboxUrl.set(null);
  }

  @HostListener('document:keydown.escape')
  onEscKey(): void {
    if (this.lightboxUrl()) this.closeLightbox();
    if (this.showEmojiPanel()) this.showEmojiPanel.set(false);
  }

  // ── File
  onFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { alert('Файл слишком большой (макс. 10 МБ)'); return; }
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

  // ── Send
  sendMessage(): void {
    const chat = this.selectedChat();
    const file = this.selectedFile();
    if (!chat || (!this.newMessage.trim() && !file)) return;

    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    const replyId = this.replyToMessage()?.id;
    this.cancelReply();

    this.dataService.sendMessage({
      chatId: chat.id,
      senderId: masterId,
      senderRole: 'master',
      content: this.newMessage.trim()
    }, file ?? undefined, replyId).subscribe(message => {
      this.messages.update(list => [...list, message]);
      this.newMessage = '';
      this.selectedFile.set(null);
      this.selectedFilePreview.set(null);
      if (this.fileInput) this.fileInput.nativeElement.value = '';
      this.aiSuggestions.set([]);
      this.shouldScroll = true;
      this.newMessagesBelow.set(0);

      this.chats.update(list => list.map(c => c.id === chat.id ? {
        ...c,
        lastMessage: message.content || '📎 Файл',
        lastMessageTime: message.timestamp || new Date()
      } : c));
    });
  }

  onInputKeydown(event: KeyboardEvent): void {
    this.typingSubject.next();
  }

  // ── Emoji
  toggleEmojiPanel(): void { this.showEmojiPanel.update(v => !v); }

  onEmojiClick(event: any): void {
    this.newMessage += event?.emoji?.native ?? '';
    this.showEmojiPanel.set(false);
  }

  // ── Templates
  toggleTemplates(): void {
    this.showTemplates.update(v => !v);
    this.showEmojiPanel.set(false);
    this.showSearch.set(false);
  }

  useTemplate(text: string): void {
    this.newMessage = text;
    this.showTemplates.set(false);
    this.msgInput?.nativeElement.focus();
  }

  // ── Search
  toggleSearch(): void {
    this.showSearch.update(v => !v);
    if (!this.showSearch()) {
      this.messageSearchQuery.set('');
      const chat = this.selectedChat();
      if (chat) this.loadMessages(chat.id, true);
    }
    this.showTemplates.set(false);
    this.showEmojiPanel.set(false);
  }

  onMessageSearch(q: string): void {
    this.messageSearchSubject.next(q);
  }

  // ── Scroll
  onScroll(event: Event): void {
    const el = event.target as HTMLElement;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    this.isAtBottom = distFromBottom < 60;
    this.showScrollBtn.set(distFromBottom > 200);

    if (this.isAtBottom) this.newMessagesBelow.set(0);

    // Auto load more when near top
    if (el.scrollTop < 80 && this.hasMore() && !this.isLoadingMore()) {
      this.loadMore();
    }
  }

  scrollToBottom(): void {
    if (this.messagesContainer) {
      const el = this.messagesContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
    this.newMessagesBelow.set(0);
  }

  // ── Recording
  async startRecording(): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];
      this.mediaRecorder.ondataavailable = e => this.audioChunks.push(e.data);
      this.mediaRecorder.onstop = () => this.onRecordingStopped();
      this.mediaRecorder.start();
      this.isRecording.set(true);
      this.recordingSeconds.set(0);
      this.recordingTimer = setInterval(() => this.recordingSeconds.update(s => s + 1), 1000);
    } catch { alert('Нет доступа к микрофону'); }
  }

  stopRecording(): void { this.mediaRecorder?.stop(); this.clearRecordingTimer(); }

  cancelRecording(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.ondataavailable = null;
      this.mediaRecorder.onstop = null;
      this.mediaRecorder.stop();
      this.mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording.set(false);
    this.clearRecordingTimer();
  }

  private onRecordingStopped(): void {
    const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
    const file = new File([blob], 'voice.webm', { type: 'audio/webm' });
    this.mediaRecorder?.stream.getTracks().forEach(t => t.stop());
    this.mediaRecorder = null;
    this.isRecording.set(false);
    this.sendAudioFile(file);
  }

  private clearRecordingTimer(): void {
    if (this.recordingTimer) { clearInterval(this.recordingTimer); this.recordingTimer = null; }
  }

  private sendAudioFile(file: File): void {
    const chat = this.selectedChat();
    if (!chat) return;
    const masterId = this.authService.masterApiId();
    if (!masterId) return;
    this.dataService.sendMessage({ chatId: chat.id, senderId: masterId, senderRole: 'master', content: '' }, file)
      .subscribe(message => {
        this.messages.update(list => [...list, message]);
        this.shouldScroll = true;
        this.chats.update(list => list.map(c => c.id === chat.id ? {
          ...c, lastMessage: '🎵 Голосовое', lastMessageTime: message.timestamp || new Date()
        } : c));
      });
  }

  formatRecordTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  // ── Booking modal
  openBookingModal(): void {
    this.showBookingModal.set(true);
    this.bookingDate = '';
    this.bookingTime = '';
    this.bookingService = '';
    this.bookingNote = '';
  }

  closeBookingModal(): void { this.showBookingModal.set(false); }

  sendBookingOffer(): void {
    if (!this.bookingDate || !this.bookingTime || !this.bookingService) return;
    const dateStr = new Date(`${this.bookingDate}T${this.bookingTime}`).toLocaleString('ru', {
      day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit'
    });
    const text = `📅 Предложение записи\n\n💅 Услуга: ${this.bookingService}\n🗓 Дата и время: ${dateStr}${this.bookingNote ? '\n📝 ' + this.bookingNote : ''}\n\nПодтвердите, пожалуйста!`;
    this.newMessage = text;
    this.closeBookingModal();
    this.sendMessage();
  }

  // ── Helpers
  shouldShowDateSeparator(index: number): boolean {
    const msgs = this.messages();
    if (index === 0) return true;
    const cur = new Date(msgs[index].timestamp);
    const prev = new Date(msgs[index - 1].timestamp);
    return cur.toDateString() !== prev.toDateString();
  }

  replyLabel(reply: ReplyPreview): string {
    if (reply.messageType === 'image') return '📷 Изображение';
    if (reply.messageType === 'audio') return '🎵 Голосовое';
    if (reply.messageType === 'file') return '📄 Файл';
    return reply.content;
  }

  openImageFullscreen(url: string): void { this.openLightbox(url); }
}
