import { Component, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      *ngIf="dialog() as state"
      class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      [attr.aria-labelledby]="'confirm-title'"
      [attr.aria-describedby]="'confirm-desc'"
    >
      <div
        class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4"
        (click)="$event.stopPropagation()"
      >
        <div class="flex items-start gap-4">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 text-xl"
            [ngClass]="state.options.danger ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'"
            aria-hidden="true"
          >
            {{ state.options.danger ? '⚠️' : '❓' }}
          </div>
          <div>
            <h3 id="confirm-title" class="text-base font-bold text-white">
              {{ state.options.title }}
            </h3>
            <p id="confirm-desc" class="text-sm text-[var(--text-secondary)] mt-1 leading-relaxed">
              {{ state.options.message }}
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <button
            type="button"
            (click)="cancel()"
            class="px-4 py-2 rounded-xl text-sm font-medium text-[var(--text-secondary)] hover:text-white bg-[var(--surface-3)] hover:bg-[var(--surface-4)] transition-colors cursor-pointer"
          >
            {{ state.options.cancelText }}
          </button>
          <button
            type="button"
            (click)="confirm()"
            class="px-4 py-2 rounded-xl text-sm font-semibold transition-colors cursor-pointer"
            [ngClass]="state.options.danger
              ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-900/30'
              : 'bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/30'"
          >
            {{ state.options.confirmText }}
          </button>
        </div>
      </div>
    </div>
  `
})
export class ConfirmDialogComponent {
  private dialogService = inject(ConfirmDialogService);
  dialog = this.dialogService.dialog;

  @HostListener('keydown.escape')
  onEscape(): void {
    if (this.dialog()) {
      this.cancel();
    }
  }

  confirm(): void {
    this.dialogService.handleAction(true);
  }

  cancel(): void {
    this.dialogService.handleAction(false);
  }
}
