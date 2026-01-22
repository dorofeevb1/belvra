export interface PortfolioItem {
  id: string;
  masterId: string;
  imageUrl: string;
  title: string;
  description: string;
  hashtags: string[];
  serviceId?: string;
  serviceName?: string;
  createdAt: Date;
  likes: number;
}

export interface PortfolioFormData {
  title: string;
  description: string;
  hashtags: string[];
  serviceId?: string;
  imageFile?: File;
  imageUrl?: string;
}

export interface AIGeneratedContent {
  description: string;
  hashtags: string[];
}
