import { Component, OnInit, AfterViewInit, ViewChild, ElementRef, NgZone, ChangeDetectionStrategy, inject, OnDestroy, effect, HostListener, signal, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { Graph, Node, Edge, Cell } from '@antv/x6';
import { CanvasService } from '../services/canvas.service';
import { AutoSaveService } from '../services/auto-save.service';
import { DiagramService } from '../services/diagram.service';
import { Diagram, NodeType, EdgeType, UMLNodeData, UMLAttribute, UMLMethod, DiagramParticipantsResponse, ParticipantItem } from '../models/diagram.model';
import { AuthService } from '../../../core/services/auth.service';
import { CanvasToolbarComponent } from '../toolbar/canvas-toolbar.component';
import { CollaborationService } from '../collaboration/services/collaboration.service';
import { PresenceBarComponent } from '../collaboration/components/presence-bar.component';
import { CursorOverlayComponent } from '../collaboration/components/cursor-overlay.component';
import { CollaboratorsPanelComponent } from '../collaboration/components/collaborators-panel.component';
import { AiDrawerComponent } from '../ai-assistant/components/ai-drawer.component';
import { CodegenService } from '../codegen/services/codegen.service';
import { LiveCodeDrawerComponent } from '../codegen/components/live-code-drawer.component';
import { FrontendPromptModalComponent } from '../codegen/components/frontend-prompt-modal.component';
import { ToolboxPaletteComponent } from '../toolbox/toolbox-palette.component';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'diagram-canvas',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CanvasToolbarComponent,
    PresenceBarComponent,
    CursorOverlayComponent,
    CollaboratorsPanelComponent,
    AiDrawerComponent,
    LiveCodeDrawerComponent,
    FrontendPromptModalComponent,
    ToolboxPaletteComponent
  ],
  templateUrl: './diagram-canvas.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DiagramCanvasComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('graphContainer') graphContainer!: ElementRef;
  @ViewChild('minimapContainer') minimapContainer!: ElementRef;
  @ViewChild('canvasWrapper') canvasWrapper!: ElementRef;

  public canvasService = inject(CanvasService);
  public autoSave = inject(AutoSaveService);
  public diagramService = inject(DiagramService);
  public colabService = inject(CollaborationService);
  public codegenService = inject(CodegenService);
  public authService = inject(AuthService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private ngZone = inject(NgZone);
  private cdr = inject(ChangeDetectorRef);

  diagramId!: string;
  diagram: Diagram | null = null;
  graph!: Graph;

  get currentUser() {
    return this.authService.getCurrentUser();
  }

  get isAdmin(): boolean {
    return this.authService.hasRole('admin');
  }

  get isScrumMaster(): boolean {
    return this.authService.hasRole('scrum_master');
  }

  get canManage(): boolean {
    return this.isAdmin || this.isScrumMaster;
  }

  // Panel states
  isToolboxOpen = true;
  isAiDrawerOpen = false;
  isLiveCodeOpen = false;
  isPromptModalOpen = false;
  isCollabPanelOpen = false;

  // Canvas Rename & Branding Modal
  isCanvasEditModalOpen = false;
  canvasEditForm = {
    name: '',
    description: '',
    image_url: '' as string | null
  };
  canvasLogoPreview: string | null = null;
  isSavingCanvasEdit = false;

  // Canvas Participants Modal
  isCanvasParticipantsModalOpen = false;
  canvasParticipantsLoading = false;
  canvasParticipantsData: DiagramParticipantsResponse | null = null;
  canvasSelectedParticipantIds = new Set<string>();
  isSavingCanvasParticipants = false;

  // Panel widths (resizable)
  toolboxWidth = 240;

  // Inline Node Edit Modal state
  isNodeEditModalOpen = false;
  editingNodeId: string | null = null;
  editingNodeData: UMLNodeData = {
    name: 'Clase',
    stereotype: null,
    attributes: [],
    methods: [],
    notes: null
  };
  editingNodeType: NodeType = 'class';

  // ═══ Floating Quick Edge Toolbar State ═══
  selectedEdgeId: string | null = null;
  edgeToolbarPos: { x: number; y: number } | null = null;
  quickEdgeType: EdgeType = 'association';
  quickEdgeLabel: string = '';
  quickEdgeSourceMult: string = '';
  quickEdgeTargetMult: string = '';

  // ═══ Floating Quick Node Toolbar & In-Box Edit State ═══
  selectedNodeId: string | null = null;
  nodeToolbarPos: { x: number; y: number } | null = null;
  inlineEditingMode: 'none' | 'name' | 'attributes' | 'methods' = 'none';
  inlineEditingNodeId: string | null = null;
  inlineEditingText: string = '';
  inlineEditorPos: { x: number; y: number; width: number; height: number } | null = null;

  visibilityOptions = [
    { value: '+', label: '+ public' },
    { value: '-', label: '- private' },
    { value: '#', label: '# protected' },
    { value: '~', label: '~ package' }
  ];

  cardinalityOptions = ['', '1', '0..1', '1..*', '0..*', '*', '1..1', '0..n', '1..n'];

  typeOptions = ['String', 'Long', 'Integer', 'Double', 'Boolean', 'Date', 'UUID', 'List<String>', 'Set<String>', 'void'];

  // Resize state
  private isResizingToolbox = false;
  private isResizingProperties = false;
  private resizeStartX = 0;
  private resizeStartWidth = 0;

  private isApplyingRemoteUpdate = false;
  private subs = new Subscription();
  private codegenTimeout: any;
  private resizeObserver: ResizeObserver | null = null;

  constructor() {
    effect(() => {
      const lockedMap = this.colabService.lockedElements();
      if (this.graph) {
        const cells = this.graph.getCells();
        cells.forEach(cell => {
          const lockedBy = lockedMap.get(cell.id);
          if (lockedBy) {
            const user = this.colabService.connectedUsers().find(u => u.user_id === lockedBy);
            if (user) {
              cell.attr('body/stroke', user.color);
              cell.attr('body/strokeWidth', 3);
            }
          } else {
            cell.attr('body/stroke', '#334155');
            cell.attr('body/strokeWidth', 1.5);
          }
        });
      }
    });
  }

  ngOnInit() {
    this.diagramId = this.route.snapshot.paramMap.get('id')!;

    this.autoSave.init(this.diagramId, () => this.canvasService.toGraphData());
    this.colabService.connect(this.diagramId);

    this.diagramService.getDiagram(this.diagramId).subscribe(res => {
      if (res.success) {
        this.diagram = res.data;
        if (this.graph && this.diagram.graph_data) {
          this.canvasService.fromGraphData(this.diagram.graph_data);
        }
        this.cdr.markForCheck();
      }
    });

    this.subs.add(
      this.colabService.remoteOperations$.subscribe(msg => {
        if (!this.graph) return;
        this.isApplyingRemoteUpdate = true;

        try {
          const isNodeOp = msg.type === 'NODE_OPERATION' || msg.type === 'node_operation';
          const isEdgeOp = msg.type === 'EDGE_OPERATION' || msg.type === 'edge_operation';
          const op = msg.op || msg.payload?.op;
          const nodeId = msg.node_id || msg.payload?.node_id;
          const edgeId = msg.edge_id || msg.payload?.edge_id;
          const data = msg.data || msg.payload?.data;

          if (isNodeOp && nodeId) {
            if (op === 'add' && data) {
              const existingNode = this.graph.getCellById(nodeId);
              if (!existingNode) {
                const nodeType = data.type || data.nodeType || 'class';
                const pos = data.position || { x: data.x || 100, y: data.y || 100 };
                const size = data.size || { width: 220, height: 140 };
                this.canvasService.addNode(nodeType, pos, nodeId, data.data, size, false);
              }
            } else if (op === 'move' && data) {
              const node = this.graph.getCellById(nodeId);
              if (node && node.isNode()) {
                const posX = data.position?.x ?? data.x;
                const posY = data.position?.y ?? data.y;
                if (posX !== undefined && posY !== undefined) {
                  node.position(posX, posY);
                }
              }
            } else if (op === 'update' && data) {
              const node = this.graph.getCellById(nodeId);
              if (node && node.isNode()) {
                if (data.nodeType || data.type) {
                  const nt = data.nodeType || data.type;
                  node.prop('nodeType', nt);
                }
                if (data.data) {
                  this.canvasService.updateNodeData(node as Node, data.data, data.nodeType || data.type);
                }
                if (data.position) {
                  node.position(data.position.x, data.position.y);
                } else if (data.x !== undefined && data.y !== undefined) {
                  node.position(data.x, data.y);
                }
                if (data.size) {
                  node.resize(data.size.width, data.size.height);
                }
              }
            } else if (op === 'delete') {
              const node = this.graph.getCellById(nodeId);
              if (node) this.graph.removeCell(node);
            }
          } else if (isEdgeOp && edgeId) {
            if (op === 'add' && data) {
              const existingEdge = this.graph.getCellById(edgeId);
              if (!existingEdge && data.source && data.target) {
                const src = typeof data.source === 'object' ? data.source.cell : data.source;
                const tgt = typeof data.target === 'object' ? data.target.cell : data.target;
                const edgeType = data.type || 'association';
                this.canvasService.addRemoteEdge(
                  edgeId,
                  edgeType,
                  src,
                  tgt,
                  data.label,
                  data.source_multiplicity,
                  data.target_multiplicity,
                  data.labels
                );
              }
            } else if (op === 'update' && data) {
              this.canvasService.updateEdgeProperties(
                edgeId,
                data.type || 'association',
                data.label || '',
                data.source_multiplicity || '',
                data.target_multiplicity || ''
              );
            } else if (op === 'delete') {
              const edge = this.graph.getCellById(edgeId);
              if (edge) this.graph.removeCell(edge);
            }
          }
        } finally {
          this.isApplyingRemoteUpdate = false;
          this.triggerCodegenPreview();
          this.updateFloatingToolbarsPosition();
          this.cdr.detectChanges();
        }
      })
    );
  }

  ngAfterViewInit() {
    this.ngZone.runOutsideAngular(() => {
      this.graph = this.canvasService.initGraph(
        this.graphContainer.nativeElement,
        this.minimapContainer.nativeElement
      );

      // Mouse tracking for cursor collaboration
      this.graphContainer.nativeElement.addEventListener('mousemove', (e: MouseEvent) => {
        const rect = this.graphContainer.nativeElement.getBoundingClientRect();
        this.colabService.sendCursor(e.clientX - rect.left, e.clientY - rect.top);
      });

      // Drop handler for toolbox drag-and-drop
      const wrapper = this.canvasWrapper?.nativeElement || this.graphContainer.nativeElement.parentElement;
      wrapper.addEventListener('dragover', (e: DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
      });
      wrapper.addEventListener('drop', (e: DragEvent) => {
        e.preventDefault();
        const nodeType = e.dataTransfer?.getData('application/classforge-node') as NodeType;
        if (nodeType && this.graph) {
          const localPoint = this.graph.clientToLocal(e.clientX, e.clientY);
          this.canvasService.addNode(nodeType, { x: localPoint.x, y: localPoint.y });
        }
      });

      // Bind graph events to autosave, codegen and real-time collaboration
      this.graph.on('node:added', ({ node }) => {
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        if (!this.isApplyingRemoteUpdate && node && node.isNode()) {
          this.colabService.sendNodeOperation('add', node.id, {
            id: node.id,
            type: node.prop('nodeType') || 'class',
            position: node.position(),
            size: node.size(),
            data: node.getData()
          });
        }
      });

      this.graph.on('node:moved', ({ node }) => {
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        this.updateFloatingToolbarsPosition();
        if (!this.isApplyingRemoteUpdate && node && node.isNode()) {
          const pos = node.position();
          this.colabService.sendNodeOperation('move', node.id, {
            x: pos.x,
            y: pos.y,
            position: pos
          });
        }
      });

      this.graph.on('node:change:data', ({ node }) => {
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        if (!this.isApplyingRemoteUpdate && node && node.isNode()) {
          this.colabService.sendNodeOperation('update', node.id, {
            id: node.id,
            nodeType: node.prop('nodeType') || 'class',
            type: node.prop('nodeType') || 'class',
            data: node.getData(),
            size: node.size(),
            position: node.position()
          });
        }
      });

      this.graph.on('node:change:size', ({ node }) => {
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        if (!this.isApplyingRemoteUpdate && node && node.isNode()) {
          this.colabService.sendNodeOperation('update', node.id, {
            id: node.id,
            nodeType: node.prop('nodeType') || 'class',
            type: node.prop('nodeType') || 'class',
            size: node.size(),
            position: node.position()
          });
        }
      });

      this.graph.on('node:removed', ({ node }) => { 
        this.autoSave.markDirty(); 
        this.triggerCodegenPreview();
        this.closeNodeQuickToolbar();
        if (!this.isApplyingRemoteUpdate && node) {
          this.colabService.sendNodeOperation('delete', node.id, null);
        }
      });

      this.graph.on('edge:added', () => { 
        this.autoSave.markDirty(); 
        this.triggerCodegenPreview(); 
      });

      this.graph.on('edge:connected', ({ edge }) => {
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        this.canvasService.clearConnectionMode();
        this.graph.cleanSelection();
        this.graph.select(edge);
        this.ngZone.run(() => {
          this.openEdgeQuickToolbar(edge);
        });
        if (!this.isApplyingRemoteUpdate && edge) {
          const src = typeof edge.getSource() === 'object' ? (edge.getSource() as any).cell : edge.getSource();
          const tgt = typeof edge.getTarget() === 'object' ? (edge.getTarget() as any).cell : edge.getTarget();
          const edgeType = (edge.shape?.replace('uml-', '') || 'association') as EdgeType;
          this.colabService.sendEdgeOperation('add', edge.id, {
            id: edge.id,
            type: edgeType,
            source: src,
            target: tgt,
            labels: edge.getLabels ? edge.getLabels() : []
          });
        }
      });

      this.graph.on('edge:removed', ({ edge }) => { 
        this.autoSave.markDirty(); 
        this.triggerCodegenPreview(); 
        this.closeEdgeQuickToolbar();
        if (!this.isApplyingRemoteUpdate && edge) {
          this.colabService.sendEdgeOperation('delete', edge.id, null);
        }
      });

      this.graph.on('cell:selected', ({ cell }) => {
        if (!this.isApplyingRemoteUpdate) {
          this.colabService.acquireLock(cell.id);
        }
        this.ngZone.run(() => {
          if (cell.isEdge()) {
            this.openEdgeQuickToolbar(cell as any);
            this.closeNodeQuickToolbar();
          } else if (cell.isNode()) {
            this.openNodeQuickToolbar(cell as any);
            this.closeEdgeQuickToolbar();
          }
        });
      });

      this.graph.on('cell:unselected', ({ cell }) => {
        if (!this.isApplyingRemoteUpdate) {
          this.colabService.releaseLock(cell.id);
        }
      });

      // Node Click (Handles '+' buttons directly on SVG or opens toolbar)
      this.graph.on('node:click', ({ node, e }) => {
        const localPoint = this.graph.clientToLocal(e.clientX, e.clientY);
        const nodePos = node.position();
        const relY = localPoint.y - nodePos.y;
        const relX = localPoint.x - nodePos.x;
        const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
        const nodeType = (node.prop('nodeType') || 'class') as NodeType;
        const hasStereotype = !!(data.stereotype || nodeType === 'interface' || nodeType === 'enum' || nodeType === 'abstract');
        const headerHeight = hasStereotype ? 42 : 32;
        const attrLineCount = Math.max(1, data.attributes?.length || 1);
        const attrDividerY = headerHeight + attrLineCount * 18 + 12;

        // If clicked '+' button in attributes compartment
        if (relX >= node.size().width - 32 && relX <= node.size().width && relY >= headerHeight && relY <= headerHeight + 24) {
          this.canvasService.addNewAttributeToNode(node);
          this.autoSave.markDirty();
          this.triggerCodegenPreview();
          e.stopPropagation();
          return;
        }

        // If clicked '+' button in methods compartment
        if (relX >= node.size().width - 32 && relX <= node.size().width && relY >= attrDividerY && relY <= attrDividerY + 24) {
          this.canvasService.addNewMethodToNode(node);
          this.autoSave.markDirty();
          this.triggerCodegenPreview();
          e.stopPropagation();
          return;
        }

        this.ngZone.run(() => {
          this.openNodeQuickToolbar(node);
        });
      });

      // Double-click on node opens in-box direct inline editing
      this.graph.on('node:dblclick', ({ node, e }) => {
        const localPoint = this.graph.clientToLocal(e.clientX, e.clientY);
        const nodePos = node.position();
        const relY = localPoint.y - nodePos.y;
        const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
        const nodeType = (node.prop('nodeType') || 'class') as NodeType;
        const hasStereotype = !!(data.stereotype || nodeType === 'interface' || nodeType === 'enum' || nodeType === 'abstract');
        const headerHeight = hasStereotype ? 42 : 32;
        const attrLineCount = Math.max(1, data.attributes?.length || 1);
        const attrDividerY = headerHeight + attrLineCount * 18 + 12;

        this.ngZone.run(() => {
          if (relY <= headerHeight) {
            this.startInlineEditing(node, 'name');
          } else if (relY > headerHeight && relY <= attrDividerY) {
            this.startInlineEditing(node, 'attributes');
          } else {
            this.startInlineEditing(node, 'methods');
          }
        });
      });

      // Edge click & dblclick opens edge quick toolbar
      this.graph.on('edge:click', ({ edge }) => {
        this.ngZone.run(() => {
          this.openEdgeQuickToolbar(edge);
          this.closeNodeQuickToolbar();
        });
      });

      this.graph.on('edge:dblclick', ({ edge }) => {
        this.ngZone.run(() => {
          this.openEdgeQuickToolbar(edge);
          this.closeNodeQuickToolbar();
        });
      });

      // Blank click closes floating toolbars and saves inline edit
      this.graph.on('blank:click', () => {
        this.ngZone.run(() => {
          if (this.inlineEditingMode !== 'none') {
            this.saveInlineEditing();
          }
          this.closeEdgeQuickToolbar();
          this.closeNodeQuickToolbar();
        });
      });

      // Disable interaction on locked elements
      this.graph.on('node:mousedown', ({ node, e }) => {
        if (this.colabService.lockedElements().has(node.id)) {
          e.stopPropagation();
        }
      });

      if (this.diagram?.graph_data) {
        this.canvasService.fromGraphData(this.diagram.graph_data);
      }

      // Setup ResizeObserver for container
      this.resizeObserver = new ResizeObserver(() => {
        this.canvasService.resizeGraphToContainer();
        this.updateFloatingToolbarsPosition();
      });
      if (this.canvasWrapper?.nativeElement) {
        this.resizeObserver.observe(this.canvasWrapper.nativeElement);
      }
    });
  }

  // ─── Floating Edge Quick Toolbar ─────────────────────────────

  openEdgeQuickToolbar(edge: any) {
    if (!edge || !this.graph) return;
    this.selectedEdgeId = edge.id;
    this.quickEdgeType = (edge.shape?.replace('uml-', '') as EdgeType) || 'association';
    const labels = edge.getLabels ? edge.getLabels() : [];
    this.quickEdgeLabel = labels[0]?.attrs?.label?.text || labels[0]?.attrs?.text?.text || '';
    this.quickEdgeSourceMult = labels[1]?.attrs?.label?.text || labels[1]?.attrs?.text?.text || '';
    this.quickEdgeTargetMult = labels[2]?.attrs?.label?.text || labels[2]?.attrs?.text?.text || '';
    this.updateFloatingToolbarsPosition();
    this.cdr.detectChanges();
  }

  closeEdgeQuickToolbar() {
    this.selectedEdgeId = null;
    this.edgeToolbarPos = null;
    this.cdr.detectChanges();
  }

  quickChangeEdgeType(type: EdgeType) {
    if (!this.selectedEdgeId) return;
    this.quickEdgeType = type;
    const newEdge = this.canvasService.changeEdgeType(this.selectedEdgeId, type);
    if (newEdge) {
      this.selectedEdgeId = newEdge.id;
      this.onQuickEdgeChange();
      this.openEdgeQuickToolbar(newEdge);
    }
  }

  onQuickEdgeChange() {
    if (!this.selectedEdgeId) return;
    this.canvasService.updateEdgeProperties(this.selectedEdgeId, this.quickEdgeType, this.quickEdgeLabel, this.quickEdgeSourceMult, this.quickEdgeTargetMult);
    this.autoSave.markDirty();
    this.triggerCodegenPreview();
    if (!this.isApplyingRemoteUpdate) {
      const edge = this.graph.getCellById(this.selectedEdgeId);
      const src = edge?.isEdge() ? (typeof edge.getSource() === 'object' ? (edge.getSource() as any).cell : edge.getSource()) : undefined;
      const tgt = edge?.isEdge() ? (typeof edge.getTarget() === 'object' ? (edge.getTarget() as any).cell : edge.getTarget()) : undefined;
      this.colabService.sendEdgeOperation('update', this.selectedEdgeId, {
        id: this.selectedEdgeId,
        type: this.quickEdgeType,
        source: src,
        target: tgt,
        label: this.quickEdgeLabel,
        source_multiplicity: this.quickEdgeSourceMult,
        target_multiplicity: this.quickEdgeTargetMult
      });
    }
  }

  swapMultiplicities() {
    const temp = this.quickEdgeSourceMult;
    this.quickEdgeSourceMult = this.quickEdgeTargetMult;
    this.quickEdgeTargetMult = temp;
    this.onQuickEdgeChange();
  }

  deleteSelectedEdge() {
    if (!this.selectedEdgeId) return;
    const edge = this.graph.getCellById(this.selectedEdgeId);
    if (edge) this.graph.removeCell(edge);
    this.closeEdgeQuickToolbar();
    this.autoSave.markDirty();
    this.triggerCodegenPreview();
  }

  // ─── Floating Node Quick Toolbar ─────────────────────────────

  openNodeQuickToolbar(node: any) {
    if (!node || !this.graph) return;
    this.selectedNodeId = node.id;
    this.updateFloatingToolbarsPosition();
    this.cdr.detectChanges();
  }

  closeNodeQuickToolbar() {
    this.selectedNodeId = null;
    this.nodeToolbarPos = null;
    this.cdr.detectChanges();
  }

  quickAddAttributeToSelectedNode() {
    if (!this.selectedNodeId) return;
    this.canvasService.addNewAttributeToNode(this.selectedNodeId);
    this.autoSave.markDirty();
    this.triggerCodegenPreview();
  }

  quickAddMethodToSelectedNode() {
    if (!this.selectedNodeId) return;
    this.canvasService.addNewMethodToNode(this.selectedNodeId);
    this.autoSave.markDirty();
    this.triggerCodegenPreview();
  }

  deleteSelectedNode() {
    if (!this.selectedNodeId) return;
    const node = this.graph.getCellById(this.selectedNodeId);
    if (node) this.graph.removeCell(node);
    this.closeNodeQuickToolbar();
    this.autoSave.markDirty();
    this.triggerCodegenPreview();
  }

  // ─── In-Box Direct Inline Editing ────────────────────────────

  startInlineEditing(node: any, mode: 'name' | 'attributes' | 'methods') {
    this.inlineEditingNodeId = node.id;
    this.inlineEditingMode = mode;
    const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
    const nodeType = (node.prop('nodeType') || 'class') as NodeType;
    const hasStereotype = !!(data.stereotype || nodeType === 'interface' || nodeType === 'enum' || nodeType === 'abstract');
    const headerHeight = hasStereotype ? 42 : 32;
    const attrLineCount = Math.max(1, data.attributes?.length || 1);
    const attrDividerY = headerHeight + attrLineCount * 18 + 12;

    const pos = node.position();
    const size = node.size();
    const clientTopLeft = this.graph.localToClient(pos);
    const containerRect = this.graphContainer.nativeElement.getBoundingClientRect();
    const pixelX = clientTopLeft.x - containerRect.left;
    const pixelY = clientTopLeft.y - containerRect.top;
    const zoom = this.graph.zoom();

    if (mode === 'name') {
      this.inlineEditingText = data.name || '';
      this.inlineEditorPos = {
        x: pixelX + 10 * zoom,
        y: pixelY + (hasStereotype ? 20 : 4) * zoom,
        width: (size.width - 20) * zoom,
        height: 28 * zoom
      };
    } else if (mode === 'attributes') {
      this.inlineEditingText = data.attributes && data.attributes.length > 0
        ? data.attributes.map(a => `${a.visibility || '+'} ${a.name}: ${a.type || 'String'}${a.default_value ? ' = ' + a.default_value : ''}`).join('\n')
        : '+ id: Long\n+ nombre: String';
      this.inlineEditorPos = {
        x: pixelX + 6 * zoom,
        y: pixelY + (headerHeight + 2) * zoom,
        width: (size.width - 12) * zoom,
        height: Math.max(70, (attrDividerY - headerHeight - 4) * zoom)
      };
    } else if (mode === 'methods') {
      this.inlineEditingText = data.methods && data.methods.length > 0
        ? data.methods.map(m => `${m.visibility || '+'} ${m.name}(${m.params || ''}): ${m.return_type || 'void'}${m.is_abstract ? ' {abstract}' : ''}`).join('\n')
        : '+ nuevoMetodo(): void';
      this.inlineEditorPos = {
        x: pixelX + 6 * zoom,
        y: pixelY + (attrDividerY + 2) * zoom,
        width: (size.width - 12) * zoom,
        height: Math.max(70, (size.height - attrDividerY - 4) * zoom)
      };
    }
    this.cdr.detectChanges();
  }

  saveInlineEditing() {
    if (!this.inlineEditingNodeId || this.inlineEditingMode === 'none') return;
    const node = this.graph.getCellById(this.inlineEditingNodeId);
    if (node && node.isNode()) {
      const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
      if (this.inlineEditingMode === 'name') {
        data.name = this.inlineEditingText.trim() || 'Clase';
      } else if (this.inlineEditingMode === 'attributes') {
        data.attributes = this.parseAttributesFromText(this.inlineEditingText);
      } else if (this.inlineEditingMode === 'methods') {
        data.methods = this.parseMethodsFromText(this.inlineEditingText);
      }
      this.canvasService.updateNodeData(node, data);
      this.autoSave.markDirty();
      this.triggerCodegenPreview();
    }
    this.cancelInlineEditing();
  }

  cancelInlineEditing() {
    this.inlineEditingMode = 'none';
    this.inlineEditingNodeId = null;
    this.inlineEditingText = '';
    this.inlineEditorPos = null;
    this.cdr.detectChanges();
  }

  parseAttributesFromText(text: string): UMLAttribute[] {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0 && !l.startsWith('—'));
    return lines.map(line => {
      let vis: any = '+';
      let cleanLine = line;
      if (line.startsWith('+') || line.startsWith('-') || line.startsWith('#') || line.startsWith('~')) {
        vis = line[0];
        cleanLine = line.slice(1).trim();
      }
      const isStatic = cleanLine.startsWith('_') && cleanLine.endsWith('_');
      if (isStatic) cleanLine = cleanLine.slice(1, -1).trim();

      let name = cleanLine;
      let type = 'String';
      let defaultVal: string | null = null;

      if (cleanLine.includes('=')) {
        const parts = cleanLine.split('=');
        defaultVal = parts[1].trim();
        cleanLine = parts[0].trim();
      }

      if (cleanLine.includes(':')) {
        const parts = cleanLine.split(':');
        name = parts[0].trim();
        type = parts[1].trim() || 'String';
      }

      return {
        visibility: vis,
        name: name || 'attr',
        type: type || 'String',
        default_value: defaultVal,
        is_static: isStatic
      };
    });
  }

  parseMethodsFromText(text: string): UMLMethod[] {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0 && !l.startsWith('—'));
    return lines.map(line => {
      let vis: any = '+';
      let cleanLine = line;
      if (line.startsWith('+') || line.startsWith('-') || line.startsWith('#') || line.startsWith('~')) {
        vis = line[0];
        cleanLine = line.slice(1).trim();
      }
      const isAbstract = cleanLine.includes('{abstract}');
      if (isAbstract) cleanLine = cleanLine.replace('{abstract}', '').trim();

      let name = cleanLine;
      let params = '';
      let returnType = 'void';

      if (cleanLine.includes(':')) {
        const colonIdx = cleanLine.lastIndexOf(':');
        returnType = cleanLine.slice(colonIdx + 1).trim();
        cleanLine = cleanLine.slice(0, colonIdx).trim();
      }

      if (cleanLine.includes('(') && cleanLine.includes(')')) {
        const openParen = cleanLine.indexOf('(');
        const closeParen = cleanLine.lastIndexOf(')');
        name = cleanLine.slice(0, openParen).trim();
        params = cleanLine.slice(openParen + 1, closeParen).trim();
      }

      return {
        visibility: vis,
        name: name || 'metodo',
        params: params,
        return_type: returnType || 'void',
        is_static: false,
        is_abstract: isAbstract
      };
    });
  }

  updateFloatingToolbarsPosition() {
    if (!this.graph || !this.graphContainer) return;
    const containerRect = this.graphContainer.nativeElement.getBoundingClientRect();

    if (this.selectedEdgeId) {
      const edge = this.graph.getCellById(this.selectedEdgeId);
      if (edge && edge.isEdge()) {
        const bbox = (edge as any).getBBox();
        if (bbox) {
          const centerLocal = bbox.getCenter();
          const clientPt = this.graph.localToClient(centerLocal);
          this.edgeToolbarPos = {
            x: Math.max(16, Math.min(containerRect.width - 480, clientPt.x - containerRect.left - 240)),
            y: Math.max(16, clientPt.y - containerRect.top - 80)
          };
        }
      }
    }

    if (this.selectedNodeId) {
      const node = this.graph.getCellById(this.selectedNodeId);
      if (node && node.isNode()) {
        const pos = node.position();
        const clientPt = this.graph.localToClient(pos);
        this.nodeToolbarPos = {
          x: Math.max(16, clientPt.x - containerRect.left),
          y: Math.max(16, clientPt.y - containerRect.top - 38)
        };
      }
    }

    if (this.inlineEditingNodeId && this.inlineEditingMode !== 'none') {
      const node = this.graph.getCellById(this.inlineEditingNodeId);
      if (node && node.isNode()) {
        this.startInlineEditing(node, this.inlineEditingMode);
      }
    }
  }

  // ─── Panel Controls ───────────────────────────────────────────

  toggleToolbox() {
    this.isToolboxOpen = !this.isToolboxOpen;
    setTimeout(() => this.canvasService.resizeGraphToContainer(), 250);
  }

  toggleAiDrawer() {
    this.isAiDrawerOpen = !this.isAiDrawerOpen;
  }

  toggleLiveCode() {
    this.isLiveCodeOpen = !this.isLiveCodeOpen;
    if (this.isLiveCodeOpen && this.graph) {
      this.triggerCodegenPreview();
    }
  }

  togglePromptModal() {
    this.isPromptModalOpen = !this.isPromptModalOpen;
  }

  toggleCollabPanel() {
    this.isCollabPanelOpen = !this.isCollabPanelOpen;
  }

  // ─── Panel Resize Handlers ────────────────────────────────────

  startToolboxResize(event: MouseEvent) {
    event.preventDefault();
    this.isResizingToolbox = true;
    this.resizeStartX = event.clientX;
    this.resizeStartWidth = this.toolboxWidth;
  }

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    if (this.isResizingToolbox) {
      const delta = event.clientX - this.resizeStartX;
      this.toolboxWidth = Math.max(180, Math.min(400, this.resizeStartWidth + delta));
      this.canvasService.resizeGraphToContainer();
    }
  }

  @HostListener('document:mouseup')
  onMouseUp() {
    this.isResizingToolbox = false;
  }

  // ─── Toolbox Events ───────────────────────────────────────────

  onNodeDropped(event: { type: NodeType; x: number; y: number }) {
    // Handled by drop event listener on the canvas wrapper
  }

  onConnectionModeChanged(type: EdgeType | null) {
    this.canvasService.setConnectionMode(type);
  }

  // ─── Inline Node Edit Modal Methods ───────────────────────────

  openNodeEditModal(node: any) {
    this.editingNodeId = node.id;
    const rawData = node.getData() || {};
    this.editingNodeData = {
      name: rawData.name || 'Clase',
      stereotype: rawData.stereotype || null,
      attributes: Array.isArray(rawData.attributes) ? JSON.parse(JSON.stringify(rawData.attributes)) : [],
      methods: Array.isArray(rawData.methods) ? JSON.parse(JSON.stringify(rawData.methods)) : [],
      notes: rawData.notes || null
    };
    this.editingNodeType = (node.prop('nodeType') || 'class') as NodeType;
    this.isNodeEditModalOpen = true;
    this.cdr.detectChanges();
  }

  saveNodeEdit() {
    if (!this.editingNodeId || !this.graph) return;
    this.canvasService.updateNodeData(this.editingNodeId, this.editingNodeData, this.editingNodeType);
    this.autoSave.markDirty();
    this.triggerCodegenPreview();
    this.isNodeEditModalOpen = false;
    this.editingNodeId = null;
    this.cdr.detectChanges();
  }

  closeNodeEditModal() {
    this.isNodeEditModalOpen = false;
    this.editingNodeId = null;
    this.cdr.detectChanges();
  }

  openPropertiesPanel() {
    if (this.selectedNodeId && this.graph) {
      const node = this.graph.getCellById(this.selectedNodeId);
      if (node && node.isNode()) {
        this.openNodeEditModal(node);
        return;
      }
    }
    const nodes = this.graph?.getNodes();
    if (nodes && nodes.length > 0) {
      this.openNodeEditModal(nodes[0]);
    } else {
      alert('Selecciona una clase o relación en el lienzo para ver y editar sus atributos, métodos y propiedades.');
    }
  }

  addModalAttribute() {
    this.editingNodeData.attributes.push({
      visibility: '+',
      name: 'nuevoAtributo',
      type: 'String',
      default_value: null,
      is_static: false
    });
  }

  removeModalAttribute(index: number) {
    this.editingNodeData.attributes.splice(index, 1);
  }

  addModalMethod() {
    this.editingNodeData.methods.push({
      visibility: '+',
      name: 'nuevoMetodo',
      params: '',
      return_type: 'void',
      is_static: false,
      is_abstract: false
    });
  }

  removeModalMethod(index: number) {
    this.editingNodeData.methods.splice(index, 1);
  }

  // ─── Codegen ──────────────────────────────────────────────────

  triggerCodegenPreview() {
    if (this.codegenTimeout) clearTimeout(this.codegenTimeout);
    this.codegenTimeout = setTimeout(() => {
      if (!this.graph) return;
      const data = this.canvasService.toGraphData();
      this.codegenService.isLoading.set(true);
      this.codegenService.getPreview(this.diagramId, data).subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.codegenService.generatedFiles.set(res.data.files);
          }
          this.codegenService.isLoading.set(false);
        },
        error: () => this.codegenService.isLoading.set(false)
      });
    }, 300);
  }

  // ─── Save ─────────────────────────────────────────────────────

  async manualSave() {
    await this.autoSave.forceSaveNow();
  }

  // ─── Canvas Branding & Rename Modal ─────────────────────────

  openCanvasEditModal() {
    if (!this.diagram) return;
    this.canvasEditForm = {
      name: this.diagram.name || '',
      description: this.diagram.description || '',
      image_url: this.diagram.image_url || null
    };
    this.canvasLogoPreview = this.diagram.image_url || null;
    this.isCanvasEditModalOpen = true;
    this.cdr.markForCheck();
  }

  closeCanvasEditModal() {
    this.isCanvasEditModalOpen = false;
    this.canvasLogoPreview = null;
    this.cdr.markForCheck();
  }

  onCanvasLogoFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      if (file.size > 3 * 1024 * 1024) {
        alert('La imagen no debe superar los 3MB.');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        this.canvasEditForm.image_url = base64;
        this.canvasLogoPreview = base64;
        this.cdr.markForCheck();
      };
      reader.readAsDataURL(file);
    }
  }

  removeCanvasLogo() {
    this.canvasEditForm.image_url = null;
    this.canvasLogoPreview = null;
    this.cdr.markForCheck();
  }

  saveCanvasEdit() {
    if (!this.diagram || !this.canvasEditForm.name.trim()) return;
    this.isSavingCanvasEdit = true;
    this.diagramService.updateDiagram(this.diagramId, {
      name: this.canvasEditForm.name.trim(),
      description: this.canvasEditForm.description?.trim(),
      image_url: this.canvasEditForm.image_url
    }).subscribe({
      next: (res) => {
        this.isSavingCanvasEdit = false;
        if (res.success && res.data) {
          if (this.diagram) {
            this.diagram.name = res.data.name;
            this.diagram.description = res.data.description;
            this.diagram.image_url = res.data.image_url;
          }
          this.closeCanvasEditModal();
        } else {
          alert(res.message || 'Error al actualizar diagrama');
        }
      },
      error: (err) => {
        this.isSavingCanvasEdit = false;
        console.error('Error al actualizar diagrama:', err);
        alert('Error: ' + (err.error?.detail || err.message));
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Canvas Participants Modal ────────────────────────────────

  openCanvasParticipantsModal() {
    this.isCanvasParticipantsModalOpen = true;
    this.canvasParticipantsLoading = true;
    this.canvasSelectedParticipantIds.clear();

    this.diagramService.getParticipants(this.diagramId).subscribe({
      next: (res) => {
        this.canvasParticipantsLoading = false;
        if (res.success && res.data) {
          this.canvasParticipantsData = res.data;
          const assigned = res.data.assigned_member_ids || [];
          this.canvasSelectedParticipantIds = new Set(assigned);
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.canvasParticipantsLoading = false;
        console.error('Error al obtener participantes:', err);
        alert('Error: ' + (err.error?.detail || err.message));
        this.cdr.markForCheck();
      }
    });
  }

  closeCanvasParticipantsModal() {
    this.isCanvasParticipantsModalOpen = false;
    this.canvasParticipantsData = null;
    this.canvasSelectedParticipantIds.clear();
    this.cdr.markForCheck();
  }

  toggleCanvasParticipant(id: string) {
    if (this.canvasSelectedParticipantIds.has(id)) {
      this.canvasSelectedParticipantIds.delete(id);
    } else {
      this.canvasSelectedParticipantIds.add(id);
    }
    this.cdr.markForCheck();
  }

  saveCanvasParticipants() {
    this.isSavingCanvasParticipants = true;
    const memberIds = Array.from(this.canvasSelectedParticipantIds);

    this.diagramService.updateParticipants(this.diagramId, memberIds).subscribe({
      next: (res) => {
        this.isSavingCanvasParticipants = false;
        if (res.success) {
          if (this.diagram) {
            this.diagram.member_ids = memberIds;
          }
          this.closeCanvasParticipantsModal();
        } else {
          alert(res.message || 'Error al actualizar participantes');
        }
      },
      error: (err) => {
        this.isSavingCanvasParticipants = false;
        console.error('Error al guardar participantes:', err);
        alert('Error: ' + (err.error?.detail || err.message));
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Navigation ───────────────────────────────────────────────

  goBack() {
    this.router.navigate(['/diagrams']);
  }

  // ─── Cleanup ──────────────────────────────────────────────────

  ngOnDestroy() {
    this.subs.unsubscribe();
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    if (this.graph) {
      this.graph.dispose();
    }
  }
}
