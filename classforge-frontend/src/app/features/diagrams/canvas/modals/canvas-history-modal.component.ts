import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Diagram } from '../../models/diagram.model';
import { DiagramService } from '../../services/diagram.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../../core/services/confirm-dialog.service';

@Component({
  selector: 'app-canvas-history-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="isOpen" 
         class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in"
         role="dialog"
         aria-modal="true"
         aria-labelledby="history-modal-title">
      <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4" (click)="$event.stopPropagation()">
        
        <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
          <div class="flex items-center gap-2">
            <span class="text-xl">📜</span>
            <h3 class="text-base font-bold text-white" id="history-modal-title">Historial de Versiones</h3>
          </div>
          <button (click)="close.emit()" class="text-[var(--text-secondary)] hover:text-white cursor-pointer" aria-label="Cerrar modal de historial">✕</button>
        </div>

        <div *ngIf="isLoading" class="py-8 text-center text-xs text-[var(--text-secondary)] flex flex-col items-center gap-2">
          <div class="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
          <span>Cargando historial de versiones...</span>
        </div>

        <div *ngIf="!isLoading && history.length === 0" class="py-8 text-center text-xs text-[var(--text-secondary)]">
          No hay versiones previas registradas para este diagrama.
        </div>

        <div *ngIf="!isLoading && history.length > 0" class="max-h-72 overflow-y-auto divide-y divide-[var(--border)] border border-[var(--border)] rounded-xl">
          <div *ngFor="let h of history" class="p-3 flex items-center justify-between bg-[var(--surface-1)] hover:bg-[var(--surface-3)] transition-colors">
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-primary/20 text-primary-light font-bold">
                  v{{ h.version }}
                </span>
                <span class="text-xs font-semibold text-white">{{ h.comment || 'Guardado automático' }}</span>
              </div>
              <p class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ formatDate(h.saved_at) }}</p>
            </div>
            
            <button (click)="restore(h.version)" 
                    class="px-2.5 py-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                    [title]="'Restaurar diagrama a versión ' + h.version"
                    [attr.aria-label]="'Restaurar a versión ' + h.version">
              Restaurar
            </button>
          </div>
        </div>

        <div class="flex justify-end pt-2">
          <button (click)="close.emit()" class="px-4 py-2 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-[var(--text-secondary)] hover:text-white rounded-xl text-xs font-medium transition-colors cursor-pointer">
            Cerrar
          </button>
        </div>

      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CanvasHistoryModalComponent {
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmDialogService);
  private cdr = inject(ChangeDetectorRef);

  @Input() set isOpen(open: boolean) {
    this._isOpen = open;
    if (open && this.diagramId) {
      this.loadHistory();
    }
  }
  get isOpen() { return this._isOpen; }
  private _isOpen = false;

  @Input() diagramId!: string;
  @Output() versionRestored = new EventEmitter<Diagram>();
  @Output() close = new EventEmitter<void>();

  isLoading = false;
  history: any[] = [];

  loadHistory() {
    this.isLoading = true;
    this.history = [];
    this.diagramService.getHistory(this.diagramId).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.history = res.data || [];
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading = false;
        this.toastService.error('Error al cargar historial de versiones');
        this.cdr.markForCheck();
      }
    });
  }

  async restore(version: number) {
    const confirmed = await this.confirmService.confirm({
      title: `¿Restaurar a versión ${version}?`,
      message: 'Se reemplazará el lienzo actual con el estado guardado de esta versión. Esta acción creará una nueva entrada en el historial.',
      confirmText: 'Restaurar Versión',
      danger: true
    });
    if (!confirmed) return;

    this.diagramService.restoreVersion(this.diagramId, version).subscribe({
      next: (res) => {
        this.toastService.success(`Diagrama restaurado a versión ${version}`);
        this.close.emit();
        if (res.data) {
          this.versionRestored.emit(res.data);
        }
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || err.message || 'Error al restaurar versión');
      }
    });
  }

  formatDate(dateStr?: string): string {
    if (!dateStr) return '—';
    try {
      return new Intl.DateTimeFormat('es-ES', { 
        day: '2-digit', 
        month: '2-digit', 
        year: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  }
}
