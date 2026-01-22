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

export type AIAnalysisType = 'general' | 'style' | 'quality' | 'recommendation';

export interface AIPhotoAnalysisGeneral {
  analysis_type: 'general';
  type: string;
  description: string;
  details: string[];
  colors: string[];
  photo_quality: string;
  confidence: number;
  raw_response?: string;
}

export interface AIPhotoAnalysisStyle {
  analysis_type: 'style';
  style: string;
  trends: string[];
  target_audience: string;
  occasions: string[];
  season: string;
  similar_styles: string[];
  raw_response?: string;
}

export interface AIPhotoAnalysisQuality {
  analysis_type: 'quality';
  overall_score: number;
  technical_score: number;
  creativity_score: number;
  cleanliness_score: number;
  strengths: string[];
  improvements: string[];
  professional_level: string;
  feedback: string;
  raw_response?: string;
}

export interface AIPhotoAnalysisRecommendation {
  analysis_type: 'recommendation';
  face_shape: string;
  skin_tone: string;
  recommended_services: { service: string; reason: string }[];
  color_palette: string[];
  style_recommendations: string[];
  care_tips: string[];
  raw_response?: string;
}

export type AIPhotoAnalysisResult =
  | AIPhotoAnalysisGeneral
  | AIPhotoAnalysisStyle
  | AIPhotoAnalysisQuality
  | AIPhotoAnalysisRecommendation
  | { error: string; analysis_type: string; raw_response?: string };
