import { Injectable, inject } from '@angular/core';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class InactivityService {
  private timeoutId: ReturnType<typeof setTimeout> | undefined;
  private warningId: ReturnType<typeof setTimeout> | undefined;
  private readonly TIMEOUT_MS = 30 * 60 * 1000; // 30 mins
  private readonly WARNING_MS = 25 * 60 * 1000; // 25 mins
  
  private authService = inject(AuthService);

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
      alert("You will be logged out in 5 minutes due to inactivity.");
    }, this.WARNING_MS);
    
    this.timeoutId = setTimeout(() => {
      this.authService.logout();
    }, this.TIMEOUT_MS);
  }
}
