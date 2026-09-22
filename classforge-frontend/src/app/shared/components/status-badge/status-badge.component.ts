import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ProjectStatus = 'in_progress' | 'completed' | 'review' | 'archived';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span [class]="getBadgeClasses()" class="px-2 py-0.5 rounded-full text-xs font-medium border">
      {{ getStatusLabel() }}
    </span>
  `
})
export class StatusBadgeComponent {
  @Input() status!: ProjectStatus;

  getBadgeClasses(): string {
    switch (this.status) {
      case 'in_progress':
        return 'bg-[var(--warning)]/20 text-[var(--warning)] border-[var(--warning)]/30';
      case 'completed':
        return 'bg-[var(--accent)]/20 text-[var(--accent)] border-[var(--accent)]/30';
      case 'review':
        return 'bg-[var(--primary)]/20 text-[var(--primary)] border-[var(--primary)]/30';
      case 'archived':
      default:
        return 'bg-[var(--surface-3)] text-[var(--text-muted)] border-[var(--border)]';
    }
  }

  getStatusLabel(): string {
    switch (this.status) {
      case 'in_progress': return 'En Proceso';
      case 'completed': return 'Completado';
      case 'review': return 'En Revisión';
      case 'archived': return 'Archivado';
      default: return 'Desconocido';
    }
  }
}
