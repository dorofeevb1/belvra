import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, catchError, filter, switchMap, take, throwError } from 'rxjs';
import { ApiService } from '../services/api.service';

const TOKEN_KEY = 'beautybook_access_token';
const REFRESH_TOKEN_KEY = 'beautybook_refresh_token';

let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<string | null>(null);

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const router = inject(Router);
  const apiService = inject(ApiService);
  const token = localStorage.getItem(TOKEN_KEY);

  // Don't add auth header for refresh token requests to avoid circular issues
  const isRefreshRequest = req.url.includes('/token/refresh/');

  // Clone request with auth header if token exists
  let authReq = req;
  if (token && !isRefreshRequest) {
    authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !isRefreshRequest) {
        // Try to refresh the token
        return handleTokenRefresh(req, next, router, apiService);
      }
      return throwError(() => error);
    })
  );
};

function handleTokenRefresh(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  router: Router,
  apiService: ApiService
) {
  if (!isRefreshing) {
    isRefreshing = true;
    refreshTokenSubject.next(null);

    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

    if (!refreshToken) {
      // No refresh token - logout
      clearAuthAndRedirect(router);
      return throwError(() => new Error('No refresh token'));
    }

    return apiService.refreshToken(refreshToken).pipe(
      switchMap((response) => {
        isRefreshing = false;
        const newAccessToken = response.access;
        localStorage.setItem(TOKEN_KEY, newAccessToken);
        refreshTokenSubject.next(newAccessToken);

        // Retry the original request with new token
        const authReq = req.clone({
          setHeaders: {
            Authorization: `Bearer ${newAccessToken}`
          }
        });
        return next(authReq);
      }),
      catchError((err) => {
        isRefreshing = false;
        // Refresh failed - logout
        clearAuthAndRedirect(router);
        return throwError(() => err);
      })
    );
  } else {
    // Wait for refresh to complete and retry
    return refreshTokenSubject.pipe(
      filter((token): token is string => token !== null),
      take(1),
      switchMap((token) => {
        const authReq = req.clone({
          setHeaders: {
            Authorization: `Bearer ${token}`
          }
        });
        return next(authReq);
      })
    );
  }
}

function clearAuthAndRedirect(router: Router) {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem('beautybook_user');
  router.navigate(['/login']);
}
