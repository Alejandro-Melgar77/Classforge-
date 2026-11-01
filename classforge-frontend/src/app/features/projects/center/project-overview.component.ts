import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ProjectCenterComponent } from './project-center.component';
import { ProjectsService } from '../services/projects.service';
import { TeamsService } from '../services/teams.service';
import { DiagramService } from '../../diagrams/services/diagram.service';
import { ToastService } from '../../../core/services/toast.service';
import { ProjectStatus } from '../models/project.model';
import { Team } from '../models/team.model';
import { PageStateComponent } from '../../../shared/components/page-state/page-state.component';

@Component({
  selector: 'app-project-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PageStateComponent],
  template: `
    <div *ngIf="center.project() as proj" class="space-y-6">
      
      <!-- Metrics Overview Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center text-xl">
            📐
          </div>
          <div>
            <p class="text-xs text-[var(--text-secondary)] font-medium">Diagramas</p>
            <p class="text-xl font-bold text-white">{{ totalDiagrams() }}</p>
          </div>
        </div>

        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center text-xl">
            🚦
          </div>
          <div class="min-w-0">
            <p class="text-xs text-[var(--text-secondary)] font-medium">Estado</p>
            <p class="text-sm font-bold text-white capitalize truncate">{{ proj.status.replace('_', ' ') }}</p>
          </div>
        </div>

        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center text-xl">
            👥
          </div>
          <div>
            <p class="text-xs text-[var(--text-secondary)] font-medium">Modalidad</p>
            <p class="text-sm font-bold text-white">{{ proj.type === 'team' ? 'En Equipo' : 'Individual' }}</p>
          </div>
        </div>

        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4 flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center text-xl">
            📅
          </div>
          <div>
            <p class="text-xs text-[var(--text-secondary)] font-medium">Creado</p>
            <p class="text-xs font-bold text-white">{{ formatDate(proj.created_at) }}</p>
          </div>
        </div>
      </div>

      <!-- Main Project Details Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Left: Project Info & Description -->
        <div class="lg:col-span-2 bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span>📋</span>
              <span>Detalles del Proyecto</span>
            </h2>
            <div class="flex items-center gap-2">
              <span class="text-xs text-[var(--text-secondary)]">Cambiar estado:</span>
              <select
                [(ngModel)]="selectedStatus"
                (change)="onStatusChange()"
                class="bg-[var(--surface-1)] border border-[var(--border)] text-white text-xs rounded-lg px-2.5 py-1 focus:outline-hidden focus:border-primary"
              >
                <option value="draft">Borrador</option>
                <option value="in_progress">En Progreso</option>
                <option value="review">En Revisión</option>
                <option value="completed">Completado</option>
                <option value="archived">Archivado</option>
              </select>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-[var(--surface-1)] border border-[var(--border)] space-y-2">
            <h3 class="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">Descripción</h3>
            <p class="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
              {{ proj.description || 'Este proyecto no cuenta con una descripción detallada todavía.' }}
            </p>
          </div>

          <!-- Quick Navigation Actions -->
          <div class="pt-2 flex flex-wrap gap-3">
            <a
              routerLink="../diagramas"
              class="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md transition-colors cursor-pointer"
            >
              <span>📐</span>
              <span>Ver Diagramas del Proyecto</span>
            </a>
            <a
              routerLink="../equipo-ia"
              class="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer"
            >
              <span>🤖</span>
              <span>Abrir Equipo IA</span>
            </a>
          </div>
        </div>

        <!-- Right: Team & Meta Sidebar -->
        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 space-y-4">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <span>👥</span>
            <span>Equipo Asignado</span>
          </h2>

          <div *ngIf="proj.type === 'team' && team()" class="space-y-3">
            <div class="p-3 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl">
              <p class="text-xs text-[var(--text-secondary)]">Nombre del Equipo</p>
              <p class="text-sm font-bold text-white">{{ team()?.name }}</p>
            </div>
            <div class="p-3 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl">
              <p class="text-xs text-[var(--text-secondary)]">Total Integrantes</p>
              <p class="text-sm font-bold text-white">{{ team()?.member_ids?.length || 0 }} miembros</p>
            </div>
            <a
              routerLink="../miembros"
              class="block text-center text-xs text-primary-light hover:underline pt-1"
            >
              Gestionar participantes →
            </a>
          </div>

          <div *ngIf="proj.type !== 'team'" class="text-center p-6 text-xs text-[var(--text-secondary)]">
            <span class="text-2xl block mb-2">👤</span>
            Este es un proyecto individual privado.
          </div>
        </div>

      </div>
    </div>
  `
})
export class ProjectOverviewComponent implements OnInit {
  center = inject(ProjectCenterComponent);
  private projectsService = inject(ProjectsService);
  private teamsService = inject(TeamsService);
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);

  totalDiagrams = signal<number>(0);
  team = signal<Team | null>(null);
  selectedStatus: ProjectStatus = 'in_progress';

  ngOnInit(): void {
    const proj = this.center.project();
    if (proj) {
      this.selectedStatus = proj.status;
      this.loadDiagramsCount(proj.id);
      if (proj.team_id) {
        this.loadTeam(proj.team_id);
      }
    }
  }

  loadDiagramsCount(projectId: string): void {
    this.diagramService.getDiagrams({ project_id: projectId }).subscribe({
      next: (res) => {
        this.totalDiagrams.set(res.data?.length || 0);
      },
      error: () => {}
    });
  }

  loadTeam(teamId: string): void {
    this.teamsService.getTeam(teamId).subscribe({
      next: (res) => {
        if (res.data) {
          this.team.set(res.data);
        }
      },
      error: () => {}
    });
  }

  onStatusChange(): void {
    const proj = this.center.project();
    if (!proj) return;

    this.projectsService.updateProjectStatus(proj.id, this.selectedStatus).subscribe({
      next: (res) => {
        if (res.data) {
          this.center.project.set(res.data);
        }
        this.toastService.success('Estado del proyecto actualizado');
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || err.message || 'Error al cambiar estado');
      }
    });
  }

  formatDate(dateStr?: string): string {
    if (!dateStr) return '—';
    return new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(dateStr));
  }
}
