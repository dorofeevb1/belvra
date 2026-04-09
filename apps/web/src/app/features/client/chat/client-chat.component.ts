import {
  Component, inject, OnInit, OnDestroy, signal, computed,
  ViewChild, ElementRef, AfterViewChecked, HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PickerComponent } from '@ctrl/ngx-emoji-mart';
import { ActivatedRoute } from '@angular/router';
import { Subject, debounceTime, takeUntil } from 'rxjs';
import { AuthService, DataService, ApiService } from '../../../core/services';
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
  { label: 'Спасибо', text: 'Спасибо большое! Очень доволен(а) результатом 💖' },
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
  private api = inject(ApiService);
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
  private messagePollInterval: ReturnType<typeof setInterval> | null = null;

  // ── Recording
  readonly isRecordingSupported = typeof window !== 'undefined' && window.isSecureContext && !!navigator.mediaDevices;
  isRecording = signal(false);
  recordingSeconds = signal(0);
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private recordingTimer: ReturnType<typeof setInterval> | null = null;

  // ── Action menu
  showActionMenu = signal(false);

  // ── Confirm dialog
  showConfirmDialog = signal(false);
  confirmDialogText = signal('');
  confirmDialogAction = signal<(() => void) | null>(null);

  // ── Context menu
  contextMenuMsg = signal<ChatMessage | null>(null);
  contextMenuPos = signal({ x: 0, y: 0 });

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
    if (this.messagePollInterval) clearInterval(this.messagePollInterval);
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

    // Start message poll for real-time updates
    if (this.messagePollInterval) clearInterval(this.messagePollInterval);
    this.messagePollInterval = setInterval(() => {
      const cur = this.selectedChat();
      if (!cur) return;
      this.dataService.getMessages(cur.id, { limit: PAGE_SIZE, offset: 0 }).subscribe(({ messages, count }) => {
        const existing = this.messages();
        if (messages.length > 0 && (existing.length === 0 || messages[messages.length - 1].id !== existing[existing.length - 1]?.id)) {
          this.messages.set(messages);
          this.totalMessages.set(count);
          this.shouldScroll = true;
          setTimeout(() => this.scrollToBottom(), 50);
        }
      });
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

  // ── Long press for mobile
  private longPressTimer: ReturnType<typeof setTimeout> | null = null;

  onTouchStart(event: TouchEvent, message: ChatMessage): void {
    this.longPressTimer = setTimeout(() => {
      const touch = event.touches[0];
      let x = touch.clientX;
      let y = touch.clientY;
      if (x + 200 > window.innerWidth) x = window.innerWidth - 210;
      if (y + 250 > window.innerHeight) y = window.innerHeight - 260;
      if (x < 10) x = 10;
      if (y < 10) y = 10;
      this.contextMenuMsg.set(message);
      this.contextMenuPos.set({ x, y });
      // Haptic feedback if available
      if (navigator.vibrate) navigator.vibrate(30);
    }, 500);
  }

  onTouchEnd(): void {
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
  }

  // ── Custom confirm dialog
  private showConfirm(text: string, action: () => void): void {
    this.confirmDialogText.set(text);
    this.confirmDialogAction.set(action);
    this.showConfirmDialog.set(true);
  }

  onConfirmOk(): void {
    const action = this.confirmDialogAction();
    this.showConfirmDialog.set(false);
    if (action) action();
  }

  onConfirmCancel(): void {
    this.showConfirmDialog.set(false);
  }

  // ── Context menu
  openContextMenu(event: MouseEvent, message: ChatMessage): void {
    event.preventDefault();
    if (message.isDeleted) return;
    // Position in viewport, clamped to not overflow
    let x = event.clientX;
    let y = event.clientY;
    // Clamp right edge (menu ~200px wide)
    if (x + 200 > window.innerWidth) x = window.innerWidth - 210;
    // Clamp bottom edge (menu ~250px tall)
    if (y + 250 > window.innerHeight) y = window.innerHeight - 260;
    if (x < 10) x = 10;
    if (y < 10) y = 10;
    this.contextMenuMsg.set(message);
    this.contextMenuPos.set({ x, y });
  }

  closeContextMenu(): void {
    this.contextMenuMsg.set(null);
  }

  @HostListener('document:click')
  onDocumentClick(): void {
    if (this.contextMenuMsg()) this.closeContextMenu();
    if (this.showActionMenu()) this.showActionMenu.set(false);
  }

  copyMessage(message: ChatMessage): void {
    navigator.clipboard.writeText(message.content).catch(() => {});
  }

  // ── Message actions
  deleteMessageForSelf(message: ChatMessage): void {
    const chat = this.selectedChat();
    if (!chat) return;
    this.api.post(`/chats/${chat.id}/delete-message/${message.id}/`, { mode: 'self' }).subscribe(() => {
      this.messages.update(msgs => msgs.filter(m => m.id !== message.id));
    });
  }

  deleteMessageForAll(message: ChatMessage): void {
    const chat = this.selectedChat();
    if (!chat) return;
    this.showConfirm('Сообщение будет удалено у всех участников чата.', () => {
      this.api.post(`/chats/${chat.id}/delete-message/${message.id}/`, { mode: 'all' }).subscribe(() => {
        this.messages.update(msgs => msgs.map(m =>
          m.id === message.id ? { ...m, isDeleted: true, content: '', fileUrl: undefined } : m
        ));
      });
    });
  }

  // Forward
  showForwardModal = signal(false);
  forwardingMessage = signal<ChatMessage | null>(null);

  forwardMessage(message: ChatMessage): void {
    const chats = this.chats().filter(c => c.id !== this.selectedChat()?.id);
    if (chats.length === 0) {
      // No other chats to forward to
      return;
    }
    if (chats.length === 1) {
      this.doForward(message, chats[0]);
      return;
    }
    this.forwardingMessage.set(message);
    this.showForwardModal.set(true);
  }

  selectForwardChat(chat: Chat): void {
    const msg = this.forwardingMessage();
    if (!msg) return;
    this.doForward(msg, chat);
    this.showForwardModal.set(false);
    this.forwardingMessage.set(null);
  }

  private doForward(message: ChatMessage, targetChat: Chat): void {
    const currentChat = this.selectedChat();
    if (!currentChat) return;
    this.api.post(`/chats/${currentChat.id}/forward-message/${message.id}/`, {
      target_chat_id: targetChat.id
    }).subscribe();
  }

  // ── Chat actions
  hideChat(): void {
    const chat = this.selectedChat();
    if (!chat) return;
    this.showActionMenu.set(false);
    this.showConfirm('Чат будет скрыт. Если собеседник напишет — чат появится снова.', () => {
      this.api.post(`/chats/${chat.id}/hide/`, {}).subscribe(() => {
        this.selectedChat.set(null);
        this.chats.update(chats => chats.filter(c => c.id !== chat.id));
      });
    });
  }

  blockUser(): void {
    const chat = this.selectedChat();
    if (!chat) return;
    this.showActionMenu.set(false);
    this.showConfirm('Пользователь не сможет отправлять вам сообщения и записываться.', () => {
      this.api.post(`/chats/${chat.id}/block/`, {}).subscribe(() => {
        this.selectedChat.update(c => c ? { ...c, isBlocked: true } : null);
      });
    });
  }

  unblockUser(): void {
    const chat = this.selectedChat();
    if (!chat) return;
    this.showActionMenu.set(false);
    this.api.post(`/chats/${chat.id}/unblock/`, {}).subscribe(() => {
      this.selectedChat.update(c => c ? { ...c, isBlocked: false } : null);
    });
  }

  formatLastSeen(date: string | null | undefined): string {
    if (!date) return '';
    const now = new Date();
    const seen = new Date(date);
    const diff = now.getTime() - seen.getTime();
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (mins < 1) return 'был(а) только что';
    if (mins < 60) return `был(а) ${mins} мин назад`;
    if (hours < 24) {
      const h = seen.getHours().toString().padStart(2, '0');
      const m = seen.getMinutes().toString().padStart(2, '0');
      return `был(а) сегодня в ${h}:${m}`;
    }
    if (hours < 48) {
      const h = seen.getHours().toString().padStart(2, '0');
      const m = seen.getMinutes().toString().padStart(2, '0');
      return `был(а) вчера в ${h}:${m}`;
    }
    const d = seen.getDate().toString().padStart(2, '0');
    const mo = (seen.getMonth() + 1).toString().padStart(2, '0');
    const h = seen.getHours().toString().padStart(2, '0');
    const mi = seen.getMinutes().toString().padStart(2, '0');
    return `был(а) ${d}.${mo} в ${h}:${mi}`;
  }
}
