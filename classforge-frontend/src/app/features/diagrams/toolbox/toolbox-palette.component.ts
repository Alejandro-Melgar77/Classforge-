import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule } from 'lucide-angular';
import { CanvasService } from '../services/canvas.service';
import { NodeType, EdgeType } from '../models/diagram.model';

export interface ClassifierItem {
  id: NodeType;
  name: string;
  color: string;
  badge: string;
}

export interface RelationshipItem {
  id: EdgeType;
  name: string;
  lineStyle: 'solid-arrow' | 'solid-triangle' | 'dashed-triangle' | 'solid-diamond-filled' | 'solid-diamond-hollow' | 'dashed-arrow';
  symbol: string;
}

@Component({
  selector: 'app-toolbox-palette',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  templateUrl: './toolbox-palette.component.html',
  host: {
    class: 'w-full h-full flex flex-col overflow-hidden bg-[var(--surface-2)] select-none'
  }
})
export class ToolboxPaletteComponent {
  @Input() isOpen: boolean = true;
  @Output() close = new EventEmitter<void>();
  @Output() nodeDropped = new EventEmitter<{type: NodeType, x: number, y: number}>();
  @Output() connectionModeChanged = new EventEmitter<EdgeType | null>();

  public canvasService = inject(CanvasService);

  activeConnectionMode: EdgeType | null = null;

  sections = {
    classifiers: true,
    relationships: true,
    tools: true
  };

  classifiers: ClassifierItem[] = [
    { id: 'class', name: 'Clase', color: '#2D6BE4', badge: 'C' },
    { id: 'interface', name: 'Interfaz', color: '#00C896', badge: 'I' },
    { id: 'abstract', name: 'Clase Abstracta', color: '#7C3AED', badge: 'A' },
    { id: 'enum', name: 'Enumeración', color: '#F5A623', badge: 'E' },
    { id: 'package', name: 'Paquete', color: '#475569', badge: 'P' },
    { id: 'note', name: 'Nota / Comentario', color: '#334155', badge: 'N' }
  ];

  relationships: RelationshipItem[] = [
    { id: 'association', name: 'Asociación', lineStyle: 'solid-arrow', symbol: '─▶' },
    { id: 'inheritance', name: 'Generalización', lineStyle: 'solid-triangle', symbol: '─▷' },
    { id: 'realization', name: 'Realización', lineStyle: 'dashed-triangle', symbol: '┈▷' },
    { id: 'composition', name: 'Composición', lineStyle: 'solid-diamond-filled', symbol: '◆─' },
    { id: 'aggregation', name: 'Agregación', lineStyle: 'solid-diamond-hollow', symbol: '◇─' },
    { id: 'dependency', name: 'Dependencia', lineStyle: 'dashed-arrow', symbol: '┈▶' }
  ];

  tools = [
    { id: 'select', name: 'Seleccionar (V)', icon: 'mouse-pointer-2' },
    { id: 'pan', name: 'Mano / Mover Lienzo (Espacio)', icon: 'hand' },
    { id: 'delete', name: 'Eliminar Selección (Supr)', icon: 'trash-2' },
    { id: 'fit', name: 'Ajustar a Pantalla', icon: 'maximize' },
    { id: 'layout', name: 'Auto-Distribuir Nodos', icon: 'layout-grid' }
  ];

  toggleSection(section: 'classifiers' | 'relationships' | 'tools') {
    this.sections[section] = !this.sections[section];
  }

  // Click to add directly at center or smart position
  onItemClick(type: NodeType) {
    this.canvasService.addNode(type);
  }

  // Drag to place at specific drop coordinates
  onDragStart(event: DragEvent, type: NodeType) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/classforge-node', type);
      event.dataTransfer.effectAllowed = 'copy';
    }
  }

  selectConnectionMode(type: EdgeType) {
    if (this.activeConnectionMode === type) {
      this.activeConnectionMode = null;
    } else {
      this.activeConnectionMode = type;
    }
    this.connectionModeChanged.emit(this.activeConnectionMode);
  }

  executeTool(toolId: string) {
    switch (toolId) {
      case 'select':
        this.canvasService.disablePanning();
        break;
      case 'pan':
        this.canvasService.enablePanning();
        break;
      case 'delete':
        this.canvasService.deleteSelected();
        break;
      case 'fit':
        this.canvasService.fitView();
        break;
      case 'layout':
        this.canvasService.autoLayout();
        break;
    }
  }
}
