import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UsersAdminService, UserAdmin, CreateUserAdminDto, UpdateUserAdminDto } from '../services/users-admin.service';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-6">
      
      <!-- Top Action Bar -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--surface-2)] border border-[var(--border)] p-4 rounded-xl">
        <div class="flex flex-wrap items-center gap-3">
          <!-- Search -->
          <div class="relative w-64">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs">🔍</span>
            <input type="text" [(ngModel)]="searchQuery" placeholder="Buscar por nombre o correo..."
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg pl-8 pr-3 py-2 text-xs text-white placeholder:text-slate-500 outline-none focus:border-[var(--primary)]">
          </div>

          <!-- Role Filter -->
          <select [(ngModel)]="roleFilter" 
                  class="bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] cursor-pointer">
            <option value="">Todos los roles</option>
            <option value="admin">Administrador (Admin)</option>
            <option value="scrum_master">Scrum Master</option>
            <option value="dev">Desarrollador (Dev)</option>
          </select>

          <span class="text-xs text-[var(--text-secondary)]">
            Total: <strong class="text-white">{{ filteredUsers.length }}</strong> usuarios
          </span>
        </div>

        <button (click)="openCreateModal()" 
                class="px-4 py-2 bg-[var(--primary)] hover:bg-blue-600 text-white font-semibold rounded-lg text-xs transition-all shadow-md flex items-center gap-2 cursor-pointer w-fit">
          <span>➕</span>
          <span>Crear Usuario</span>
        </button>
      </div>

      <!-- Loading State -->
      <div *ngIf="isLoading" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="w-8 h-8 border-3 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
        <span class="text-xs text-[var(--text-secondary)]">Cargando lista de usuarios...</span>
      </div>

      <!-- Empty State -->
      <div *ngIf="!isLoading && filteredUsers.length === 0" class="p-12 text-center bg-[var(--surface-2)] border border-dashed border-[var(--border)] rounded-xl">
        <div class="text-4xl mb-3">👥</div>
        <h3 class="font-bold text-sm text-white mb-1">No se encontraron usuarios</h3>
        <p class="text-xs text-[var(--text-secondary)] max-w-md mx-auto mb-4">
          No hay usuarios que coincidan con los criterios de búsqueda.
        </p>
        <button (click)="openCreateModal()" class="px-4 py-2 bg-[var(--primary)] hover:bg-blue-600 text-white text-xs font-semibold rounded-lg cursor-pointer">
          + Crear Primer Usuario
        </button>
      </div>

      <!-- Users Table -->
      <div *ngIf="!isLoading && filteredUsers.length > 0" class="bg-[var(--surface-2)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-[var(--surface-1)] border-b border-[var(--border)] text-slate-400 font-bold uppercase text-[10px] tracking-wider">
              <tr>
                <th class="px-5 py-3.5">Usuario</th>
                <th class="px-5 py-3.5">Rol en el Sistema</th>
                <th class="px-5 py-3.5">Estado</th>
                <th class="px-5 py-3.5">Fecha de Registro</th>
                <th class="px-5 py-3.5 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--border)]">
              <tr *ngFor="let user of filteredUsers" class="hover:bg-[var(--surface-3)]/60 transition-colors">
                
                <!-- User Profile & Avatar -->
                <td class="px-5 py-3.5">
                  <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs shadow-xs"
                         [ngClass]="{
                           'bg-red-500/20 text-red-300 border border-red-500/30': user.role === 'admin',
                           'bg-purple-500/20 text-purple-300 border border-purple-500/30': user.role === 'scrum_master',
                           'bg-blue-500/20 text-blue-300 border border-blue-500/30': user.role === 'dev'
                         }">
                      {{ user.name ? user.name.charAt(0).toUpperCase() : 'U' }}
                    </div>
                    <div>
                      <div class="font-bold text-white text-xs">{{ user.name }}</div>
                      <div class="text-[11px] text-slate-400">{{ user.email }}</div>
                    </div>
                  </div>
                </td>

                <!-- Role Badge -->
                <td class="px-5 py-3.5">
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold"
                        [ngClass]="{
                          'bg-red-500/15 text-red-300 border border-red-500/30': user.role === 'admin',
                          'bg-purple-500/15 text-purple-300 border border-purple-500/30': user.role === 'scrum_master',
                          'bg-blue-500/15 text-blue-300 border border-blue-500/30': user.role === 'dev'
                        }">
                    <span>{{ user.role === 'admin' ? '🛡️' : (user.role === 'scrum_master' ? '👑' : '💻') }}</span>
                    <span>{{ user.role === 'admin' ? 'Administrador' : (user.role === 'scrum_master' ? 'Scrum Master' : 'Desarrollador') }}</span>
                  </span>
                </td>

                <!-- Active Status -->
                <td class="px-5 py-3.5">
                  <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium"
                        [ngClass]="user.is_active ? 'bg-green-500/15 text-green-400 border border-green-500/30' : 'bg-slate-500/15 text-slate-400 border border-slate-500/30'">
                    <span class="w-1.5 h-1.5 rounded-full" [ngClass]="user.is_active ? 'bg-green-400' : 'bg-slate-400'"></span>
                    {{ user.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>

                <!-- Created Date -->
                <td class="px-5 py-3.5 text-slate-400 text-[11px]">
                  {{ user.created_at ? (user.created_at | date:'dd/MM/yyyy HH:mm') : '—' }}
                </td>

                <!-- Actions -->
                <td class="px-5 py-3.5 text-right space-x-1.5">
                  <button (click)="openEditModal(user)" 
                          class="p-1.5 rounded text-slate-300 hover:text-white hover:bg-[var(--surface-3)] transition-colors border border-[var(--border)]/60"
                          title="Editar usuario y rol">
                    ✏️
                  </button>
                  <button (click)="deleteUser(user)" 
                          class="p-1.5 rounded text-red-400 hover:text-red-300 hover:bg-red-500/20 transition-colors border border-red-500/30"
                          title="Eliminar usuario">
                    🗑️
                  </button>
                </td>

              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- ═══ MODAL: CREAR / EDITAR USUARIO ═══ -->
    <div *ngIf="isUserModalOpen" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="w-full max-w-md bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        <div class="px-5 py-4 bg-[var(--surface-1)] border-b border-[var(--border)] flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ isEditMode ? '✏️' : '👤' }}</span>
            <h2 class="font-bold text-sm text-white">
              {{ isEditMode ? 'Editar Usuario: ' + editingUser?.name : 'Crear Nuevo Usuario' }}
            </h2>
          </div>
          <button (click)="closeUserModal()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-[var(--surface-3)]">✕</button>
        </div>

        <div class="p-5 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
          
          <!-- Name -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-1">Nombre Completo <span class="text-red-400">*</span></label>
            <input type="text" [(ngModel)]="userForm.name" placeholder="ej. Juan Perez, Maria Gomez"
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] font-medium">
          </div>

          <!-- Email -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-1">Correo Electrónico <span class="text-red-400">*</span></label>
            <input type="email" [(ngModel)]="userForm.email" placeholder="usuario@classforge.com"
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] font-medium">
          </div>

          <!-- Password (Only on Create) -->
          <div *ngIf="!isEditMode">
            <label class="text-xs font-bold text-slate-300 block mb-1">Contraseña Inicial <span class="text-red-400">*</span></label>
            <input type="password" [(ngModel)]="userForm.password" placeholder="Contraseña de acceso"
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] font-medium">
          </div>

          <!-- Role Selector -->
          <div>
            <label class="text-xs font-bold text-slate-300 block mb-1">Rol en el Sistema <span class="text-red-400">*</span></label>
            <select [(ngModel)]="userForm.role"
                    class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] cursor-pointer">
              <option value="dev">💻 Desarrollador (dev)</option>
              <option value="scrum_master">👑 Scrum Master (scrum_master)</option>
              <option value="admin">🛡️ Administrador (admin)</option>
            </select>
          </div>

          <!-- Active Status (Only on Edit) -->
          <div *ngIf="isEditMode" class="flex items-center gap-2 pt-1">
            <input type="checkbox" id="userActiveCheck" [(ngModel)]="userForm.is_active" class="w-4 h-4 rounded text-blue-600 cursor-pointer">
            <label for="userActiveCheck" class="text-xs font-semibold text-slate-300 cursor-pointer">Usuario Activo en la plataforma</label>
          </div>

        </div>

        <div class="px-5 py-3.5 bg-[var(--surface-1)] border-t border-[var(--border)] flex items-center justify-end gap-2.5">
          <button (click)="closeUserModal()" class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-300 hover:bg-[var(--surface-3)]">
            Cancelar
          </button>
          <button (click)="saveUserModal()" [disabled]="isSaving"
                  class="bg-[var(--primary)] hover:bg-blue-600 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-xs font-bold shadow-md flex items-center gap-2 cursor-pointer">
            <span *ngIf="isSaving" class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>{{ isEditMode ? 'Guardar Cambios' : 'Crear Usuario' }}</span>
          </button>
        </div>

      </div>
    </div>
  `
})
export class UserListComponent implements OnInit {
  private usersService = inject(UsersAdminService);

  users: UserAdmin[] = [];
  searchQuery = '';
  roleFilter = '';
  isLoading = false;
  isSaving = false;

  // Modal State
  isUserModalOpen = false;
  isEditMode = false;
  editingUser: UserAdmin | null = null;
  userForm = {
    name: '',
    email: '',
    password: '1234',
    role: 'dev' as 'admin' | 'scrum_master' | 'dev',
    is_active: true
  };

  get filteredUsers(): UserAdmin[] {
    let list = this.users;
    if (this.roleFilter) {
      list = list.filter(u => u.role === this.roleFilter);
    }
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase().trim();
      list = list.filter(u => 
        (u.name && u.name.toLowerCase().includes(q)) ||
        (u.email && u.email.toLowerCase().includes(q))
      );
    }
    return list;
  }

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.isLoading = true;
    this.usersService.getUsers().subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success && res.data) {
          this.users = res.data;
        }
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Error al cargar usuarios:', err);
      }
    });
  }

  openCreateModal() {
    this.isEditMode = false;
    this.editingUser = null;
    this.userForm = {
      name: '',
      email: '',
      password: '1234',
      role: 'dev',
      is_active: true
    };
    this.isUserModalOpen = true;
  }

  openEditModal(user: UserAdmin) {
    this.isEditMode = true;
    this.editingUser = user;
    this.userForm = {
      name: user.name,
      email: user.email,
      password: '',
      role: user.role,
      is_active: user.is_active
    };
    this.isUserModalOpen = true;
  }

  closeUserModal() {
    this.isUserModalOpen = false;
    this.editingUser = null;
  }

  saveUserModal() {
    if (!this.userForm.name.trim()) {
      alert('Por favor ingresa un nombre para el usuario');
      return;
    }
    if (!this.userForm.email.trim()) {
      alert('Por favor ingresa un correo electrónico válido');
      return;
    }

    this.isSaving = true;

    if (this.isEditMode && this.editingUser) {
      this.usersService.updateUser(this.editingUser.id, {
        name: this.userForm.name.trim(),
        email: this.userForm.email.trim(),
        role: this.userForm.role,
        is_active: this.userForm.is_active
      }).subscribe({
        next: (res) => {
          this.isSaving = false;
          if (res.success) {
            this.closeUserModal();
            this.loadUsers();
          } else {
            alert(res.message || 'Error al actualizar usuario');
          }
        },
        error: (err) => {
          this.isSaving = false;
          console.error('Error:', err);
          alert('Error: ' + (err.error?.detail || err.message));
        }
      });
    } else {
      if (!this.userForm.password.trim()) {
        alert('Por favor ingresa una contraseña');
        this.isSaving = false;
        return;
      }

      this.usersService.createUser({
        name: this.userForm.name.trim(),
        email: this.userForm.email.trim(),
        password: this.userForm.password.trim(),
        role: this.userForm.role
      }).subscribe({
        next: (res) => {
          this.isSaving = false;
          if (res.success) {
            this.closeUserModal();
            this.loadUsers();
          } else {
            alert(res.message || 'Error al crear usuario');
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

  deleteUser(user: UserAdmin) {
    if (!confirm(`¿Estás seguro de que deseas eliminar al usuario "${user.name}" (${user.email})?`)) {
      return;
    }

    this.usersService.deleteUser(user.id).subscribe({
      next: (res) => {
        if (res.success) {
          this.loadUsers();
        } else {
          alert(res.message || 'Error al eliminar usuario');
        }
      },
      error: (err) => {
        console.error('Error:', err);
        alert('Error: ' + (err.error?.detail || err.message));
      }
    });
  }
}
