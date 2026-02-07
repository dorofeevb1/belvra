import { Injectable, signal, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap, catchError, of, map } from 'rxjs';
import { ApiService } from './api.service';
import { User, Master, Client, UserRole, UserSubscription } from '../models';

const TOKEN_KEY = 'beautybook_access_token';
const REFRESH_TOKEN_KEY = 'beautybook_refresh_token';
const USER_KEY = 'beautybook_user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private router = inject(Router);
  private api = inject(ApiService);

  private currentUserSignal = signal<User | null>(null);
  private isAuthenticatedSignal = signal<boolean>(false);

  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isAuthenticated = this.isAuthenticatedSignal.asReadonly();

  readonly isMaster = computed(() => this.currentUserSignal()?.role === 'master');
  readonly isClient = computed(() => this.currentUserSignal()?.role === 'client');
  readonly masterData = computed(() =>
    this.isMaster() ? (this.currentUserSignal() as Master) : null
  );
  readonly clientData = computed(() =>
    this.isClient() ? (this.currentUserSignal() as Client) : null
  );
  /** Returns the master profile ID for API calls (different from user ID) */
  readonly masterApiId = computed(() => {
    const master = this.masterData();
    return master ? (master.masterProfileId || master.id) : null;
  });

  /** Check if current user has active PRO subscription */
  readonly isPro = computed(() => {
    const user = this.currentUserSignal();
    if (!user) return false;

    const subscription = (user as Master | Client).subscription;
    if (!subscription) return false;

    if (subscription.tier !== 'pro') return false;

    // Check if subscription is not expired
    if (subscription.expiresAt) {
      return new Date(subscription.expiresAt) > new Date();
    }

    return subscription.status === 'active';
  });

  constructor() {
    this.checkStoredAuth();
  }

  private checkStoredAuth(): void {
    const token = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);

    if (token && storedUser) {
      try {
        const user = JSON.parse(storedUser);
        this.currentUserSignal.set(user);
        this.isAuthenticatedSignal.set(true);
      } catch {
        this.clearStorage();
      }
    }
  }

  private clearStorage(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  private mapBackendUser(backendUser: any, role: UserRole): User {
    const baseUser = {
      id: backendUser.id,
      email: backendUser.email,
      name: backendUser.full_name || `${backendUser.first_name} ${backendUser.last_name}`,
      role: role,
      phone: backendUser.phone || '',
      avatar: backendUser.avatar,
      createdAt: new Date(backendUser.created_at)
    };

    // Map subscription data if available
    let subscription: UserSubscription | undefined;
    if (backendUser.subscription) {
      subscription = {
        tier: backendUser.subscription.tier || 'free',
        expiresAt: backendUser.subscription.expires_at
          ? new Date(backendUser.subscription.expires_at)
          : undefined,
        status: backendUser.subscription.status
      };
    }

    if (role === 'master') {
      // Build coordinates if available
      const coordinates = backendUser.latitude && backendUser.longitude
        ? { lat: parseFloat(backendUser.latitude), lng: parseFloat(backendUser.longitude) }
        : undefined;

      return {
        ...baseUser,
        masterProfileId: backendUser.master_profile_id || backendUser.id,
        specialization: backendUser.specialization || '',
        description: backendUser.bio || '',
        address: backendUser.address || '',
        coordinates,
        rating: parseFloat(backendUser.rating) || 0,
        reviewsCount: backendUser.reviews_count || 0,
        workSchedule: {
          monday: null,
          tuesday: null,
          wednesday: null,
          thursday: null,
          friday: null,
          saturday: null,
          sunday: null
        },
        services: [],
        subscription
      } as Master;
    }

    return {
      ...baseUser,
      favoritesMasters: [],
      subscription
    } as Client;
  }

  login(email: string, password: string): Observable<boolean> {
    return this.api.login(email, password).pipe(
      tap(response => {
        localStorage.setItem(TOKEN_KEY, response.access);
        localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh);

        const role: UserRole = response.user.role === 'master' ? 'master' : 'client';
        const user = this.mapBackendUser(response.user, role);

        localStorage.setItem(USER_KEY, JSON.stringify(user));
        this.currentUserSignal.set(user);
        this.isAuthenticatedSignal.set(true);
      }),
      map(() => true),
      catchError(error => {
        console.error('Login error:', error);
        return of(false);
      })
    );
  }

  // Register new user
  register(data: {
    email: string;
    password: string;
    password_confirm: string;
    first_name: string;
    last_name: string;
    phone?: string;
  }): Observable<boolean> {
    return this.registerWithRole({ ...data, role: 'client' });
  }

  // Register with role selection
  registerWithRole(data: {
    email: string;
    password: string;
    password_confirm: string;
    first_name: string;
    last_name: string;
    phone?: string;
    role: UserRole;
  }): Observable<boolean> {
    return this.api.register(data).pipe(
      tap(response => {
        localStorage.setItem(TOKEN_KEY, response.access);
        localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh);

        const role: UserRole = response.user.role === 'master' ? 'master' : 'client';
        const user = this.mapBackendUser(response.user, role);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        this.currentUserSignal.set(user);
        this.isAuthenticatedSignal.set(true);
      }),
      map(() => true),
      catchError(error => {
        console.error('Registration error:', error);
        throw error;
      })
    );
  }

  logout(): void {
    this.api.logout().subscribe({
      error: (err) => console.error('Logout error:', err)
    });

    this.currentUserSignal.set(null);
    this.isAuthenticatedSignal.set(false);
    this.clearStorage();
    this.router.navigate(['/login']);
  }

  updateMasterProfile(updates: Partial<Master>, localOnly = false): Observable<boolean> {
    const current = this.currentUserSignal();

    if (!current || current.role !== 'master') {
      return of(false);
    }

    if (localOnly) {
      const updated = { ...current, ...updates } as Master;
      this.currentUserSignal.set(updated);
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      return of(true);
    }

    // Call API to update profile
    const payload = {
      first_name: updates.name?.split(' ')[0],
      last_name: updates.name?.split(' ').slice(1).join(' ') || '',
      phone: updates.phone,
      specialization: updates.specialization,
      bio: updates.description
    };

    return this.api.updateProfile(payload).pipe(
      tap(() => {
        const updated = { ...current, ...updates } as Master;
        this.currentUserSignal.set(updated);
        localStorage.setItem(USER_KEY, JSON.stringify(updated));
      }),
      map(() => true),
      catchError(error => {
        console.error('Profile update error:', error);
        return of(false);
      })
    );
  }

  updateClientProfile(updates: Partial<Client>): Observable<boolean> {
    const current = this.currentUserSignal();
    if (!current || current.role !== 'client') {
      return of(false);
    }

    // Build API payload only with defined fields
    const apiData: Record<string, any> = {};
    if (updates.name !== undefined) {
      apiData['first_name'] = updates.name.split(' ')[0];
      apiData['last_name'] = updates.name.split(' ').slice(1).join(' ') || '';
    }
    if (updates.phone !== undefined) {
      apiData['phone'] = updates.phone;
    }
    if (updates.avatar !== undefined) {
      apiData['avatar'] = updates.avatar;
    }

    // Filter out undefined values from local updates
    const definedUpdates: Partial<Client> = {};
    for (const [key, value] of Object.entries(updates)) {
      if (value !== undefined) {
        (definedUpdates as any)[key] = value;
      }
    }

    // Call API to update profile
    return this.api.updateProfile(apiData).pipe(
      tap(() => {
        const updated = { ...current, ...definedUpdates } as Client;
        this.currentUserSignal.set(updated);
        localStorage.setItem(USER_KEY, JSON.stringify(updated));
      }),
      map(() => true),
      catchError(error => {
        console.error('Profile update error:', error);
        return of(false);
      })
    );
  }

  // Refresh profile from backend (to get updated data like coordinates)
  refreshProfile(): Observable<boolean> {
    return this.api.getProfile().pipe(
      tap(backendUser => {
        const role: UserRole = backendUser.role === 'master' ? 'master' : 'client';
        const user = this.mapBackendUser(backendUser, role);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        this.currentUserSignal.set(user);
      }),
      map(() => true),
      catchError(error => {
        console.error('Profile refresh error:', error);
        return of(false);
      })
    );
  }

  // Email verification
  verifyEmail(email: string, code: string): Observable<{ detail: string }> {
    return this.api.verifyEmail(email, code).pipe(
      tap(() => {
        // Update user's verified status locally
        const user = this.currentUserSignal();
        if (user) {
          const updatedUser = { ...user, isVerified: true };
          this.currentUserSignal.set(updatedUser);
          localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
        }
      })
    );
  }

  resendVerificationEmail(): Observable<{ detail: string }> {
    return this.api.resendVerificationEmail();
  }

  // Check if current user is verified
  readonly isEmailVerified = computed(() => {
    const user = this.currentUserSignal();
    return user ? (user as any).isVerified === true : false;
  });
}
