import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  if (!authService.isEmailVerified()) {
    router.navigate(['/verify-email'], {
      queryParams: { email: authService.currentUser()?.email }
    });
    return false;
  }

  return true;
};

export const masterGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  if (!authService.isEmailVerified()) {
    router.navigate(['/verify-email'], {
      queryParams: { email: authService.currentUser()?.email }
    });
    return false;
  }

  if (!authService.isMaster()) {
    router.navigate(['/login']);
    return false;
  }

  return true;
};

export const clientGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  if (!authService.isEmailVerified()) {
    router.navigate(['/verify-email'], {
      queryParams: { email: authService.currentUser()?.email }
    });
    return false;
  }

  if (!authService.isClient()) {
    router.navigate(['/login']);
    return false;
  }

  return true;
};

export const guestGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    return true;
  }

  // Authenticated but not verified — let them through to login/register pages
  // so they can navigate to verify-email
  if (!authService.isEmailVerified()) {
    return true;
  }

  if (authService.isMaster()) {
    router.navigate(['/master']);
  } else {
    router.navigate(['/client']);
  }
  return false;
};
