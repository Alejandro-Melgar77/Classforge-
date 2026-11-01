import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse } from '../models/api-response.model';
import { AppNotification, NotificationsPayload } from '../models/notification.model';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/notifications`;

  private notificationsSignal = signal<AppNotification[]>([]);
  private unreadCountSignal = signal<number>(0);
  private isLoadingSignal = signal<boolean>(false);

  public notifications = this.notificationsSignal.asReadonly();
  public unreadCount = this.unreadCountSignal.asReadonly();
  public isLoading = this.isLoadingSignal.asReadonly();

  loadNotifications(): Observable<ApiResponse<NotificationsPayload>> {
    this.isLoadingSignal.set(true);
    return this.http.get<ApiResponse<NotificationsPayload>>(this.apiUrl).pipe(
      tap(res => {
        this.isLoadingSignal.set(false);
        if (res.success && res.data) {
          this.notificationsSignal.set(res.data.items || []);
          this.unreadCountSignal.set(res.data.unread_count || 0);
        }
      }),
      catchError(err => {
        this.isLoadingSignal.set(false);
        return of({ success: false, message: 'Error cargando notificaciones', data: { items: [], total: 0, unread_count: 0, page: 1, limit: 30 } });
      })
    );
  }

  markAsRead(notificationId: string): Observable<ApiResponse<void>> {
    // Optimistic update
    this.notificationsSignal.update(items =>
      items.map(item => item.id === notificationId ? { ...item, read: true } : item)
    );
    this.unreadCountSignal.update(c => Math.max(0, c - 1));

    return this.http.put<ApiResponse<void>>(`${this.apiUrl}/${notificationId}/read`, {});
  }

  markAllAsRead(): Observable<ApiResponse<{ updated: number }>> {
    this.notificationsSignal.update(items =>
      items.map(item => ({ ...item, read: true }))
    );
    this.unreadCountSignal.set(0);

    return this.http.put<ApiResponse<{ updated: number }>>(`${this.apiUrl}/read-all`, {});
  }

  deleteNotification(notificationId: string): Observable<ApiResponse<void>> {
    const target = this.notificationsSignal().find(n => n.id === notificationId);
    if (target && !target.read) {
      this.unreadCountSignal.update(c => Math.max(0, c - 1));
    }
    this.notificationsSignal.update(items => items.filter(n => n.id !== notificationId));

    return this.http.delete<ApiResponse<void>>(`${this.apiUrl}/${notificationId}`);
  }
}
