import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, ToastMessage } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0"
      aria-live="polite"
      aria-atomic="true"
      role="region"
      aria-label="Notificaciones del sistema"
    >
      <div
        *ngFor="let toast of toasts(); trackBy: trackById"
        class="pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-xl transition-all duration-300 transform translate-y-0"
        [ngClass]="getToastClasses(toast)"
        role="status"
      >
        <span class="text-lg shrink-0 mt-0.5" aria-hidden="true">
          {{ getIcon(toast.type) }}
        </span>

        <div class="flex-1 min-w-0">
          <h4 *ngIf="toast.title" class="text-sm font-semibold mb-0.5">
            {{ toast.title }}
          </h4>
          <p class="text-xs leading-relaxed opacity-90 break-words">
            {{ toast.message }}
          </p>
        </div>

        <button
          type="button"
          (click)="dismiss(toast.id)"
          class="shrink-0 p-1 rounded-md opacity-70 hover:opacity-100 hover:bg-black/10 dark:hover:bg-white/10 transition-colors cursor-pointer"
          aria-label="Cerrar notificación"
        >
          ✕
        </button>
      </div>
    </div>
  `
})
export class ToastContainerComponent {
  private toastService = inject(ToastService);
  toasts = this.toastService.toasts;

  trackById(_index: number, item: ToastMessage): string {
    return item.id;
  }

  dismiss(id: string): void {
    this.toastService.dismiss(id);
  }

  getIcon(type: string): string {
    switch (type) {
      case 'success': return '✅';
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info':
      default: return 'ℹ️';
    }
  }

  getToastClasses(toast: ToastMessage): string {
    switch (toast.type) {
      case 'success':
        return 'bg-emerald-900/90 border-emerald-500/50 text-emerald-100 backdrop-blur-md';
      case 'error':
        return 'bg-rose-900/90 border-rose-500/50 text-rose-100 backdrop-blur-md';
      case 'warning':
        return 'bg-amber-900/90 border-amber-500/50 text-amber-100 backdrop-blur-md';
      case 'info':
      default:
        return 'bg-slate-800/95 border-slate-600/50 text-slate-100 backdrop-blur-md';
    }
  }
}
