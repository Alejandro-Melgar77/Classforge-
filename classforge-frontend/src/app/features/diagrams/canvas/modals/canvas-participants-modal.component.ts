import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, inject, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiagramParticipantsResponse } from '../../models/diagram.model';
import { DiagramService } from '../../services/diagram.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-canvas-participants-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="isOpen" 
         class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
         role="dialog"
         aria-modal="true"
         aria-labelledby="participants-modal-title">
      
      <div class="w-full max-w-md bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div class="px-5 py-4 bg-[var(--surface-1)] border-b border-[var(--border)] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <span class="text-lg">👥</span>
            <div>
              <h2 class="font-bold text-sm text-white" id="participants-modal-title">Participantes / Editores</h2>
              <p class="text-[11px] text-[var(--text-secondary)]">
                {{ participantsData?.team_name ? 'Equipo: ' + participantsData?.team_name : 'Asigna desarrolladores para colaborar en tiempo real' }}
              </p>
            </div>
          </div>
          <button (click)="close.emit()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-[var(--surface-3)]" aria-label="Cerrar modal">✕</button>
        </div>

        <div class="p-5 flex flex-col gap-3 overflow-y-auto custom-scrollbar">
          <div *ngIf="isLoading" class="flex flex-col items-center justify-center py-10 gap-2">
            <div class="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
            <span class="text-xs text-[var(--text-secondary)]">Cargando participantes...</span>
          </div>

          <div *ngIf="!isLoading && (!participantsData?.available_members || participantsData?.available_members?.length === 0)" class="text-center py-8 text-xs text-slate-400">
            No hay desarrolladores disponibles en este equipo.
          </div>

          <div *ngIf="!isLoading && (participantsData?.available_members?.length || 0) > 0" class="flex flex-col gap-2">
            <div *ngFor="let m of participantsData?.available_members"
                 (click)="toggleParticipant(m.id)"
                 class="p-2.5 bg-[var(--surface-1)] hover:bg-[var(--surface-3)] border border-[var(--border)] rounded-xl flex items-center justify-between gap-3 cursor-pointer transition-colors"
                 [class.border-blue-500]="selectedParticipantIds.has(m.id)">
              
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-full bg-blue-600/30 text-blue-300 border border-blue-500/40 flex items-center justify-center text-xs font-bold shrink-0">
                  {{ m.name.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <div class="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>{{ m.name }}</span>
                    <span class="text-[9px] px-1 py-0.2 rounded font-mono uppercase bg-slate-700/50 text-slate-300">{{ m.role }}</span>
                  </div>
                  <div class="text-[10px] text-slate-400">{{ m.email }}</div>
                </div>
              </div>

              <input type="checkbox" [checked]="selectedParticipantIds.has(m.id)" 
                     (click)="$event.stopPropagation(); toggleParticipant(m.id)"
                     class="w-4 h-4 rounded text-blue-600 focus:ring-0 cursor-pointer"
                     [attr.aria-label]="'Asignar a ' + m.name">
            </div>
          </div>
        </div>

        <div class="px-5 py-3.5 bg-[var(--surface-1)] border-t border-[var(--border)] flex items-center justify-between">
          <span class="text-xs text-slate-400">{{ selectedParticipantIds.size }} seleccionados</span>
          <div class="flex items-center gap-2">
            <button (click)="close.emit()" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:bg-[var(--surface-3)] cursor-pointer">
              Cancelar
            </button>
            <button (click)="save()" [disabled]="isSaving"
                    class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-1.5 rounded-lg text-xs font-bold shadow-md flex items-center gap-1.5 cursor-pointer">
              <span *ngIf="isSaving" class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>Guardar</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CanvasParticipantsModalComponent {
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  @Input() set isOpen(open: boolean) {
    this._isOpen = open;
    if (open && this.diagramId) {
      this.loadParticipants();
    }
  }
  get isOpen() { return this._isOpen; }
  private _isOpen = false;

  @Input() diagramId!: string;
  @Output() updated = new EventEmitter<string[]>();
  @Output() close = new EventEmitter<void>();

  isLoading = false;
  isSaving = false;
  participantsData: DiagramParticipantsResponse | null = null;
  selectedParticipantIds = new Set<string>();

  loadParticipants() {
    this.isLoading = true;
    this.selectedParticipantIds.clear();

    this.diagramService.getParticipants(this.diagramId).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success && res.data) {
          this.participantsData = res.data;
          const assigned = res.data.assigned_member_ids || [];
          this.selectedParticipantIds = new Set(assigned);
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isLoading = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al obtener participantes');
        this.cdr.markForCheck();
      }
    });
  }

  toggleParticipant(id: string) {
    if (this.selectedParticipantIds.has(id)) {
      this.selectedParticipantIds.delete(id);
    } else {
      this.selectedParticipantIds.add(id);
    }
    this.cdr.markForCheck();
  }

  save() {
    this.isSaving = true;
    const memberIds = Array.from(this.selectedParticipantIds);

    this.diagramService.updateParticipants(this.diagramId, memberIds).subscribe({
      next: (res) => {
        this.isSaving = false;
        if (res.success) {
          this.toastService.success('Participantes actualizados exitosamente');
          this.updated.emit(memberIds);
          this.close.emit();
        } else {
          this.toastService.error(res.message || 'Error al actualizar participantes');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isSaving = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al guardar participantes');
        this.cdr.markForCheck();
      }
    });
  }
}
