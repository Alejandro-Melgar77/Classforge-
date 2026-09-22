import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService, DashboardStats } from './dashboard.service';
import { AuthService } from '../../core/services/auth.service';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, StatusBadgeComponent],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  private dashboardService = inject(DashboardService);
  private authService = inject(AuthService);

  stats: DashboardStats | null = null;
  loading = true;
  error: string | null = null;

  user$ = this.authService.currentUser$;

  ngOnInit() {
    this.loadStats();
  }

  loadStats() {
    this.loading = true;
    this.error = null;
    this.dashboardService.getStats().subscribe({
      next: (response) => {
        this.stats = response.data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'No se pudieron cargar las estadísticas. Por favor, intente de nuevo.';
        this.loading = false;
        console.error('Dashboard stats error:', err);
      }
    });
  }

  getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Buenos días';
    if (hour < 19) return 'Buenas tardes';
    return 'Buenas noches';
  }

  getCurrentDate(): string {
    return new Intl.DateTimeFormat('es-ES', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    }).format(new Date());
  }

  formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    
    // Si es hoy, mostrar hace X horas/minutos
    if (diff < 86400000 && now.getDate() === d.getDate()) {
      const hours = Math.floor(diff / 3600000);
      if (hours > 0) return `hace ${hours}h`;
      const mins = Math.floor(diff / 60000);
      return `hace ${mins}m`;
    }
    
    // Si no, fecha corta
    return new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: 'short' }).format(d);
  }
}
