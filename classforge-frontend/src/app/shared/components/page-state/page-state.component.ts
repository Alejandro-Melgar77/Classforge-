import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

export type PageStateType = 'loading' | 'empty' | 'error' | 'ready';

@Component({
  selector: 'app-page-state',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      *ngIf="state !== 'ready'"
      class="flex flex-col items-center justify-center p-8 text-center min-h-[260px] w-full"
      role="status"
      [attr.aria-live]="state === 'error' ? 'assertive' : 'polite'"
    >
      <!-- 1. Loading State -->
      <div *ngIf="state === 'loading'" class="flex flex-col items-center gap-3">
        <div class="relative w-12 h-12">
          <div class="absolute inset-0 rounded-full border-4 border-indigo-500/20"></div>
          <div class="absolute inset-0 rounded-full border-4 border-t-primary animate-spin"></div>
        </div>
        <p class="text-sm font-medium text-[var(--text-secondary)] mt-2">
          {{ message || 'Cargando información...' }}
        </p>
      </div>

      <!-- 2. Empty State -->
      <div *ngIf="state === 'empty'" class="flex flex-col items-center max-w-md space-y-3">
        <div class="w-16 h-16 rounded-2xl bg-[var(--surface-3)] border border-[var(--border)] flex items-center justify-center text-3xl shadow-inner">
          {{ emptyIcon || '📭' }}
        </div>
        <h3 class="text-base font-bold text-white">
          {{ title || 'No hay elementos para mostrar' }}
        </h3>
        <p class="text-xs text-[var(--text-secondary)] leading-relaxed">
          {{ message || 'No se han encontrado registros en esta sección.' }}
        </p>
        <button
          *ngIf="actionLabel"
          type="button"
          (click)="action.emit()"
          class="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold shadow-md transition-colors cursor-pointer"
        >
          <span>{{ actionIcon || '➕' }}</span>
          <span>{{ actionLabel }}</span>
        </button>
      </div>

      <!-- 3. Error State -->
      <div *ngIf="state === 'error'" class="flex flex-col items-center max-w-md space-y-3">
        <div class="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-3xl text-rose-400">
          {{ errorIcon || '⚠️' }}
        </div>
        <h3 class="text-base font-bold text-white">
          {{ title || 'Ocurrió un problema' }}
        </h3>
        <p class="text-xs text-rose-300 leading-relaxed">
          {{ message || 'No se pudo cargar el contenido solicitado o no tienes permisos de acceso.' }}
        </p>
        <div class="flex items-center gap-3 mt-2">
          <button
            *ngIf="showRetry"
            type="button"
            (click)="retry.emit()"
            class="inline-flex items-center gap-2 px-4 py-2 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-white border border-[var(--border)] rounded-xl text-xs font-semibold transition-colors cursor-pointer"
          >
            <span>🔄</span>
            <span>Reintentar</span>
          </button>
          <button
            *ngIf="secondaryActionLabel"
            type="button"
            (click)="secondaryAction.emit()"
            class="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold transition-colors cursor-pointer"
          >
            <span>{{ secondaryActionLabel }}</span>
          </button>
        </div>
      </div>
    </div>
  `
})
export class PageStateComponent {
  @Input() state: PageStateType = 'ready';
  @Input() title?: string;
  @Input() message?: string;
  @Input() emptyIcon?: string;
  @Input() errorIcon?: string;
  @Input() actionLabel?: string;
  @Input() actionIcon?: string;
  @Input() secondaryActionLabel?: string;
  @Input() showRetry = true;

  @Output() action = new EventEmitter<void>();
  @Output() retry = new EventEmitter<void>();
  @Output() secondaryAction = new EventEmitter<void>();
}
