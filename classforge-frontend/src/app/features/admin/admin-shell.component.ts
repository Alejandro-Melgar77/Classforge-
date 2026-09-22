import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-white mb-2">Administración</h1>
        <p class="text-[var(--text-secondary)]">Gestiona los usuarios, equipos y configuraciones de ClassForge.</p>
      </div>
      
      <!-- Sub-navigation Tabs -->
      <div class="flex gap-4 border-b border-[var(--border)]">
        <a routerLink="users" routerLinkActive="text-[var(--primary)] border-b-2 border-[var(--primary)]" 
           class="px-4 py-3 text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors">
          Usuarios
        </a>
        <a routerLink="teams" routerLinkActive="text-[var(--primary)] border-b-2 border-[var(--primary)]" 
           class="px-4 py-3 text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors">
          Equipos
        </a>
        <a routerLink="config" routerLinkActive="text-[var(--primary)] border-b-2 border-[var(--primary)]" 
           class="px-4 py-3 text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors">
          Configuración Global
        </a>
      </div>

      <div class="mt-6">
        <router-outlet></router-outlet>
      </div>
    </div>
  `
})
export class AdminShellComponent {}
