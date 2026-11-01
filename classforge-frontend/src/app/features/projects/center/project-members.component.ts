import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectCenterComponent } from './project-center.component';
import { TeamsService } from '../services/teams.service';
import { UsersAdminService } from '../../admin/services/users-admin.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';
import { Team } from '../models/team.model';
import { PageStateComponent, PageStateType } from '../../../shared/components/page-state/page-state.component';

@Component({
  selector: 'app-project-members',
  standalone: true,
  imports: [CommonModule, FormsModule, PageStateComponent],
  template: `
    <div class="space-y-6">
      
      <!-- Top Action Bar -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4">
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <span>👥</span>
            <span>Integrantes y Participantes</span>
          </h2>
          <p class="text-xs text-[var(--text-secondary)]">
            Colaboradores con acceso de edición y modelado en este proyecto.
          </p>
        </div>

        <div *ngIf="canManage() && team()" class="flex items-center gap-2">
          <button
            type="button"
            (click)="isAddMemberModalOpen = true"
            class="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-primary/20 transition-colors cursor-pointer"
          >
            <span>➕</span>
            <span>Añadir Integrante</span>
          </button>
        </div>
      </div>

      <!-- Individual project notice -->
      <div *ngIf="center.project()?.type !== 'team'" class="p-8 text-center bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl">
        <span class="text-3xl block mb-2">👤</span>
        <h3 class="text-base font-bold text-white">Proyecto Individual</h3>
        <p class="text-xs text-[var(--text-secondary)] mt-1 max-w-md mx-auto">
          Este proyecto es de ámbito personal. Solo tú tienes acceso a sus diagramas y artefactos.
        </p>
      </div>

      <!-- Team Members Grid -->
      <div *ngIf="center.project()?.type === 'team'">
        
        <app-page-state
          *ngIf="pageState() !== 'ready'"
          [state]="pageState()"
          title="Sin integrantes"
          message="No se encontraron miembros registrados para este equipo."
          emptyIcon="👥"
        ></app-page-state>

        <div *ngIf="pageState() === 'ready'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            *ngFor="let member of members()"
            class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4 flex items-center justify-between gap-3 shadow-xs"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center font-bold text-primary-light shrink-0">
                {{ getInitials(member.name) }}
              </div>
              <div class="min-w-0">
                <p class="text-sm font-bold text-white truncate">{{ member.name }}</p>
                <p class="text-xs text-[var(--text-secondary)] truncate">{{ member.email }}</p>
                <span class="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--surface-3)] text-[var(--text-muted)] border border-[var(--border)]">
                  {{ member.role }}
                </span>
              </div>
            </div>

            <button
              *ngIf="canManage()"
              type="button"
              (click)="removeMember(member.id)"
              class="p-1.5 rounded-lg text-xs text-rose-400 hover:text-white hover:bg-rose-600 transition-colors cursor-pointer shrink-0"
              title="Quitar miembro del equipo"
            >
              ✕
            </button>
          </div>
        </div>

      </div>

      <!-- Add Member Modal -->
      <div
        *ngIf="isAddMemberModalOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in"
        role="dialog"
        aria-modal="true"
      >
        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4" (click)="$event.stopPropagation()">
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <h3 class="text-base font-bold text-white">Añadir Integrante al Equipo</h3>
            <button (click)="isAddMemberModalOpen = false" class="text-slate-400 hover:text-white">✕</button>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Seleccionar Usuario</label>
            <select
              [(ngModel)]="selectedUserId"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
            >
              <option value="">Selecciona un usuario...</option>
              <option *ngFor="let u of availableUsers()" [value]="u.id">
                {{ u.name }} ({{ u.email }})
              </option>
            </select>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button
              (click)="isAddMemberModalOpen = false"
              class="px-4 py-2 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-slate-300 rounded-xl text-xs font-semibold transition-colors"
            >
              Cancelar
            </button>
            <button
              (click)="addMember()"
              [disabled]="!selectedUserId || isSubmitting"
              class="px-4 py-2 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition-colors"
            >
              {{ isSubmitting ? 'Añadiendo...' : 'Añadir' }}
            </button>
          </div>
        </div>
      </div>

    </div>
  `
})
export class ProjectMembersComponent implements OnInit {
  center = inject(ProjectCenterComponent);
  private teamsService = inject(TeamsService);
  private usersAdminService = inject(UsersAdminService);
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmDialogService);

  team = signal<Team | null>(null);
  members = signal<any[]>([]);
  availableUsers = signal<any[]>([]);
  pageState = signal<PageStateType>('loading');

  isAddMemberModalOpen = false;
  selectedUserId = '';
  isSubmitting = false;

  ngOnInit(): void {
    const proj = this.center.project();
    if (proj?.team_id) {
      this.loadTeamMembers(proj.team_id);
    } else {
      this.pageState.set('ready');
    }
  }

  loadTeamMembers(teamId: string): void {
    this.pageState.set('loading');
    this.teamsService.getTeam(teamId).subscribe({
      next: (res) => {
        if (res.data) {
          this.team.set(res.data);
          // Load users to get full details
          this.usersAdminService.getUsers().subscribe({
            next: (uRes) => {
              const allUsers = uRes.data || [];
              const teamMemberIds = res.data?.member_ids || [];
              const teamMembers = allUsers.filter(u => teamMemberIds.includes(u.id));
              const notInTeam = allUsers.filter(u => !teamMemberIds.includes(u.id));

              this.members.set(teamMembers);
              this.availableUsers.set(notInTeam);
              this.pageState.set(teamMembers.length > 0 ? 'ready' : 'empty');
            },
            error: () => this.pageState.set('ready')
          });
        } else {
          this.pageState.set('empty');
        }
      },
      error: () => this.pageState.set('error')
    });
  }

  canManage(): boolean {
    const user = this.authService.getCurrentUser();
    return user?.role === 'admin' || user?.role === 'scrum_master';
  }

  getInitials(name: string): string {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  }

  addMember(): void {
    const currentTeam = this.team();
    if (!currentTeam || !this.selectedUserId) return;

    this.isSubmitting = true;
    this.teamsService.addMember(currentTeam.id, this.selectedUserId).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.isAddMemberModalOpen = false;
        this.selectedUserId = '';
        this.toastService.success('Integrante añadido al equipo');
        this.loadTeamMembers(currentTeam.id);
      },
      error: (err) => {
        this.isSubmitting = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al añadir integrante');
      }
    });
  }

  async removeMember(userId: string): Promise<void> {
    const currentTeam = this.team();
    if (!currentTeam) return;

    const confirmed = await this.confirmService.confirm({
      title: '¿Quitar integrante del equipo?',
      message: 'El usuario perderá acceso directo a los diagramas de este proyecto.',
      confirmText: 'Quitar Miembro',
      danger: true
    });
    if (!confirmed) return;

    this.teamsService.removeMember(currentTeam.id, userId).subscribe({
      next: () => {
        this.toastService.success('Integrante removido');
        this.loadTeamMembers(currentTeam.id);
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || err.message || 'Error al quitar integrante');
      }
    });
  }
}
