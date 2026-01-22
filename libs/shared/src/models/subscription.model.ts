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
  commissionPercent: number;
  searchBoostEnabled: boolean;
  analyticsLevel: 'basic' | 'advanced';
  priorityBooking: boolean;
  cashbackPercent: number;
  discountPercent: number;
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
  commissionPercent: 10,
  searchBoostEnabled: false,
  analyticsLevel: 'basic',
  priorityBooking: false,
  cashbackPercent: 0,
  discountPercent: 0
};

const PRO_MASTER_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: null, // Unlimited
  maxServicesCount: null,
  maxPortfolioItems: null,
  commissionPercent: 5,
  searchBoostEnabled: true,
  analyticsLevel: 'advanced',
  priorityBooking: false,
  cashbackPercent: 0,
  discountPercent: 0
};

const FREE_CLIENT_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: null,
  maxServicesCount: null,
  maxPortfolioItems: null,
  commissionPercent: 0,
  searchBoostEnabled: false,
  analyticsLevel: 'basic',
  priorityBooking: false,
  cashbackPercent: 0,
  discountPercent: 0
};

const PRO_CLIENT_LIMITS: SubscriptionLimits = {
  maxAppointmentsPerMonth: null,
  maxServicesCount: null,
  maxPortfolioItems: null,
  commissionPercent: 0,
  searchBoostEnabled: false,
  analyticsLevel: 'basic',
  priorityBooking: true,
  cashbackPercent: 5,
  discountPercent: 10
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
    features: [
      { name: 'Записи', description: '10 записей в месяц', included: true, limit: 10 },
      { name: 'Услуги', description: 'До 5 услуг', included: true, limit: 5 },
      { name: 'Портфолио', description: '10 фото в портфолио', included: true, limit: 10 },
      { name: 'Комиссия', description: 'Комиссия 10%', included: true },
      { name: 'Продвижение', description: 'Продвижение в поиске', included: false },
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
    features: [
      { name: 'Записи', description: 'Неограниченные записи', included: true, limit: null },
      { name: 'Услуги', description: 'Неограниченные услуги', included: true, limit: null },
      { name: 'Портфолио', description: 'Неограниченное портфолио', included: true, limit: null },
      { name: 'Комиссия', description: 'Сниженная комиссия 5%', included: true },
      { name: 'Продвижение', description: 'Продвижение в поиске', included: true },
      { name: 'Аналитика', description: 'Расширенная аналитика', included: true }
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
    features: [
      { name: 'Записи', description: 'Неограниченные записи', included: true, limit: null },
      { name: 'Услуги', description: 'Неограниченные услуги', included: true, limit: null },
      { name: 'Портфолио', description: 'Неограниченное портфолио', included: true, limit: null },
      { name: 'Комиссия', description: 'Сниженная комиссия 5%', included: true },
      { name: 'Продвижение', description: 'Продвижение в поиске', included: true },
      { name: 'Аналитика', description: 'Расширенная аналитика', included: true }
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
    features: [
      { name: 'Запись', description: 'Запись к мастерам', included: true },
      { name: 'Скидки', description: 'Скидка 10% на услуги', included: false },
      { name: 'Приоритет', description: 'Приоритетная запись', included: false },
      { name: 'Кешбэк', description: 'Кешбэк 5%', included: false }
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
    features: [
      { name: 'Запись', description: 'Запись к мастерам', included: true },
      { name: 'Скидки', description: 'Скидка 10% на услуги', included: true },
      { name: 'Приоритет', description: 'Приоритетная запись', included: true },
      { name: 'Кешбэк', description: 'Кешбэк 5%', included: true }
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
    features: [
      { name: 'Запись', description: 'Запись к мастерам', included: true },
      { name: 'Скидки', description: 'Скидка 10% на услуги', included: true },
      { name: 'Приоритет', description: 'Приоритетная запись', included: true },
      { name: 'Кешбэк', description: 'Кешбэк 5%', included: true }
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
