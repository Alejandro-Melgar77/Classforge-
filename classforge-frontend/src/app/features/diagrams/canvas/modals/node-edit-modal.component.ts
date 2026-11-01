import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UMLNodeData, NodeType, UMLAttribute, UMLMethod, Visibility } from '../../models/diagram.model';

@Component({
  selector: 'app-node-edit-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="isOpen" 
         class="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
         role="dialog" 
         aria-modal="true" 
         aria-labelledby="node-edit-title">
      
      <div class="w-full max-w-lg bg-[var(--surface-2)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
        
        <!-- Header -->
        <div class="h-12 px-4 border-b border-[var(--border)] bg-[var(--surface-1)] flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2 font-bold text-sm text-white" id="node-edit-title">
            <span>✏️</span>
            <span>Editar Elemento UML: <span class="text-blue-400">{{ localData.name }}</span></span>
          </div>
          <button (click)="close.emit()" 
                  class="text-[var(--text-secondary)] hover:text-white p-1 rounded hover:bg-[var(--surface-3)] transition-colors cursor-pointer"
                  aria-label="Cerrar editor de elemento">
            ✕
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-4 custom-scrollbar flex flex-col gap-4">
          <!-- Clasificador Info -->
          <div class="grid grid-cols-2 gap-3 p-3 bg-[var(--surface-1)] rounded-lg border border-[var(--border)]">
            <div>
              <label for="node-name-input" class="text-[11px] font-semibold text-[var(--text-secondary)] mb-1 block">Nombre de la Clase</label>
              <input id="node-name-input" type="text" [(ngModel)]="localData.name" class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded px-2 py-1 text-xs text-white focus:border-[var(--primary)] outline-none font-medium">
            </div>
            <div>
              <label for="node-type-select" class="text-[11px] font-semibold text-[var(--text-secondary)] mb-1 block">Tipo de Elemento</label>
              <select id="node-type-select" [(ngModel)]="localType" class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded px-2 py-1 text-xs text-white focus:border-[var(--primary)] outline-none">
                <option value="class">Clase (Class)</option>
                <option value="interface">Interfaz («interface»)</option>
                <option value="abstract">Clase Abstracta (Abstract)</option>
                <option value="enum">Enumeración («enum»)</option>
                <option value="package">Paquete (Package)</option>
                <option value="note">Nota / Comentario</option>
              </select>
            </div>
            <div class="col-span-2">
              <label for="node-stereotype-input" class="text-[11px] font-semibold text-[var(--text-secondary)] mb-1 block">Estereotipo (opcional)</label>
              <input id="node-stereotype-input" type="text" [(ngModel)]="localData.stereotype" placeholder="ej. entity, service, repository, DTO" class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded px-2 py-1 text-xs text-white focus:border-[var(--primary)] outline-none">
            </div>
          </div>

          <!-- Atributos UML -->
          <div *ngIf="localType !== 'note' && localType !== 'package'" class="border border-[var(--border)] rounded-lg bg-[var(--surface-1)] overflow-hidden">
            <div class="px-3 py-2 bg-[var(--surface-3)]/60 border-b border-[var(--border)] flex items-center justify-between">
              <span class="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Atributos ({{ localData.attributes.length }})
              </span>
              <button (click)="addAttribute()" class="px-2 py-1 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 border border-blue-500/40 rounded text-[11px] font-semibold flex items-center gap-1 cursor-pointer">
                + Añadir Atributo
              </button>
            </div>

            <div class="p-2 flex flex-col gap-2">
              <div *ngFor="let attr of localData.attributes; let i = index" class="p-2 bg-[var(--surface-2)] rounded border border-[var(--border)]/70 flex flex-col gap-2">
                <div class="flex items-center gap-1.5">
                  <select [(ngModel)]="attr.visibility" class="w-24 bg-[var(--surface-3)] border border-[var(--border)] rounded px-1 py-1 text-xs font-mono text-white" aria-label="Visibilidad del atributo">
                    <option *ngFor="let v of visibilityOptions" [value]="v.value">{{ v.label }}</option>
                  </select>
                  <input type="text" [(ngModel)]="attr.name" placeholder="nombreAtributo" class="flex-1 bg-[var(--surface-3)] border border-[var(--border)] rounded px-2 py-1 text-xs text-white font-mono" aria-label="Nombre del atributo">
                  <button (click)="removeAttribute(i)" class="text-red-400 hover:text-red-300 p-1 hover:bg-red-400/10 rounded cursor-pointer" title="Eliminar atributo" aria-label="Eliminar atributo">
                    ✕
                  </button>
                </div>

                <div class="flex items-center gap-2">
                  <input type="text" [(ngModel)]="attr.type" placeholder="Tipo (String, Long...)" class="flex-1 bg-[var(--surface-3)] border border-[var(--border)] rounded px-2 py-1 text-xs text-sky-400 font-mono" aria-label="Tipo de dato">
                  <input type="text" [(ngModel)]="attr.default_value" placeholder="Valor por defecto" class="w-32 bg-[var(--surface-3)] border border-[var(--border)] rounded px-2 py-1 text-xs text-emerald-400 font-mono" aria-label="Valor por defecto">
                  <label class="flex items-center gap-1 text-[11px] text-slate-300 cursor-pointer">
                    <input type="checkbox" [(ngModel)]="attr.is_static" class="rounded"> Static
                  </label>
                </div>
              </div>

              <div *ngIf="localData.attributes.length === 0" class="text-center py-3 text-xs text-[var(--text-muted)] italic">
                No hay atributos añadidos. Clic en "+ Añadir Atributo" para crear uno.
              </div>
            </div>
          </div>

          <!-- Métodos / Operaciones UML -->
          <div *ngIf="localType !== 'note' && localType !== 'package'" class="border border-[var(--border)] rounded-lg bg-[var(--surface-1)] overflow-hidden">
            <div class="px-3 py-2 bg-[var(--surface-3)]/60 border-b border-[var(--border)] flex items-center justify-between">
              <span class="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Métodos / Operaciones ({{ localData.methods.length }})
              </span>
              <button (click)="addMethod()" class="px-2 py-1 bg-blue-600/30 text-blue-400 hover:bg-blue-600/50 border border-blue-500/40 rounded text-[11px] font-semibold flex items-center gap-1 cursor-pointer">
                + Añadir Método
              </button>
            </div>

            <div class="p-2 flex flex-col gap-2">
              <div *ngFor="let m of localData.methods; let i = index" class="p-2 bg-[var(--surface-2)] rounded border border-[var(--border)]/70 flex flex-col gap-2">
                <div class="flex items-center gap-1.5">
                  <select [(ngModel)]="m.visibility" class="w-24 bg-[var(--surface-3)] border border-[var(--border)] rounded px-1 py-1 text-xs font-mono text-white" aria-label="Visibilidad del método">
                    <option *ngFor="let v of visibilityOptions" [value]="v.value">{{ v.label }}</option>
                  </select>
                  <input type="text" [(ngModel)]="m.name" placeholder="nombreMetodo" class="flex-1 bg-[var(--surface-3)] border border-[var(--border)] rounded px-2 py-1 text-xs text-white font-mono" aria-label="Nombre del método">
                  <button (click)="removeMethod(i)" class="text-red-400 hover:text-red-300 p-1 hover:bg-red-400/10 rounded cursor-pointer" title="Eliminar método" aria-label="Eliminar método">
                    ✕
                  </button>
                </div>

                <div class="flex items-center gap-2">
                  <input type="text" [(ngModel)]="m.params" placeholder="parámetros ej: id: Long" class="flex-1 bg-[var(--surface-3)] border border-[var(--border)] rounded px-2 py-1 text-xs text-slate-300 font-mono" aria-label="Parámetros del método">
                  <input type="text" [(ngModel)]="m.return_type" placeholder="Retorno ej: void" class="w-28 bg-[var(--surface-3)] border border-[var(--border)] rounded px-2 py-1 text-xs text-sky-400 font-mono" aria-label="Tipo de retorno">
                  <label class="flex items-center gap-1 text-[11px] text-slate-300 cursor-pointer">
                    <input type="checkbox" [(ngModel)]="m.is_static" class="rounded"> Static
                  </label>
                  <label class="flex items-center gap-1 text-[11px] text-purple-300 cursor-pointer">
                    <input type="checkbox" [(ngModel)]="m.is_abstract" class="rounded"> Abstract
                  </label>
                </div>
              </div>

              <div *ngIf="localData.methods.length === 0" class="text-center py-3 text-xs text-[var(--text-muted)] italic">
                No hay métodos añadidos. Clic en "+ Añadir Método" para crear uno.
              </div>
            </div>
          </div>

          <!-- Nota -->
          <div *ngIf="localType === 'note'" class="p-3 bg-[var(--surface-1)] rounded-lg border border-[var(--border)]">
            <label for="node-notes-textarea" class="text-[11px] font-semibold text-[var(--text-secondary)] mb-1 block">Contenido de la Nota</label>
            <textarea id="node-notes-textarea" [(ngModel)]="localData.notes" rows="4" class="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded p-2 text-xs text-white focus:border-[var(--primary)] outline-none"></textarea>
          </div>
        </div>

        <!-- Footer -->
        <div class="h-14 px-4 border-t border-[var(--border)] bg-[var(--surface-1)] flex items-center justify-end gap-2 shrink-0">
          <button (click)="close.emit()" class="px-4 py-1.5 rounded text-xs font-semibold text-slate-300 hover:bg-[var(--surface-3)] transition-colors cursor-pointer">
            Cancelar
          </button>
          <button (click)="onSave()" class="px-5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-bold shadow-lg transition-colors cursor-pointer flex items-center gap-1.5">
            <span>✓</span> Guardar Cambios
          </button>
        </div>

      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NodeEditModalComponent {
  @Input() isOpen = false;
  @Input() set nodeData(val: UMLNodeData) {
    if (val) {
      this.localData = {
        name: val.name || 'Clase',
        stereotype: val.stereotype || null,
        attributes: Array.isArray(val.attributes) ? JSON.parse(JSON.stringify(val.attributes)) : [],
        methods: Array.isArray(val.methods) ? JSON.parse(JSON.stringify(val.methods)) : [],
        notes: val.notes || null
      };
    }
  }
  @Input() set nodeType(val: NodeType) {
    this.localType = val || 'class';
  }

  @Output() save = new EventEmitter<{ data: UMLNodeData; type: NodeType }>();
  @Output() close = new EventEmitter<void>();

  localData: UMLNodeData = {
    name: 'Clase',
    stereotype: null,
    attributes: [],
    methods: [],
    notes: null
  };
  localType: NodeType = 'class';

  visibilityOptions: { value: Visibility; label: string }[] = [
    { value: '+', label: '+ public' },
    { value: '-', label: '- private' },
    { value: '#', label: '# protected' },
    { value: '~', label: '~ package' }
  ];

  addAttribute() {
    this.localData.attributes.push({
      visibility: '+',
      name: 'nuevoAtributo',
      type: 'String',
      default_value: null,
      is_static: false
    });
  }

  removeAttribute(index: number) {
    this.localData.attributes.splice(index, 1);
  }

  addMethod() {
    this.localData.methods.push({
      visibility: '+',
      name: 'nuevoMetodo',
      params: '',
      return_type: 'void',
      is_static: false,
      is_abstract: false
    });
  }

  removeMethod(index: number) {
    this.localData.methods.splice(index, 1);
  }

  onSave() {
    this.save.emit({ data: this.localData, type: this.localType });
  }
}
