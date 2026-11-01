import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectCenterComponent } from './project-center.component';
import { AiTeamStore } from '../../ai-team/data-access/ai-team.store';
import { ToastService } from '../../../core/services/toast.service';
import { PageStateComponent, PageStateType } from '../../../shared/components/page-state/page-state.component';

interface ProjectTask {
  id: string;
  title: string;
  role: string;
  severity: 'low' | 'medium' | 'high';
  status: 'pending' | 'in_progress' | 'completed';
  created_at: string;
}

@Component({
  selector: 'app-project-tasks',
  standalone: true,
  imports: [CommonModule, FormsModule, PageStateComponent],
  template: `
    <div class="space-y-6">
      
      <!-- Top Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4">
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <span>✅</span>
            <span>Tareas y Hallazgos del Proyecto</span>
          </h2>
          <p class="text-xs text-[var(--text-secondary)]">
            Acciones recomendadas por el equipo humano y los agentes IA.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <select
            [(ngModel)]="filterStatus"
            class="bg-[var(--surface-1)] border border-[var(--border)] text-white text-xs rounded-xl px-3 py-2 focus:outline-hidden focus:border-primary"
          >
            <option value="all">Todas las tareas</option>
            <option value="pending">Pendientes</option>
            <option value="completed">Completadas</option>
          </select>

          <button
            type="button"
            (click)="addNewTaskPrompt()"
            class="px-3.5 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>➕</span>
            <span>Nueva Tarea</span>
          </button>
        </div>
      </div>

      <!-- State Handling -->
      <app-page-state
        *ngIf="filteredTasks().length === 0"
        state="empty"
        title="No hay tareas registradas"
        message="Las tareas generadas por revisiones de arquitectura o añadidas por el equipo aparecerán aquí."
        emptyIcon="📋"
        actionLabel="Crear Tarea"
        (action)="addNewTaskPrompt()"
      ></app-page-state>

      <!-- Tasks List -->
      <div *ngIf="filteredTasks().length > 0" class="divide-y divide-[var(--border)] bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl overflow-hidden shadow-md">
        <div
          *ngFor="let task of filteredTasks()"
          class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-[var(--surface-3)] transition-colors"
        >
          <div class="flex items-start gap-3 min-w-0">
            <button
              type="button"
              (click)="toggleTaskStatus(task)"
              class="w-6 h-6 rounded-lg border flex items-center justify-center text-xs shrink-0 mt-0.5 transition-colors cursor-pointer"
              [ngClass]="task.status === 'completed' ? 'bg-emerald-600 border-emerald-500 text-white' : 'border-[var(--border)] bg-[var(--surface-1)] text-transparent hover:border-primary'"
            >
              ✓
            </button>

            <div class="min-w-0">
              <p
                class="text-sm font-semibold text-white truncate"
                [class.line-through]="task.status === 'completed'"
                [class.opacity-60]="task.status === 'completed'"
              >
                {{ task.title }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-primary/10 text-primary-light border border-primary/20">
                  {{ task.role }}
                </span>
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-semibold"
                  [ngClass]="getSeverityClass(task.severity)"
                >
                  Prioridad {{ task.severity }}
                </span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 self-end sm:self-center shrink-0">
            <button
              type="button"
              (click)="deleteTask(task.id)"
              class="p-1.5 rounded-lg text-xs text-rose-400 hover:text-white hover:bg-rose-600 transition-colors cursor-pointer"
              title="Eliminar tarea"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

    </div>
  `
})
export class ProjectTasksComponent implements OnInit {
  center = inject(ProjectCenterComponent);
  private store = inject(AiTeamStore);
  private toastService = inject(ToastService);

  tasks = signal<ProjectTask[]>([]);
  filterStatus = 'all';

  ngOnInit(): void {
    // Generate initial task items from findings or local store
    this.tasks.set([
      {
        id: '1',
        title: 'Verificar relaciones cíclicas entre entidades principales',
        role: 'architect',
        severity: 'high',
        status: 'pending',
        created_at: new Date().toISOString()
      },
      {
        id: '2',
        title: 'Comprobar cobertura de casos de uso en diagrama de clases',
        role: 'qa',
        severity: 'medium',
        status: 'completed',
        created_at: new Date().toISOString()
      },
      {
        id: '3',
        title: 'Auditar índices y claves foráneas en entidades de base de datos',
        role: 'dba',
        severity: 'medium',
        status: 'pending',
        created_at: new Date().toISOString()
      }
    ]);
  }

  filteredTasks(): ProjectTask[] {
    const list = this.tasks();
    if (this.filterStatus === 'all') return list;
    return list.filter(t => t.status === this.filterStatus);
  }

  toggleTaskStatus(task: ProjectTask): void {
    const nextStatus = task.status === 'completed' ? 'pending' : 'completed';
    this.tasks.update(all =>
      all.map(t => t.id === task.id ? { ...t, status: nextStatus } : t)
    );
    this.toastService.info(`Tarea marcada como ${nextStatus === 'completed' ? 'completada' : 'pendiente'}`);
  }

  addNewTaskPrompt(): void {
    const title = prompt('Descripción de la nueva tarea:');
    if (!title || !title.trim()) return;

    const newTask: ProjectTask = {
      id: Date.now().toString(),
      title: title.trim(),
      role: 'equipo',
      severity: 'medium',
      status: 'pending',
      created_at: new Date().toISOString()
    };

    this.tasks.update(all => [newTask, ...all]);
    this.toastService.success('Tarea agregada exitosamente');
  }

  deleteTask(id: string): void {
    this.tasks.update(all => all.filter(t => t.id !== id));
    this.toastService.info('Tarea eliminada');
  }

  getSeverityClass(severity: string): string {
    switch (severity) {
      case 'high': return 'bg-rose-500/10 text-rose-300 border border-rose-500/20';
      case 'medium': return 'bg-amber-500/10 text-amber-300 border border-amber-500/20';
      default: return 'bg-blue-500/10 text-blue-300 border border-blue-500/20';
    }
  }
}
