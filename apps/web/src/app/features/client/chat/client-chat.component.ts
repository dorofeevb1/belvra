import {
  Component, inject, OnInit, OnDestroy, signal, computed,
  ViewChild, ElementRef, AfterViewChecked, HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PickerComponent } from '@ctrl/ngx-emoji-mart';
import { ActivatedRoute } from '@angular/router';
import { Subject, debounceTime, takeUntil } from 'rxjs';
import { AuthService, DataService } from '../../../core/services';
import { InAppNotificationService } from '../../../core/services/in-app-notification.service';
import { Chat, ChatMessage, Master, ReplyPreview } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';

const PAGE_SIZE = 40;

const CLIENT_TEMPLATES = [
  { label: 'Запись', text: 'Хочу записаться, подскажите свободное время?' },
  { label: 'Цена', text: 'Сколько стоит услуга?' },
  { label: 'Подтверждение', text: 'Подтверждаю запись! Буду вовремя 🙏' },
  { label: 'Перенос', text: 'Могу я перенести запись на другое время?' },
  { label: 'Отмена', text: 'К сожалению, не смогу прийти. Извините!' },
  { label: 'Спасибо', text: 'Спасибо большое! Очень довольна результатом 💖' },
];

@Component({
  selector: 'app-client-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, DateFormatPipe, PickerComponent],
  templateUrl: './client-chat.component.html',
  styleUrls: ['./client-chat.component.scss']
})
export class ClientChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('msgInput') msgInput!: ElementRef<HTMLInputElement>;

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private route = inject(ActivatedRoute);
  private inAppNotifications = inject(InAppNotificationService);

  // ── Core state
  isLoading = signal(true);
  chats = signal<Chat[]>([]);
  selectedChat = signal<Chat | null>(null);
  messages = signal<ChatMessage[]>([]);
  currentUserId = computed(() => this.authService.currentUser()?.id || '');

  // ── Input
  searchQuery = '';
  newMessage = '';
  selectedFile = signal<File | null>(null);
  selectedFilePreview = signal<string | null>(null);

  // ── UI panels
  showEmojiPanel = signal(false);
  showTemplates = signal(false);
  showSearch = signal(false);

  // ── Search
  messageSearchQuery = signal('');
  private messageSearchSubject = new Subject<string>();

  // ── Reply
  replyToMessage = signal<ChatMessage | null>(null);

  // ── Lightbox
  lightboxUrl = signal<string | null>(null);

  // ── Scroll
  showScrollBtn = signal(false);

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

  // ── New chat modal
  showNewChatModal = signal(false);
  masters = signal<Master[]>([]);
  mastersLoading = signal(false);
  masterSearchQuery = '';

  // ── Internal
  private shouldScroll = false;
  private chatPollInterval: ReturnType<typeof setInterval> | null = null;
  private destroy$ = new Subject<void>();

  readonly templates = CLIENT_TEMPLATES;

  filteredChats = computed(() => {
    const query = this.searchQuery.toLowerCase().trim();
    let result = this.chats();
    if (query) result = result.filter(c => c.masterName?.toLowerCase().includes(query));
    return [...result].sort((a, b) => {
      const tA = a.lastMessageTime ? new Date(a.lastMessageTime).getTime() : 0;
      const tB = b.lastMessageTime ? new Date(b.lastMessageTime).getTime() : 0;
      return tB - tA;
    });
  });

  filteredMasters = computed(() => {
    const query = this.masterSearchQuery.toLowerCase().trim();
    if (!query) return this.masters();
    return this.masters().filter(m =>
      m.name.toLowerCase().includes(query) || m.specialization?.toLowerCase().includes(query)
    );
  });

  ngOnInit(): void {
    this.loadChats();
    this.handleQueryParams();
    this.chatPollInterval = setInterval(() => this.pollChats(), 30000);

    this.messageSearchSubject.pipe(debounceTime(400), takeUntil(this.destroy$)).subscribe(q => {
      this.messageSearchQuery.set(q);
      const chat = this.selectedChat();
      if (chat) this.loadMessages(chat.id, true, q || undefined);
    });

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

  private handleQueryParams(): void {
    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe(params => {
      const masterId = params['masterId'];
      if (masterId) this.openChatWithMaster(masterId);
    });
  }

  private openChatWithMaster(masterId: string): void {
    this.dataService.getChatWithMaster(masterId).subscribe(chat => {
      this.chats.update(list => {
        const exists = list.find(c => c.id === chat.id);
        return exists ? list : [chat, ...list];
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

  private pollChats(): void {
    this.dataService.getAllChats().subscribe(data => {
      const cur = this.selectedChat();
      this.chats.set(data);
      if (cur) {
        const updated = data.find(c => c.id === cur.id);
        if (updated && updated.unreadCount > 0) this.loadMessages(cur.id);
      }
    });
  }

  selectChat(chat: Chat): void {
    this.selectedChat.set(chat);
    this.replyToMessage.set(null);
    this.showSearch.set(false);
    this.messageSearchQuery.set('');
    this.messagesOffset = 0;
    this.loadMessages(chat.id, true);

    if (chat.unreadCount > 0) {
      this.dataService.markMessagesAsRead(chat.id).subscribe(() => {
        this.chats.update(list => list.map(c => c.id === chat.id ? { ...c, unreadCount: 0 } : c));
        this.inAppNotifications.fetchUnreadCount().subscribe();
      });
    }

    if (this.typingPollInterval) clearInterval(this.typingPollInterval);
    this.typingPollInterval = setInterval(() => {
      this.dataService.getWhoIsTyping(chat.id).subscribe(t => this.isTypingOther.set(t));
    }, 3000);
  }

  private loadMessages(chatId: string, reset = true, search?: string): void {
    if (reset) { this.messagesOffset = 0; this.hasMore.set(false); }

    this.dataService.getMessages(chatId, { limit: PAGE_SIZE, offset: this.messagesOffset, search }).subscribe(
      ({ messages, count }) => {
        this.totalMessages.set(count);
        if (reset) {
          this.messages.set(messages);
          this.shouldScroll = true;
          setTimeout(() => this.scrollToBottom(), 50);
        } else {
          this.messages.update(existing => [...messages, ...existing]);
        }
        this.hasMore.set(this.messagesOffset + PAGE_SIZE < count);
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

  // ── Reply
  setReply(msg: ChatMessage): void {
    this.replyToMessage.set(msg);
    this.msgInput?.nativeElement.focus();
  }

  cancelReply(): void { this.replyToMessage.set(null); }

  // ── Lightbox
  openLightbox(url: string): void { this.lightboxUrl.set(url); }
  closeLightbox(): void { this.lightboxUrl.set(null); }

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

    const userId = this.authService.currentUser()?.id;
    if (!userId) return;

    const replyId = this.replyToMessage()?.id;
    this.cancelReply();

    this.dataService.sendMessage({
      chatId: chat.id,
      senderId: userId,
      senderRole: 'client',
      content: this.newMessage.trim()
    }, file ?? undefined, replyId).subscribe(message => {
      this.messages.update(list => [...list, message]);
      this.newMessage = '';
      this.selectedFile.set(null);
      this.selectedFilePreview.set(null);
      if (this.fileInput) this.fileInput.nativeElement.value = '';
      this.shouldScroll = true;

      this.chats.update(list => list.map(c => c.id === chat.id ? {
        ...c,
        lastMessage: message.content || '📎 Файл',
        lastMessageTime: message.timestamp || new Date()
      } : c));
    });
  }

  onInputKeydown(): void { this.typingSubject.next(); }

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

  onMessageSearch(q: string): void { this.messageSearchSubject.next(q); }

  // ── Scroll
  onScroll(event: Event): void {
    const el = event.target as HTMLElement;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    this.showScrollBtn.set(distFromBottom > 200);

    if (el.scrollTop < 80 && this.hasMore() && !this.isLoadingMore()) this.loadMore();
  }

  scrollToBottom(): void {
    if (this.messagesContainer) {
      const el = this.messagesContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
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
    const userId = this.authService.currentUser()?.id;
    if (!userId) return;
    this.dataService.sendMessage({ chatId: chat.id, senderId: userId, senderRole: 'client', content: '' }, file)
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

  // ── New chat modal
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

  closeNewChatModal(): void { this.showNewChatModal.set(false); }

  selectMaster(master: Master): void {
    this.closeNewChatModal();
    this.openChatWithMaster(master.id);
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
}
