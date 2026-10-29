import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiTask, AiTaskCreate, AiTaskStatus } from '../../models/ai-task.model';
import { AiRoleId, AI_ROLE_THEMES } from '../../models/ai-conversation.model';

@Component({
  selector: 'app-ai-task-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="task-panel">
      <!-- Create Task Form -->
      <div class="create-task-form">
        <h4 class="form-title">📋 Nueva Tarea para la IA</h4>
        <select class="form-select" [(ngModel)]="newTask.ai_role">
          <option value="architect">🏛️ Arquitecto</option>
          <option value="qa">🔬 QA</option>
          <option value="tech_lead">⚡ Tech Lead</option>
          <option value="mentor">📚 Mentor</option>
        </select>
        <input
          class="form-input"
          type="text"
          placeholder="Título de la tarea..."
          [(ngModel)]="newTask.title"
          maxlength="200"
        />
        <textarea
          class="form-textarea"
          placeholder="Descripción detallada de la tarea..."
          [(ngModel)]="newTask.description"
          rows="3"
          maxlength="2000"
        ></textarea>
        <button class="btn-create" (click)="onCreateTask()" [disabled]="!isFormValid()">
          + Asignar Tarea
        </button>
      </div>

      <!-- Task List -->
      <div class="task-list">
        <p class="empty-state" *ngIf="tasks.length === 0">
          No hay tareas asignadas a la IA.
        </p>
        <div *ngFor="let task of tasks" class="task-card" [class]="'status-' + task.status">
          <div class="task-header">
            <span class="task-role" [style.color]="getRoleColor(task.ai_role)">
              {{ getRoleEmoji(task.ai_role) }} {{ task.ai_role }}
            </span>
            <span class="task-status" [class]="'badge-' + task.status">
              {{ getStatusLabel(task.status) }}
            </span>
          </div>
          <p class="task-title">{{ task.title }}</p>
          <p class="task-result" *ngIf="task.result">{{ task.result }}</p>
          <button
            class="btn-execute"
            *ngIf="task.status === 'pending' || task.status === 'failed'"
            (click)="executeTask.emit(task)"
          >
            ▶ Ejecutar
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .task-panel { padding: 16px; display: flex; flex-direction: column; gap: 20px; }
    .form-title { font-size: 13px; color: #9CA3AF; margin: 0 0 10px; }
    .create-task-form { display: flex; flex-direction: column; gap: 8px; }
    .form-select, .form-input, .form-textarea {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 6px;
      color: #E5E7EB;
      padding: 8px 10px;
      font-size: 13px;
    }
    .form-select option { background: #1F2937; }
    .form-textarea { resize: vertical; }
    .btn-create {
      padding: 8px;
      background: #3B82F6;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
    }
    .btn-create:disabled { opacity: 0.5; cursor: not-allowed; }
    .task-card {
      padding: 12px;
      border-radius: 8px;
      border-left: 3px solid #374151;
      background: rgba(255,255,255,0.04);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .status-pending { border-left-color: #F59E0B; }
    .status-in_progress { border-left-color: #3B82F6; }
    .status-completed { border-left-color: #10B981; }
    .status-failed { border-left-color: #EF4444; }
    .task-header { display: flex; justify-content: space-between; align-items: center; }
    .task-role { font-size: 12px; font-weight: 600; text-transform: capitalize; }
    .task-status { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
    .badge-pending { background: rgba(245,158,11,0.2); color: #FCD34D; }
    .badge-in_progress { background: rgba(59,130,246,0.2); color: #93C5FD; }
    .badge-completed { background: rgba(16,185,129,0.2); color: #6EE7B7; }
    .badge-failed { background: rgba(239,68,68,0.2); color: #FCA5A5; }
    .task-title { margin: 0; font-size: 13px; color: #E5E7EB; }
    .task-result { margin: 0; font-size: 12px; color: #9CA3AF; white-space: pre-wrap; }
    .btn-execute {
      align-self: flex-start;
      padding: 4px 10px;
      background: rgba(59,130,246,0.2);
      color: #93C5FD;
      border: 1px solid rgba(59,130,246,0.3);
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
    }
    .btn-execute:hover { background: rgba(59,130,246,0.3); }
    .empty-state { color: #6B7280; font-size: 13px; text-align: center; padding: 20px 0; }
  `]
})
export class AiTaskPanelComponent {
  @Input() tasks: AiTask[] = [];
  @Output() createTask = new EventEmitter<AiTaskCreate>();
  @Output() executeTask = new EventEmitter<AiTask>();

  newTask: AiTaskCreate = { ai_role: 'architect', title: '', description: '' };

  isFormValid(): boolean {
    return this.newTask.title.trim().length >= 3 && this.newTask.description.trim().length >= 10;
  }

  onCreateTask(): void {
    if (this.isFormValid()) {
      this.createTask.emit({ ...this.newTask });
      this.newTask = { ai_role: 'architect', title: '', description: '' };
    }
  }

  getRoleColor(roleId: string): string {
    return AI_ROLE_THEMES[roleId as AiRoleId]?.textColor ?? '#9CA3AF';
  }

  getRoleEmoji(roleId: string): string {
    return AI_ROLE_THEMES[roleId as AiRoleId]?.emoji ?? '🤖';
  }

  getStatusLabel(status: AiTaskStatus): string {
    const labels: Record<AiTaskStatus, string> = {
      pending: 'Pendiente',
      in_progress: 'En progreso',
      completed: 'Completada',
      failed: 'Fallida'
    };
    return labels[status] ?? status;
  }
}
