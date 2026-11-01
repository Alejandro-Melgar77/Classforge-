import { Component, Output, EventEmitter, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ShortcutCategory {
  title: string;
  items: { key: string; description: string }[];
}

@Component({
  selector: 'app-shortcuts-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-dialog-title"
    >
      <div
        class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        (click)="$event.stopPropagation()"
      >
        <!-- Header -->
        <div class="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-3)]">
          <div class="flex items-center gap-2">
            <span class="text-xl">⌨️</span>
            <h2 id="shortcuts-dialog-title" class="text-base font-bold text-white">
              Atajos de Teclado Globales
            </h2>
          </div>
          <button
            type="button"
            (click)="close.emit()"
            class="text-[var(--text-secondary)] hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer text-sm"
            aria-label="Cerrar ayuda"
          >
            ✕
          </button>
        </div>

        <!-- Content -->
        <div class="p-6 overflow-y-auto space-y-6">
          <div *ngFor="let cat of categories">
            <h3 class="text-xs font-bold uppercase tracking-wider text-primary-light mb-3">
              {{ cat.title }}
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div
                *ngFor="let item of cat.items"
                class="flex items-center justify-between p-2.5 rounded-xl bg-[var(--surface-1)] border border-[var(--border)]"
              >
                <span class="text-xs text-[var(--text-secondary)]">{{ item.description }}</span>
                <kbd class="px-2 py-1 text-[11px] font-mono font-bold bg-[var(--surface-3)] text-white border border-[var(--border)] rounded-lg shadow-xs">
                  {{ item.key }}
                </kbd>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-6 py-3 border-t border-[var(--border)] bg-[var(--surface-3)] flex items-center justify-between text-xs text-[var(--text-muted)]">
          <span>Presiona <kbd class="px-1.5 py-0.5 bg-[var(--surface-2)] border border-[var(--border)] rounded font-mono text-[10px] text-white">Esc</kbd> o <kbd class="px-1.5 py-0.5 bg-[var(--surface-2)] border border-[var(--border)] rounded font-mono text-[10px] text-white">?</kbd> para cerrar</span>
          <button
            type="button"
            (click)="close.emit()"
            class="px-4 py-1.5 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-xl transition-colors cursor-pointer"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  `
})
export class ShortcutsDialogComponent {
  @Output() close = new EventEmitter<void>();

  @HostListener('window:keydown.escape')
  onEscape(): void {
    this.close.emit();
  }

  categories: ShortcutCategory[] = [
    {
      title: 'Navegación General',
      items: [
        { key: '?', description: 'Abrir / cerrar esta guía de atajos' },
        { key: 'Esc', description: 'Cerrar modal, panel o menú activo' },
        { key: 'Alt + D', description: 'Ir al Dashboard de inicio' },
        { key: 'Alt + P', description: 'Ir a Mis Proyectos' },
        { key: 'Alt + U', description: 'Ir a Galería de Diagramas' }
      ]
    },
    {
      title: 'Lienzo de Diagramas UML',
      items: [
        { key: 'Ctrl + S', description: 'Guardar cambios del diagrama' },
        { key: 'Ctrl + Z', description: 'Deshacer última acción' },
        { key: 'Ctrl + Y', description: 'Rehacer acción' },
        { key: 'Supr / Del', description: 'Eliminar elemento o relación seleccionada' },
        { key: 'Ctrl + C', description: 'Copiar elemento seleccionado' },
        { key: 'Ctrl + V', description: 'Pegar elemento' },
        { key: 'Espacio + Arrastre', description: 'Paneo libre del lienzo' }
      ]
    },
    {
      title: 'Asistente y Equipo IA',
      items: [
        { key: 'Alt + I', description: 'Abrir / colapsar Drawer de Equipo IA' },
        { key: 'Ctrl + Enter', description: 'Enviar orden de modelado en consola' }
      ]
    }
  ];
}
