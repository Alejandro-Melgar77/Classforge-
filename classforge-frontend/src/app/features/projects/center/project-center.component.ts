import { Component, inject, OnInit, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ProjectsService } from '../services/projects.service';
import { Project } from '../models/project.model';
import { BreadcrumbService } from '../../../core/services/breadcrumb.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';
import { AuthService } from '../../../core/services/auth.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { PageStateComponent, PageStateType } from '../../../shared/components/page-state/page-state.component';

@Component({
  selector: 'app-project-center',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    StatusBadgeComponent,
    PageStateComponent
  ],
  template: `
    <div class="h-full flex flex-col bg-[var(--surface-1)] overflow-hidden">
      <!-- Loading or Error State -->
      <div *ngIf="pageState() !== 'ready'" class="p-8 flex-1 flex items-center justify-center">
        <app-page-state
          [state]="pageState()"
          [title]="pageState() === 'error' ? 'Proyecto no disponible' : 'Cargando centro de proyecto'"
          [message]="errorMessage"
          [showRetry]="true"
          secondaryActionLabel="← Volver a Proyectos"
          (retry)="loadProject()"
          (secondaryAction)="goBack()"
        ></app-page-state>
      </div>

      <!-- Main Project Center View -->
      <div *ngIf="pageState() === 'ready' && project() as proj" class="flex-1 flex flex-col overflow-hidden">
        
        <!-- Project Center Header -->
        <header class="bg-[var(--surface-2)] border-b border-[var(--border)] px-4 sm:px-6 py-3 shrink-0">
          <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
            
            <!-- Left Info & Back Link -->
            <div class="flex items-center gap-3 min-w-0">
              <button
                type="button"
                (click)="goBack()"
                class="px-2.5 py-1.5 rounded-xl bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-[var(--text-secondary)] hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shrink-0"
                title="Volver a lista de proyectos"
              >
                <span>←</span>
                <span>Proyectos</span>
              </button>

              <div class="w-1.5 h-6 rounded-full shrink-0" [style.backgroundColor]="proj.color_tag || 'var(--primary)'"></div>

              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <h1 class="text-base sm:text-lg font-bold text-white truncate" [title]="proj.name">
                    {{ proj.name }}
                  </h1>
                  <app-status-badge [status]="proj.status"></app-status-badge>
                </div>
                <p class="text-xs text-[var(--text-secondary)] truncate max-w-md" [title]="proj.description">
                  {{ proj.description || 'Sin descripción' }}
                </p>
              </div>
            </div>

            <!-- Right Actions -->
            <div class="flex items-center gap-2 shrink-0">
              <span class="px-2.5 py-1 rounded-lg bg-[var(--surface-3)] text-xs text-[var(--text-secondary)] border border-[var(--border)]">
                {{ proj.type === 'team' ? '👥 Equipo' : '👤 Personal' }}
              </span>

              <button
                *ngIf="canDelete()"
                type="button"
                (click)="deleteProject(proj.id)"
                class="p-1.5 text-xs text-rose-400 hover:text-white bg-rose-500/10 hover:bg-rose-600 rounded-lg border border-rose-500/20 transition-colors cursor-pointer"
                title="Eliminar proyecto"
              >
                🗑️
              </button>
            </div>
          </div>

          <!-- Project Navigation Tabs -->
          <nav
            class="max-w-7xl mx-auto flex items-center gap-2 sm:gap-4 mt-3 border-t border-[var(--border)]/50 pt-2 overflow-x-auto scrollbar-none"
            aria-label="Pestañas del proyecto"
          >
            <a
              routerLink="resumen"
              routerLinkActive="text-primary border-primary font-bold"
              class="px-3 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
            >
              <span>📊</span>
              <span>Resumen</span>
            </a>

            <a
              routerLink="diagramas"
              routerLinkActive="text-primary border-primary font-bold"
              class="px-3 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
            >
              <span>📐</span>
              <span>Diagramas</span>
            </a>

            <a
              routerLink="equipo-ia"
              routerLinkActive="text-primary border-primary font-bold"
              class="px-3 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
            >
              <span>🤖</span>
              <span>Equipo IA</span>
            </a>

            <a
              routerLink="tareas"
              routerLinkActive="text-primary border-primary font-bold"
              class="px-3 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
            >
              <span>✅</span>
              <span>Tareas</span>
            </a>

            <a
              routerLink="miembros"
              routerLinkActive="text-primary border-primary font-bold"
              class="px-3 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-white border-b-2 border-transparent transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
            >
              <span>👥</span>
              <span>Miembros</span>
            </a>
          </nav>
        </header>

        <!-- Project Tab Router Outlet -->
        <div class="flex-1 overflow-y-auto p-4 sm:p-6">
          <div class="max-w-7xl mx-auto h-full">
            <router-outlet></router-outlet>
          </div>
        </div>

      </div>
    </div>
  `
})
export class ProjectCenterComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private projectsService = inject(ProjectsService);
  private breadcrumbService = inject(BreadcrumbService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmDialogService);
  private authService = inject(AuthService);

  projectId: string | null = null;
  project = signal<Project | null>(null);
  pageState = signal<PageStateType>('loading');
  errorMessage = 'Cargando información del proyecto...';

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.projectId = params.get('projectId');
      if (this.projectId) {
        this.loadProject();
      } else {
        this.pageState.set('error');
        this.errorMessage = 'Identificador de proyecto no especificado.';
      }
    });
  }

  ngOnDestroy(): void {
    this.breadcrumbService.clearDynamicLabels();
  }

  loadProject(): void {
    if (!this.projectId) return;
    this.pageState.set('loading');

    this.projectsService.getProject(this.projectId).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.project.set(res.data);
          this.pageState.set('ready');
          this.breadcrumbService.setDynamicLabel(':projectId', res.data.name);
        } else {
          this.pageState.set('error');
          this.errorMessage = 'No se encontró el proyecto o fue eliminado.';
        }
      },
      error: (err) => {
        this.pageState.set('error');
        if (err.status === 403) {
          this.errorMessage = 'No tienes permisos para acceder a este proyecto.';
        } else if (err.status === 404) {
          this.errorMessage = 'El proyecto solicitado no existe.';
        } else {
          this.errorMessage = 'Error de conexión al cargar el proyecto.';
        }
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/projects']);
  }

  canDelete(): boolean {
    const user = this.authService.getCurrentUser();
    return user?.role === 'admin';
  }

  async deleteProject(id: string): Promise<void> {
    const confirmed = await this.confirmService.confirm({
      title: '¿Eliminar proyecto?',
      message: 'Esta acción eliminará el proyecto y todos sus diagramas asociados de manera permanente.',
      confirmText: 'Eliminar Proyecto',
      danger: true
    });
    if (!confirmed) return;

    this.projectsService.deleteProject(id).subscribe({
      next: () => {
        this.toastService.success('Proyecto eliminado exitosamente');
        this.goBack();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || err.message || 'Error al eliminar proyecto');
      }
    });
  }
}
