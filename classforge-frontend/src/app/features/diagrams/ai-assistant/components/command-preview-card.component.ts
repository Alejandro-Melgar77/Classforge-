import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UMLCommandResponse } from '../models/ai-command.model';

@Component({
  selector: 'app-command-preview-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="command-preview-card p-4 rounded-xl bg-slate-900/90 border border-purple-500/30 shadow-2xl mb-4 backdrop-blur-sm">
      <div class="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800">
        <h4 class="text-xs font-bold text-purple-400 flex items-center gap-1.5 uppercase tracking-wider">
          <span>⚡</span> Propuesta de Cambios
        </h4>
        <span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
          Offline
        </span>
      </div>

      <p class="text-xs text-slate-300 mb-3 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/50 leading-relaxed">
        {{ command.explanation }}
      </p>
      
      <!-- Classes -->
      <div *ngIf="command.classes.length > 0" class="mb-3">
        <h5 class="text-[11px] font-bold text-blue-400 mb-1.5 flex items-center gap-1">
          <span>📦</span> Clases / Tablas ({{ command.classes.length }}):
        </h5>
        <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          <div *ngFor="let cls of command.classes" class="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700">
            <div class="flex items-center justify-between mb-1">
              <strong class="text-xs text-white font-mono">{{ cls.name }}</strong>
              <span *ngIf="cls.stereotype" class="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 font-mono">
                &laquo;{{ cls.stereotype }}&raquo;
              </span>
            </div>

            <!-- Attributes preview -->
            <div *ngIf="cls.attributes && cls.attributes.length > 0" class="mt-1 pl-2 border-l-2 border-blue-500/40 space-y-0.5">
              <div *ngFor="let attr of cls.attributes" class="text-[11px] text-slate-300 font-mono">
                <span class="text-blue-400">{{ attr.visibility || '+' }}</span> {{ attr.name }}: <span class="text-emerald-400">{{ attr.type }}</span>
              </div>
            </div>

            <!-- Methods preview -->
            <div *ngIf="cls.methods && cls.methods.length > 0" class="mt-1 pl-2 border-l-2 border-emerald-500/40 space-y-0.5">
              <div *ngFor="let m of cls.methods" class="text-[11px] text-slate-300 font-mono">
                <span class="text-emerald-400">{{ m.visibility || '+' }}</span> {{ m.name }}({{ m.params }}): <span class="text-cyan-400">{{ m.return_type || 'void' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Relations & Cardinalities -->
      <div *ngIf="command.relations.length > 0" class="mb-3">
        <h5 class="text-[11px] font-bold text-cyan-400 mb-1.5 flex items-center gap-1">
          <span>🔗</span> Relaciones y Cardinalidades:
        </h5>
        <ul class="text-xs space-y-1.5">
          <li *ngFor="let rel of command.relations" class="bg-slate-800/80 p-2 rounded-lg border border-slate-700 font-mono text-[11px] flex items-center justify-between">
            <span class="text-white font-bold">{{ rel.source }}</span>
            <div class="flex items-center gap-1.5 text-[10px] text-cyan-300">
              <span *ngIf="rel.sourceMultiplicity" class="px-1 bg-cyan-950/80 rounded border border-cyan-800/50 text-cyan-400 font-bold">[{{ rel.sourceMultiplicity }}]</span>
              <span>── {{ rel.type }} ──></span>
              <span *ngIf="rel.targetMultiplicity" class="px-1 bg-cyan-950/80 rounded border border-cyan-800/50 text-cyan-400 font-bold">[{{ rel.targetMultiplicity }}]</span>
            </div>
            <span class="text-white font-bold">{{ rel.target }}</span>
          </li>
        </ul>
      </div>

      <!-- Deleted elements -->
      <div *ngIf="command.deleted_elements.length > 0" class="mb-3">
        <h5 class="text-[11px] font-bold text-red-400 mb-1 flex items-center gap-1">
          <span>🗑️</span> Elementos a Eliminar:
        </h5>
        <ul class="text-xs space-y-1 text-red-400">
          <li *ngFor="let el of command.deleted_elements" class="bg-red-950/30 p-2 rounded-lg border border-red-800/40">
            {{ el }}
          </li>
        </ul>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 mt-4 pt-3 border-t border-slate-800">
        <button class="flex-1 py-2 px-3 rounded-lg text-xs font-bold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                (click)="confirm.emit()">
          <span>✓</span> Aplicar al Lienzo
        </button>
        <button class="py-2 px-3 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors cursor-pointer"
                (click)="discard.emit()">
          ✕ Descartar
        </button>
      </div>
    </div>
  `
})
export class CommandPreviewCardComponent {
  @Input() command!: UMLCommandResponse;
  @Output() confirm = new EventEmitter<void>();
  @Output() discard = new EventEmitter<void>();
}

