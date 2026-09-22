import { Component, Input, OnInit, OnDestroy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Graph, Cell, Node, Edge } from '@antv/x6';
import { LucideAngularModule, Plus, X, Settings2, ChevronDown, ChevronRight } from 'lucide-angular';
import { UMLNodeData, UMLAttribute, UMLMethod, Visibility, EdgeType, NodeType } from '../models/diagram.model';
import { AutoSaveService } from '../services/auto-save.service';
import { CanvasService } from '../services/canvas.service';

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

  private cdr = inject(ChangeDetectorRef);
  private autoSave = inject(AutoSaveService);
  private canvasService = inject(CanvasService);

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
    if (!this.graph) return;

    this.bindSelectionEvents();
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
          attributes: Array.isArray(rawData.attributes) ? JSON.parse(JSON.stringify(rawData.attributes)) : [],
          methods: Array.isArray(rawData.methods) ? JSON.parse(JSON.stringify(rawData.methods)) : [],
          notes: rawData.notes || null
        };
        this.nodeType = (this.selectedCell.prop('nodeType') || 'class') as NodeType;
      } else {
        const edge = this.selectedCell as Edge;
        const labels = edge.getLabels() || [];
        this.edgeData = {
          label: (labels[0]?.attrs as any)?.['text']?.['text'] || (labels[0]?.attrs as any)?.['label']?.['text'] || '',
          type: (this.selectedCell.shape.replace('uml-', '') as EdgeType) || 'association',
          source_multiplicity: (labels[1]?.attrs as any)?.['text']?.['text'] || (labels[1]?.attrs as any)?.['label']?.['text'] || '',
          target_multiplicity: (labels[2]?.attrs as any)?.['text']?.['text'] || (labels[2]?.attrs as any)?.['label']?.['text'] || '',
          source_role: '',
          target_role: ''
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
    this.nodeData.stereotype = newType !== 'class' && newType !== 'note' && newType !== 'package' ? newType : null;

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
        is_static: false
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
    const labels: any[] = [
      // 0: Main relationship label (center)
      {
        position: 0.5,
        attrs: {
          label: {
            text: this.edgeData.label || '',
            fill: '#E2E8F0',
            fontSize: 11,
            fontFamily: 'Inter, sans-serif',
            fontWeight: '500',
            display: this.edgeData.label ? 'block' : 'none'
          },
          body: {
            fill: '#1E293B',
            stroke: '#475569',
            strokeWidth: 1,
            rx: 3,
            ry: 3,
            display: this.edgeData.label ? 'block' : 'none'
          }
        }
      },
      // 1: Source Multiplicity (near source)
      {
        position: { distance: 35, offset: { x: 0, y: -14 } },
        attrs: {
          label: {
            text: this.edgeData.source_multiplicity || '',
            fill: '#38BDF8',
            fontSize: 11,
            fontFamily: 'JetBrains Mono, monospace',
            fontWeight: 'bold',
            display: this.edgeData.source_multiplicity ? 'block' : 'none'
          },
          body: { fill: 'transparent', stroke: 'none' }
        }
      },
      // 2: Target Multiplicity (near target)
      {
        position: { distance: -35, offset: { x: 0, y: -14 } },
        attrs: {
          label: {
            text: this.edgeData.target_multiplicity || '',
            fill: '#38BDF8',
            fontSize: 11,
            fontFamily: 'JetBrains Mono, monospace',
            fontWeight: 'bold',
            display: this.edgeData.target_multiplicity ? 'block' : 'none'
          },
          body: { fill: 'transparent', stroke: 'none' }
        }
      }
    ];

    edge.setLabels(labels);
    this.autoSave.markDirty();
  }

  changeEdgeType(newType: EdgeType) {
    if (!this.selectedCell || !this.edgeData) return;
    this.edgeData.type = newType;

    this.canvasService.changeEdgeType(this.selectedCell.id, newType);

    this.selectedCell = null;
    this.cellType = null;
    this.edgeData = null;
    this.autoSave.markDirty();
    this.cdr.detectChanges();
  }
}
