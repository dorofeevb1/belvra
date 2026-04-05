export type SubscriptionTier = 'free' | 'pro';
export type SubscriptionPeriod = 'monthly' | 'yearly';
export type SubscriptionStatus = 'active' | 'cancelled' | 'expired' | 'pending';

export interface SubscriptionFeature {
  name: string;
  description: string;
  included: boolean;
  limit?: number | null; // null means unlimited
}

export interface SubscriptionLimits {
  maxAppointmentsPerMonth: number | null; // null = unlimited
  maxServicesCount: number | null;
  maxPortfolioItems: number | null;
  searchBoostEnabled: boolean;
  analyticsLevel: 'basic' | 'advanced';
  priorityBooking: boolean;
  extended_search: boolean;
  history_months: number;
  client_stats_enabled: boolean;
  max_favorites: number;
  pro_badge: boolean;
  client_notes_enabled: boolean;
  max_pinned_portfolio: number;
  rebooking_reminder_enabled: boolean;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: SubscriptionTier;
  userType: 'master' | 'client';
  period: SubscriptionPeriod;
  price: number;
  originalPrice?: number; // For showing discount on yearly plans
  features: SubscriptionFeature[];
  limits: SubscriptionLimits;
  isPopular?: boolean;
  extended_search: boolean;
  history_months: number;
  client_stats_enabled: boolean;
  max_favorites: number;
  pro_badge: boolean;
  client_notes_enabled: boolean;
  max_pinned_portfolio: number;
  rebooking_reminder_enabled: boolean;
}

export interface Subscription {
  id: string;
  userId: string;
  planId: string;
  tier: SubscriptionTier;
  period: SubscriptionPeriod;
  status: SubscriptionStatus;
  currentPeriodStart: Date;
  currentPeriodEnd: Date;
  cancelAtPeriodEnd: boolean;
  autoRenew: boolean;
}

export interface UsageStats {
  appointmentsThisMonth: number;
  servicesCount: number;
  portfolioItemsCount: number;
}

export interface UserSubscription {
  tier: SubscriptionTier;
  expiresAt?: Date;
  status?: SubscriptionStatus;
}

// ============ Plan Constants ============

const FREE_MASTER_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: 10,
  maxServicesCount: 5,
  maxPortfolioItems: 10,
  searchBoostEnabled: false,
  analyticsLevel: 'basic',
  priorityBooking: false,
  extended_search: false,
  history_months: 3,
  client_stats_enabled: false,
  max_favorites: 5,
  pro_badge: false,
  client_notes_enabled: false,
  max_pinned_portfolio: 0,
  rebooking_reminder_enabled: false
};

const PRO_MASTER_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: null, // Unlimited
  maxServicesCount: null,
  maxPortfolioItems: null,
  searchBoostEnabled: true,
  analyticsLevel: 'advanced',
  priorityBooking: false,
  extended_search: true,
  history_months: 0, // unlimited
  client_stats_enabled: true,
  max_favorites: 0, // unlimited
  pro_badge: true,
  client_notes_enabled: true,
  max_pinned_portfolio: 5,
  rebooking_reminder_enabled: true
};

const FREE_CLIENT_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: null,
  maxServicesCount: null,
  maxPortfolioItems: null,
  searchBoostEnabled: false,
  analyticsLevel: 'basic',
  priorityBooking: false,
  extended_search: false,
  history_months: 3,
  client_stats_enabled: false,
  max_favorites: 5,
  pro_badge: false,
  client_notes_enabled: false,
  max_pinned_portfolio: 0,
  rebooking_reminder_enabled: false
};

const PRO_CLIENT_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: null,
  maxServicesCount: null,
  maxPortfolioItems: null,
  searchBoostEnabled: true,
  analyticsLevel: 'basic',
  priorityBooking: true,
  extended_search: true,
  history_months: 0, // unlimited
  client_stats_enabled: true,
  max_favorites: 0, // unlimited
  pro_badge: true,
  client_notes_enabled: false,
  max_pinned_portfolio: 0,
  rebooking_reminder_enabled: false
};

export const MASTER_PLANS: SubscriptionPlan[] = [
  // FREE Master Plan
  {
    id: 'master-free',
    name: 'Базовый',
    tier: 'free',
    userType: 'master',
    period: 'monthly',
    price: 0,
    limits: FREE_MASTER_LIMITS,
    extended_search: false,
    history_months: 3,
    client_stats_enabled: false,
    max_favorites: 5,
    pro_badge: false,
    client_notes_enabled: false,
    max_pinned_portfolio: 0,
    rebooking_reminder_enabled: false,
    features: [
      { name: 'Записи', description: '10 записей в месяц', included: true, limit: 10 },
      { name: 'Услуги', description: 'До 5 услуг', included: true, limit: 5 },
      { name: 'Портфолио', description: '10 фото в портфолио', included: true, limit: 10 },
      { name: 'PRO-бейдж', description: 'PRO-бейдж в профиле', included: false },
      { name: 'Продвижение', description: 'Буст в поиске', included: false },
      { name: 'Аналитика', description: 'Расширенная аналитика', included: false }
    ]
  },
  // PRO Master Monthly
  {
    id: 'master-pro-monthly',
    name: 'PRO',
    tier: 'pro',
    userType: 'master',
    period: 'monthly',
    price: 299,
    limits: PRO_MASTER_LIMITS,
    isPopular: true,
    extended_search: true,
    history_months: 0,
    client_stats_enabled: true,
    max_favorites: 0,
    pro_badge: true,
    client_notes_enabled: true,
    max_pinned_portfolio: 5,
    rebooking_reminder_enabled: true,
    features: [
      { name: 'Записи', description: 'Безлимит записей/услуг/портфолио', included: true, limit: null },
      { name: 'PRO-бейдж', description: 'PRO-бейдж в профиле', included: true },
      { name: 'Продвижение', description: 'Буст в поиске', included: true },
      { name: 'AI-ассистент', description: 'AI-ассистент', included: true },
      { name: 'Аналитика', description: 'Расширенная аналитика', included: true },
      { name: 'Заметки', description: 'Заметки о клиентах', included: true },
      { name: 'Закрепление', description: 'Закрепление работ в портфолио', included: true },
      { name: 'Напоминания', description: 'Напоминания о перезаписи', included: true },
      { name: 'Экспорт', description: 'Экспорт CSV', included: true },
      { name: 'Уведомления', description: 'Расширенные уведомления', included: true }
    ]
  },
  // PRO Master Yearly
  {
    id: 'master-pro-yearly',
    name: 'PRO',
    tier: 'pro',
    userType: 'master',
    period: 'yearly',
    price: 2499,
    originalPrice: 3588, // 299 * 12
    limits: PRO_MASTER_LIMITS,
    isPopular: true,
    extended_search: true,
    history_months: 0,
    client_stats_enabled: true,
    max_favorites: 0,
    pro_badge: true,
    client_notes_enabled: true,
    max_pinned_portfolio: 5,
    rebooking_reminder_enabled: true,
    features: [
      { name: 'Записи', description: 'Безлимит записей/услуг/портфолио', included: true, limit: null },
      { name: 'PRO-бейдж', description: 'PRO-бейдж в профиле', included: true },
      { name: 'Продвижение', description: 'Буст в поиске', included: true },
      { name: 'AI-ассистент', description: 'AI-ассистент', included: true },
      { name: 'Аналитика', description: 'Расширенная аналитика', included: true },
      { name: 'Заметки', description: 'Заметки о клиентах', included: true },
      { name: 'Закрепление', description: 'Закрепление работ в портфолио', included: true },
      { name: 'Напоминания', description: 'Напоминания о перезаписи', included: true },
      { name: 'Экспорт', description: 'Экспорт CSV', included: true },
      { name: 'Уведомления', description: 'Расширенные уведомления', included: true }
    ]
  }
];

export const CLIENT_PLANS: SubscriptionPlan[] = [
  // FREE Client Plan
  {
    id: 'client-free',
    name: 'Базовый',
    tier: 'free',
    userType: 'client',
    period: 'monthly',
    price: 0,
    limits: FREE_CLIENT_LIMITS,
    extended_search: false,
    history_months: 3,
    client_stats_enabled: false,
    max_favorites: 5,
    pro_badge: false,
    client_notes_enabled: false,
    max_pinned_portfolio: 0,
    rebooking_reminder_enabled: false,
    features: [
      { name: 'Запись', description: 'Запись к мастерам', included: true },
      { name: 'Приоритет', description: 'Приоритетная запись', included: false },
      { name: 'Избранные', description: 'Безлимит избранных', included: false },
      { name: 'Поиск', description: 'Расширенный поиск', included: false },
      { name: 'История', description: 'Полная история записей', included: false }
    ]
  },
  // PRO Client Monthly
  {
    id: 'client-pro-monthly',
    name: 'PRO',
    tier: 'pro',
    userType: 'client',
    period: 'monthly',
    price: 199,
    limits: PRO_CLIENT_LIMITS,
    isPopular: true,
    extended_search: true,
    history_months: 0,
    client_stats_enabled: true,
    max_favorites: 0,
    pro_badge: true,
    client_notes_enabled: false,
    max_pinned_portfolio: 0,
    rebooking_reminder_enabled: false,
    features: [
      { name: 'Запись', description: 'Запись к мастерам', included: true },
      { name: 'Приоритет', description: 'Приоритетная запись', included: true },
      { name: 'Избранные', description: 'Безлимит избранных', included: true },
      { name: 'Поиск', description: 'Расширенный поиск', included: true },
      { name: 'История', description: 'Полная история записей', included: true },
      { name: 'Статистика', description: 'Статистика расходов', included: true }
    ]
  },
  // PRO Client Yearly
  {
    id: 'client-pro-yearly',
    name: 'PRO',
    tier: 'pro',
    userType: 'client',
    period: 'yearly',
    price: 1699,
    originalPrice: 2388, // 199 * 12
    limits: PRO_CLIENT_LIMITS,
    isPopular: true,
    extended_search: true,
    history_months: 0,
    client_stats_enabled: true,
    max_favorites: 0,
    pro_badge: true,
    client_notes_enabled: false,
    max_pinned_portfolio: 0,
    rebooking_reminder_enabled: false,
    features: [
      { name: 'Запись', description: 'Запись к мастерам', included: true },
      { name: 'Приоритет', description: 'Приоритетная запись', included: true },
      { name: 'Избранные', description: 'Безлимит избранных', included: true },
      { name: 'Поиск', description: 'Расширенный поиск', included: true },
      { name: 'История', description: 'Полная история записей', included: true },
      { name: 'Статистика', description: 'Статистика расходов', included: true }
    ]
  }
];

// Helper functions
export function getPlanById(planId: string): SubscriptionPlan | undefined {
  return [...MASTER_PLANS, ...CLIENT_PLANS].find(p => p.id === planId);
}

export function getPlansForUserType(userType: 'master' | 'client'): SubscriptionPlan[] {
  return userType === 'master' ? MASTER_PLANS : CLIENT_PLANS;
}

export function getDefaultLimits(userType: 'master' | 'client'): SubscriptionLimits {
  return userType === 'master' ? FREE_MASTER_LIMITS : FREE_CLIENT_LIMITS;
}

export function getProLimits(userType: 'master' | 'client'): SubscriptionLimits {
  return userType === 'master' ? PRO_MASTER_LIMITS : PRO_CLIENT_LIMITS;
}
