import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SessionStateService } from '../../../core/services/session-state.service';

@Component({
  selector: 'app-session-expired-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      *ngIf="sessionState.isExpired()"
      class="fixed inset-0 z-[10001] flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="session-expired-title"
      aria-describedby="session-expired-desc"
    >
      <div
        class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 text-center"
        (click)="$event.stopPropagation()"
      >
        <div class="w-14 h-14 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center text-2xl mx-auto" aria-hidden="true">
          ⏳
        </div>

        <h3 id="session-expired-title" class="text-lg font-bold text-white">
          Tu sesión ha expirado
        </h3>

        <p id="session-expired-desc" class="text-xs text-[var(--text-secondary)] leading-relaxed">
          Han transcurrido más de 30 minutos de inactividad o tus credenciales han caducado. Tu progreso reciente en el lienzo ha sido respaldado de manera segura en tu navegador.
        </p>

        <div class="pt-2">
          <button
            type="button"
            (click)="relogin()"
            class="w-full py-2.5 px-4 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-semibold shadow-lg shadow-primary/30 transition-all cursor-pointer"
          >
            Iniciar sesión nuevamente
          </button>
        </div>
      </div>
    </div>
  `
})
export class SessionExpiredModalComponent {
  sessionState = inject(SessionStateService);

  relogin(): void {
    this.sessionState.dismissAndRedirect();
  }
}
