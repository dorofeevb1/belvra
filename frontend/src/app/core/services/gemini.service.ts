import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AIGeneratedContent, AISuggestion } from '../models';
import { Master } from '../models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class GeminiService {
  private api = inject(ApiService);

  async generatePortfolioContent(imageBase64: string): Promise<AIGeneratedContent> {
    try {
      const result = await firstValueFrom(this.api.generatePortfolioContent(imageBase64));
      return {
        description: result.description || '',
        hashtags: result.hashtags || []
      };
    } catch (error) {
      console.error('Error generating portfolio content:', error);
      return { description: '', hashtags: [] };
    }
  }

  async generateChatSuggestions(
    chatHistory: { role: string; content: string }[],
    lastClientMessage: string
  ): Promise<AISuggestion[]> {
    try {
      const suggestions = await firstValueFrom(
        this.api.generateChatSuggestions(chatHistory, lastClientMessage)
      );
      return suggestions || [];
    } catch (error) {
      console.error('Error generating chat suggestions:', error);
      return [];
    }
  }

  async searchMasters(
    query: string,
    masters: Master[]
  ): Promise<string[]> {
    try {
      const mastersInfo = masters.map(m => ({
        id: m.id,
        name: m.name,
        specialization: m.specialization,
        address: m.address,
        rating: m.rating,
        description: m.description
      }));

      const result = await firstValueFrom(this.api.aiSearchMasters(query, mastersInfo));
      return result.master_ids || masters.map(m => m.id);
    } catch (error) {
      console.error('Error searching masters:', error);
      return masters.map(m => m.id);
    }
  }
}
