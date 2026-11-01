import { Component, inject, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { NotificationService } from '../../../core/services/notification.service';
import { AppNotification } from '../../../core/models/notification.model';
import { PageStateComponent } from '../../../shared/components/page-state/page-state.component';

@Component({
  selector: 'app-notifications-panel',
  standalone: true,
  imports: [CommonModule, PageStateComponent],
  template: `
    <div
      class="w-80 sm:w-96 bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[480px]"
      role="dialog"
      aria-label="Panel de Notificaciones"
    >
      <!-- Panel Header -->
      <div class="p-3.5 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-3)]">
        <div class="flex items-center gap-2">
          <span class="text-base" aria-hidden="true">🔔</span>
          <h3 class="text-sm font-bold text-white">Notificaciones</h3>
          <span
            *ngIf="unreadCount() > 0"
            class="px-1.5 py-0.2 bg-primary text-white text-[10px] font-bold rounded-full font-mono"
          >
            {{ unreadCount() }}
          </span>
        </div>
        <div class="flex items-center gap-1.5">
          <button
            *ngIf="unreadCount() > 0"
            (click)="markAllAsRead()"
            class="text-[11px] text-primary-light hover:text-white transition-colors cursor-pointer px-1.5 py-0.5 rounded hover:bg-white/5"
            title="Marcar todas como leídas"
          >
            Leídas
          </button>
          <button
            (click)="close.emit()"
            class="text-[var(--text-secondary)] hover:text-white p-1 rounded-md hover:bg-white/5 cursor-pointer text-xs"
            aria-label="Cerrar notificaciones"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- Panel Content -->
      <div class="flex-1 overflow-y-auto divide-y divide-[var(--border)]">
        <app-page-state
          *ngIf="notifications().length === 0"
          state="empty"
          title="Sin notificaciones"
          message="No tienes avisos pendientes por el momento."
          emptyIcon="🔔"
        ></app-page-state>

        <div
          *ngFor="let item of notifications()"
          (click)="onNotificationClick(item)"
          class="p-3.5 flex items-start gap-3 hover:bg-[var(--surface-3)] transition-colors cursor-pointer relative group"
          [ngClass]="{ 'bg-primary/5': !item.read }"
        >
          <div
            class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-sm mt-0.5"
            [ngClass]="getBadgeClass(item.type)"
          >
            {{ getTypeIcon(item.type) }}
          </div>

          <div class="flex-1 min-w-0 pr-6">
            <div class="flex items-center justify-between gap-1 mb-0.5">
              <span class="text-xs font-semibold text-white truncate">{{ item.title }}</span>
              <span class="text-[10px] text-[var(--text-muted)] shrink-0 font-mono">
                {{ formatRelative(item.created_at) }}
              </span>
            </div>
            <p class="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
              {{ item.message }}
            </p>
          </div>

          <button
            (click)="deleteItem($event, item.id)"
            class="absolute right-2 top-3 opacity-0 group-hover:opacity-100 p-1 text-[var(--text-muted)] hover:text-rose-400 hover:bg-white/5 rounded transition-all cursor-pointer text-xs"
            title="Eliminar notificación"
          >
            🗑️
          </button>

          <span
            *ngIf="!item.read"
            class="w-2 h-2 rounded-full bg-primary absolute left-1.5 top-1/2 -translate-y-1/2"
            title="No leída"
          ></span>
        </div>
      </div>
    </div>
  `
})
export class NotificationsPanelComponent implements OnInit {
  @Output() close = new EventEmitter<void>();

  private notificationService = inject(NotificationService);
  private router = inject(Router);

  notifications = this.notificationService.notifications;
  unreadCount = this.notificationService.unreadCount;

  ngOnInit(): void {
    this.notificationService.loadNotifications().subscribe();
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead().subscribe();
  }

  deleteItem(event: Event, id: string): void {
    event.stopPropagation();
    this.notificationService.deleteNotification(id).subscribe();
  }

  onNotificationClick(item: AppNotification): void {
    if (!item.read) {
      this.notificationService.markAsRead(item.id).subscribe();
    }
    this.close.emit();

    if (item.diagram_id) {
      this.router.navigate(['/diagrams', item.diagram_id]);
    } else if (item.project_id) {
      this.router.navigate(['/projects', item.project_id]);
    }
  }

  getTypeIcon(type: string): string {
    switch (type) {
      case 'diagram_update': return '📊';
      case 'mention': return '💬';
      case 'team_invite': return '👥';
      default: return '📢';
    }
  }

  getBadgeClass(type: string): string {
    switch (type) {
      case 'diagram_update': return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
      case 'mention': return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      case 'team_invite': return 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
    }
  }

  formatRelative(dateStr: string): string {
    if (!dateStr) return '';
    const now = new Date().getTime();
    const then = new Date(dateStr).getTime();
    const diffMin = Math.round((now - then) / 60000);

    if (diffMin < 1) return 'ahora';
    if (diffMin < 60) return `${diffMin}m`;
    const diffHours = Math.round(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h`;
    const diffDays = Math.round(diffHours / 24);
    return `${diffDays}d`;
  }
}
