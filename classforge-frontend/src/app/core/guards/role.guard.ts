import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/user.model';

export const roleGuard: CanActivateFn = (route) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  const requiredRole = route.data['role'] as UserRole | undefined;
  if (requiredRole && authService.hasRole(requiredRole)) {
    return true;
  }
  
  return router.createUrlTree(['/']);
};
