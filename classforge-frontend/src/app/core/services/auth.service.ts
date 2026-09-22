import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { BehaviorSubject, Observable, tap, catchError, throwError } from 'rxjs';
import { User, UserRole } from '../models/user.model';
import { AuthResponse, AuthResponseData } from '../models/api-response.model';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private apiUrl = `${environment.apiUrl}/auth`;

  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  /** Access token stored in-memory only (never persisted to localStorage for security) */
  private accessToken: string | null = null;

  constructor() {
    this.restoreSessionFromStorage();
  }

  /**
   * On app init, restore user profile from sessionStorage (tab-isolated) or
   * localStorage so the UI immediately knows who is logged in.
   */
  private restoreSessionFromStorage(): void {
    const userJson = sessionStorage.getItem('cf_user') || localStorage.getItem('cf_user');
    if (userJson) {
      try {
        const user = JSON.parse(userJson);
        if (user && user.name) {
          this.currentUserSubject.next(user);
        }
      } catch {
        sessionStorage.removeItem('cf_user');
        localStorage.removeItem('cf_user');
      }
    }
  }

  /**
   * Authenticate user with email + password.
   * On success, stores tokens and emits the current user.
   */
  login(credentials: { email: string; password: string; device_info?: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.apiUrl}/login`, credentials).pipe(
      tap(response => {
        if (response.success && response.data) {
          this.setAuthData(response.data);
        }
      })
    );
  }

  register(userData: { name: string; email: string; password: string }): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/register`, userData);
  }

  logout(): void {
    if (this.accessToken) {
      // Best-effort — invalidate backend session, ignore errors
      this.http.post(`${this.apiUrl}/logout`, {}).subscribe({ error: () => {} });
    }
    this.clearAuthData();
    this.router.navigate(['/auth/login']);
  }

  logoutAll(): Observable<unknown> {
    return this.http.post(`${this.apiUrl}/logout-all`, {});
  }

  /**
   * Exchange a refresh token for a new access token.
   * Implements token rotation: the old refresh token is invalidated and a new
   * one is issued by the backend.
   */
  refreshToken(): Observable<AuthResponse> {
    const refreshToken = sessionStorage.getItem('cf_refresh_token') || localStorage.getItem('cf_refresh_token');
    if (!refreshToken) {
      this.clearAuthData();
      return throwError(() => new Error('No refresh token available'));
    }
    return this.http.post<AuthResponse>(`${this.apiUrl}/refresh`, { refresh_token: refreshToken }).pipe(
      tap(response => {
        if (response.success && response.data) {
          this.setAuthData(response.data);
        }
      }),
      catchError(err => {
        this.clearAuthData();
        this.router.navigate(['/auth/login']);
        return throwError(() => err);
      })
    );
  }

  fetchProfile(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/me`).pipe(
      tap(res => {
        if (res.success && res.data) {
          const user = res.data;
          sessionStorage.setItem('cf_user', JSON.stringify(user));
          localStorage.setItem('cf_user', JSON.stringify(user));
          this.currentUserSubject.next(user);
        }
      })
    );
  }

  private setAuthData(data: AuthResponseData): void {
    this.accessToken = data.access_token;
    
    if (data.refresh_token) {
      sessionStorage.setItem('cf_refresh_token', data.refresh_token);
      localStorage.setItem('cf_refresh_token', data.refresh_token);
    }
    
    if (data.user) {
      sessionStorage.setItem('cf_user', JSON.stringify(data.user));
      localStorage.setItem('cf_user', JSON.stringify(data.user));
      this.currentUserSubject.next(data.user);
    } else {
      // Fallback: fetch profile from /auth/me
      this.fetchProfile().subscribe({ error: () => {} });
    }
  }

  private clearAuthData(): void {
    this.accessToken = null;
    sessionStorage.removeItem('cf_refresh_token');
    sessionStorage.removeItem('cf_user');
    localStorage.removeItem('cf_refresh_token');
    localStorage.removeItem('cf_user');
    this.currentUserSubject.next(null);
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  isAuthenticated(): boolean {
    // User is considered authenticated if we have an in-memory access token
    // OR a refresh token in storage (to allow silent refresh on page reload)
    return !!this.accessToken || !!sessionStorage.getItem('cf_refresh_token') || !!localStorage.getItem('cf_refresh_token');
  }

  hasRole(role: UserRole): boolean {
    const user = this.currentUserSubject.value;
    return user?.role === role;
  }

  hasAnyRole(roles: UserRole[]): boolean {
    const user = this.currentUserSubject.value;
    return user ? roles.includes(user.role) : false;
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }
}
