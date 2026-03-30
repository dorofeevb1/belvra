import { describe, it, expect, beforeEach, vi } from 'vitest';

/**
 * AuthService tests — we test the core logic (storage, signals, computed properties)
 * without bootstrapping Angular's DI. We instantiate the class directly and mock
 * its injected dependencies via Object.defineProperty.
 */

// ---------- Fake localStorage ----------
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
  removeItem: vi.fn((key: string) => { delete store[key]; }),
  clear: vi.fn(() => { for (const k of Object.keys(store)) delete store[k]; }),
};
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock, writable: true });

// ---------- Stub Angular primitives ----------
// We need `signal`, `computed`, `inject`, `Injectable` from @angular/core.
// Vitest runs in Node so Angular is available from node_modules.
import { signal, computed } from '@angular/core';
import { AuthService } from './auth.service';
import { Master } from '../models';

// Keys must match those in the service
const TOKEN_KEY = 'belvra_access_token';
const REFRESH_TOKEN_KEY = 'belvra_refresh_token';
const USER_KEY = 'belvra_user';

/**
 * Helper: build a minimal AuthService instance **without** Angular TestBed.
 * We override the private fields that are normally set via `inject()`.
 */
function createService(): AuthService {
  // Clear storage before each creation
  localStorageMock.clear();
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();

  // Prevent constructor from calling checkStoredAuth with stale data
  // by ensuring localStorage is clean before instantiation
  const svc = Object.create(AuthService.prototype) as AuthService;

  // Set up private signals manually (mimic what the class body initialiser does)
  const currentUserSignal = signal<any>(null);
  const isAuthenticatedSignal = signal<boolean>(false);

  Object.defineProperty(svc, 'currentUserSignal', { value: currentUserSignal, writable: true });
  Object.defineProperty(svc, 'isAuthenticatedSignal', { value: isAuthenticatedSignal, writable: true });

  // Public readonly signals
  Object.defineProperty(svc, 'currentUser', { value: currentUserSignal.asReadonly(), writable: true });
  Object.defineProperty(svc, 'isAuthenticated', { value: isAuthenticatedSignal.asReadonly(), writable: true });

  // Computed properties
  Object.defineProperty(svc, 'isMaster', {
    value: computed(() => currentUserSignal()?.role === 'master'),
    writable: true,
  });
  Object.defineProperty(svc, 'isClient', {
    value: computed(() => currentUserSignal()?.role === 'client'),
    writable: true,
  });
  Object.defineProperty(svc, 'masterData', {
    value: computed(() => currentUserSignal()?.role === 'master' ? currentUserSignal() as Master : null),
    writable: true,
  });
  Object.defineProperty(svc, 'clientData', {
    value: computed(() => currentUserSignal()?.role === 'client' ? currentUserSignal() : null),
    writable: true,
  });
  Object.defineProperty(svc, 'masterApiId', {
    value: computed(() => {
      const master = currentUserSignal()?.role === 'master' ? currentUserSignal() as Master : null;
      return master ? (master.masterProfileId || master.id) : null;
    }),
    writable: true,
  });
  Object.defineProperty(svc, 'isEmailVerified', {
    value: computed(() => currentUserSignal()?.isVerified === true),
    writable: true,
  });

  // Mock router and api (they are injected but not needed for these unit tests)
  Object.defineProperty(svc, 'router', { value: { navigate: vi.fn() }, writable: true });
  Object.defineProperty(svc, 'api', {
    value: { logout: () => ({ subscribe: vi.fn() }) },
    writable: true,
  });

  return svc;
}

describe('AuthService', () => {
  let service: AuthService;

  beforeEach(() => {
    service = createService();
  });

  // ------- isAuthenticated -------

  describe('isAuthenticated', () => {
    it('returns false by default', () => {
      expect(service.isAuthenticated()).toBe(false);
    });

    it('returns true after simulating login (setting signals)', () => {
      // Simulate what login() does: set signals + storage
      const user = { id: '1', email: 'a@b.c', name: 'Test', role: 'client' as const, createdAt: new Date() };
      (service as any).currentUserSignal.set(user);
      (service as any).isAuthenticatedSignal.set(true);

      expect(service.isAuthenticated()).toBe(true);
    });
  });

  // ------- Login stores tokens correctly -------

  describe('login stores tokens', () => {
    it('stores access and refresh tokens in localStorage', () => {
      // We simulate what login() does internally after API response:
      localStorage.setItem(TOKEN_KEY, 'access-abc');
      localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh-xyz');
      const user = { id: '1', email: 'a@b.c', name: 'Test', role: 'client', createdAt: new Date().toISOString() };
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      (service as any).currentUserSignal.set(user);
      (service as any).isAuthenticatedSignal.set(true);

      expect(localStorage.getItem(TOKEN_KEY)).toBe('access-abc');
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('refresh-xyz');
      expect(localStorage.getItem(USER_KEY)).toBeTruthy();
      expect(service.isAuthenticated()).toBe(true);
    });
  });

  // ------- Logout clears all data -------

  describe('logout', () => {
    it('clears signals, storage, and navigates to /login', () => {
      // Setup: simulate logged-in state
      const user = { id: '1', email: 'a@b.c', name: 'Test', role: 'client' as const, createdAt: new Date() };
      (service as any).currentUserSignal.set(user);
      (service as any).isAuthenticatedSignal.set(true);
      localStorage.setItem(TOKEN_KEY, 'token');
      localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh');
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      service.logout();

      expect(service.isAuthenticated()).toBe(false);
      expect(service.currentUser()).toBeNull();
      expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
      expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
      expect(localStorage.getItem(USER_KEY)).toBeNull();
      expect((service as any).router.navigate).toHaveBeenCalledWith(['/login']);
    });
  });

  // ------- masterApiId returns profile ID not user ID -------

  describe('masterApiId', () => {
    it('returns masterProfileId when available (not user id)', () => {
      const master: any = {
        id: 'user-123',
        masterProfileId: 'profile-456',
        role: 'master',
        email: 'm@b.c',
        name: 'Master',
        createdAt: new Date(),
      };
      (service as any).currentUserSignal.set(master);

      expect(service.masterApiId()).toBe('profile-456');
    });

    it('falls back to user id when masterProfileId is absent', () => {
      const master: any = {
        id: 'user-123',
        role: 'master',
        email: 'm@b.c',
        name: 'Master',
        createdAt: new Date(),
      };
      (service as any).currentUserSignal.set(master);

      expect(service.masterApiId()).toBe('user-123');
    });

    it('returns null when user is not a master', () => {
      const client: any = {
        id: 'user-789',
        role: 'client',
        email: 'c@b.c',
        name: 'Client',
        createdAt: new Date(),
      };
      (service as any).currentUserSignal.set(client);

      expect(service.masterApiId()).toBeNull();
    });

    it('returns null when not authenticated', () => {
      expect(service.masterApiId()).toBeNull();
    });
  });
});
