import { Injectable, signal, inject } from '@angular/core';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class SessionStateService {
  private router = inject(Router);

  private isExpiredSignal = signal<boolean>(false);
  private returnUrlSignal = signal<string>('/');

  public isExpired = this.isExpiredSignal.asReadonly();
  public returnUrl = this.returnUrlSignal.asReadonly();

  handleSessionExpired(currentUrl?: string): void {
    const url = currentUrl || this.router.url || '/';
    this.returnUrlSignal.set(url);

    // Save diagram draft if on diagram canvas
    const match = url.match(/\/diagrams\/([a-f0-9]+)/i);
    if (match && match[1]) {
      const diagramId = match[1];
      try {
        const liveCells = localStorage.getItem(`cf_live_cells_${diagramId}`);
        if (liveCells) {
          localStorage.setItem(`cf_draft_diagram_${diagramId}`, JSON.stringify({
            cells: JSON.parse(liveCells),
            savedAt: new Date().toISOString()
          }));
        }
      } catch {
        // LocalStorage fallback
      }
    }

    this.isExpiredSignal.set(true);
  }

  dismissAndRedirect(): void {
    const url = this.returnUrlSignal();
    this.isExpiredSignal.set(false);
    this.router.navigate(['/auth/login'], { queryParams: { returnUrl: url } });
  }
}
