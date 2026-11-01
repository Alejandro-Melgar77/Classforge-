import { Injectable, inject } from '@angular/core';
import { AuthService } from './auth.service';
import { ToastService } from './toast.service';
import { SessionStateService } from './session-state.service';

@Injectable({
  providedIn: 'root'
})
export class InactivityService {
  private timeoutId: ReturnType<typeof setTimeout> | undefined;
  private warningId: ReturnType<typeof setTimeout> | undefined;
  private readonly TIMEOUT_MS = 30 * 60 * 1000; // 30 mins
  private readonly WARNING_MS = 25 * 60 * 1000; // 25 mins
  
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private sessionState = inject(SessionStateService);

  constructor() {
    this.initListener();
  }

  private initListener() {
    window.addEventListener('mousemove', this.resetTimer.bind(this));
    window.addEventListener('click', this.resetTimer.bind(this));
    window.addEventListener('keypress', this.resetTimer.bind(this));
    this.resetTimer();
  }

  private resetTimer() {
    if (!this.authService.isAuthenticated()) return;
    
    clearTimeout(this.timeoutId);
    clearTimeout(this.warningId);
    
    this.warningId = setTimeout(() => {
      this.toastService.warning(
        'Tu sesión se cerrará en 5 minutos por inactividad. Mueve el cursor o interactúa para mantenerla activa.',
        'Aviso de Inactividad'
      );
    }, this.WARNING_MS);
    
    this.timeoutId = setTimeout(() => {
      this.sessionState.handleSessionExpired();
    }, this.TIMEOUT_MS);
  }
}
