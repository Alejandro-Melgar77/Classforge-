import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Graph, Cell, Node, Edge } from '@antv/x6';
import { LucideAngularModule, Plus, X, Settings2, ChevronDown, ChevronRight } from 'lucide-angular';
import { UMLNodeData, UMLAttribute, UMLMethod, Visibility, EdgeType, NodeType } from '../models/diagram.model';
import { AutoSaveService } from '../services/auto-save.service';
import { CanvasService } from '../services/canvas.service';
import { buildUmlEdgeLabels } from '../nodes/uml-nodes';

@Component({
  selector: 'properties-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './properties-panel.component.html',
  host: {
    class: 'w-full h-full flex flex-col overflow-hidden bg-[var(--surface-2)] select-none'
  }
})
export class PropertiesPanelComponent implements OnInit, OnDestroy {
  @Input() graph!: Graph;
  @Output() close = new EventEmitter<void>();

  private cdr = inject(ChangeDetectorRef);
  private autoSave = inject(AutoSaveService);
  public canvasService = inject(CanvasService);

  selectedCell: Cell | null = null;
  cellType: 'node' | 'edge' | null = null;

  nodeData: UMLNodeData | null = null;
  nodeType: NodeType = 'class';

  edgeData: {
    label: string;
    type: EdgeType;
    source_multiplicity: string;
    target_multiplicity: string;
    source_role: string;
    target_role: string;
  } | null = null;

  // Accordion sections
  sections = {
    basic: true,
    attributes: true,
    methods: true,
    edgeDetails: true
  };

  edgeTypes: { value: EdgeType; label: string; icon: string }[] = [
    { value: 'association', label: 'Asociación (─▶)', icon: '─▶' },
    { value: 'inheritance', label: 'Generalización (─▷)', icon: '─▷' },
    { value: 'realization', label: 'Realización (┈▷)', icon: '┈▷' },
    { value: 'composition', label: 'Composición (◆─)', icon: '◆─' },
    { value: 'aggregation', label: 'Agregación (◇─)', icon: '◇─' },
    { value: 'dependency', label: 'Dependencia (┈▶)', icon: '┈▶' }
  ];

  multiplicityOptions = ['', '1', '0..1', '0..*', '1..*', '*', '1..1', '0..n', '1..n'];

  visibilityOptions: { value: Visibility; label: string; color: string }[] = [
    { value: '+', label: '+ public', color: '#4ADE80' },
    { value: '-', label: '- private', color: '#F87171' },
    { value: '#', label: '# protected', color: '#FBBF24' },
    { value: '~', label: '~ package', color: '#C084FC' }
  ];

  ngOnInit() {
    if (!this.graph) {
      this.graph = this.canvasService.getGraph();
    }
    if (this.graph) {
      this.bindSelectionEvents();
    }
  }

  bindSelectionEvents() {
    this.graph.on('selection:changed', ({ selected }) => {
      this.handleSelection(selected);
    });

    this.graph.on('cell:click', ({ cell }) => {
      this.handleSelection([cell]);
    });

    this.graph.on('node:click', ({ node }) => {
      this.handleSelection([node]);
    });

    this.graph.on('edge:click', ({ edge }) => {
      this.handleSelection([edge]);
    });
  }

  private handleSelection(selected: Cell[]) {
    if (selected && selected.length >= 1) {
      this.selectedCell = selected[0];
      this.cellType = this.selectedCell.isNode() ? 'node' : 'edge';

      if (this.cellType === 'node') {
        const rawData = this.selectedCell.getData() || {};
        this.nodeData = {
          name: rawData.name || 'NombreClase',
          stereotype: rawData.stereotype || null,
          is_abstract: !!(rawData.is_abstract || (rawData as any).isAbstract),
          attributes: Array.isArray(rawData.attributes) ? JSON.parse(JSON.stringify(rawData.attributes)) : [],
          methods: Array.isArray(rawData.methods) ? JSON.parse(JSON.stringify(rawData.methods)) : [],
          notes: rawData.notes || null
        };
        this.nodeType = (this.selectedCell.prop('nodeType') || 'class') as NodeType;
      } else {
        const edge = this.selectedCell as Edge;
        const labels = edge.getLabels() || [];
        const getLabel = (idx: number) => {
          if (idx >= labels.length) return '';
          const l = labels[idx];
          return (l?.attrs as any)?.['label']?.['text'] || (l?.attrs as any)?.['text']?.['text'] || '';
        };

        const rawEdgeData = (edge.getData() as any) || {};

        this.edgeData = {
          label: rawEdgeData.label || getLabel(0),
          type: (this.selectedCell.shape.replace('uml-', '') as EdgeType) || 'association',
          source_multiplicity: rawEdgeData.source_multiplicity || rawEdgeData.sourceMultiplicity || getLabel(1),
          target_multiplicity: rawEdgeData.target_multiplicity || rawEdgeData.targetMultiplicity || getLabel(2),
          source_role: (rawEdgeData.source_role || rawEdgeData.sourceRole || getLabel(3)).replace(/^\+/, ''),
          target_role: (rawEdgeData.target_role || rawEdgeData.targetRole || getLabel(4)).replace(/^\+/, '')
        };
      }
    } else {
      this.selectedCell = null;
      this.cellType = null;
      this.nodeData = null;
      this.edgeData = null;
    }
    this.cdr.detectChanges();
  }

  ngOnDestroy() {
    if (this.graph) {
      this.graph.off('selection:changed');
      this.graph.off('cell:click');
      this.graph.off('node:click');
      this.graph.off('edge:click');
    }
  }

  toggleSection(section: keyof typeof this.sections) {
    this.sections[section] = !this.sections[section];
  }

  // ─── Node Operations ──────────────────────────────────────────

  updateNode() {
    if (this.selectedCell && this.cellType === 'node' && this.nodeData) {
      this.canvasService.updateNodeData(this.selectedCell as Node, this.nodeData, this.nodeType);
      this.autoSave.markDirty();
    }
  }

  changeNodeType(newType: NodeType) {
    if (!this.selectedCell || !this.nodeData) return;

    this.nodeType = newType;
    if (newType === 'interface') this.nodeData.stereotype = 'interface';
    else if (newType === 'abstract') {
      this.nodeData.stereotype = 'abstract';
      this.nodeData.is_abstract = true;
    } else if (newType === 'enum') this.nodeData.stereotype = 'enumeration';
    else if (newType === 'class') this.nodeData.stereotype = null;

    this.canvasService.updateNodeData(this.selectedCell as Node, this.nodeData, newType);
    this.autoSave.markDirty();
  }

  addAttribute() {
    if (this.nodeData) {
      if (!this.nodeData.attributes) this.nodeData.attributes = [];
      this.nodeData.attributes.push({
        visibility: '+',
        name: 'nuevoAtributo',
        type: 'String',
        default_value: null,
        is_static: false,
        is_derived: false,
        multiplicity: null
      });
      this.updateNode();
    }
  }

  removeAttribute(index: number) {
    if (this.nodeData?.attributes) {
      this.nodeData.attributes.splice(index, 1);
      this.updateNode();
    }
  }

  addMethod() {
    if (this.nodeData) {
      if (!this.nodeData.methods) this.nodeData.methods = [];
      this.nodeData.methods.push({
        visibility: '+',
        name: 'nuevoMetodo',
        params: '',
        return_type: 'void',
        is_static: false,
        is_abstract: false
      });
      this.updateNode();
    }
  }

  removeMethod(index: number) {
    if (this.nodeData?.methods) {
      this.nodeData.methods.splice(index, 1);
      this.updateNode();
    }
  }

  // ─── Edge Operations ──────────────────────────────────────────

  updateEdge() {
    if (!this.selectedCell || this.cellType !== 'edge' || !this.edgeData) return;

    const edge = this.selectedCell as Edge;
    const isLight = this.canvasService.isLightMode();
    const labels = buildUmlEdgeLabels(
      this.edgeData.label,
      this.edgeData.source_multiplicity,
      this.edgeData.target_multiplicity,
      this.edgeData.source_role,
      this.edgeData.target_role,
      isLight
    );

    edge.setLabels(labels);
    edge.setData({
      label: this.edgeData.label,
      type: this.edgeData.type,
      source_multiplicity: this.edgeData.source_multiplicity,
      target_multiplicity: this.edgeData.target_multiplicity,
      source_role: this.edgeData.source_role,
      target_role: this.edgeData.target_role
    });
    this.autoSave.markDirty();
  }

  changeEdgeType(newType: EdgeType) {
    if (!this.selectedCell || !this.edgeData) return;
    this.edgeData.type = newType;

    const newEdge = this.canvasService.changeEdgeType(this.selectedCell.id, newType);
    if (newEdge) {
      this.selectedCell = newEdge;
      this.updateEdge();
    }
    this.autoSave.markDirty();
    this.cdr.detectChanges();
  }

  validateIdentifier(name: string): { valid: boolean; warning?: string } {
    if (!name || !name.trim()) return { valid: false, warning: 'El nombre no puede estar vacío.' };
    if (/\s/.test(name)) return { valid: false, warning: 'No debe contener espacios.' };
    const reserved = ['class', 'interface', 'public', 'private', 'protected', 'static', 'void', 'def', 'import', 'from', 'return'];
    if (reserved.includes(name.toLowerCase())) {
      return { valid: true, warning: 'Palabra reservada del lenguaje.' };
    }
    return { valid: true };
  }
}
