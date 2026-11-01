import { Component, inject, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';
import { PageStateComponent } from '../../../shared/components/page-state/page-state.component';

@Component({
  selector: 'app-user-menu-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, PageStateComponent],
  template: `
    <div
      class="fixed inset-0 z-[9990] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-modal-title"
    >
      <div
        class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        (click)="$event.stopPropagation()"
      >
        <!-- Modal Header -->
        <div class="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-3)]">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center font-bold text-primary-light">
              {{ getInitials(currentUser?.name || '') }}
            </div>
            <div>
              <h2 id="user-modal-title" class="text-base font-bold text-white">
                Cuenta de Usuario
              </h2>
              <p class="text-xs text-[var(--text-secondary)]">
                {{ currentUser?.email }} ({{ getRoleLabel(currentUser?.role || 'dev') }})
              </p>
            </div>
          </div>
          <button
            type="button"
            (click)="close.emit()"
            class="text-[var(--text-secondary)] hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer text-sm"
            aria-label="Cerrar modal"
          >
            ✕
          </button>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex border-b border-[var(--border)] px-6 bg-[var(--surface-2)]">
          <button
            type="button"
            (click)="activeTab = 'profile'"
            class="py-3 px-4 text-xs font-semibold border-b-2 transition-colors cursor-pointer"
            [ngClass]="activeTab === 'profile' ? 'border-primary text-primary-light' : 'border-transparent text-[var(--text-secondary)] hover:text-white'"
          >
            👤 Mi Perfil
          </button>
          <button
            type="button"
            (click)="activeTab = 'password'"
            class="py-3 px-4 text-xs font-semibold border-b-2 transition-colors cursor-pointer"
            [ngClass]="activeTab === 'password' ? 'border-primary text-primary-light' : 'border-transparent text-[var(--text-secondary)] hover:text-white'"
          >
            🔑 Cambiar Contraseña
          </button>
          <button
            type="button"
            (click)="loadSessions(); activeTab = 'sessions'"
            class="py-3 px-4 text-xs font-semibold border-b-2 transition-colors cursor-pointer"
            [ngClass]="activeTab === 'sessions' ? 'border-primary text-primary-light' : 'border-transparent text-[var(--text-secondary)] hover:text-white'"
          >
            💻 Sesiones Activas
          </button>
        </div>

        <!-- Tab 1: Profile -->
        <div *ngIf="activeTab === 'profile'" class="p-6 overflow-y-auto space-y-4">
          <div>
            <label class="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Nombre Completo</label>
            <input
              type="text"
              [(ngModel)]="profileName"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
              placeholder="Tu nombre"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--text-secondary)] mb-1">URL de Avatar (Opcional)</label>
            <input
              type="url"
              [(ngModel)]="profileAvatar"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
              placeholder="https://ejemplo.com/avatar.png"
            />
          </div>

          <div class="pt-2 flex justify-end">
            <button
              type="button"
              (click)="saveProfile()"
              [disabled]="isSavingProfile"
              class="px-5 py-2 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-md transition-colors cursor-pointer"
            >
              {{ isSavingProfile ? 'Guardando...' : 'Guardar Cambios' }}
            </button>
          </div>
        </div>

        <!-- Tab 2: Password -->
        <div *ngIf="activeTab === 'password'" class="p-6 overflow-y-auto space-y-4">
          <div>
            <label class="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Contraseña Actual</label>
            <input
              type="password"
              [(ngModel)]="oldPassword"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Nueva Contraseña (mínimo 6 caracteres)</label>
            <input
              type="password"
              [(ngModel)]="newPassword"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Confirmar Nueva Contraseña</label>
            <input
              type="password"
              [(ngModel)]="confirmPassword"
              class="w-full px-3 py-2 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl text-white text-sm focus:outline-hidden focus:border-primary"
              placeholder="••••••••"
            />
          </div>

          <div class="pt-2 flex justify-end">
            <button
              type="button"
              (click)="savePassword()"
              [disabled]="isSavingPassword"
              class="px-5 py-2 bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-md transition-colors cursor-pointer"
            >
              {{ isSavingPassword ? 'Actualizando...' : 'Cambiar Contraseña' }}
            </button>
          </div>
        </div>

        <!-- Tab 3: Active Sessions -->
        <div *ngIf="activeTab === 'sessions'" class="p-6 overflow-y-auto space-y-4">
          <div class="flex items-center justify-between mb-2">
            <p class="text-xs text-[var(--text-secondary)]">
              Dispositivos donde has iniciado sesión recientemente:
            </p>
            <button
              type="button"
              (click)="logoutAll()"
              class="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
            >
              Cerrar en todos los dispositivos
            </button>
          </div>

          <app-page-state
            *ngIf="isLoadingSessions"
            state="loading"
            message="Consultando sesiones activas..."
          ></app-page-state>

          <app-page-state
            *ngIf="!isLoadingSessions && sessions.length === 0"
            state="empty"
            title="Sin sesiones adicionales"
            message="Solo tienes tu sesión actual en uso."
            emptyIcon="💻"
          ></app-page-state>

          <div *ngIf="!isLoadingSessions && sessions.length > 0" class="divide-y divide-[var(--border)] border border-[var(--border)] rounded-xl overflow-hidden">
            <div *ngFor="let s of sessions" class="p-3 bg-[var(--surface-1)] flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="text-xl">🖥️</span>
                <div>
                  <p class="text-xs font-bold text-white">{{ s.device_info || 'Dispositivo Web' }}</p>
                  <p class="text-[11px] text-[var(--text-secondary)]">IP: {{ s.ip_address || '127.0.0.1' }}</p>
                </div>
              </div>
              <span class="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                Activa
              </span>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="px-6 py-3 border-t border-[var(--border)] bg-[var(--surface-3)] flex items-center justify-between">
          <button
            type="button"
            (click)="logoutCurrent()"
            class="text-xs font-semibold text-rose-400 hover:text-rose-300 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>🚪</span>
            <span>Cerrar sesión actual</span>
          </button>
          <button
            type="button"
            (click)="close.emit()"
            class="px-4 py-1.5 bg-[var(--surface-2)] hover:bg-[var(--surface-4)] text-[var(--text-secondary)] hover:text-white rounded-xl text-xs font-medium transition-colors cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  `
})
export class UserMenuModalComponent implements OnInit {
  @Output() close = new EventEmitter<void>();

  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmDialogService);

  currentUser = this.authService.getCurrentUser();
  activeTab: 'profile' | 'password' | 'sessions' = 'profile';

  profileName = '';
  profileAvatar = '';
  isSavingProfile = false;

  oldPassword = '';
  newPassword = '';
  confirmPassword = '';
  isSavingPassword = false;

  sessions: any[] = [];
  isLoadingSessions = false;

  ngOnInit(): void {
    if (this.currentUser) {
      this.profileName = this.currentUser.name || '';
      this.profileAvatar = this.currentUser.avatar_url || '';
    }
  }

  getInitials(name: string): string {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  }

  getRoleLabel(role: string): string {
    const labels: Record<string, string> = {
      'admin': 'Administrador',
      'scrum_master': 'Scrum Master',
      'dev': 'Desarrollador'
    };
    return labels[role] || role;
  }

  saveProfile(): void {
    if (!this.profileName.trim()) {
      this.toastService.error('El nombre no puede estar vacío');
      return;
    }
    this.isSavingProfile = true;
    this.authService.updateProfile({
      name: this.profileName.trim(),
      avatar_url: this.profileAvatar.trim() || undefined
    }).subscribe({
      next: () => {
        this.isSavingProfile = false;
        this.currentUser = this.authService.getCurrentUser();
        this.toastService.success('Perfil actualizado correctamente');
      },
      error: (err) => {
        this.isSavingProfile = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al actualizar perfil');
      }
    });
  }

  savePassword(): void {
    if (!this.oldPassword) {
      this.toastService.error('Ingresa tu contraseña actual');
      return;
    }
    if (this.newPassword.length < 6) {
      this.toastService.error('La nueva contraseña debe tener al menos 6 caracteres');
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      this.toastService.error('Las nuevas contraseñas no coinciden');
      return;
    }

    this.isSavingPassword = true;
    this.authService.changePassword({
      old_password: this.oldPassword,
      new_password: this.newPassword
    }).subscribe({
      next: () => {
        this.isSavingPassword = false;
        this.oldPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
        this.toastService.success('Contraseña cambiada exitosamente');
      },
      error: (err) => {
        this.isSavingPassword = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al cambiar contraseña');
      }
    });
  }

  loadSessions(): void {
    this.isLoadingSessions = true;
    this.authService.getSessions().subscribe({
      next: (res) => {
        this.isLoadingSessions = false;
        this.sessions = res.data || [];
      },
      error: () => {
        this.isLoadingSessions = false;
        this.sessions = [];
      }
    });
  }

  async logoutAll(): Promise<void> {
    const confirmed = await this.confirmService.confirm({
      title: '¿Cerrar todas las sesiones?',
      message: 'Se cerrará la sesión en todos los demás dispositivos y navegadores.',
      confirmText: 'Cerrar en todos',
      danger: true
    });
    if (!confirmed) return;

    this.authService.logoutAll().subscribe({
      next: () => {
        this.toastService.success('Sesiones cerradas en todos los dispositivos');
        this.loadSessions();
      },
      error: () => {
        this.toastService.error('Error al cerrar todas las sesiones');
      }
    });
  }

  logoutCurrent(): void {
    this.close.emit();
    this.authService.logout();
  }
}
