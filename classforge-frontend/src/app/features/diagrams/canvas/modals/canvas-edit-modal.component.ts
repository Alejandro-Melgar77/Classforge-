import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Diagram } from '../../models/diagram.model';
import { DiagramService } from '../../services/diagram.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-canvas-edit-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="isOpen" 
         class="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
         role="dialog"
         aria-modal="true"
         aria-labelledby="canvas-edit-title">
      
      <div class="w-full max-w-md bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div class="px-5 py-4 bg-[var(--surface-1)] border-b border-[var(--border)] flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-lg">✏️</span>
            <h2 class="font-bold text-sm text-white" id="canvas-edit-title">Editar Nombre & Logo de la Empresa</h2>
          </div>
          <button (click)="close.emit()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-[var(--surface-3)]" aria-label="Cerrar modal">✕</button>
        </div>

        <div class="p-5 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
          <!-- Nombre -->
          <div>
            <label for="canvas-name-field" class="text-xs font-bold text-slate-300 block mb-1">Nombre del Diagrama / Empresa <span class="text-red-400">*</span></label>
            <input id="canvas-name-field" type="text" [(ngModel)]="form.name" placeholder="ej. Veterinaria PeloSuave"
                   class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-[var(--primary)] font-medium">
          </div>

          <!-- Logo Upload -->
          <div class="p-3.5 bg-[var(--surface-1)] rounded-xl border border-[var(--border)]">
            <label class="text-xs font-bold text-slate-300 block mb-2">Logo Corporativo</label>
            <div class="flex items-center gap-4">
              <div class="w-16 h-16 rounded-xl bg-[var(--surface-3)] border border-[var(--border)] flex items-center justify-center overflow-hidden shrink-0">
                <img *ngIf="logoPreview" [src]="logoPreview" class="w-full h-full object-contain p-1" alt="Logo de empresa">
                <span *ngIf="!logoPreview" class="text-xl text-slate-500">🏢</span>
              </div>

              <div class="flex-1 flex flex-col gap-2">
                <label class="bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-colors inline-flex items-center gap-1.5 shadow-xs w-fit">
                  <span>📁</span> Seleccionar Logo
                  <input type="file" (change)="onFileSelected($event)" accept="image/*" class="hidden">
                </label>
                <button *ngIf="logoPreview" (click)="removeLogo()" class="text-xs text-red-400 hover:text-red-300 w-fit cursor-pointer">
                  Quitar logo
                </button>
              </div>
            </div>
          </div>

          <!-- Descripción -->
          <div>
            <label for="canvas-desc-field" class="text-xs font-bold text-slate-300 block mb-1">Descripción</label>
            <textarea id="canvas-desc-field" [(ngModel)]="form.description" rows="2"
                      class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg p-2 text-xs text-white outline-none focus:border-[var(--primary)]"></textarea>
          </div>
        </div>

        <div class="px-5 py-3.5 bg-[var(--surface-1)] border-t border-[var(--border)] flex items-center justify-end gap-2">
          <button (click)="close.emit()" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:bg-[var(--surface-3)] cursor-pointer">
            Cancelar
          </button>
          <button (click)="save()" [disabled]="isSaving || !form.name.trim()"
                  class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-1.5 rounded-lg text-xs font-bold shadow-md flex items-center gap-1.5 cursor-pointer">
            <span *ngIf="isSaving" class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>Guardar Cambios</span>
          </button>
        </div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CanvasEditModalComponent {
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  @Input() isOpen = false;
  @Input() diagramId!: string;
  @Input() set diagram(d: Diagram | null) {
    if (d) {
      this.form = {
        name: d.name || '',
        description: d.description || '',
        image_url: d.image_url || null
      };
      this.logoPreview = d.image_url || null;
    }
  }

  @Output() saved = new EventEmitter<{ name: string; description?: string; image_url: string | null }>();
  @Output() close = new EventEmitter<void>();

  form = {
    name: '',
    description: '',
    image_url: '' as string | null
  };
  logoPreview: string | null = null;
  isSaving = false;

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      if (file.size > 3 * 1024 * 1024) {
        this.toastService.warning('La imagen no debe superar los 3MB.');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        this.form.image_url = base64;
        this.logoPreview = base64;
        this.cdr.markForCheck();
      };
      reader.readAsDataURL(file);
    }
  }

  removeLogo() {
    this.form.image_url = null;
    this.logoPreview = null;
    this.cdr.markForCheck();
  }

  save() {
    if (!this.diagramId || !this.form.name.trim()) return;
    this.isSaving = true;

    this.diagramService.updateDiagram(this.diagramId, {
      name: this.form.name.trim(),
      description: this.form.description?.trim(),
      image_url: this.form.image_url
    }).subscribe({
      next: (res) => {
        this.isSaving = false;
        if (res.success && res.data) {
          this.toastService.success('Diagrama actualizado correctamente');
          this.saved.emit({
            name: res.data.name,
            description: res.data.description,
            image_url: res.data.image_url ?? null
          });
          this.close.emit();
        } else {
          this.toastService.error(res.message || 'Error al actualizar diagrama');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isSaving = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al actualizar diagrama');
        this.cdr.markForCheck();
      }
    });
  }
}
