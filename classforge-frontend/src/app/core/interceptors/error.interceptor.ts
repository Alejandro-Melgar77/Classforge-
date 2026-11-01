import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  
  return next(req).pipe(
    catchError(err => {
      if (err.status === 401 && !req.url.includes('/auth/refresh')) {
        return authService.refreshToken().pipe(
          switchMap((res) => {
            const cloned = req.clone({
              setHeaders: { Authorization: `Bearer ${res.data.access_token}` }
            });
            return next(cloned);
          }),
          catchError((refreshErr) => {
            return throwError(() => refreshErr);
          })
        );
      }
      return throwError(() => err);
    })
  );
};
