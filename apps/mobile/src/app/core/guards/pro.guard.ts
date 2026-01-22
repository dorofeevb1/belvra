import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { SubscriptionService } from '../services/subscription.service';
import { AuthService } from '../services/auth.service';

/**
 * Guard that checks if user has PRO subscription.
 * Redirects to subscription page if not.
 */
export const proGuard: CanActivateFn = () => {
  const subscriptionService = inject(SubscriptionService);
  const authService = inject(AuthService);
  const router = inject(Router);

  if (subscriptionService.isPro()) {
    return true;
  }

  // Redirect to appropriate subscription page based on user role
  if (authService.isMaster()) {
    router.navigate(['/master/subscription']);
  } else {
    router.navigate(['/client/subscription']);
  }

  return false;
};

/**
 * Guard that checks if master can create more appointments.
 * Shows notification and redirects to subscription if limit reached.
 */
export const appointmentLimitGuard: CanActivateFn = () => {
  const subscriptionService = inject(SubscriptionService);
  const authService = inject(AuthService);
  const router = inject(Router);

  if (subscriptionService.canCreateAppointment()) {
    return true;
  }

  // Redirect to subscription page with limit reached indicator
  if (authService.isMaster()) {
    router.navigate(['/master/subscription'], {
      queryParams: { limitReached: 'appointments' }
    });
  }

  return false;
};

/**
 * Guard that checks if master can add more services.
 */
export const serviceLimitGuard: CanActivateFn = () => {
  const subscriptionService = inject(SubscriptionService);
  const authService = inject(AuthService);
  const router = inject(Router);

  if (subscriptionService.canAddService()) {
    return true;
  }

  if (authService.isMaster()) {
    router.navigate(['/master/subscription'], {
      queryParams: { limitReached: 'services' }
    });
  }

  return false;
};

/**
 * Guard that checks if master can add more portfolio items.
 */
export const portfolioLimitGuard: CanActivateFn = () => {
  const subscriptionService = inject(SubscriptionService);
  const authService = inject(AuthService);
  const router = inject(Router);

  if (subscriptionService.canAddPortfolioItem()) {
    return true;
  }

  if (authService.isMaster()) {
    router.navigate(['/master/subscription'], {
      queryParams: { limitReached: 'portfolio' }
    });
  }

  return false;
};
