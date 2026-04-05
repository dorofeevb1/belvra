import { Injectable, inject } from '@angular/core';
import { Observable, of, delay, map, catchError, throwError, forkJoin, switchMap, Subject } from 'rxjs';
import { ApiService } from './api.service';
import {
  Appointment, AppointmentStatus,
  BeautyService, Master,
  Transaction, TransactionStatus, calculateNetProfit,
  PortfolioItem, Chat, ChatMessage,
  Review, TodoItem, TodoStatus, UsedMaterial,
  ServiceCategory
} from '../models';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DataService {
  private api = inject(ApiService);
  private readonly DELAY = 300;
  private readonly MEDIA_BASE_URL = environment.mediaUrl;

  readonly chatRead$ = new Subject<string>();

  private getFullMediaUrl(url: string | null): string {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return `${this.MEDIA_BASE_URL}${url}`;
  }

  // ==================== MAPPERS ====================

  private mapBackendService(backendService: any): BeautyService {
    // Map backend category slug to frontend category
    const categoryMap: Record<string, ServiceCategory> = {
      'hair': 'hair',
      'nails': 'manicure',
      'cosmetology': 'cosmetology',
      'makeup': 'makeup',
      'massage': 'massage',
      'brows-lashes': 'eyebrows'
    };

    return {
      id: backendService.id,
      masterId: backendService.master_id || '',
      serviceId: backendService.id, // For global catalog, id is the serviceId
      name: backendService.name,
      description: backendService.description || '',
      duration: backendService.duration,
      price: parseFloat(backendService.price),
      defaultMaterialsCost: 0,
      category: categoryMap[backendService.category_slug] || 'other',
      isActive: backendService.is_active !== false
    };
  }

  private mapBackendMaster(backendMaster: any): Master {
    // Build coordinates object if latitude and longitude are available
    const coordinates = backendMaster.latitude && backendMaster.longitude
      ? { lat: parseFloat(backendMaster.latitude), lng: parseFloat(backendMaster.longitude) }
      : undefined;

    return {
      id: backendMaster.id,
      email: backendMaster.user?.email || '',
      name: backendMaster.user?.full_name || `${backendMaster.user?.first_name} ${backendMaster.user?.last_name}`,
      role: 'master',
      phone: backendMaster.user?.phone || '',
      avatar: backendMaster.user?.avatar || 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150',
      specialization: backendMaster.specialization || '',
      description: backendMaster.bio || '',
      address: backendMaster.address || '',
      coordinates,
      experienceYears: backendMaster.experience_years || 0,
      isAvailable: backendMaster.is_available !== false,
      rating: parseFloat(backendMaster.rating) || 0,
      reviewsCount: backendMaster.reviews_count || 0,
      isPro: backendMaster.is_pro || false,
      distanceKm: backendMaster.distance_km ?? null,
      workSchedule: {
        monday: { start: '09:00', end: '18:00' },
        tuesday: { start: '09:00', end: '18:00' },
        wednesday: { start: '09:00', end: '18:00' },
        thursday: { start: '09:00', end: '18:00' },
        friday: { start: '09:00', end: '18:00' },
        saturday: { start: '10:00', end: '16:00' },
        sunday: null
      },
      services: [],
      createdAt: new Date(backendMaster.user?.created_at || Date.now())
    };
  }

  private mapBackendAppointment(backendApt: any): Appointment {
    const statusMap: Record<string, AppointmentStatus> = {
      'pending': 'pending',
      'confirmed': 'confirmed',
      'cancelled': 'cancelled',
      'completed': 'completed',
      'no_show': 'no_show'
    };

    return {
      id: backendApt.id,
      masterId: backendApt.master?.id || backendApt.master,
      clientId: backendApt.client?.id || backendApt.client,
      serviceId: backendApt.service?.id || backendApt.service,
      serviceName: backendApt.service?.name || backendApt.service_name || '',
      clientName: backendApt.client?.full_name || backendApt.client_name || '',
      clientPhone: backendApt.client?.phone || '',
      date: backendApt.date,
      startTime: backendApt.start_time?.slice(0, 5) || backendApt.start_time,
      endTime: backendApt.end_time?.slice(0, 5) || backendApt.end_time,
      duration: backendApt.service?.duration || 60,
      price: parseFloat(backendApt.price),
      status: statusMap[backendApt.status] || 'pending',
      notes: backendApt.notes || '',
      usedMaterials: backendApt.used_materials || [],
      materialsCost: parseFloat(backendApt.materials_cost) || 0,
      createdAt: new Date(backendApt.created_at),
      updatedAt: new Date(backendApt.updated_at || backendApt.created_at),
    };
  }

  private mapBackendReview(backendReview: any): Review {
    return {
      id: backendReview.id,
      masterId: backendReview.appointment?.master || '',
      clientId: backendReview.appointment?.client || '',
      clientName: backendReview.appointment?.client_name || 'Клиент',
      clientAvatar: undefined,
      appointmentId: backendReview.appointment?.id || backendReview.appointment,
      rating: backendReview.rating,
      comment: backendReview.comment || '',
      createdAt: new Date(backendReview.created_at)
    };
  }

  // ==================== SERVICES (from backend) ====================

  getAllServices(): Observable<BeautyService[]> {
    return this.api.getServices({ limit: 100 }).pipe(
      map((response: any) => {
        const results = response.results || response;
        return results.map((s: any) => this.mapBackendService(s));
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить услуги')))
    );
  }

  getServices(masterId: string): Observable<BeautyService[]> {
    return this.api.getMasterServices({ master: masterId }).pipe(
      map((response: any) => {
        const results = response.results || response;
        return results.map((ms: any) => ({
          id: ms.id, // MasterService ID (for update/delete operations)
          masterId: ms.master?.id || masterId,
          serviceId: ms.service?.id, // Global catalog service ID
          name: ms.name || ms.service?.name,
          description: ms.description || ms.service?.description || '',
          duration: ms.actual_duration || ms.duration || ms.service?.duration || 60,
          price: parseFloat(ms.actual_price || ms.price || ms.service?.price || 0),
          defaultMaterialsCost: 0,
          category: (ms.category?.slug || ms.service?.category?.slug || 'other') as ServiceCategory,
          isActive: ms.is_active !== false
        }));
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить услуги мастера')))
    );
  }

  addService(service: Omit<BeautyService, 'id'> & { serviceId?: string }): Observable<BeautyService> {
    // Prepare request data
    const requestData: any = {
      price: service.price,
      duration: service.duration
    };

    if (service.serviceId) {
      // Catalog service - link to global service
      requestData.service_id = service.serviceId;
    } else {
      // Custom service - provide name and description
      requestData.custom_name = service.name;
      requestData.custom_description = service.description || '';
    }

    return this.api.createMasterService(requestData).pipe(
      map((response: any) => ({
        id: response.id,
        masterId: response.master?.id || '',
        name: response.name || response.service?.name || service.name,
        description: response.description || response.service?.description || service.description,
        duration: response.actual_duration || response.duration || service.duration,
        price: parseFloat(response.actual_price || response.price || service.price),
        defaultMaterialsCost: 0,
        category: (service.category || 'other') as ServiceCategory,
        isActive: response.is_active ?? true
      })),
      catchError(() => throwError(() => new Error('Не удалось создать услугу')))
    );
  }

  updateService(id: string, updates: Partial<BeautyService>): Observable<BeautyService> {
    // Prepare update data
    const updateData: any = {
      price: updates.price,
      duration: updates.duration
    };

    // If we have a name, update custom_name (for custom services)
    if (updates.name) {
      updateData.custom_name = updates.name;
    }
    if (updates.description) {
      updateData.custom_description = updates.description;
    }

    return this.api.updateMasterService(id, updateData).pipe(
      map((response: any) => ({
        id: response.id,
        masterId: response.master?.id || updates.masterId || '',
        name: response.name || response.service?.name || updates.name || '',
        description: response.description || response.service?.description || updates.description || '',
        duration: response.actual_duration || response.duration || updates.duration || 60,
        price: parseFloat(response.actual_price || response.price || updates.price || 0),
        defaultMaterialsCost: 0,
        category: (updates.category || 'other') as ServiceCategory,
        isActive: response.is_active ?? true
      })),
      catchError(() => throwError(() => new Error('Не удалось обновить услугу')))
    );
  }

  deleteService(id: string): Observable<void> {
    return this.api.deleteMasterService(id).pipe(
      map(() => void 0),
      catchError(() => of(void 0))
    );
  }

  // Get master's own services (for authenticated master)
  getMyServices(): Observable<BeautyService[]> {
    return this.api.getMyMasterServices().pipe(
      map((response: any) => {
        const results = response.results || response;
        return (Array.isArray(results) ? results : []).map((ms: any) => ({
          id: ms.id, // MasterService ID (for update/delete operations)
          masterId: ms.master?.id || '',
          serviceId: ms.service?.id, // Global catalog service ID
          name: ms.name || ms.service?.name || '',
          description: ms.description || ms.service?.description || '',
          duration: ms.actual_duration || ms.duration || ms.service?.duration || 60,
          price: parseFloat(ms.actual_price || ms.price || ms.service?.price || 0),
          defaultMaterialsCost: 0,
          category: (ms.category?.slug || ms.service?.category?.slug || 'other') as ServiceCategory,
          isActive: ms.is_active !== false
        }));
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить ваши услуги')))
    );
  }

  // ==================== APPOINTMENTS (from backend) ====================

  getAppointments(_masterId?: string, role?: 'master' | 'client'): Observable<Appointment[]> {
    const params = role ? { role } : undefined;
    return this.api.getAppointments(params).pipe(
      map((response: any) => {
        const results = response.results || response;
        return results.map((apt: any) => this.mapBackendAppointment(apt));
      }),
      catchError(() => of([]))
    );
  }

  getClientAppointments(clientId: string): Observable<Appointment[]> {
    return this.api.getAppointments({ role: 'client' }).pipe(
      map((response: any) => {
        const results = response.results || response;
        return results
          .filter((apt: any) => apt.client?.id === clientId || apt.client === clientId)
          .map((apt: any) => this.mapBackendAppointment(apt));
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить записи')))
    );
  }

  getUpcomingAppointments(): Observable<Appointment[]> {
    return this.api.getUpcomingAppointments().pipe(
      map((response: any) => {
        const results = response.results || response;
        return results.map((apt: any) => this.mapBackendAppointment(apt));
      }),
      catchError(() => of([]))
    );
  }

  updateAppointmentStatus(id: string, status: AppointmentStatus): Observable<Appointment> {
    let apiCall: Observable<any>;

    switch (status) {
      case 'confirmed':
        apiCall = this.api.confirmAppointment(id);
        break;
      case 'completed':
        apiCall = this.api.completeAppointment(id);
        break;
      case 'cancelled':
        apiCall = this.api.cancelAppointment(id);
        break;
      default:
        return of({ id, status } as Appointment).pipe(delay(this.DELAY));
    }

    return apiCall.pipe(
      map((response: any) => this.mapBackendAppointment(response))
    );
  }

  rescheduleAppointment(id: string, newDate: string, newStartTime: string): Observable<Appointment> {
    return this.api.rescheduleAppointment(id, {
      date: newDate,
      start_time: newStartTime
    }).pipe(
      map((response: any) => this.mapBackendAppointment(response)),
      catchError(() => throwError(() => new Error('Не удалось перенести запись')))
    );
  }

  updateAppointmentMaterials(id: string, materials: UsedMaterial[], totalCost: number): Observable<Appointment> {
    return this.api.updateAppointmentMaterials(id, {
      materials: materials.map(m => ({ name: m.name, quantity: m.quantity, cost: m.totalCost })),
      materials_cost: totalCost
    }).pipe(
      map((response: any) => this.mapBackendAppointment(response)),
      catchError(() => throwError(() => new Error('Не удалось обновить материалы')))
    );
  }

  createAppointment(appointment: Omit<Appointment, 'id' | 'createdAt' | 'updatedAt'>): Observable<Appointment> {
    return this.api.createAppointment({
      master_id: appointment.masterId,
      service_id: appointment.serviceId,
      date: appointment.date,
      start_time: appointment.startTime,
      notes: appointment.notes
    }).pipe(
      map((response: any) => this.mapBackendAppointment(response))
    );
  }

  // ==================== AVAILABLE SLOTS (from backend) ====================

  getAvailableSlots(masterId: string, date: string, duration: number): Observable<string[]> {
    // Need a service ID for the API - get the first service of master
    return this.getServices(masterId).pipe(
      map(services => services[0]?.id || ''),
      switchMap(serviceId => {
        if (!serviceId) return throwError(() => new Error('Нет услуг для получения слотов'));
        return this.api.getAvailableSlots(masterId, serviceId, date).pipe(
          map((response: any) => {
            const slots = response?.slots || response || [];
            if (Array.isArray(slots)) {
              return slots.map((s: any) =>
                typeof s === 'string' ? s : s.start_time?.slice(0, 5) || s
              );
            }
            return [];
          }),
          catchError(() => throwError(() => new Error('Не удалось загрузить доступные слоты')))
        );
      }),
      catchError(err => throwError(() => err))
    );
  }

  getAvailableSlotsForService(masterId: string, serviceId: string, date: string): Observable<string[]> {
    return this.api.getAvailableSlots(masterId, serviceId, date).pipe(
      map((response: any) => {
        const slots = response?.slots || [];
        return slots.map((s: any) => s.start_time?.slice(0, 5) || s);
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить доступные слоты')))
    );
  }

  // ==================== REVIEWS (from backend) ====================

  getReviews(masterId: string): Observable<Review[]> {
    return this.api.getReviewsByMaster(masterId).pipe(
      map((response: any) => {
        const results = response.results || response;
        return (Array.isArray(results) ? results : []).map((r: any) => this.mapBackendReview(r));
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить отзывы')))
    );
  }

  getClientReviews(): Observable<Review[]> {
    return this.api.getMyReviews().pipe(
      map((response: any) => {
        const results = response.results || response;
        return (Array.isArray(results) ? results : []).map((r: any) => this.mapBackendReview(r));
      }),
      catchError(() => of([]))
    );
  }

  updateReview(id: string, data: { rating?: number; comment?: string }): Observable<Review> {
    return this.api.updateReview(id, data).pipe(
      map((response: any) => this.mapBackendReview(response)),
      catchError(() => throwError(() => new Error('Не удалось обновить отзыв')))
    );
  }

  deleteReview(id: string): Observable<void> {
    return this.api.deleteReview(id).pipe(
      map(() => void 0),
      catchError(() => of(void 0))
    );
  }

  addReview(review: Omit<Review, 'id' | 'createdAt'>): Observable<Review> {
    return this.api.createReview({
      appointment: review.appointmentId,
      rating: review.rating,
      comment: review.comment
    }).pipe(
      map((response: any) => this.mapBackendReview(response)),
      catchError(() => throwError(() => new Error('Не удалось отправить отзыв')))
    );
  }

  // ==================== MASTERS (from backend) ====================

  getAllMasters(): Observable<Master[]> {
    return this.api.getMasters().pipe(
      map((response: any) => {
        const results = response.results || response;
        return results.map((m: any) => this.mapBackendMaster(m));
      }),
      catchError(() => throwError(() => new Error('Не удалось загрузить мастеров')))
    );
  }

  searchMasters(params: any): Observable<Master[]> {
    return this.api.getMasters(params).pipe(
      map((response: any) => {
        const results = response.results || response;
        return results.map((m: any) => this.mapBackendMaster(m));
      }),
      catchError(() => of([]))
    );
  }

  getMasterById(id: string): Observable<Master | undefined> {
    return this.api.getMasterById(id).pipe(
      map((response: any) => this.mapBackendMaster(response)),
      catchError(() => throwError(() => new Error('Не удалось загрузить профиль мастера')))
    );
  }

  // ==================== CATEGORIES (from backend) ====================

  getCategories(): Observable<any[]> {
    return this.api.getCategories().pipe(
      map((response: any) => response.results || response),
      catchError(() => of([]))
    );
  }

  // ==================== TRANSACTIONS ====================

  private mapBackendTransaction(t: any): Transaction {
    return {
      id: t.id,
      masterId: t.master_id,
      appointmentId: t.appointment_id,
      clientName: t.client_name,
      serviceName: t.service_name,
      date: t.date,
      income: t.income,
      materialsCost: t.materials_cost,
      netProfit: t.net_profit,
      status: t.status as TransactionStatus,
      createdAt: new Date(t.created_at)
    };
  }

  getTransactions(masterId: string): Observable<Transaction[]> {
    // Derive transactions from completed appointments (payments module removed)
    return this.getAppointments(masterId).pipe(
      map(appointments => {
        const completed = appointments.filter(a => a.status === 'completed');
        return completed.map((apt, index) => {
          const netProfit = calculateNetProfit(apt.price, apt.materialsCost || 0);
          return {
            id: `trans-${apt.id}`,
            masterId: apt.masterId,
            appointmentId: apt.id,
            clientName: apt.clientName,
            serviceName: apt.serviceName,
            date: apt.date,
            income: apt.price,
            materialsCost: apt.materialsCost || 0,
            netProfit,
            status: (index === 0 ? 'pending' : 'paid') as TransactionStatus,
            createdAt: apt.createdAt
          };
        });
      }),
      catchError(() => of([]))
    );
  }

  getFinancialSummary(): Observable<{
    totalProfit: number;
    pendingAmount: number;
    lastPayout: number;
    lastPayoutDate?: string;
  }> {
    // Derive financial summary from completed appointments (payments module removed)
    return this.getTransactions('').pipe(
      map(transactions => {
        const totalProfit = transactions.reduce((sum, t) => sum + t.netProfit, 0);
        const pendingAmount = transactions
          .filter(t => t.status === 'pending')
          .reduce((sum, t) => sum + t.netProfit, 0);
        return {
          totalProfit,
          pendingAmount,
          lastPayout: 0
        };
      }),
      catchError(() => of({
        totalProfit: 0,
        pendingAmount: 0,
        lastPayout: 0
      }))
    );
  }

  // ==================== PORTFOLIO ====================

  private mapBackendPortfolioItem(item: any): PortfolioItem {
    return {
      id: item.id,
      masterId: item.master,
      imageUrl: this.getFullMediaUrl(item.image),
      title: item.title,
      description: item.description || '',
      hashtags: item.hashtags || [],
      serviceId: item.service,
      serviceName: item.service_name,
      createdAt: new Date(item.created_at),
      likes: item.likes_count || 0
    };
  }

  getPortfolio(masterId: string): Observable<PortfolioItem[]> {
    return this.api.getPortfolioByMaster(masterId).pipe(
      map((items: any[]) => items.map(item => this.mapBackendPortfolioItem(item))),
      catchError(() => of([]))
    );
  }

  getMyPortfolio(): Observable<PortfolioItem[]> {
    return this.api.getMyPortfolio().pipe(
      map((items: any[]) => items.map(item => this.mapBackendPortfolioItem(item))),
      catchError(() => of([]))
    );
  }

  addPortfolioItem(item: Omit<PortfolioItem, 'id' | 'createdAt' | 'likes'>, imageFile?: File): Observable<PortfolioItem> {
    const formData = new FormData();
    formData.append('title', item.title);
    if (item.description) formData.append('description', item.description);
    if (item.serviceId) formData.append('service', item.serviceId);
    if (item.hashtags?.length) formData.append('hashtags', JSON.stringify(item.hashtags));
    if (imageFile) formData.append('image', imageFile);

    return this.api.createPortfolioItem(formData).pipe(
      map((response: any) => this.mapBackendPortfolioItem(response)),
      catchError(() => throwError(() => new Error('Не удалось добавить работу в портфолио')))
    );
  }

  updatePortfolioItem(id: string, updates: Partial<PortfolioItem>, imageFile?: File): Observable<PortfolioItem> {
    const formData = new FormData();
    if (updates.title) formData.append('title', updates.title);
    if (updates.description !== undefined) formData.append('description', updates.description);
    // Always send service field, even if empty, to allow unlinking
    if (updates.serviceId !== undefined) {
      formData.append('service', updates.serviceId || '');
    }
    if (updates.hashtags) formData.append('hashtags', JSON.stringify(updates.hashtags));
    if (imageFile) formData.append('image', imageFile);

    return this.api.updatePortfolioItem(id, formData).pipe(
      map((response: any) => this.mapBackendPortfolioItem(response)),
      catchError(() => throwError(() => new Error('Не удалось обновить работу')))
    );
  }

  deletePortfolioItem(id: string): Observable<void> {
    return this.api.deletePortfolioItem(id).pipe(
      map(() => void 0)
    );
  }

  likePortfolioItem(id: string): Observable<number> {
    return this.api.likePortfolioItem(id).pipe(
      map((response: any) => response.likes_count),
      catchError(() => of(0))
    );
  }

  // ==================== CHATS ====================

  private mapBackendChat(chat: any): Chat {
    return {
      id: chat.id,
      masterId: chat.master_id,
      clientId: chat.client_id,
      clientName: chat.client_name || 'Клиент',
      clientAvatar: chat.client_avatar,
      masterName: chat.master_name || 'Мастер',
      masterAvatar: chat.master_avatar ? this.getFullMediaUrl(chat.master_avatar) : undefined,
      lastMessage: chat.last_message,
      lastMessageTime: chat.last_message_time ? new Date(chat.last_message_time) : undefined,
      unreadCount: chat.unread_count || 0
    };
  }

  private mapBackendMessage(msg: any): ChatMessage {
    return {
      id: msg.id,
      chatId: msg.chat,
      senderId: msg.sender,
      senderRole: msg.sender_role as 'master' | 'client',
      content: msg.content || '',
      timestamp: new Date(msg.created_at),
      isRead: msg.is_read,
      fileUrl: msg.file_url ? this.getFullMediaUrl(msg.file_url) : undefined,
      messageType: msg.message_type as 'text' | 'image' | 'file' | undefined,
      replyTo: msg.reply_to ? {
        id: msg.reply_to.id,
        content: msg.reply_to.content || '',
        senderRole: msg.reply_to.sender_role,
        messageType: msg.reply_to.message_type,
      } : undefined,
    };
  }

  getChats(_masterId?: string): Observable<Chat[]> {
    return this.api.getChats('master').pipe(
      map((response: any) => {
        const results = response.results || response;
        return (Array.isArray(results) ? results : [])
          .map((c: any) => this.mapBackendChat(c));
      }),
      catchError(() => of([]))
    );
  }

  getAllChats(): Observable<Chat[]> {
    return this.api.getChats('client').pipe(
      map((response: any) => {
        const results = response.results || response;
        return (Array.isArray(results) ? results : []).map((c: any) => this.mapBackendChat(c));
      }),
      catchError(() => of([]))
    );
  }

  getChatWithMaster(masterId: string): Observable<Chat> {
    return this.api.getChatWithMaster(masterId).pipe(
      map((chat: any) => this.mapBackendChat(chat)),
      catchError(() => throwError(() => new Error('Не удалось загрузить чат')))
    );
  }

  getMessages(chatId: string, params?: { limit?: number; offset?: number; search?: string }): Observable<{ messages: ChatMessage[]; count: number }> {
    return this.api.getChatMessages(chatId, params).pipe(
      map((response: any) => {
        const raw = Array.isArray(response) ? response : (response.results || []);
        const count = response.count ?? raw.length;
        return { messages: raw.map((m: any) => this.mapBackendMessage(m)).reverse(), count };
      }),
      catchError(() => of({ messages: [], count: 0 }))
    );
  }

  sendMessage(message: Omit<ChatMessage, 'id' | 'timestamp' | 'isRead'>, file?: File, replyToId?: string): Observable<ChatMessage> {
    return this.api.sendMessage(message.chatId, message.content, file, replyToId).pipe(
      map((response: any) => this.mapBackendMessage(response)),
      catchError(() => throwError(() => new Error('Не удалось отправить сообщение')))
    );
  }

  sendTyping(chatId: string): Observable<void> {
    return this.api.sendTyping(chatId).pipe(
      map(() => void 0),
      catchError(() => of(void 0))
    );
  }

  getWhoIsTyping(chatId: string): Observable<boolean> {
    return this.api.getWhoIsTyping(chatId).pipe(
      map((r: any) => !!r.typing),
      catchError(() => of(false))
    );
  }

  markMessagesAsRead(chatId: string): Observable<void> {
    return this.api.markChatRead(chatId).pipe(
      map(() => {
        this.chatRead$.next(chatId);
      }),
      catchError(() => of(void 0))
    );
  }

  // ==================== TODOS ====================

  private mapBackendTodo(todo: any): TodoItem {
    return {
      id: todo.id,
      masterId: todo.master_id,
      title: todo.title,
      description: todo.description || '',
      date: todo.date,
      time: todo.time?.slice(0, 5),
      status: todo.status as TodoStatus,
      priority: todo.priority as 'low' | 'medium' | 'high',
      createdAt: new Date(todo.created_at),
      updatedAt: new Date(todo.updated_at)
    };
  }

  getTodos(masterId: string, date?: string): Observable<TodoItem[]> {
    const params: { date?: string } = {};
    if (date) params.date = date;

    return this.api.getTodos(params).pipe(
      map((response: any) => {
        const results = response.results || response;
        return (Array.isArray(results) ? results : []).map((t: any) => this.mapBackendTodo(t));
      }),
      catchError(() => of([]))
    );
  }

  getTodosForDate(date: string): Observable<TodoItem[]> {
    return this.api.getTodosByDate(date).pipe(
      map((todos: any[]) => todos.map(t => this.mapBackendTodo(t))),
      catchError(() => of([]))
    );
  }

  getTodosToday(): Observable<TodoItem[]> {
    return this.api.getTodosToday().pipe(
      map((todos: any[]) => todos.map(t => this.mapBackendTodo(t))),
      catchError(() => of([]))
    );
  }

  addTodo(todo: Omit<TodoItem, 'id' | 'createdAt' | 'updatedAt'>): Observable<TodoItem> {
    return this.api.createTodo({
      title: todo.title,
      description: todo.description,
      date: todo.date,
      time: todo.time,
      status: todo.status,
      priority: todo.priority
    }).pipe(
      map((response: any) => this.mapBackendTodo(response)),
      catchError(() => throwError(() => new Error('Не удалось создать задачу')))
    );
  }

  updateTodoStatus(id: string, status: TodoStatus): Observable<TodoItem> {
    // Validate ID to prevent API calls with undefined/null/empty IDs
    if (!id || id === 'undefined' || id === 'null') {
      console.error('Invalid todo ID for status update:', id);
      return of({ id, status } as TodoItem);
    }
    return this.api.updateTodoStatus(id, status).pipe(
      map((response: any) => this.mapBackendTodo(response)),
      catchError(() => of({ id, status } as TodoItem))
    );
  }

  updateTodo(id: string, updates: Partial<TodoItem>): Observable<TodoItem> {
    // Validate ID to prevent API calls with undefined/null/empty IDs
    if (!id || id === 'undefined' || id === 'null') {
      console.error('Invalid todo ID for update:', id);
      return of({ id, ...updates } as TodoItem);
    }
    return this.api.updateTodo(id, {
      title: updates.title,
      description: updates.description,
      date: updates.date,
      time: updates.time,
      status: updates.status,
      priority: updates.priority
    }).pipe(
      map((response: any) => this.mapBackendTodo(response)),
      catchError(() => of({ id, ...updates } as TodoItem))
    );
  }

  deleteTodo(id: string): Observable<void> {
    // Validate ID to prevent API calls with undefined/null/empty IDs
    if (!id || id === 'undefined' || id === 'null') {
      console.error('Invalid todo ID for delete:', id);
      return of(void 0);
    }
    return this.api.deleteTodo(id).pipe(
      map(() => void 0),
      catchError(() => of(void 0))
    );
  }

  // ==================== STATS ====================

  getDashboardStats(masterId: string): Observable<{
    totalProfit: number;
    upcomingAppointments: number;
    newClients: number;
    averageRating: number;
  }> {
    return forkJoin({
      appointments: this.getAppointments(masterId),
      reviews: this.getReviews(masterId)
    }).pipe(
      map(({ appointments, reviews }) => {
        const today = this.getDateString(0);
        const upcomingAppointments = appointments.filter(
          a => a.date >= today && (a.status === 'confirmed' || a.status === 'pending')
        ).length;

        const completedAppointments = appointments.filter(a => a.status === 'completed');
        const totalProfit = completedAppointments.reduce((sum, a) => {
          const netProfit = calculateNetProfit(a.price, a.materialsCost || 0);
          return sum + netProfit;
        }, 0);

        const averageRating = reviews.length > 0
          ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
          : 0;

        const uniqueClients = new Set(appointments.map(a => a.clientId));

        return {
          totalProfit,
          upcomingAppointments,
          newClients: uniqueClients.size,
          averageRating: Math.round(averageRating * 10) / 10
        };
      }),
      catchError(() => of({
        totalProfit: 0,
        upcomingAppointments: 0,
        newClients: 0,
        averageRating: 0
      }))
    );
  }

  getWeeklyAppointmentsTrend(masterId: string): Observable<{ date: string; count: number }[]> {
    return this.getAppointments(masterId).pipe(
      map(appointments => {
        const result: { date: string; count: number }[] = [];
        for (let i = 6; i >= 0; i--) {
          const date = this.getDateString(-i);
          const count = appointments.filter(a => a.date === date).length;
          result.push({ date, count });
        }
        return result;
      })
    );
  }

  getServicesPopularity(masterId: string): Observable<{ serviceName: string; count: number }[]> {
    return this.getAppointments(masterId).pipe(
      map(appointments => {
        const countMap = new Map<string, number>();
        appointments.forEach(a => {
          if (a.serviceName) {
            countMap.set(a.serviceName, (countMap.get(a.serviceName) || 0) + 1);
          }
        });
        return Array.from(countMap.entries()).map(([serviceName, count]) => ({
          serviceName,
          count
        }));
      })
    );
  }

  // ==================== HELPERS ====================

  private getDateString(daysOffset: number): string {
    const date = new Date();
    date.setDate(date.getDate() + daysOffset);
    return date.toISOString().split('T')[0];
  }

}
