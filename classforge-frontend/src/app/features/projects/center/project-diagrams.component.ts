import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ProjectCenterComponent } from './project-center.component';
import { DiagramService } from '../../diagrams/services/diagram.service';
import { FoldersService } from '../services/folders.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';
import { Diagram } from '../../diagrams/models/diagram.model';
import { Folder } from '../models/folder.model';
import { PageStateComponent, PageStateType } from '../../../shared/components/page-state/page-state.component';

@Component({
  selector: 'app-project-diagrams',
  standalone: true,
  imports: [CommonModule, FormsModule, PageStateComponent],
  template: `
    <div class="space-y-6">
      
      <!-- Top Action Bar -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4">
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <span>📐</span>
            <span>Diagramas del Proyecto</span>
          </h2>
          <p class="text-xs text-[var(--text-secondary)]">
            Gestiona los esquemas de clases UML de este proyecto.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <!-- Import XMI Button -->
          <label class="px-3 py-2 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-[var(--text-secondary)] hover:text-white border border-[var(--border)] rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer">
            <span>📥</span>
            <span>Importar XMI</span>
            <input type="file" accept=".xmi,.xml" (change)="onFileSelected($event)" class="hidden" />
          </label>

          <!-- Create Diagram Button -->
          <button
            type="button"
            (click)="isCreateModalOpen = true"
            class="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-primary/20 transition-colors cursor-pointer"
          >
            <span>➕</span>
            <span>Nuevo Diagrama</span>
          </button>
        </div>
      </div>

      <!-- State Handling -->
      <app-page-state
        *ngIf="pageState() !== 'ready'"
        [state]="pageState()"
        [title]="pageState() === 'empty' ? 'Sin diagramas en este proyecto' : 'Cargando diagramas...'"
        [message]="pageState() === 'empty' ? 'Crea un nuevo diagrama o importa un archivo XMI para comenzar a modelar.' : undefined"
        [actionLabel]="pageState() === 'empty' ? 'Crear Primer Diagrama' : undefined"
        (action)="isCreateModalOpen = true"
        (retry)="loadDiagrams()"
      ></app-page-state>

      <!-- Diagrams Grid -->
      <div *ngIf="pageState() === 'ready'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          *ngFor="let diag of diagrams()"
          class="bg-[var(--surface-2)] border border-[var(--border)] hover:border-primary/50 rounded-2xl p-4 flex flex-col justify-between transition-all duration-200 group hover:shadow-xl hover:shadow-[var(--surface-1)]"
        >
          <div>
            <div class="flex items-start justify-between gap-2 mb-2">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-primary/10 text-primary-light border border-primary/20">
                v{{ diag.version }}
              </span>
              <span class="text-[10px] text-[var(--text-muted)] capitalize px-2 py-0.5 rounded-full bg-[var(--surface-3)]">
                {{ diag.status }}
              </span>
            </div>

            <h3 class="text-sm font-bold text-white mb-1 truncate" [title]="diag.name">
              {{ diag.name }}
            </h3>

            <p class="text-xs text-[var(--text-secondary)] line-clamp-2 mb-4 leading-relaxed">
              {{ diag.description || 'Sin descripción' }}
            </p>
          </div>

          <div class="pt-3 border-t border-[var(--border)] flex items-center justify-between">
            <button
              type="button"
              (click)="openDiagram(diag.id)"
              class="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>Abrir Lienzo</span>
              <span>→</span>
            </button>

            <div class="flex items-center gap-1">
              <button
                type="button"
                (click)="exportXmi(diag.id, diag.name)"
                class="p-1.5 rounded-lg text-xs text-[var(--text-muted)] hover:text-white hover:bg-[var(--surface-3)] transition-colors cursor-pointer"
                title="Exportar XMI"
              >
                📥
              </button>
              <button
                type="button"
                (click)="deleteDiagram(diag.id)"
                class="p-1.5 rounded-lg text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors cursor-pointer"
                title="Eliminar diagrama"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Create Diagram Modal -->
      <div
        *ngIf="isCreateModalOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in"
        role="dialog"
        aria-modal="true"
      >
        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4" (click)="$event.stopPropagation()">
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h3 class="text-base font-bold text-white">Nuevo Diagrama UML</h3>
            <button (click)="isCreateModalOpen = false" class="text-slate-400 hover:text-white">✕</button>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Nombre del Diagrama</label>
            <input
              type="text"
              [(ngModel)]="newDiagramName"
              placeholder="Ej. Arquitectura del Sistema"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Descripción</label>
            <textarea
              [(ngModel)]="newDiagramDesc"
              rows="3"
              placeholder="Descripción breve del diagrama..."
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
            ></textarea>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button
              (click)="isCreateModalOpen = false"
              class="px-4 py-2 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-slate-300 rounded-xl text-xs font-semibold transition-colors"
            >
              Cancelar
            </button>
            <button
              (click)="createDiagram()"
              [disabled]="isCreating"
              class="px-4 py-2 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors"
            >
              {{ isCreating ? 'Creando...' : 'Crear Diagrama' }}
            </button>
          </div>
        </div>
      </div>

    </div>
  `
})
export class ProjectDiagramsComponent implements OnInit {
  center = inject(ProjectCenterComponent);
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmDialogService);
  private router = inject(Router);

  diagrams = signal<Diagram[]>([]);
  pageState = signal<PageStateType>('loading');

  isCreateModalOpen = false;
  newDiagramName = '';
  newDiagramDesc = '';
  isCreating = false;

  ngOnInit(): void {
    this.loadDiagrams();
  }

  loadDiagrams(): void {
    const proj = this.center.project();
    if (!proj) return;
    this.pageState.set('loading');

    this.diagramService.getDiagrams({ project_id: proj.id }).subscribe({
      next: (res) => {
        const items = res.data || [];
        this.diagrams.set(items);
        this.pageState.set(items.length > 0 ? 'ready' : 'empty');
      },
      error: () => {
        this.pageState.set('error');
      }
    });
  }

  openDiagram(id: string): void {
    this.router.navigate(['/diagrams', id]);
  }

  createDiagram(): void {
    const proj = this.center.project();
    if (!proj) return;
    if (!this.newDiagramName.trim()) {
      this.toastService.error('Ingresa un nombre para el diagrama');
      return;
    }

    this.isCreating = true;
    this.diagramService.createDiagram({
      name: this.newDiagramName.trim(),
      description: this.newDiagramDesc.trim(),
      project_id: proj.id,
      team_id: proj.team_id
    }).subscribe({
      next: (res) => {
        this.isCreating = false;
        this.isCreateModalOpen = false;
        this.newDiagramName = '';
        this.newDiagramDesc = '';
        this.toastService.success('Diagrama creado exitosamente');
        this.loadDiagrams();
        if (res.data) {
          this.openDiagram(res.data.id);
        }
      },
      error: (err) => {
        this.isCreating = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al crear diagrama');
      }
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const proj = this.center.project();
    if (!proj) return;

    // Create a new diagram first, then import XMI into it
    const diagramName = file.name.replace(/\.[^/.]+$/, '');
    this.toastService.info('Importando archivo XMI...');

    this.diagramService.createDiagram({
      name: diagramName,
      description: `Importado desde archivo ${file.name}`,
      project_id: proj.id,
      team_id: proj.team_id
    }).subscribe({
      next: (res) => {
        if (res.data) {
          this.diagramService.importXmi(res.data.id, file).subscribe({
            next: () => {
              this.toastService.success('Archivo XMI importado correctamente');
              this.loadDiagrams();
            },
            error: (err) => {
              this.toastService.error('Error al parsear el archivo XMI');
            }
          });
        }
      },
      error: () => {
        this.toastService.error('Error al inicializar diagrama para XMI');
      }
    });

    input.value = '';
  }

  exportXmi(id: string, name: string): void {
    this.diagramService.exportXmi(id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${name || 'diagram'}.xmi`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('Archivo XMI descargado');
      },
      error: () => this.toastService.error('Error al exportar XMI')
    });
  }

  async deleteDiagram(id: string): Promise<void> {
    const confirmed = await this.confirmService.confirm({
      title: '¿Eliminar diagrama?',
      message: 'Esta acción no se puede deshacer.',
      confirmText: 'Eliminar',
      danger: true
    });
    if (!confirmed) return;

    this.diagramService.deleteDiagram(id).subscribe({
      next: () => {
        this.toastService.success('Diagrama eliminado');
        this.loadDiagrams();
      },
      error: () => this.toastService.error('Error al eliminar diagrama')
    });
  }
}
