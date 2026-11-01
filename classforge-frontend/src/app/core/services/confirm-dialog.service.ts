import { Injectable, signal } from '@angular/core';

export interface ConfirmDialogOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ConfirmDialogService {
  private dialogSignal = signal<{
    options: ConfirmDialogOptions;
    resolve: (confirmed: boolean) => void;
  } | null>(null);

  public dialog = this.dialogSignal.asReadonly();

  confirm(options: ConfirmDialogOptions): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      this.dialogSignal.set({
        options: {
          confirmText: 'Confirmar',
          cancelText: 'Cancelar',
          danger: false,
          ...options
        },
        resolve
      });
    });
  }

  handleAction(confirmed: boolean): void {
    const current = this.dialogSignal();
    if (current) {
      current.resolve(confirmed);
      this.dialogSignal.set(null);
    }
  }
}
