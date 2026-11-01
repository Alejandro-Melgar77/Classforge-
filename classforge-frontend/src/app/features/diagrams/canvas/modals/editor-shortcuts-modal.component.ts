import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-editor-shortcuts-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="isOpen" 
         class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150"
         role="dialog"
         aria-modal="true"
         aria-labelledby="shortcuts-modal-title">
      <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4" (click)="$event.stopPropagation()">
        
        <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
          <div class="flex items-center gap-2">
            <span class="text-xl">⌨️</span>
            <h3 class="text-base font-bold text-white" id="shortcuts-modal-title">Atajos de Teclado del Editor</h3>
          </div>
          <button (click)="close.emit()" class="text-[var(--text-secondary)] hover:text-white cursor-pointer" aria-label="Cerrar ventana de atajos">✕</button>
        </div>

        <div class="space-y-4 text-xs max-h-80 overflow-y-auto custom-scrollbar pr-1">
          <!-- Navegación & Selección -->
          <div>
            <h4 class="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2">Navegación & Selección</h4>
            <div class="grid grid-cols-2 gap-2">
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Saltar entre clases</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Tab / Shift+Tab</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Mover nodo seleccionado</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Flechas (↑ ↓ ← →)</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Desplazamiento rápido</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Shift + Flechas</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Seleccionar todo</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Ctrl + A</kbd>
              </div>
            </div>
          </div>

          <!-- Lienzo, Zoom & Pan -->
          <div>
            <h4 class="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2">Lienzo & Zoom</h4>
            <div class="grid grid-cols-2 gap-2">
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Ajustar a pantalla</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">F</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Pan / Desplazar lienzo</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Espacio + Arrastre</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Pan con teclado</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Alt + Flechas</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Zoom +/-</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Ctrl + Rueda / + -</kbd>
              </div>
            </div>
          </div>

          <!-- Edición & Guardado -->
          <div>
            <h4 class="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-2">Edición & Historial</h4>
            <div class="grid grid-cols-2 gap-2">
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Guardar ahora</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Ctrl + S</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Deshacer</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Ctrl + Z</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Rehacer</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Ctrl + Y / Ctrl+Shift+Z</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Eliminar seleccionado</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Supr / Backspace</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Cancelar / Deseleccionar</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">Escape</kbd>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-[var(--surface-1)] border border-[var(--border)]">
                <span class="text-slate-300">Ayuda de atajos</span>
                <kbd class="px-2 py-0.5 rounded bg-[var(--surface-3)] text-amber-300 font-mono text-[10px]">?</kbd>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end pt-2 border-t border-[var(--border)]">
          <button (click)="close.emit()" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold cursor-pointer">
            Entendido
          </button>
        </div>

      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EditorShortcutsModalComponent {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
}
