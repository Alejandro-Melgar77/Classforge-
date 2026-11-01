import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  durationMs?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toastsSignal = signal<ToastMessage[]>([]);
  public toasts = this.toastsSignal.asReadonly();

  show(message: string, type: ToastType = 'info', title?: string, durationMs = 4000): string {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const toast: ToastMessage = { id, type, title, message, durationMs };

    this.toastsSignal.update(current => [...current, toast]);

    if (durationMs > 0) {
      setTimeout(() => {
        this.dismiss(id);
      }, durationMs);
    }

    return id;
  }

  success(message: string, title?: string, durationMs = 4000): string {
    return this.show(message, 'success', title || 'Éxito', durationMs);
  }

  error(message: string, title?: string, durationMs = 5000): string {
    return this.show(message, 'error', title || 'Error', durationMs);
  }

  info(message: string, title?: string, durationMs = 4000): string {
    return this.show(message, 'info', title || 'Información', durationMs);
  }

  warning(message: string, title?: string, durationMs = 4500): string {
    return this.show(message, 'warning', title || 'Atención', durationMs);
  }

  dismiss(id: string): void {
    this.toastsSignal.update(current => current.filter(t => t.id !== id));
  }

  clearAll(): void {
    this.toastsSignal.set([]);
  }
}
