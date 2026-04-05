import { Injectable, inject, signal, computed } from '@angular/core';
import { Observable, of, tap, catchError, map } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import {
  Subscription,
  SubscriptionTier,
  SubscriptionLimits,
  UsageStats,
  SubscriptionPlan,
  MASTER_PLANS,
  CLIENT_PLANS,
  getDefaultLimits,
  getProLimits,
  getPlanById
} from '../models';

/** Map API plan response to SubscriptionPlan, merging with local feature/limit definitions. */
function mapApiPlan(apiPlan: any): SubscriptionPlan {
  const tier: SubscriptionTier = apiPlan.tier || 'free';
  const userType = apiPlan.user_type || 'master';
  const period = apiPlan.period || 'monthly';

  // Find matching local plan for features/limits
  const localPlans = userType === 'master' ? MASTER_PLANS : CLIENT_PLANS;
  const localMatch = localPlans.find(p => p.tier === tier && p.period === period);

  const limits = localMatch?.limits || getDefaultLimits(userType);

  return {
    id: apiPlan.id,  // Real UUID from server
    name: localMatch?.name || apiPlan.name,
    tier,
    userType,
    period,
    price: parseFloat(apiPlan.price) || 0,
    originalPrice: apiPlan.original_price ? parseFloat(apiPlan.original_price) : localMatch?.originalPrice,
    features: localMatch?.features || [],
    limits,
    isPopular: localMatch?.isPopular || tier === 'pro',
    extended_search: localMatch?.extended_search ?? limits.extended_search,
    history_months: localMatch?.history_months ?? limits.history_months,
    client_stats_enabled: localMatch?.client_stats_enabled ?? limits.client_stats_enabled,
    max_favorites: localMatch?.max_favorites ?? limits.max_favorites,
    pro_badge: localMatch?.pro_badge ?? limits.pro_badge,
    client_notes_enabled: localMatch?.client_notes_enabled ?? limits.client_notes_enabled,
    max_pinned_portfolio: localMatch?.max_pinned_portfolio ?? limits.max_pinned_portfolio,
    rebooking_reminder_enabled: localMatch?.rebooking_reminder_enabled ?? limits.rebooking_reminder_enabled,
  };
}

@Injectable({
  providedIn: 'root'
})
export class SubscriptionService {
  private api = inject(ApiService);
  private auth = inject(AuthService);

  // State signals
  private subscriptionSignal = signal<Subscription | null>(null);
  private usageStatsSignal = signal<UsageStats>({
    appointmentsThisMonth: 0,
    servicesCount: 0,
    portfolioItemsCount: 0
  });
  private loadingSignal = signal<boolean>(false);
  private apiPlansSignal = signal<SubscriptionPlan[]>([]);

  // Public readonly signals
  readonly subscription = this.subscriptionSignal.asReadonly();
  readonly usageStats = this.usageStatsSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  // Computed signals
  readonly isEarlyAdopter = computed(() => {
    return this.auth.currentUser()?.isEarlyAdopter === true;
  });

  readonly isPro = computed(() => {
    // Early adopters have lifetime Pro
    if (this.isEarlyAdopter()) return true;

    const sub = this.subscriptionSignal();
    if (sub && sub.status === 'active' && sub.tier === 'pro') {
      return new Date(sub.currentPeriodEnd) > new Date();
    }
    // Also check user's subscription from auth service
    const user = this.auth.currentUser();
    if (user && 'subscription' in user) {
      const userSub = (user as any).subscription;
      if (userSub?.tier === 'pro' && userSub?.expiresAt) {
        return new Date(userSub.expiresAt) > new Date();
      }
    }
    return false;
  });

  readonly currentTier = computed((): SubscriptionTier => {
    return this.isPro() ? 'pro' : 'free';
  });

  readonly limits = computed((): SubscriptionLimits => {
    const user = this.auth.currentUser();
    const userType = user?.role === 'master' ? 'master' : 'client';
    return this.isPro() ? getProLimits(userType) : getDefaultLimits(userType);
  });

  readonly daysUntilExpiry = computed((): number | null => {
    const sub = this.subscriptionSignal();
    if (!sub || sub.status !== 'active') return null;

    const now = new Date();
    const end = new Date(sub.currentPeriodEnd);
    const diffTime = end.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  });

  readonly currentPlan = computed((): SubscriptionPlan | null => {
    const sub = this.subscriptionSignal();
    if (sub?.planId) {
      return getPlanById(sub.planId) || null;
    }
    return null;
  });

  // Available plans based on user type (prefer API plans, fallback to local)
  readonly availablePlans = computed((): SubscriptionPlan[] => {
    const user = this.auth.currentUser();
    const userType = user?.role === 'master' ? 'master' : 'client';
    const apiPlans = this.apiPlansSignal().filter(p => p.userType === userType);
    if (apiPlans.length > 0) return apiPlans;
    return userType === 'master' ? MASTER_PLANS : CLIENT_PLANS;
  });

  // ============ Limit checking methods ============

  canCreateAppointment(): boolean {
    const limits = this.limits();
    const usage = this.usageStatsSignal();

    if (limits.maxAppointmentsPerMonth === null) return true;
    return usage.appointmentsThisMonth < limits.maxAppointmentsPerMonth;
  }

  canAddService(): boolean {
    const limits = this.limits();
    const usage = this.usageStatsSignal();

    if (limits.maxServicesCount === null) return true;
    return usage.servicesCount < limits.maxServicesCount;
  }

  canAddPortfolioItem(): boolean {
    const limits = this.limits();
    const usage = this.usageStatsSignal();

    if (limits.maxPortfolioItems === null) return true;
    return usage.portfolioItemsCount < limits.maxPortfolioItems;
  }

  getRemainingAppointments(): number | null {
    const limits = this.limits();
    const usage = this.usageStatsSignal();

    if (limits.maxAppointmentsPerMonth === null) return null;
    return Math.max(0, limits.maxAppointmentsPerMonth - usage.appointmentsThisMonth);
  }

  getRemainingServices(): number | null {
    const limits = this.limits();
    const usage = this.usageStatsSignal();

    if (limits.maxServicesCount === null) return null;
    return Math.max(0, limits.maxServicesCount - usage.servicesCount);
  }

  getRemainingPortfolioItems(): number | null {
    const limits = this.limits();
    const usage = this.usageStatsSignal();

    if (limits.maxPortfolioItems === null) return null;
    return Math.max(0, limits.maxPortfolioItems - usage.portfolioItemsCount);
  }

  // ============ API methods ============

  loadPlans(): Observable<SubscriptionPlan[]> {
    return this.api.getSubscriptionPlans().pipe(
      tap((response: any) => {
        const results = Array.isArray(response) ? response : (response?.results || []);
        const plans = results.map(mapApiPlan);
        this.apiPlansSignal.set(plans);
      }),
      map(() => this.apiPlansSignal()),
      catchError(error => {
        console.error('Error loading plans:', error);
        return of([]);
      })
    );
  }

  loadSubscription(): Observable<Subscription | null> {
    this.loadingSignal.set(true);

    return this.api.getSubscription().pipe(
      tap((response: any) => {
        if (response) {
          const plan = response.plan || {};
          const subscription: Subscription = {
            id: response.id,
            userId: response.user_id || response.user,
            planId: plan.id || response.plan_id,
            tier: plan.tier || response.tier || 'free',
            period: plan.period || response.period || 'monthly',
            status: response.status,
            currentPeriodStart: new Date(response.current_period_start),
            currentPeriodEnd: new Date(response.current_period_end),
            cancelAtPeriodEnd: response.cancel_at_period_end,
            autoRenew: response.auto_renew
          };
          this.subscriptionSignal.set(subscription);
        } else {
          this.subscriptionSignal.set(null);
        }
        this.loadingSignal.set(false);
      }),
      map((response: any) => response ? this.subscriptionSignal() : null),
      catchError(error => {
        console.error('Error loading subscription:', error);
        this.loadingSignal.set(false);
        return of(null);
      })
    );
  }

  loadUsageStats(): Observable<UsageStats> {
    return this.api.getSubscriptionUsage().pipe(
      tap((response: any) => {
        const stats: UsageStats = {
          appointmentsThisMonth: response.appointments_this_month || 0,
          servicesCount: response.services_count || 0,
          portfolioItemsCount: response.portfolio_items_count || 0
        };
        this.usageStatsSignal.set(stats);
      }),
      map(() => this.usageStatsSignal()),
      catchError(error => {
        console.error('Error loading usage stats:', error);
        return of(this.usageStatsSignal());
      })
    );
  }

  subscribeToPlan(planId: string, returnUrl?: string): Observable<{ payment_url: string } | null> {
    this.loadingSignal.set(true);

    return this.api.createSubscription({
      plan_id: planId,
      return_url: returnUrl || window.location.origin + '/subscription/success'
    }).pipe(
      tap(() => {
        this.loadingSignal.set(false);
      }),
      catchError(error => {
        console.error('Error creating subscription:', error);
        this.loadingSignal.set(false);
        throw error;
      })
    );
  }

  cancelSubscription(): Observable<boolean> {
    this.loadingSignal.set(true);

    return this.api.cancelSubscription().pipe(
      tap(() => {
        const current = this.subscriptionSignal();
        if (current) {
          this.subscriptionSignal.set({
            ...current,
            cancelAtPeriodEnd: true,
            autoRenew: false
          });
        }
        this.loadingSignal.set(false);
      }),
      map(() => true),
      catchError(error => {
        console.error('Error canceling subscription:', error);
        this.loadingSignal.set(false);
        return of(false);
      })
    );
  }

  reactivateSubscription(): Observable<boolean> {
    this.loadingSignal.set(true);

    return this.api.reactivateSubscription().pipe(
      tap(() => {
        const current = this.subscriptionSignal();
        if (current) {
          this.subscriptionSignal.set({
            ...current,
            cancelAtPeriodEnd: false,
            autoRenew: true
          });
        }
        this.loadingSignal.set(false);
      }),
      map(() => true),
      catchError(error => {
        console.error('Error reactivating subscription:', error);
        this.loadingSignal.set(false);
        return of(false);
      })
    );
  }

  changePlan(newPlanId: string): Observable<{ payment_url?: string } | null> {
    this.loadingSignal.set(true);

    return this.api.changeSubscriptionPlan({
      plan_id: newPlanId,
      return_url: window.location.origin + '/subscription/success'
    }).pipe(
      tap(() => {
        this.loadingSignal.set(false);
      }),
      catchError(error => {
        console.error('Error changing plan:', error);
        this.loadingSignal.set(false);
        throw error;
      })
    );
  }

  // ============ Helper methods ============

  updateUsageStats(partial: Partial<UsageStats>): void {
    const current = this.usageStatsSignal();
    this.usageStatsSignal.set({ ...current, ...partial });
  }

  // Increment counters locally (for optimistic updates)
  incrementAppointments(): void {
    const current = this.usageStatsSignal();
    this.usageStatsSignal.set({
      ...current,
      appointmentsThisMonth: current.appointmentsThisMonth + 1
    });
  }

  incrementServices(): void {
    const current = this.usageStatsSignal();
    this.usageStatsSignal.set({
      ...current,
      servicesCount: current.servicesCount + 1
    });
  }

  decrementServices(): void {
    const current = this.usageStatsSignal();
    this.usageStatsSignal.set({
      ...current,
      servicesCount: Math.max(0, current.servicesCount - 1)
    });
  }

  incrementPortfolio(): void {
    const current = this.usageStatsSignal();
    this.usageStatsSignal.set({
      ...current,
      portfolioItemsCount: current.portfolioItemsCount + 1
    });
  }

  decrementPortfolio(): void {
    const current = this.usageStatsSignal();
    this.usageStatsSignal.set({
      ...current,
      portfolioItemsCount: Math.max(0, current.portfolioItemsCount - 1)
    });
  }

  // Check if user should see upgrade prompt
  shouldShowUpgradePrompt(): boolean {
    if (this.isPro()) return false;

    const limits = this.limits();
    const usage = this.usageStatsSignal();

    // Show prompt if user is at 80% or more of any limit
    if (limits.maxAppointmentsPerMonth !== null) {
      const threshold = limits.maxAppointmentsPerMonth * 0.8;
      if (usage.appointmentsThisMonth >= threshold) return true;
    }

    if (limits.maxServicesCount !== null) {
      const threshold = limits.maxServicesCount * 0.8;
      if (usage.servicesCount >= threshold) return true;
    }

    if (limits.maxPortfolioItems !== null) {
      const threshold = limits.maxPortfolioItems * 0.8;
      if (usage.portfolioItemsCount >= threshold) return true;
    }

    return false;
  }
}
