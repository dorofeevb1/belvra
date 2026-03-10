import { describe, it, expect, vi, beforeEach } from 'vitest';

/**
 * Auth guard tests — we test the functional guards by mocking
 * Angular's inject() via vi.mock before the guards are imported.
 */

// Stub types
interface MockAuthService {
  isAuthenticated: () => boolean;
  isMaster: () => boolean;
  isClient: () => boolean;
  isEmailVerified: () => boolean;
  currentUser: () => any;
}

interface MockRouter {
  navigate: ReturnType<typeof vi.fn>;
}

let mockAuth: MockAuthService;
let mockRouter: MockRouter;

// Mock @angular/core to control inject()
vi.mock('@angular/core', async (importOriginal) => {
  const orig: any = await importOriginal();
  return {
    ...orig,
    inject: (_token: any) => {
      // Determine what to return based on the token
      // AuthService has isAuthenticated; Router has navigate
      const name = _token?.name || _token?.toString?.() || '';
      if (name === 'AuthService' || name.includes('Auth')) {
        return mockAuth;
      }
      return mockRouter;
    },
  };
});

// Mock the AuthService import path so it doesn't trigger real DI
vi.mock('../services/auth.service', () => ({
  AuthService: class AuthService {
    static name = 'AuthService';
  },
}));

// Mock @angular/router to provide a Router token
vi.mock('@angular/router', async (importOriginal) => {
  const orig: any = await importOriginal();
  return {
    ...orig,
    Router: class Router {
      static name = 'Router';
    },
  };
});

// Import guards AFTER mocks are set up
import { authGuard, masterGuard, clientGuard } from './auth.guard';

describe('Auth Guards', () => {
  beforeEach(() => {
    mockRouter = { navigate: vi.fn() };
    mockAuth = {
      isAuthenticated: () => false,
      isMaster: () => false,
      isClient: () => false,
      isEmailVerified: () => true,
      currentUser: () => null,
    };
  });

  // ---------- authGuard ----------

  describe('authGuard', () => {
    it('redirects to /login when not authenticated', () => {
      mockAuth.isAuthenticated = () => false;

      const result = (authGuard as Function)(null, null);

      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/login']);
    });

    it('returns true when authenticated and verified', () => {
      mockAuth.isAuthenticated = () => true;
      mockAuth.isEmailVerified = () => true;

      const result = (authGuard as Function)(null, null);

      expect(result).toBe(true);
    });

    it('redirects to /verify-email when authenticated but not verified', () => {
      mockAuth.isAuthenticated = () => true;
      mockAuth.isEmailVerified = () => false;
      mockAuth.currentUser = () => ({ email: 'test@example.com' });

      const result = (authGuard as Function)(null, null);

      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/verify-email'], {
        queryParams: { email: 'test@example.com' },
      });
    });
  });

  // ---------- masterGuard ----------

  describe('masterGuard', () => {
    it('redirects to /login when not authenticated', () => {
      mockAuth.isAuthenticated = () => false;

      const result = (masterGuard as Function)(null, null);

      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/login']);
    });

    it('redirects to /client when authenticated but not a master', () => {
      mockAuth.isAuthenticated = () => true;
      mockAuth.isEmailVerified = () => true;
      mockAuth.isMaster = () => false;

      const result = (masterGuard as Function)(null, null);

      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/client']);
    });

    it('returns true when authenticated as master and verified', () => {
      mockAuth.isAuthenticated = () => true;
      mockAuth.isEmailVerified = () => true;
      mockAuth.isMaster = () => true;

      const result = (masterGuard as Function)(null, null);

      expect(result).toBe(true);
    });
  });

  // ---------- clientGuard ----------

  describe('clientGuard', () => {
    it('redirects to /login when not authenticated', () => {
      mockAuth.isAuthenticated = () => false;

      const result = (clientGuard as Function)(null, null);

      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/login']);
    });

    it('redirects to /master when authenticated but not a client', () => {
      mockAuth.isAuthenticated = () => true;
      mockAuth.isEmailVerified = () => true;
      mockAuth.isClient = () => false;

      const result = (clientGuard as Function)(null, null);

      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/master']);
    });

    it('returns true when authenticated as client and verified', () => {
      mockAuth.isAuthenticated = () => true;
      mockAuth.isEmailVerified = () => true;
      mockAuth.isClient = () => true;

      const result = (clientGuard as Function)(null, null);

      expect(result).toBe(true);
    });
  });
});
