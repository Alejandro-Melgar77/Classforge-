import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { catchError, switchMap, throwError } from 'rxjs';

/**
 * JWT Interceptor — attaches Bearer token to all outgoing API requests.
 * On 401 response: automatically attempts one silent token refresh.
 * If the refresh also fails, the user is logged out.
 *
 * Rule R03: Access token is in-memory only; refresh token in localStorage.
 */
export const jwtInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);

  // Skip auth header for auth endpoints themselves to avoid circular dependencies
  const isAuthEndpoint = req.url.includes('/auth/login') ||
                         req.url.includes('/auth/register') ||
                         req.url.includes('/auth/refresh');

  const token = authService.getAccessToken();
  const clonedReq = (token && !isAuthEndpoint)
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(clonedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Only attempt refresh on 401 from non-auth endpoints
      if (error.status === 401 && !isAuthEndpoint) {
        return authService.refreshToken().pipe(
          switchMap(response => {
            // Retry original request with new access token
            const newToken = authService.getAccessToken();
            const retryReq = newToken
              ? req.clone({ setHeaders: { Authorization: `Bearer ${newToken}` } })
              : req;
            return next(retryReq);
          }),
          catchError(refreshError => {
            // Refresh failed — authService.refreshToken() already calls logout()
            return throwError(() => refreshError);
          })
        );
      }
      return throwError(() => error);
    })
  );
};
