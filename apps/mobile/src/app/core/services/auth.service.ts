import { Injectable, signal, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap, catchError, of, map } from 'rxjs';
import { ApiService } from './api.service';
import { User, Master, Client, UserRole, AuthCredentials, UserSubscription } from '../models';

const TOKEN_KEY = 'beautybook_access_token';
const REFRESH_TOKEN_KEY = 'beautybook_refresh_token';
const USER_KEY = 'beautybook_user';

// Demo data for fallback mode
const DEMO_MASTER: Master = {
  id: 'master-1',
  email: 'master@beautybook.ru',
  name: 'Анна Петрова',
  role: 'master',
  phone: '+7 (999) 123-45-67',
  avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150',
  specialization: 'Мастер маникюра и педикюра',
  description: 'Профессиональный мастер маникюра с опытом работы более 5 лет.',
  address: 'Москва, ул. Тверская, д. 15',
  coordinates: { lat: 55.764019, lng: 37.606738 },
  rating: 4.8,
  reviewsCount: 156,
  workSchedule: {
    monday: { start: '09:00', end: '18:00' },
    tuesday: { start: '09:00', end: '18:00' },
    wednesday: { start: '09:00', end: '18:00' },
    thursday: { start: '09:00', end: '18:00' },
    friday: { start: '09:00', end: '18:00' },
    saturday: { start: '10:00', end: '16:00' },
    sunday: null
  },
  services: ['service-1', 'service-2', 'service-3'],
  createdAt: new Date('2023-01-15')
};

const DEMO_CLIENT: Client = {
  id: 'client-1',
  email: 'client@beautybook.ru',
  name: 'Мария Иванова',
  role: 'client',
  phone: '+7 (999) 987-65-43',
  avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150',
  favoritesMasters: ['master-1'],
  createdAt: new Date('2023-06-01')
};

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private router = inject(Router);
  private api = inject(ApiService);

  private currentUserSignal = signal<User | null>(null);
  private isAuthenticatedSignal = signal<boolean>(false);
  private useDemoMode = signal<boolean>(false);

  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isAuthenticated = this.isAuthenticatedSignal.asReadonly();
  readonly isDemoMode = this.useDemoMode.asReadonly();

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

  // Real API login
  loginWithApi(email: string, password: string): Observable<boolean> {
    return this.api.login(email, password).pipe(
      tap(response => {
        localStorage.setItem(TOKEN_KEY, response.access);
        localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh);

        const role: UserRole = response.user.role === 'master' ? 'master' : 'client';
        const user = this.mapBackendUser(response.user, role);

        localStorage.setItem(USER_KEY, JSON.stringify(user));
        this.currentUserSignal.set(user);
        this.isAuthenticatedSignal.set(true);
        this.useDemoMode.set(false);
      }),
      map(() => true),
      catchError(error => {
        console.error('Login error:', error);
        return of(false);
      })
    );
  }

  // Demo mode login (fallback)
  login(credentials: AuthCredentials): boolean {
    // Try demo credentials
    if (credentials.role === 'master') {
      if (credentials.email === 'master@beautybook.ru' && credentials.password === 'master123') {
        this.setDemoUser(DEMO_MASTER);
        return true;
      }
    } else {
      if (credentials.email === 'client@beautybook.ru' && credentials.password === 'client123') {
        this.setDemoUser(DEMO_CLIENT);
        return true;
      }
    }
    return false;
  }

  private setDemoUser(user: User): void {
    this.currentUserSignal.set(user);
    this.isAuthenticatedSignal.set(true);
    this.useDemoMode.set(true);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
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
        this.useDemoMode.set(false);
      }),
      map(() => true),
      catchError(error => {
        console.error('Registration error:', error);
        throw error;
      })
    );
  }

  logout(): void {
    if (!this.useDemoMode()) {
      this.api.logout().subscribe({
        error: (err) => console.error('Logout error:', err)
      });
    }

    this.currentUserSignal.set(null);
    this.isAuthenticatedSignal.set(false);
    this.useDemoMode.set(false);
    this.clearStorage();
    this.router.navigate(['/login']);
  }

  updateMasterProfile(updates: Partial<Master>, localOnly = false): Observable<boolean> {
    const current = this.currentUserSignal();

    if (!current || current.role !== 'master') {
      return of(false);
    }

    // If localOnly flag is set or in demo mode, just update locally
    if (localOnly || this.useDemoMode()) {
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
        // Still update locally on error
        const updated = { ...current, ...updates } as Master;
        this.currentUserSignal.set(updated);
        localStorage.setItem(USER_KEY, JSON.stringify(updated));
        return of(true);
      })
    );
  }

  updateClientProfile(updates: Partial<Client>): Observable<boolean> {
    const current = this.currentUserSignal();
    if (!current || current.role !== 'client') {
      return of(false);
    }

    // If in demo mode, just update locally
    if (this.useDemoMode()) {
      const updated = { ...current, ...updates } as Client;
      this.currentUserSignal.set(updated);
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      return of(true);
    }

    // Call API to update profile
    return this.api.updateProfile({
      first_name: updates.name?.split(' ')[0],
      last_name: updates.name?.split(' ').slice(1).join(' ') || '',
      phone: updates.phone,
      avatar: updates.avatar
    }).pipe(
      tap(() => {
        const updated = { ...current, ...updates } as Client;
        this.currentUserSignal.set(updated);
        localStorage.setItem(USER_KEY, JSON.stringify(updated));
      }),
      map(() => true),
      catchError(error => {
        console.error('Profile update error:', error);
        // Still update locally on error
        const updated = { ...current, ...updates } as Client;
        this.currentUserSignal.set(updated);
        localStorage.setItem(USER_KEY, JSON.stringify(updated));
        return of(true);
      })
    );
  }

  getDemoCredentials(role: UserRole): { email: string; password: string } {
    return role === 'master'
      ? { email: 'master@beautybook.ru', password: 'master123' }
      : { email: 'client@beautybook.ru', password: 'client123' };
  }

  // Get backend credentials hint
  getBackendCredentials(): { admin: { email: string; password: string } } {
    return {
      admin: { email: 'admin@example.com', password: 'admin123' }
    };
  }

  // Refresh profile from backend (to get updated data like coordinates)
  refreshProfile(): Observable<boolean> {
    if (this.useDemoMode()) {
      return of(true);
    }

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
  verifyEmail(token: string): Observable<{ detail: string }> {
    return this.api.verifyEmail(token).pipe(
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
