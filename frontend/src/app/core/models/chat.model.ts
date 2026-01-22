export interface ChatMessage {
  id: string;
  chatId: string;
  senderId: string;
  senderRole: 'master' | 'client';
  content: string;
  timestamp: Date;
  isRead: boolean;
}

export interface Chat {
  id: string;
  masterId: string;
  clientId: string;
  clientName: string;
  clientAvatar?: string;
  masterName?: string;
  masterAvatar?: string;
  lastMessage?: string;
  lastMessageTime?: Date;
  unreadCount: number;
}

export interface AISuggestion {
  id: string;
  text: string;
}
