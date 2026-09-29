import { Injectable, NgZone, inject, signal } from '@angular/core';
import { Graph, Shape, Node, Edge, Cell } from '@antv/x6';
import { History } from '@antv/x6-plugin-history';
import { MiniMap } from '@antv/x6-plugin-minimap';
import { Scroller } from '@antv/x6-plugin-scroller';
import { Selection } from '@antv/x6-plugin-selection';
import { Snapline } from '@antv/x6-plugin-snapline';
import { Transform } from '@antv/x6-plugin-transform';
import { Keyboard } from '@antv/x6-plugin-keyboard';
import { Clipboard } from '@antv/x6-plugin-clipboard';
import { Export } from '@antv/x6-plugin-export';
import { jsPDF } from 'jspdf';
import { registerUMLNodesAndEdges, applyUMLNodeAttrs, calculateNodeHeight, setUMLNodeTheme } from '../nodes/uml-nodes';
import { GraphData, NodeType, UMLNodeData, DiagramNode, DiagramEdge, EdgeType } from '../models/diagram.model';

const NODE_SHAPE_MAP: Record<NodeType, string> = {
  class: 'uml-class',
  interface: 'uml-interface',
  abstract: 'uml-abstract',
  enum: 'uml-enum',
  note: 'uml-note',
  package: 'uml-package'
};

const EDGE_SHAPE_MAP: Record<EdgeType, string> = {
  inheritance: 'uml-inheritance',
  composition: 'uml-composition',
  aggregation: 'uml-aggregation',
  association: 'uml-association',
  dependency: 'uml-dependency',
  realization: 'uml-realization'
};

const SHAPE_TO_EDGE_TYPE: Record<string, EdgeType> = {
  'uml-inheritance': 'inheritance',
  'uml-composition': 'composition',
  'uml-aggregation': 'aggregation',
  'uml-association': 'association',
  'uml-dependency': 'dependency',
  'uml-realization': 'realization'
};

const DEFAULT_NODE_SIZES: Record<NodeType, { width: number; height: number }> = {
  class: { width: 220, height: 140 },
  interface: { width: 220, height: 140 },
  abstract: { width: 220, height: 140 },
  enum: { width: 220, height: 140 },
  note: { width: 200, height: 100 },
  package: { width: 260, height: 160 }
};

@Injectable({ providedIn: 'root' })
export class CanvasService {
  private graph!: Graph;
  private ngZone = inject(NgZone);

  /** Currently active connection mode — when set, new edges use this type */
  connectionMode = signal<EdgeType | null>(null);

  /** Theme mode for canvas: Light or Dark */
  isLightMode = signal<boolean>(false);

  toggleTheme() {
    const next = !this.isLightMode();
    this.isLightMode.set(next);
    setUMLNodeTheme(next);

    if (!this.graph) return;

    if (next) {
      this.graph.drawBackground({ color: '#F8FAFC' });
      this.graph.drawGrid({
        type: 'dot',
        args: { color: '#94A3B8', thickness: 1.5 }
      });
    } else {
      this.graph.drawBackground({ color: '#0F172A' });
      this.graph.drawGrid({
        type: 'dot',
        args: { color: '#334155', thickness: 1.5 }
      });
    }

    // Force re-render of all nodes in new theme
    this.graph.getNodes().forEach(n => {
      applyUMLNodeAttrs(n, next);
    });
  }

  initGraph(container: HTMLElement, minimapContainer: HTMLElement): Graph {
    registerUMLNodesAndEdges();

    const self = this;

    this.graph = new Graph({
      container,
      autoResize: true,
      background: { color: this.isLightMode() ? '#F8FAFC' : '#0F172A' },
      grid: {
        size: 20,
        visible: true,
        type: 'dot',
        args: { color: this.isLightMode() ? '#94A3B8' : '#334155', thickness: 1.5 }
      },
      connecting: {
        router: {
          name: 'manhattan',
          args: {
            padding: 20
          }
        },
        connector: { name: 'rounded', args: { radius: 8 } },
        anchor: 'center',
        connectionPoint: 'boundary',
        allowBlank: false,
        highlight: true,
        snap: { radius: 30 },
        createEdge() {
          const mode = self.connectionMode();
          const edgeShape = mode ? EDGE_SHAPE_MAP[mode] : 'uml-association';
          return self.graph.createEdge({ shape: edgeShape });
        },
        validateConnection({ sourceCell, targetCell }) {
          if (!sourceCell || !targetCell) return false;
          if (sourceCell === targetCell) return false;
          return true;
        }
      },
      highlighting: {
        magnetAdsorbed: {
          name: 'stroke',
          args: { attrs: { fill: '#2D6BE4', stroke: '#2D6BE4' } }
        }
      },
      mousewheel: { enabled: true, zoomAtMousePosition: true, modifiers: 'ctrl', minScale: 0.2, maxScale: 3 },
      panning: { enabled: true, modifiers: ['space'] },
      interacting: {
        magnetConnectable: true,
        nodeMovable: true,
        edgeMovable: true,
        edgeLabelMovable: true
      }
    });

    // Plugins
    this.graph.use(new History({ enabled: true, stackSize: 50 }));
    this.graph.use(new Selection({ enabled: true, multiple: true, rubberband: true, movable: true, showNodeSelectionBox: true }));
    this.graph.use(new Snapline({ enabled: true, sharp: true }));
    this.graph.use(new Transform({ resizing: { enabled: true, minWidth: 150, minHeight: 80 }, rotating: false }));
    this.graph.use(new Keyboard({ enabled: true, global: true }));
    this.graph.use(new Clipboard({ enabled: true }));
    this.graph.use(new Scroller({ enabled: true, pannable: true, pageVisible: true, pageBreak: false }));
    this.graph.use(new MiniMap({ container: minimapContainer, width: 190, height: 120, padding: 10 }));
    this.graph.use(new Export());

    // Keyboard shortcuts
    this.graph.bindKey(['ctrl+z', 'meta+z'], () => this.undo());
    this.graph.bindKey(['ctrl+shift+z', 'ctrl+y'], () => this.redo());
    this.graph.bindKey(['ctrl+c'], () => this.graph.copy(this.graph.getSelectedCells()));
    this.graph.bindKey(['ctrl+v'], () => this.graph.paste());
    this.graph.bindKey(['delete', 'backspace'], () => this.deleteSelected());
    this.graph.bindKey(['ctrl+a'], () => this.selectAll());
    this.graph.bindKey(['ctrl+shift+f'], () => this.fitView());
    this.graph.bindKey(['escape'], () => this.clearConnectionMode());

    // Auto-update SVG compartments and height when node data or size changes
    this.graph.on('node:change:data', ({ node }) => {
      if (!node || !node.isNode()) return;
      const data = (node.getData() as UMLNodeData) || { name: 'Clase', stereotype: null, attributes: [], methods: [], notes: null };
      const currentType = (node.prop('nodeType') || 'class') as NodeType;
      const newH = calculateNodeHeight(data, currentType);
      const currentSize = node.size();
      if (currentSize && Math.abs(currentSize.height - newH) > 2) {
        node.resize(currentSize.width || 220, newH);
      }
      applyUMLNodeAttrs(node, this.isLightMode());
    });

    this.graph.on('node:change:size', ({ node }) => {
      if (!node || !node.isNode()) return;
      applyUMLNodeAttrs(node, this.isLightMode());
    });

    return this.graph;
  }

  getGraph(): Graph {
    return this.graph;
  }

  // ─── Connection Mode ─────────────────────────────────────────

  setConnectionMode(type: EdgeType | null) {
    this.connectionMode.set(type);
    if (type) {
      (this.graph as any).disableRubberband?.();
    } else {
      (this.graph as any).enableRubberband?.();
    }
  }

  clearConnectionMode() {
    this.setConnectionMode(null);
  }

  addNode(
    type: NodeType, 
    position?: { x: number; y: number }, 
    id?: string, 
    customData?: UMLNodeData, 
    customSize?: { width: number; height: number },
    select: boolean = true
  ): Node | undefined {
    if (!this.graph) {
      console.warn('CanvasService: graph is not ready yet');
      return undefined;
    }

    const defaultSize = customSize || DEFAULT_NODE_SIZES[type] || { width: 220, height: 140 };
    const pos = position || this.findFreePosition(defaultSize.width, defaultSize.height);

    const data: UMLNodeData = customData || {
      name: this.generateDefaultName(type),
      stereotype: type !== 'class' && type !== 'note' && type !== 'package' ? type : null,
      attributes: type !== 'note' && type !== 'package' ? [
        { visibility: '+', name: 'id', type: 'Long', default_value: null, is_static: false }
      ] : [],
      methods: [],
      notes: type === 'note' ? 'Escribe aquí tu nota...' : null
    };

    const calculatedH = calculateNodeHeight(data, type);
    const nodeId = id || `node_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;

    try {
      const newNode = this.graph.addNode({
        id: nodeId,
        shape: NODE_SHAPE_MAP[type] || 'uml-class',
        x: pos.x,
        y: pos.y,
        width: defaultSize.width,
        height: Math.max(calculatedH, defaultSize.height),
        data,
        prop: { nodeType: type },
        ports: {
          groups: {
            default: {
              markup: [{ tagName: 'circle', selector: 'portBody' }],
              attrs: {
                portBody: {
                  r: 5,
                  magnet: true,
                  stroke: '#2D6BE4',
                  fill: '#0F172A',
                  strokeWidth: 2
                }
              },
              position: 'absolute'
            }
          },
          items: [
            { id: `${nodeId}-port-t`, group: 'default', args: { x: '50%', y: 0 } },
            { id: `${nodeId}-port-b`, group: 'default', args: { x: '50%', y: '100%' } },
            { id: `${nodeId}-port-l`, group: 'default', args: { x: 0, y: '50%' } },
            { id: `${nodeId}-port-r`, group: 'default', args: { x: '100%', y: '50%' } }
          ]
        }
      });

      // Apply crisp SVG UML 2.5 compartments
      applyUMLNodeAttrs(newNode, this.isLightMode());

      // Optionally select the newly created node
      if (select) {
        this.graph.cleanSelection();
        this.graph.select(newNode);
      }

      return newNode;

    } catch (err) {
      console.error('Error in CanvasService.addNode:', err);
      return undefined;
    }
  }

  updateNodeData(nodeOrId: Node | string, data: UMLNodeData, nodeType?: NodeType) {
    if (!this.graph) return;
    const node = typeof nodeOrId === 'string' ? (this.graph.getCellById(nodeOrId) as Node) : nodeOrId;
    if (!node || !node.isNode()) return;

    if (nodeType) {
      node.prop('nodeType', nodeType);
      node.prop('shape', NODE_SHAPE_MAP[nodeType] || 'uml-class');
    }
    node.setData(data, { overwrite: true });

    const currentType = (node.prop('nodeType') || 'class') as NodeType;
    const newH = calculateNodeHeight(data, currentType);
    const currentSize = node.size();
    node.resize(currentSize.width || 220, newH);

    applyUMLNodeAttrs(node, this.isLightMode());
  }

  private generateDefaultName(type: NodeType): string {
    const existing = this.graph.getNodes().filter(n => {
      const nt = n.prop('nodeType') as NodeType;
      return nt === type;
    });
    const prefix = type.charAt(0).toUpperCase() + type.slice(1);
    return `${prefix}${existing.length > 0 ? existing.length + 1 : ''}`;
  }

  private findFreePosition(width: number, height: number): { x: number; y: number } {
    const nodes = this.graph.getNodes();
    if (!nodes || nodes.length === 0) return { x: 120, y: 100 };

    const count = nodes.length;
    const cols = 3;
    const col = count % cols;
    const row = Math.floor(count / cols);

    return {
      x: 100 + col * (width + 50),
      y: 80 + row * (height + 50)
    };
  }

  addNewAttributeToNode(nodeOrId: Node | string) {
    if (!this.graph) return;
    const node = typeof nodeOrId === 'string' ? (this.graph.getCellById(nodeOrId) as Node) : nodeOrId;
    if (!node || !node.isNode()) return;

    const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
    if (!data.attributes) data.attributes = [];
    const count = data.attributes.length + 1;
    data.attributes.push({
      visibility: '+',
      name: `atributo${count}`,
      type: 'String',
      default_value: null,
      is_static: false
    });

    this.updateNodeData(node, data);
  }

  addNewMethodToNode(nodeOrId: Node | string) {
    if (!this.graph) return;
    const node = typeof nodeOrId === 'string' ? (this.graph.getCellById(nodeOrId) as Node) : nodeOrId;
    if (!node || !node.isNode()) return;

    const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
    if (!data.methods) data.methods = [];
    const count = data.methods.length + 1;
    data.methods.push({
      visibility: '+',
      name: `metodo${count}`,
      params: '',
      return_type: 'void',
      is_static: false,
      is_abstract: false
    });

    this.updateNodeData(node, data);
  }

  // ─── Edge Operations ──────────────────────────────────────────

  addEdge(type: EdgeType, sourceId: string, targetId: string, label?: string) {
    if (!this.graph) return;
    return this.graph.addEdge({
      shape: EDGE_SHAPE_MAP[type],
      source: { cell: sourceId },
      target: { cell: targetId },
      labels: label ? [{ attrs: { text: { text: label } } }] : []
    });
  }

  addRemoteEdge(
    id: string,
    type: EdgeType,
    sourceId: string,
    targetId: string,
    label?: string,
    sourceMult?: string,
    targetMult?: string,
    labels?: any[]
  ): Edge | undefined {
    if (!this.graph) return undefined;
    const existing = this.graph.getCellById(id);
    if (existing) return existing as Edge;

    const edgeLabels: any[] = labels || [];
    if (!labels) {
      const isLight = this.isLightMode();
      if (label) {
        edgeLabels.push({
          position: 0.5,
          attrs: {
            label: { text: label, fill: isLight ? '#0F172A' : '#F1F5F9', fontSize: 11, fontFamily: 'Inter, sans-serif', fontWeight: '600' },
            body: { fill: isLight ? '#FFFFFF' : '#1E293B', stroke: isLight ? '#CBD5E1' : '#475569', strokeWidth: 1, rx: 3, ry: 3 }
          }
        });
      }
      if (sourceMult) {
        edgeLabels.push({
          position: { distance: 24, offset: { x: 0, y: -12 } },
          attrs: {
            label: { text: sourceMult, fill: isLight ? '#0284C7' : '#38BDF8', fontSize: 11, fontFamily: "'JetBrains Mono', monospace", fontWeight: 'bold' },
            body: { fill: isLight ? '#FFFFFF' : '#0F172A', stroke: isLight ? '#CBD5E1' : '#334155', strokeWidth: 1, rx: 3, ry: 3 }
          }
        });
      }
      if (targetMult) {
        edgeLabels.push({
          position: { distance: -24, offset: { x: 0, y: -12 } },
          attrs: {
            label: { text: targetMult, fill: isLight ? '#0284C7' : '#38BDF8', fontSize: 11, fontFamily: "'JetBrains Mono', monospace", fontWeight: 'bold' },
            body: { fill: isLight ? '#FFFFFF' : '#0F172A', stroke: isLight ? '#CBD5E1' : '#334155', strokeWidth: 1, rx: 3, ry: 3 }
          }
        });
      }
    }

    try {
      const newEdge = this.graph.addEdge({
        id,
        shape: EDGE_SHAPE_MAP[type] || 'uml-association',
        source: { cell: sourceId },
        target: { cell: targetId },
        labels: edgeLabels
      });
      return newEdge;
    } catch (err) {
      console.error('Error adding remote edge:', err);
      return undefined;
    }
  }

  changeEdgeType(edgeId: string, newType: EdgeType): Edge | undefined {
    if (!this.graph) return;
    const edge = this.graph.getCellById(edgeId) as Edge;
    if (!edge || !edge.isEdge()) return;

    const source = edge.getSource();
    const target = edge.getTarget();
    const labels = edge.getLabels();

    this.graph.removeCell(edge);

    const newEdge = this.graph.addEdge({
      id: edgeId,
      shape: EDGE_SHAPE_MAP[newType],
      source,
      target,
      labels
    });

    this.graph.cleanSelection();
    this.graph.select(newEdge);
    return newEdge;
  }

  updateEdgeProperties(edgeId: string, type: EdgeType, label: string, sourceMult: string, targetMult: string) {
    if (!this.graph) return;
    let edge = this.graph.getCellById(edgeId) as Edge;
    if (!edge || !edge.isEdge()) return;

    const currentShape = edge.shape;
    const expectedShape = EDGE_SHAPE_MAP[type];
    if (currentShape !== expectedShape) {
      edge = this.changeEdgeType(edgeId, type)!;
      if (!edge) return;
    }

    const isLight = this.isLightMode();
    const labels: any[] = [
      {
        position: 0.5,
        attrs: {
          label: {
            text: label || '',
            fill: isLight ? '#0F172A' : '#F1F5F9',
            fontSize: 11,
            fontFamily: 'Inter, sans-serif',
            fontWeight: '600',
            display: label ? 'block' : 'none'
          },
          body: {
            fill: isLight ? '#FFFFFF' : '#1E293B',
            stroke: isLight ? '#CBD5E1' : '#475569',
            strokeWidth: 1,
            rx: 3,
            ry: 3,
            display: label ? 'block' : 'none'
          }
        }
      },
      {
        position: { distance: 35, offset: { x: 0, y: -14 } },
        attrs: {
          label: {
            text: sourceMult || '',
            fill: isLight ? '#0284C7' : '#38BDF8',
            fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 'bold',
            display: sourceMult ? 'block' : 'none'
          },
          body: { fill: 'transparent', stroke: 'none' }
        }
      },
      {
        position: { distance: -35, offset: { x: 0, y: -14 } },
        attrs: {
          label: {
            text: targetMult || '',
            fill: isLight ? '#0284C7' : '#38BDF8',
            fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 'bold',
            display: targetMult ? 'block' : 'none'
          },
          body: { fill: 'transparent', stroke: 'none' }
        }
      }
    ];

    edge.setLabels(labels);
  }

  // ─── Standard Operations ──────────────────────────────────────

  undo() { this.graph?.undo(); }
  redo() { this.graph?.redo(); }
  selectAll() { if (this.graph) this.graph.select(this.graph.getCells()); }
  deleteSelected() { if (this.graph) this.graph.removeCells(this.graph.getSelectedCells()); }

  fitView() {
    this.graph?.zoomToFit({ maxScale: 1, padding: 40 });
  }

  zoomIn() {
    this.graph?.zoom(0.1);
  }

  zoomOut() {
    this.graph?.zoom(-0.1);
  }

  getZoom(): number {
    return this.graph ? this.graph.zoom() : 1;
  }

  autoLayout() {
    const nodes = this.graph?.getNodes();
    if (!nodes || nodes.length === 0) return;

    const cols = Math.ceil(Math.sqrt(nodes.length));
    const spacingX = 280;
    const spacingY = 220;
    const startX = 80;
    const startY = 80;

    nodes.forEach((node, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      node.position(startX + col * spacingX, startY + row * spacingY);
    });

    this.fitView();
  }

  /** Focus, select and center a node in the diagram by class/entity name */
  focusNodeByName(name: string): boolean {
    if (!this.graph || !name) return false;
    const clean = name.toLowerCase().replace(/\.(java|ts|js|json|xml|yml|yaml|md|txt)$/, '').replace(/(controller|service|dto|mapper|repository|requestdto|responsedto|serviceimpl)$/i, '').trim();
    const nodes = this.graph.getNodes();
    const target = nodes.find(n => {
      const data = n.getData() as any;
      const nodeName = (data?.name || '').toLowerCase().trim();
      return nodeName === clean || (nodeName.length > 2 && (clean.includes(nodeName) || nodeName.includes(clean)));
    });
    if (target) {
      this.graph.cleanSelection();
      this.graph.select(target);
      this.graph.centerCell(target);
      return true;
    }
    return false;
  }

  /** Resize graph to fit its container after panel resize */
  resizeGraphToContainer() {
    if (!this.graph) return;
    try {
      const container = (this.graph as any).container;
      if (container && container.parentElement) {
        const rect = container.parentElement.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          this.graph.resize(rect.width, rect.height);
        }
      }
    } catch (e) {
      console.warn('Could not resize graph:', e);
    }
  }

  enablePanning() {
    this.graph?.enablePanning();
    (this.graph as any)?.disableRubberband?.();
  }

  disablePanning() {
    this.graph?.disablePanning();
    (this.graph as any)?.enableRubberband?.();
  }

  // ─── Export ───────────────────────────────────────────────────

  async exportPng(): Promise<void> {
    (this.graph as any)?.exportPNG?.('classforge-diagram', { padding: 20, quality: 1 });
  }

  async exportPdf(diagramName: string): Promise<void> {
    return new Promise((resolve) => {
      (this.graph as any)?.toPNG?.((dataUrl: string) => {
        const pdf = new jsPDF({ orientation: 'landscape', unit: 'px', format: [1920, 1080] });
        pdf.addImage(dataUrl, 'PNG', 0, 0, 1920, 1080);
        pdf.save(`${diagramName}.pdf`);
        resolve();
      }, { padding: 20 });
    });
  }

  // ─── Serialization ────────────────────────────────────────────

  toGraphData(): GraphData {
    if (!this.graph) {
      return { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } };
    }
    const json = this.graph.toJSON();

    const nodes: DiagramNode[] = json.cells
      .filter((c: any) => c.shape && c.shape.startsWith('uml-') && !c.source && !c.target)
      .map((c: any) => ({
        id: c.id,
        type: (c.prop?.nodeType || this.shapeToNodeType(c.shape)) as NodeType,
        position: { x: c.position?.x || 0, y: c.position?.y || 0 },
        size: { width: c.size?.width || 220, height: c.size?.height || 140 },
        data: (c.data as UMLNodeData) || { name: 'Clase', stereotype: null, attributes: [], methods: [], notes: null }
      }));

    const edges: DiagramEdge[] = json.cells
      .filter((c: any) => c.source && c.target)
      .map((c: any) => {
        const edgeType = SHAPE_TO_EDGE_TYPE[c.shape] || 'association';
        const labels = c.labels || [];
        return {
          id: c.id,
          type: edgeType,
          source: typeof c.source === 'object' ? c.source.cell : c.source,
          target: typeof c.target === 'object' ? c.target.cell : c.target,
          label: this.extractLabelText(labels, 0),
          source_multiplicity: this.extractLabelText(labels, 1),
          target_multiplicity: this.extractLabelText(labels, 2)
        };
      });

    return {
      nodes,
      edges,
      viewport: { x: 0, y: 0, zoom: this.graph.zoom() }
    };
  }

  private shapeToNodeType(shape: string): NodeType {
    const map: Record<string, NodeType> = {
      'uml-class': 'class',
      'uml-interface': 'interface',
      'uml-abstract': 'abstract',
      'uml-enum': 'enum',
      'uml-note': 'note',
      'uml-package': 'package'
    };
    return map[shape] || 'class';
  }

  private extractLabelText(labels: any[], index: number): string | null {
    if (!labels || index >= labels.length) return null;
    const label = labels[index];
    return label?.attrs?.text?.text || label?.attrs?.label?.text || null;
  }

  fromGraphData(data: GraphData) {
    if (!data || !this.graph) return;

    this.graph.clearCells();

    // Load nodes
    data.nodes?.forEach(n => {
      const calculatedH = calculateNodeHeight(n.data, n.type);
      const node = this.graph.addNode({
        id: n.id,
        shape: NODE_SHAPE_MAP[n.type] || 'uml-class',
        x: n.position.x,
        y: n.position.y,
        width: n.size.width || 220,
        height: calculatedH || n.size.height || 140,
        data: n.data,
        prop: { nodeType: n.type },
        ports: {
          groups: {
            default: {
              markup: [{ tagName: 'circle', selector: 'portBody' }],
              attrs: {
                portBody: {
                  r: 5,
                  magnet: true,
                  stroke: '#2D6BE4',
                  fill: '#0F172A',
                  strokeWidth: 2
                }
              },
              position: 'absolute'
            }
          },
          items: [
            { id: `${n.id}-port-t`, group: 'default', args: { x: '50%', y: 0 } },
            { id: `${n.id}-port-b`, group: 'default', args: { x: '50%', y: '100%' } },
            { id: `${n.id}-port-l`, group: 'default', args: { x: 0, y: '50%' } },
            { id: `${n.id}-port-r`, group: 'default', args: { x: '100%', y: '50%' } }
          ]
        }
      });
      applyUMLNodeAttrs(node, this.isLightMode());
    });

    // Load edges with multiplicity labels
    data.edges?.forEach(e => {
      const edgeLabels: any[] = [];

      if (e.label) {
        edgeLabels.push({
          position: 0.5,
          attrs: {
            text: { text: e.label, fill: '#94A3B8', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            rect: { fill: '#1E293B', stroke: '#334155', strokeWidth: 1, rx: 3, ry: 3 }
          }
        });
      }

      if (e.source_multiplicity) {
        edgeLabels.push({
          position: { distance: 35, offset: { x: 0, y: -14 } },
          attrs: {
            label: { text: e.source_multiplicity, fill: '#38BDF8', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fontWeight: 'bold' },
            body: { fill: 'transparent', stroke: 'none' }
          }
        });
      }

      if (e.target_multiplicity) {
        edgeLabels.push({
          position: { distance: -35, offset: { x: 0, y: -14 } },
          attrs: {
            label: { text: e.target_multiplicity, fill: '#38BDF8', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fontWeight: 'bold' },
            body: { fill: 'transparent', stroke: 'none' }
          }
        });
      }

      this.graph.addEdge({
        id: e.id,
        shape: EDGE_SHAPE_MAP[e.type] || 'uml-association',
        source: { cell: e.source },
        target: { cell: e.target },
        labels: edgeLabels
      });
    });
  }
}
