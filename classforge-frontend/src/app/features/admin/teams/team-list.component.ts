import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TeamsService } from '../../projects/services/teams.service';
import { UsersAdminService, UserAdmin } from '../services/users-admin.service';
import { Team, TeamMember, CreateTeamDto, UpdateTeamDto } from '../../projects/models/team.model';

@Component({
  selector: 'app-team-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-6">
      
      <!-- Top Action Bar -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--surface-2)] border border-[var(--border)] p-4 rounded-xl">
        <div class="flex items-center gap-3">
          <div class="relative flex-1 sm:w-72">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs">🔍</span>
            <input type="text" [(ngModel)]="searchQuery" placeholder="Buscar equipo o scrum master..."
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg pl-8 pr-3 py-2 text-xs text-white placeholder:text-slate-500 outline-none focus:border-[var(--primary)]">
          </div>
          <span class="text-xs text-[var(--text-secondary)]">
            Total: <strong class="text-white">{{ filteredTeams.length }}</strong> equipos
          </span>
        </div>

        <button (click)="openCreateModal()" 
                class="px-4 py-2 bg-[var(--primary)] hover:bg-blue-600 text-white font-semibold rounded-lg text-xs transition-all shadow-md flex items-center gap-2 cursor-pointer w-fit">
          <span>➕</span>
          <span>Crear Equipo</span>
        </button>
      </div>

      <!-- Loading State -->
      <div *ngIf="isLoading" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="w-8 h-8 border-3 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
        <span class="text-xs text-[var(--text-secondary)]">Cargando equipos...</span>
      </div>

      <!-- Empty State -->
      <div *ngIf="!isLoading && filteredTeams.length === 0" class="p-12 text-center bg-[var(--surface-2)] border border-dashed border-[var(--border)] rounded-xl">
        <div class="text-4xl mb-3">🛡️</div>
        <h3 class="font-bold text-sm text-white mb-1">No se encontraron equipos</h3>
        <p class="text-xs text-[var(--text-secondary)] max-w-md mx-auto mb-4">
          Crea un equipo de desarrollo y asigna un Scrum Master para empezar a colaborar en proyectos y diagramas.
        </p>
        <button (click)="openCreateModal()" class="px-4 py-2 bg-[var(--primary)] hover:bg-blue-600 text-white text-xs font-semibold rounded-lg cursor-pointer">
          + Crear Primer Equipo
        </button>
      </div>

      <!-- Teams Grid -->
      <div *ngIf="!isLoading && filteredTeams.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div *ngFor="let team of filteredTeams" 
             class="bg-[var(--surface-2)] border border-[var(--border)] hover:border-indigo-500/50 rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all flex flex-col justify-between">
          
          <!-- Card Header -->
          <div class="p-5 border-b border-[var(--border)]">
            <div class="flex items-start justify-between gap-3 mb-2">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white text-sm shadow-md"
                     [style.backgroundColor]="team.avatar_color || '#2563eb'">
                  {{ team.name.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <h3 class="font-bold text-sm text-white">{{ team.name }}</h3>
                  <span class="text-[11px] text-[var(--text-secondary)] flex items-center gap-1">
                    <span class="w-1.5 h-1.5 rounded-full" [ngClass]="team.is_active ? 'bg-green-400' : 'bg-red-400'"></span>
                    {{ team.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </div>
              </div>

              <!-- Quick Actions Dropdown/Buttons -->
              <div class="flex items-center gap-1">
                <button (click)="openEditModal(team)" class="p-1.5 rounded text-xs text-slate-400 hover:text-white hover:bg-[var(--surface-3)] transition-colors" title="Editar equipo">
                  ✏️
                </button>
                <button (click)="deleteTeam(team)" class="p-1.5 rounded text-xs text-red-400 hover:text-red-300 hover:bg-red-500/20 transition-colors" title="Eliminar equipo">
                  🗑️
                </button>
              </div>
            </div>

            <p class="text-xs text-[var(--text-secondary)] line-clamp-2 mt-2">
              {{ team.description || 'Sin descripción del equipo' }}
            </p>
          </div>

          <!-- Card Content: Scrum Master & Members -->
          <div class="p-5 space-y-4 flex-1">
            
            <!-- Scrum Master Info -->
            <div class="p-3 bg-[var(--surface-1)] rounded-lg border border-[var(--border)] flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-full bg-purple-600/30 text-purple-300 border border-purple-500/40 flex items-center justify-center text-xs font-bold">
                  👑
                </div>
                <div>
                  <div class="text-[10px] text-purple-400 font-bold uppercase tracking-wider">Scrum Master</div>
                  <div class="text-xs font-semibold text-white truncate max-w-[160px]">
                    {{ team.scrum_master_name || getScrumMasterName(team.scrum_master_id) }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Members Section -->
            <div>
              <div class="flex items-center justify-between text-xs mb-2">
                <span class="font-bold text-slate-300 flex items-center gap-1.5">
                  <span>👥 Miembros</span>
                  <span class="text-[10px] font-mono px-1.5 py-0.2 bg-[var(--surface-3)] text-slate-300 rounded-full">
                    {{ team.member_ids.length }}
                  </span>
                </span>
                <button (click)="openMembersModal(team)" class="text-[11px] text-[var(--primary)] hover:underline font-semibold cursor-pointer">
                  + Gestionar
                </button>
              </div>

              <!-- Members Avatars List -->
              <div *ngIf="team.members && team.members.length > 0" class="flex flex-wrap gap-1.5">
                <div *ngFor="let member of team.members" 
                     class="px-2 py-1 bg-[var(--surface-1)] border border-[var(--border)] rounded-md text-[11px] text-slate-300 flex items-center gap-1.5"
                     [title]="member.name + ' (' + member.email + ')'">
                  <span class="w-2 h-2 rounded-full" [ngClass]="member.role === 'scrum_master' ? 'bg-purple-400' : 'bg-blue-400'"></span>
                  <span class="truncate max-w-[110px]">{{ member.name }}</span>
                </div>
              </div>

              <div *ngIf="!team.members || team.members.length === 0" class="text-[11px] text-slate-500 italic py-1">
                No hay miembros añadidos. Haz clic en "Gestionar" para agregar desarrolladores.
              </div>
            </div>

          </div>

          <!-- Card Footer -->
          <div class="px-5 py-3 bg-[var(--surface-1)] border-t border-[var(--border)] flex items-center justify-between">
            <span class="text-[10px] text-slate-500">
              ID: {{ team.id.slice(-6) }}
            </span>
            <button (click)="openMembersModal(team)" 
                    class="px-3 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors">
              <span>👥</span>
              <span>Asignar Miembros</span>
            </button>
          </div>

        </div>
      </div>

    </div>

    <!-- ═══ MODAL: CREAR / EDITAR EQUIPO ═══ -->
    <div *ngIf="isTeamModalOpen" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="w-full max-w-lg bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        <div class="px-5 py-4 bg-[var(--surface-1)] border-b border-[var(--border)] flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ isEditMode ? '✏️' : '🛡️' }}</span>
            <h2 class="font-bold text-sm text-white">
              {{ isEditMode ? 'Editar Equipo: ' + editingTeam?.name : 'Crear Nuevo Equipo de Desarrollo' }}
            </h2>
          </div>
          <button (click)="closeTeamModal()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-[var(--surface-3)]">✕</button>
        </div>

        <div class="p-5 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
          
          <!-- Team Name -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-1">Nombre del Equipo <span class="text-red-400">*</span></label>
            <input type="text" [(ngModel)]="teamForm.name" placeholder="ej. Equipo Alpha, Equipo Veterinaria"
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] font-medium">
          </div>

          <!-- Description -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-1">Descripción</label>
            <textarea [(ngModel)]="teamForm.description" rows="2" placeholder="Equipo responsable de arquitectura y desarrollo..."
                      class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg p-2 text-xs text-white outline-none focus:border-[var(--primary)]"></textarea>
          </div>

          <!-- Scrum Master Selector -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-1">
              Scrum Master Responsable <span class="text-red-400">*</span>
            </label>
            <select [(ngModel)]="teamForm.scrum_master_id" 
                    class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] cursor-pointer">
              <option value="" disabled>-- Selecciona un Scrum Master --</option>
              <option *ngFor="let sm of scrumMastersList" [value]="sm.id">
                {{ sm.name }} ({{ sm.email }})
              </option>
            </select>
          </div>

          <!-- Initial Members Selection -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-2">
              Miembros Desarrolladores Asignados
            </label>

            <div class="max-h-44 overflow-y-auto custom-scrollbar space-y-1.5 p-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-lg">
              <div *ngFor="let dev of developersList" 
                   (click)="toggleFormMember(dev.id)"
                   class="flex items-center justify-between p-2 rounded hover:bg-[var(--surface-3)] cursor-pointer text-xs"
                   [ngClass]="{'bg-blue-600/20': isMemberSelectedInForm(dev.id)}">
                
                <div class="flex items-center gap-2">
                  <div class="w-6 h-6 rounded-full bg-blue-600/30 text-blue-300 flex items-center justify-center text-[10px] font-bold">
                    {{ dev.name.charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <span class="font-semibold text-white">{{ dev.name }}</span>
                    <span class="text-[10px] text-slate-400 ml-1.5">{{ dev.email }}</span>
                  </div>
                </div>

                <input type="checkbox" [checked]="isMemberSelectedInForm(dev.id)" (click)="$event.stopPropagation(); toggleFormMember(dev.id)"
                       class="w-4 h-4 rounded text-blue-600 cursor-pointer">
              </div>

              <div *ngIf="developersList.length === 0" class="text-center py-4 text-xs text-slate-400 italic">
                No hay desarrolladores registrados aún.
              </div>
            </div>
          </div>

        </div>

        <div class="px-5 py-3.5 bg-[var(--surface-1)] border-t border-[var(--border)] flex items-center justify-end gap-2.5">
          <button (click)="closeTeamModal()" class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-300 hover:bg-[var(--surface-3)]">
            Cancelar
          </button>
          <button (click)="saveTeamModal()" [disabled]="isSaving"
                  class="bg-[var(--primary)] hover:bg-blue-600 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-xs font-bold shadow-md flex items-center gap-2 cursor-pointer">
            <span *ngIf="isSaving" class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>{{ isEditMode ? 'Guardar Cambios' : 'Crear Equipo' }}</span>
          </button>
        </div>

      </div>
    </div>

    <!-- ═══ MODAL: GESTIONAR MIEMBROS DEL EQUIPO ═══ -->
    <div *ngIf="isMembersModalOpen" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="w-full max-w-md bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        
        <div class="px-5 py-4 bg-[var(--surface-1)] border-b border-[var(--border)] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <span class="text-lg">👥</span>
            <div>
              <h2 class="font-bold text-sm text-white">Miembros del Equipo</h2>
              <p class="text-[11px] text-[var(--text-secondary)]">{{ activeTeamForMembers?.name }}</p>
            </div>
          </div>
          <button (click)="closeMembersModal()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-[var(--surface-3)]">✕</button>
        </div>

        <div class="p-5 flex flex-col gap-3 overflow-y-auto custom-scrollbar">
          <p class="text-xs text-slate-300 font-semibold mb-1">
            Selecciona los desarrolladores que integran este equipo:
          </p>

          <div *ngFor="let user of allUsers" 
               (click)="toggleMemberInActiveTeam(user.id)"
               class="p-2.5 bg-[var(--surface-1)] hover:bg-[var(--surface-3)] border border-[var(--border)] rounded-xl flex items-center justify-between gap-3 cursor-pointer transition-colors"
               [class.border-blue-500]="isUserInActiveTeam(user.id)">
            
            <div class="flex items-center gap-2.5">
              <div class="w-7 h-7 rounded-full bg-blue-600/30 text-blue-300 border border-blue-500/40 flex items-center justify-center text-xs font-bold">
                {{ user.name.charAt(0).toUpperCase() }}
              </div>
              <div>
                <div class="text-xs font-bold text-white flex items-center gap-1.5">
                  <span>{{ user.name }}</span>
                  <span class="text-[9px] px-1.5 py-0.2 rounded font-mono uppercase"
                        [ngClass]="user.role === 'scrum_master' ? 'bg-purple-500/20 text-purple-300' : 'bg-blue-500/20 text-blue-300'">
                    {{ user.role }}
                  </span>
                </div>
                <div class="text-[10px] text-slate-400">{{ user.email }}</div>
              </div>
            </div>

            <input type="checkbox" [checked]="isUserInActiveTeam(user.id)" (click)="$event.stopPropagation(); toggleMemberInActiveTeam(user.id)"
                   class="w-4 h-4 rounded text-blue-600 cursor-pointer">
          </div>
        </div>

        <div class="px-5 py-3.5 bg-[var(--surface-1)] border-t border-[var(--border)] flex items-center justify-between">
          <span class="text-xs text-slate-400">{{ activeTeamSelectedMemberIds.size }} miembros</span>
          <div class="flex items-center gap-2">
            <button (click)="closeMembersModal()" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:bg-[var(--surface-3)]">
              Cancelar
            </button>
            <button (click)="saveTeamMembers()" [disabled]="isSaving"
                    class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-1.5 rounded-lg text-xs font-bold shadow-md flex items-center gap-1.5 cursor-pointer">
              <span *ngIf="isSaving" class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>Guardar Miembros</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  `
})
export class TeamListComponent implements OnInit {
  private teamsService = inject(TeamsService);
  private usersService = inject(UsersAdminService);

  teams: Team[] = [];
  allUsers: UserAdmin[] = [];
  searchQuery = '';
  isLoading = false;
  isSaving = false;

  // Modal Crear / Editar
  isTeamModalOpen = false;
  isEditMode = false;
  editingTeam: Team | null = null;
  teamForm = {
    name: '',
    description: '',
    scrum_master_id: '',
    member_ids: [] as string[]
  };

  // Modal Miembros
  isMembersModalOpen = false;
  activeTeamForMembers: Team | null = null;
  activeTeamSelectedMemberIds = new Set<string>();

  get filteredTeams(): Team[] {
    if (!this.searchQuery.trim()) return this.teams;
    const q = this.searchQuery.toLowerCase().trim();
    return this.teams.filter(t => 
      t.name.toLowerCase().includes(q) ||
      (t.description && t.description.toLowerCase().includes(q)) ||
      (t.scrum_master_name && t.scrum_master_name.toLowerCase().includes(q))
    );
  }

  get scrumMastersList(): UserAdmin[] {
    return this.allUsers.filter(u => u.role === 'scrum_master' || u.role === 'admin');
  }

  get developersList(): UserAdmin[] {
    return this.allUsers.filter(u => u.role === 'dev' || u.role === 'scrum_master');
  }

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.isLoading = true;
    this.teamsService.getTeams().subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success && res.data) {
          this.teams = res.data;
        }
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Error al cargar equipos:', err);
      }
    });

    this.usersService.getUsers().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.allUsers = res.data;
        }
      },
      error: (err) => console.error('Error al cargar usuarios:', err)
    });
  }

  getScrumMasterName(smId: string): string {
    const user = this.allUsers.find(u => u.id === smId);
    return user ? user.name : 'No asignado';
  }

  // ═══ Modal Crear / Editar Equipo ═══

  openCreateModal() {
    this.isEditMode = false;
    this.editingTeam = null;
    const defaultSm = this.scrumMastersList.length > 0 ? this.scrumMastersList[0].id : '';
    this.teamForm = {
      name: '',
      description: '',
      scrum_master_id: defaultSm,
      member_ids: []
    };
    this.isTeamModalOpen = true;
  }

  openEditModal(team: Team) {
    this.isEditMode = true;
    this.editingTeam = team;
    this.teamForm = {
      name: team.name,
      description: team.description || '',
      scrum_master_id: team.scrum_master_id,
      member_ids: team.member_ids ? [...team.member_ids] : []
    };
    this.isTeamModalOpen = true;
  }

  closeTeamModal() {
    this.isTeamModalOpen = false;
    this.editingTeam = null;
  }

  toggleFormMember(userId: string) {
    const idx = this.teamForm.member_ids.indexOf(userId);
    if (idx >= 0) {
      this.teamForm.member_ids.splice(idx, 1);
    } else {
      this.teamForm.member_ids.push(userId);
    }
  }

  isMemberSelectedInForm(userId: string): boolean {
    return this.teamForm.member_ids.includes(userId);
  }

  saveTeamModal() {
    if (!this.teamForm.name.trim()) {
      alert('Por favor ingresa un nombre para el equipo');
      return;
    }
    if (!this.teamForm.scrum_master_id) {
      alert('Por favor selecciona un Scrum Master para el equipo');
      return;
    }

    this.isSaving = true;

    if (this.isEditMode && this.editingTeam) {
      this.teamsService.updateTeam(this.editingTeam.id, {
        name: this.teamForm.name.trim(),
        description: this.teamForm.description.trim(),
        scrum_master_id: this.teamForm.scrum_master_id,
        member_ids: this.teamForm.member_ids
      }).subscribe({
        next: (res) => {
          this.isSaving = false;
          if (res.success) {
            this.closeTeamModal();
            this.loadData();
          } else {
            alert(res.message || 'Error al actualizar equipo');
          }
        },
        error: (err) => {
          this.isSaving = false;
          console.error('Error:', err);
          alert('Error: ' + (err.error?.detail || err.message));
        }
      });
    } else {
      this.teamsService.createTeam({
        name: this.teamForm.name.trim(),
        description: this.teamForm.description.trim(),
        scrum_master_id: this.teamForm.scrum_master_id,
        member_ids: this.teamForm.member_ids
      }).subscribe({
        next: (res) => {
          this.isSaving = false;
          if (res.success) {
            this.closeTeamModal();
            this.loadData();
          } else {
            alert(res.message || 'Error al crear equipo');
          }
        },
        error: (err) => {
          this.isSaving = false;
          console.error('Error:', err);
          alert('Error: ' + (err.error?.detail || err.message));
        }
      });
    }
  }

  // ═══ Modal Gestionar Miembros ═══

  openMembersModal(team: Team) {
    this.activeTeamForMembers = team;
    this.activeTeamSelectedMemberIds = new Set(team.member_ids || []);
    this.isMembersModalOpen = true;
  }

  closeMembersModal() {
    this.isMembersModalOpen = false;
    this.activeTeamForMembers = null;
    this.activeTeamSelectedMemberIds.clear();
  }

  isUserInActiveTeam(userId: string): boolean {
    return this.activeTeamSelectedMemberIds.has(userId);
  }

  toggleMemberInActiveTeam(userId: string) {
    if (this.activeTeamSelectedMemberIds.has(userId)) {
      this.activeTeamSelectedMemberIds.delete(userId);
    } else {
      this.activeTeamSelectedMemberIds.add(userId);
    }
  }

  saveTeamMembers() {
    if (!this.activeTeamForMembers) return;
    this.isSaving = true;
    const memberIds = Array.from(this.activeTeamSelectedMemberIds);

    this.teamsService.updateTeam(this.activeTeamForMembers.id, {
      member_ids: memberIds
    }).subscribe({
      next: (res) => {
        this.isSaving = false;
        if (res.success) {
          this.closeMembersModal();
          this.loadData();
        } else {
          alert(res.message || 'Error al guardar miembros');
        }
      },
      error: (err) => {
        this.isSaving = false;
        console.error('Error:', err);
        alert('Error: ' + (err.error?.detail || err.message));
      }
    });
  }

  // ═══ Delete Team ═══

  deleteTeam(team: Team) {
    if (!confirm(`¿Estás seguro de que deseas eliminar el equipo "${team.name}"?`)) {
      return;
    }
    this.teamsService.deleteTeam(team.id).subscribe({
      next: (res) => {
        if (res.success) {
          this.loadData();
        } else {
          alert(res.message || 'Error al eliminar equipo');
        }
      },
      error: (err) => {
        console.error('Error:', err);
        alert('Error: ' + (err.error?.detail || err.message));
      }
    });
  }
}
