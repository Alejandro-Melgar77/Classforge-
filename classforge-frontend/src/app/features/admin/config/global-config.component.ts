import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface SystemConfig {
  appName: string;
  allowRegistration: boolean;
  defaultRole: string;
  sessionTimeoutMinutes: number;
  autoSaveIntervalMs: number;
  heartbeatIntervalSeconds: number;
  maxDiagramsPerUser: number;
  canvasGridType: 'mesh' | 'dot' | 'fixedDot';
  enableSnapToGrid: boolean;
  enableCollaborationCursorTracking: boolean;
}

const DEFAULT_CONFIG: SystemConfig = {
  appName: 'ClassForge UML Modeler',
  allowRegistration: true,
  defaultRole: 'developer',
  sessionTimeoutMinutes: 120,
  autoSaveIntervalMs: 3000,
  heartbeatIntervalSeconds: 15,
  maxDiagramsPerUser: 50,
  canvasGridType: 'mesh',
  enableSnapToGrid: true,
  enableCollaborationCursorTracking: true
};

@Component({
  selector: 'app-global-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-6 max-w-4xl">
      <!-- Success / Status Toast -->
      @if (savedToast) {
        <div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between text-emerald-400 animate-fade-in">
          <div class="flex items-center gap-2 text-sm font-medium">
            <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span>Configuración del sistema actualizada correctamente.</span>
          </div>
          <button (click)="savedToast = false" class="text-emerald-400/60 hover:text-emerald-300">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      }

      <!-- System General Settings -->
      <div class="p-6 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl space-y-4">
        <h2 class="text-base font-semibold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-[var(--primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          General de la Plataforma
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1">Nombre de la Aplicación</label>
            <input type="text" [(ngModel)]="config.appName"
                   class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--primary)]" />
          </div>

          <div>
            <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1">Rol por Defecto para Nuevos Registros</label>
            <select [(ngModel)]="config.defaultRole"
                    class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--primary)]">
              <option value="developer">Developer (Desarrollador)</option>
              <option value="scrum_master">Scrum Master</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-[var(--border)]">
          <div>
            <p class="text-sm font-medium text-white">Permitir Registro Público</p>
            <p class="text-xs text-[var(--text-muted)]">Los usuarios pueden crear cuentas nuevas sin invitación previa de un administrador.</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" [(ngModel)]="config.allowRegistration" class="sr-only peer">
            <div class="w-11 h-6 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--primary)]"></div>
          </label>
        </div>
      </div>

      <!-- Realtime Collaboration Settings -->
      <div class="p-6 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl space-y-4">
        <h2 class="text-base font-semibold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Motor Colaborativo en Tiempo Real (WebSockets)
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1">Intervalo de Autoguardado (ms)</label>
            <input type="number" [(ngModel)]="config.autoSaveIntervalMs" min="1000" step="500"
                   class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--primary)]" />
            <span class="text-[10px] text-[var(--text-muted)]">Tiempo de debounce antes de sincronizar el estado del lienzo con MongoDB.</span>
          </div>

          <div>
            <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1">Heartbeat / Ping WebSocket (seg)</label>
            <input type="number" [(ngModel)]="config.heartbeatIntervalSeconds" min="5" max="60"
                   class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--primary)]" />
            <span class="text-[10px] text-[var(--text-muted)]">Frecuencia de comprobación de conexión activa de los colaboradores.</span>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-[var(--border)]">
          <div>
            <p class="text-sm font-medium text-white">Sincronización de Cursores en Vivo</p>
            <p class="text-xs text-[var(--text-muted)]">Muestra los punteros y nombres de los participantes conectados en el lienzo en tiempo real.</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" [(ngModel)]="config.enableCollaborationCursorTracking" class="sr-only peer">
            <div class="w-11 h-6 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--primary)]"></div>
          </label>
        </div>
      </div>

      <!-- Canvas & Editor Defaults -->
      <div class="p-6 bg-[var(--surface-1)] border border-[var(--border)] rounded-xl space-y-4">
        <h2 class="text-base font-semibold text-white flex items-center gap-2">
          <svg class="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
          Lienzo de Diagramación (AntV X6)
        </h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1">Patrón de Cuadrícula</label>
            <select [(ngModel)]="config.canvasGridType"
                    class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--primary)]">
              <option value="mesh">Malla (Mesh)</option>
              <option value="dot">Puntos (Dot)</option>
              <option value="fixedDot">Puntos Fijos (Fixed Dot)</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1">Alineación Magnética (Snap to Grid)</label>
            <div class="pt-2">
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" [(ngModel)]="config.enableSnapToGrid" class="sr-only peer">
                <div class="w-11 h-6 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--primary)]"></div>
                <span class="ml-3 text-xs text-[var(--text-secondary)]">Alinear elementos a la cuadrícula automáticamente</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-end gap-3 pt-4">
        <button type="button" (click)="resetDefaults()"
                class="px-4 py-2 border border-[var(--border)] text-xs font-medium text-[var(--text-secondary)] hover:text-white rounded-lg hover:bg-[var(--surface-2)] transition-colors">
          Restaurar Valores por Defecto
        </button>
        <button type="button" (click)="saveConfig()"
                class="px-5 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-1.5">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          Guardar Configuración
        </button>
      </div>
    </div>
  `
})
export class GlobalConfigComponent implements OnInit {
  config: SystemConfig = { ...DEFAULT_CONFIG };
  savedToast = false;

  ngOnInit(): void {
    const saved = localStorage.getItem('classforge_global_config');
    if (saved) {
      try {
        this.config = { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      } catch {
        this.config = { ...DEFAULT_CONFIG };
      }
    }
  }

  saveConfig(): void {
    localStorage.setItem('classforge_global_config', JSON.stringify(this.config));
    this.savedToast = true;
    setTimeout(() => {
      this.savedToast = false;
    }, 4000);
  }

  resetDefaults(): void {
    this.config = { ...DEFAULT_CONFIG };
    this.saveConfig();
  }
}
