import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  // Generic HTTP methods for flexible API calls
  get<T = any>(endpoint: string, params?: any): Observable<T> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<T>(`${this.baseUrl}${endpoint}`, { params: httpParams });
  }

  post<T = any>(endpoint: string, body: any): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${endpoint}`, body);
  }

  put<T = any>(endpoint: string, body: any): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}${endpoint}`, body);
  }

  patch<T = any>(endpoint: string, body: any): Observable<T> {
    return this.http.patch<T>(`${this.baseUrl}${endpoint}`, body);
  }

  delete<T = any>(endpoint: string): Observable<T> {
    return this.http.delete<T>(`${this.baseUrl}${endpoint}`);
  }

  // Auth endpoints
  login(email: string, password: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/login/`, { email, password });
  }

  register(data: {
    email: string;
    password: string;
    password_confirm: string;
    first_name: string;
    last_name: string;
    phone?: string;
    role?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/register/`, data);
  }

  logout(): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/logout/`, {});
  }

  refreshToken(refreshToken: string): Observable<{ access: string }> {
    return this.http.post<{ access: string }>(`${this.baseUrl}/auth/token/refresh/`, {
      refresh: refreshToken
    });
  }

  getProfile(): Observable<any> {
    return this.http.get(`${this.baseUrl}/auth/profile/`);
  }

  updateProfile(data: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/auth/profile/`, data);
  }

  uploadAvatar(file: File): Observable<{ avatar: string; detail: string }> {
    const formData = new FormData();
    formData.append('avatar', file);
    return this.http.post<{ avatar: string; detail: string }>(`${this.baseUrl}/auth/profile/avatar/`, formData);
  }

  deleteAvatar(): Observable<any> {
    return this.http.delete(`${this.baseUrl}/auth/profile/avatar/`);
  }

  switchRole(role: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/profile/switch-role/`, { role });
  }

  becomeMaster(): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/profile/become-master/`, {});
  }

  changePassword(oldPassword: string, newPassword: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/password/change/`, {
      old_password: oldPassword,
      new_password: newPassword
    });
  }

  // Password Reset endpoints
  requestPasswordReset(email: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/password/reset/`, { email });
  }

  validateResetToken(token: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/password/reset/validate/`, { token });
  }

  confirmPasswordReset(token: string, newPassword: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/password/reset/confirm/`, {
      token,
      new_password: newPassword
    });
  }

  // Email verification
  verifyEmail(email: string, code: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/email/verify/`, { email, code });
  }

  resendVerificationEmail(): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/email/resend-verification/`, {});
  }

  // Masters endpoints
  getMasters(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/auth/masters/`, { params: httpParams });
  }

  getMasterById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/auth/masters/${id}/`);
  }

  // Categories endpoints
  getCategories(): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/categories/`);
  }

  getCategoryBySlug(slug: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/categories/${slug}/`);
  }

  getCategoryServices(slug: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/categories/${slug}/services/`);
  }

  // Services endpoints
  getServices(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/services/items/`, { params: httpParams });
  }

  getServiceBySlug(slug: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/items/${slug}/`);
  }

  getPopularServices(): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/items/popular/`);
  }

  // Master Services endpoints
  getMasterServices(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/services/master-services/`, { params: httpParams });
  }

  getMyMasterServices(): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/master-services/my_services/`);
  }

  getMasterServiceById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/master-services/${id}/`);
  }

  createMasterService(data: {
    service_id?: string | null;  // For catalog service
    custom_name?: string;        // For custom service
    custom_description?: string;
    category?: string;
    price?: number;
    duration?: number;
    is_active?: boolean;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/services/master-services/`, data);
  }

  updateMasterService(id: string, data: {
    service_id?: string | null;
    custom_name?: string;
    custom_description?: string;
    category?: string;
    price?: number;
    duration?: number;
    is_active?: boolean;
  }): Observable<any> {
    return this.http.patch(`${this.baseUrl}/services/master-services/${id}/`, data);
  }

  deleteMasterService(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/services/master-services/${id}/`);
  }

  // Appointments endpoints
  getAppointments(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/appointments/`, { params: httpParams });
  }

  getUpcomingAppointments(): Observable<any> {
    return this.http.get(`${this.baseUrl}/appointments/upcoming/`);
  }

  createAppointment(data: {
    master_id: string;
    service_id: string;
    date: string;
    start_time: string;
    notes?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/`, data);
  }

  getAppointmentById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/appointments/${id}/`);
  }

  cancelAppointment(id: string, reason?: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/${id}/cancel/`, { reason });
  }

  confirmAppointment(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/${id}/confirm/`, {});
  }

  completeAppointment(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/${id}/complete/`, {});
  }

  rescheduleAppointment(id: string, data: { date: string; start_time: string }): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/${id}/reschedule/`, data);
  }

  // Available slots
  getAvailableSlots(masterId: string, serviceId: string, date: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/available-slots/`, {
      master_id: masterId,
      service_id: serviceId,
      date
    });
  }

  // Reviews endpoints
  getReviews(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/appointments/reviews/`, { params: httpParams });
  }

  getReviewsByMaster(masterId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/appointments/reviews/master/${masterId}/`);
  }

  createReview(data: {
    appointment: string;
    rating: number;
    comment?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/reviews/`, data);
  }

  updateReview(id: string, data: { rating?: number; comment?: string }): Observable<any> {
    return this.http.patch(`${this.baseUrl}/appointments/reviews/${id}/`, data);
  }

  deleteReview(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/appointments/reviews/${id}/`);
  }

  getMyReviews(): Observable<any> {
    return this.http.get(`${this.baseUrl}/appointments/reviews/`, { params: { my: 'true' } });
  }

  // ============ Payments endpoints ============

  // Wallet
  getWallet(): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/wallet/`);
  }

  updateWallet(data: { auto_withdraw?: boolean }): Observable<any> {
    return this.http.patch(`${this.baseUrl}/payments/wallet/`, data);
  }

  getWalletStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/wallet/stats/`);
  }

  // Payments
  getPayments(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/payments/payments/`, { params: httpParams });
  }

  getPaymentById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/payments/${id}/`);
  }

  createPayment(data: {
    appointment_id: string;
    payment_type?: string;
    amount?: number;
    return_url?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/payments/`, data);
  }

  getPaymentStatus(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/payments/${id}/status/`);
  }

  refundPayment(id: string, data?: { amount?: number; reason?: string }): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/payments/${id}/refund/`, data || {});
  }

  confirmTestPayment(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/payments/${id}/confirm-test/`, {});
  }

  // Client payments (history)
  getClientPayments(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/payments/my-payments/`, { params: httpParams });
  }

  // Master received payments
  getMasterPayments(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/payments/received-payments/`, { params: httpParams });
  }

  // Payout Destinations
  getPayoutDestinations(): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/payout-destinations/`);
  }

  getPayoutDestinationById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/payout-destinations/${id}/`);
  }

  createPayoutDestination(data: {
    destination_type: string;
    is_default?: boolean;
    card_number?: string;
    yoomoney_account?: string;
    bank_name?: string;
    bik?: string;
    account_number?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/payout-destinations/`, data);
  }

  deletePayoutDestination(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/payments/payout-destinations/${id}/`);
  }

  setDefaultPayoutDestination(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/payout-destinations/${id}/set_default/`, {});
  }

  // Withdrawals
  getWithdrawals(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/payments/withdrawals/`, { params: httpParams });
  }

  createWithdrawal(data: {
    amount: number;
    destination_id: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/withdrawals/`, data);
  }

  cancelWithdrawal(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/payments/withdrawals/${id}/cancel/`, {});
  }

  // ============ Favorites endpoints ============

  getFavorites(): Observable<any> {
    return this.http.get(`${this.baseUrl}/auth/favorites/`);
  }

  addToFavorites(masterId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/favorites/`, { master_id: masterId });
  }

  removeFromFavorites(favoriteId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/auth/favorites/${favoriteId}/`);
  }

  checkFavorite(masterId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/auth/favorites/check/${masterId}/`);
  }

  toggleFavorite(masterId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/favorites/toggle/${masterId}/`, {});
  }

  // ============ Notifications endpoints ============

  getNotifications(): Observable<any> {
    return this.http.get(`${this.baseUrl}/notifications/`);
  }

  getUnreadNotificationsCount(): Observable<any> {
    return this.http.get(`${this.baseUrl}/notifications/unread_count/`);
  }

  markNotificationsRead(notificationIds?: string[]): Observable<any> {
    return this.http.post(`${this.baseUrl}/notifications/mark_read/`, {
      notification_ids: notificationIds || []
    });
  }

  markNotificationRead(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/notifications/${id}/read/`, {});
  }

  deleteNotification(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/notifications/${id}/`);
  }

  clearReadNotifications(): Observable<any> {
    return this.http.delete(`${this.baseUrl}/notifications/clear_read/`);
  }

  // ============ Schedule endpoints ============

  getSchedules(params?: { master?: string }): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key as keyof typeof params] !== undefined && params[key as keyof typeof params] !== null) {
          httpParams = httpParams.set(key, params[key as keyof typeof params]!);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/appointments/schedules/`, { params: httpParams });
  }

  getScheduleById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/appointments/schedules/${id}/`);
  }

  createSchedule(data: {
    weekday: number;
    start_time: string;
    end_time: string;
    is_working: boolean;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/schedules/`, data);
  }

  updateSchedule(id: string, data: {
    weekday?: number;
    start_time?: string;
    end_time?: string;
    is_working?: boolean;
  }): Observable<any> {
    return this.http.patch(`${this.baseUrl}/appointments/schedules/${id}/`, data);
  }

  deleteSchedule(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/appointments/schedules/${id}/`);
  }

  // Bulk update schedules (create/update multiple at once)
  bulkUpdateSchedules(schedules: {
    weekday: number;
    start_time: string;
    end_time: string;
    is_working: boolean;
  }[]): Observable<any> {
    return this.http.post(`${this.baseUrl}/appointments/schedules/bulk/`, { schedules });
  }

  // ============ Portfolio endpoints ============

  getPortfolioItems(params?: { master?: string }): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key as keyof typeof params] !== undefined && params[key as keyof typeof params] !== null) {
          httpParams = httpParams.set(key, params[key as keyof typeof params]!);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/services/portfolio/`, { params: httpParams });
  }

  getMyPortfolio(): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/portfolio/my_portfolio/`);
  }

  getPortfolioByMaster(masterId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/portfolio/master/${masterId}/`);
  }

  getPortfolioItem(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/services/portfolio/${id}/`);
  }

  createPortfolioItem(data: FormData): Observable<any> {
    return this.http.post(`${this.baseUrl}/services/portfolio/`, data);
  }

  updatePortfolioItem(id: string, data: FormData): Observable<any> {
    return this.http.patch(`${this.baseUrl}/services/portfolio/${id}/`, data);
  }

  deletePortfolioItem(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/services/portfolio/${id}/`);
  }

  likePortfolioItem(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/services/portfolio/${id}/like/`, {});
  }

  // ============ Chat endpoints ============

  getChats(role?: 'client' | 'master'): Observable<any> {
    if (role) {
      return this.http.get(`${this.baseUrl}/chats/`, { params: { role } });
    }
    return this.http.get(`${this.baseUrl}/chats/`);
  }

  getChatById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/chats/${id}/`);
  }

  getChatWithMaster(masterId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/chats/with-master/${masterId}/`);
  }

  createChat(masterId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/chats/`, { master_id: masterId });
  }

  getChatMessages(chatId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/chats/${chatId}/messages/`);
  }

  sendMessage(chatId: string, content: string, file?: File): Observable<any> {
    if (file) {
      const formData = new FormData();
      if (content) formData.append('content', content);
      formData.append('file', file, file.name);
      return this.http.post(`${this.baseUrl}/chats/${chatId}/send_message/`, formData);
    }
    return this.http.post(`${this.baseUrl}/chats/${chatId}/send_message/`, { content });
  }

  markChatRead(chatId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/chats/${chatId}/mark_read/`, {});
  }

  // ============ Todo endpoints ============

  getTodos(params?: { date?: string; status?: string; priority?: string }): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        const value = params[key as keyof typeof params];
        if (value !== undefined && value !== null) {
          httpParams = httpParams.set(key, value);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/todos/`, { params: httpParams });
  }

  getTodoById(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/todos/${id}/`);
  }

  getTodosByDate(date: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/todos/by-date/${date}/`);
  }

  getTodosToday(): Observable<any> {
    return this.http.get(`${this.baseUrl}/todos/today/`);
  }

  getTodoStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/todos/stats/`);
  }

  createTodo(data: {
    title: string;
    description?: string;
    date: string;
    time?: string;
    status?: string;
    priority?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/todos/`, data);
  }

  updateTodo(id: string, data: {
    title?: string;
    description?: string;
    date?: string;
    time?: string;
    status?: string;
    priority?: string;
  }): Observable<any> {
    return this.http.patch(`${this.baseUrl}/todos/${id}/`, data);
  }

  updateTodoStatus(id: string, status: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/todos/${id}/update_status/`, { status });
  }

  deleteTodo(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/todos/${id}/`);
  }

  // ============ Transaction endpoints ============

  getTransactions(): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/transactions/`);
  }

  getTransactionsSummary(): Observable<any> {
    return this.http.get(`${this.baseUrl}/payments/transactions/summary/`);
  }

  // ============ AI endpoints ============

  analyzePhoto(imageBase64: string, analysisType: 'general' | 'style' | 'quality' | 'recommendation' = 'general'): Observable<any> {
    return this.http.post(`${this.baseUrl}/ai/analyze-photo/`, {
      image_base64: imageBase64,
      analysis_type: analysisType
    });
  }

  generatePortfolioContent(imageBase64: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/ai/portfolio-content/`, {
      image_base64: imageBase64
    });
  }

  generateChatSuggestions(chatHistory: { role: string; content: string }[], lastClientMessage: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/ai/chat-suggestions/`, {
      chat_history: chatHistory,
      last_client_message: lastClientMessage
    });
  }

  aiSearchMasters(query: string, masters: any[]): Observable<any> {
    return this.http.post(`${this.baseUrl}/ai/search-masters/`, {
      query,
      masters
    });
  }

  // ============ Subscription endpoints ============

  getSubscription(): Observable<any> {
    return this.http.get(`${this.baseUrl}/subscriptions/current/`);
  }

  getSubscriptionUsage(): Observable<any> {
    return this.http.get(`${this.baseUrl}/subscriptions/usage/`);
  }

  createSubscription(data: {
    plan_id: string;
    return_url?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/subscriptions/subscribe/`, data);
  }

  cancelSubscription(): Observable<any> {
    return this.http.post(`${this.baseUrl}/subscriptions/cancel/`, {});
  }

  reactivateSubscription(): Observable<any> {
    return this.http.post(`${this.baseUrl}/subscriptions/reactivate/`, {});
  }

  changeSubscriptionPlan(data: {
    plan_id: string;
    return_url?: string;
  }): Observable<any> {
    return this.http.post(`${this.baseUrl}/subscriptions/change-plan/`, data);
  }

  getSubscriptionPayments(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get(`${this.baseUrl}/subscriptions/payments/`, { params: httpParams });
  }

  getSubscriptionPlans(): Observable<any> {
    return this.http.get(`${this.baseUrl}/subscriptions/plans/`);
  }
}
