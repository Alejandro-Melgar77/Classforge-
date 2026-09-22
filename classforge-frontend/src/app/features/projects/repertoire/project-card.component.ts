import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Project } from '../models/project.model';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-project-card',
  standalone: true,
  imports: [CommonModule, StatusBadgeComponent],
  template: `
    <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-xl overflow-hidden hover:-translate-y-1 hover:shadow-xl hover:shadow-[var(--surface-1)] transition-all duration-300 flex flex-col h-full group">
      
      <!-- Color bar -->
      <div class="h-2 w-full" [style.backgroundColor]="project.color_tag || 'var(--primary)'"></div>
      
      <div class="p-5 flex-1 flex flex-col">
        <div class="flex justify-between items-start mb-3">
          <app-status-badge [status]="project.status"></app-status-badge>
          <div class="flex items-center gap-2">
            <span class="text-xs text-[var(--text-muted)]">{{ formatDate(project.created_at) }}</span>
            <div class="w-6 h-6 rounded-full bg-[var(--surface-3)] flex items-center justify-center text-[10px] text-white border border-[var(--border)]" title="Owner">
              U
            </div>
          </div>
        </div>
        
        <h3 class="text-lg font-bold text-white mb-1 truncate" [title]="project.name">{{ project.name }}</h3>
        
        <p class="text-sm text-[var(--text-secondary)] line-clamp-2 mb-4 flex-1" [title]="project.description">
          {{ project.description || 'Sin descripción' }}
        </p>

        <div class="flex items-center justify-between mt-auto pt-4 border-t border-[var(--border)]">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-full bg-[var(--surface-3)] flex items-center justify-center text-xs text-white">
              👥
            </div>
            <span class="text-xs text-[var(--text-secondary)] truncate max-w-[100px]" [title]="project.type === 'team' ? 'Equipo' : 'Personal'">
              {{ project.type === 'team' ? 'Equipo' : 'Personal' }}
            </span>
          </div>

          <div class="flex gap-2 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
            <button (click)="view.emit(project)" class="p-1.5 text-[var(--text-secondary)] hover:text-white bg-[var(--surface-3)] rounded" title="Visualizar">
              👁️
            </button>
            <button *ngIf="canEdit()" (click)="edit.emit(project)" class="p-1.5 text-[var(--text-secondary)] hover:text-[var(--primary)] bg-[var(--surface-3)] rounded" title="Editar">
              ✏️
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ProjectCardComponent {
  @Input() project!: Project;
  @Output() view = new EventEmitter<Project>();
  @Output() edit = new EventEmitter<Project>();

  private authService = inject(AuthService);

  formatDate(dateStr: string): string {
    return new Intl.DateTimeFormat('es-ES', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    }).format(new Date(dateStr));
  }

  canEdit(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user) return false;
    if (user.role === 'admin' || user.role === 'scrum_master') return true;
    if (this.project.owner_id === user.id) return true;
    // In a real app we would check if they are in the team and have edit rights
    return false;
  }
}
