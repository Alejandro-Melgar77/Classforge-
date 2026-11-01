import { Component, OnInit, AfterViewInit, ViewChild, ElementRef, NgZone, ChangeDetectionStrategy, inject, OnDestroy, HostListener, signal, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { Graph, Node, Edge, Cell } from '@antv/x6';
import { CanvasService } from '../services/canvas.service';
import { AutoSaveService } from '../services/auto-save.service';
import { DiagramService } from '../services/diagram.service';
import { Diagram, NodeType, EdgeType, UMLNodeData, UMLAttribute, UMLMethod } from '../models/diagram.model';
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
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';
import { NodeEditModalComponent } from './modals/node-edit-modal.component';
import { CanvasEditModalComponent } from './modals/canvas-edit-modal.component';
import { CanvasParticipantsModalComponent } from './modals/canvas-participants-modal.component';
import { CanvasHistoryModalComponent } from './modals/canvas-history-modal.component';
import { EditorShortcutsModalComponent } from './modals/editor-shortcuts-modal.component';

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
    ToolboxPaletteComponent,
    NodeEditModalComponent,
    CanvasEditModalComponent,
    CanvasParticipantsModalComponent,
    CanvasHistoryModalComponent,
    EditorShortcutsModalComponent
  ],
  templateUrl: './diagram-canvas.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DiagramCanvasComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('graphContainer') graphContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('minimapContainer') minimapContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('canvasWrapper') canvasWrapper!: ElementRef<HTMLDivElement>;

  public canvasService = inject(CanvasService);
  public autoSave = inject(AutoSaveService);
  public diagramService = inject(DiagramService);
  public colabService = inject(CollaborationService);
  public codegenService = inject(CodegenService);
  public authService = inject(AuthService);
  public toastService = inject(ToastService);
  public confirmService = inject(ConfirmDialogService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private ngZone = inject(NgZone);
  private cdr = inject(ChangeDetectorRef);

  diagramId!: string;
  diagram: Diagram | null = null;
  graph!: Graph;

  get currentUser() { return this.authService.getCurrentUser(); }
  get isAdmin(): boolean { return this.authService.hasRole('admin'); }
  get isScrumMaster(): boolean { return this.authService.hasRole('scrum_master'); }
  get canManage(): boolean { return this.isAdmin || this.isScrumMaster; }

  // Estados responsivos y paneles
  isMobileViewer = signal<boolean>(false);
  isToolboxOpen = true;
  toolboxWidth = 240;
  isAiDrawerOpen = false;
  isLiveCodeOpen = false;
  isPromptModalOpen = false;
  isCollabPanelOpen = false;
  projectId?: string;

  // Estados de modales desacoplados
  isNodeEditModalOpen = false;
  editingNodeData: UMLNodeData = { name: 'Clase', stereotype: null, attributes: [], methods: [], notes: null };
  editingNodeType: NodeType = 'class';
  editingNodeId: string | null = null;

  isCanvasEditModalOpen = false;
  isCanvasParticipantsModalOpen = false;
  isCanvasHistoryModalOpen = false;
  isShortcutsModalOpen = false;

  // Barras flotantes rápidas
  selectedEdgeId: string | null = null;
  edgeToolbarPos: { x: number; y: number } | null = null;
  quickEdgeType: EdgeType = 'association';
  quickEdgeLabel = '';
  quickEdgeSourceMult = '';
  quickEdgeTargetMult = '';
  cardinalityOptions = ['', '1', '0..1', '1..*', '0..*', '*', '1..1', '0..n', '1..n'];

  selectedNodeId: string | null = null;
  nodeToolbarPos: { x: number; y: number } | null = null;

  // In-box direct inline editing
  inlineEditingMode: 'none' | 'name' | 'attributes' | 'methods' = 'none';
  inlineEditingNodeId: string | null = null;
  inlineEditingText = '';
  inlineEditorPos: { x: number; y: number; width: number; height: number } | null = null;

  // Resize estado
  private isResizingToolbox = false;
  private resizeStartX = 0;
  private resizeStartWidth = 0;

  private isApplyingRemoteUpdate = false;
  private subs = new Subscription();
  private codegenTimeout: any = null;
  private resizeObserver: ResizeObserver | null = null;

  // Referencias a listeners DOM para limpieza garantizada en ngOnDestroy
  private mouseMoveListener?: (e: MouseEvent) => void;
  private dragOverListener?: (e: DragEvent) => void;
  private dropListener?: (e: DragEvent) => void;

  ngOnInit() {
    this.diagramId = this.route.snapshot.paramMap.get('id')!;
    this.checkScreenSize();

    this.autoSave.init(this.diagramId, () => this.canvasService.toGraphData());
    this.colabService.connect(this.diagramId);

    // Cargar diagrama
    this.diagramService.getDiagram(this.diagramId).subscribe(res => {
      if (res.success && res.data) {
        this.diagram = res.data;
        this.projectId = (res.data as any)?.project_id || (res.data as any)?.project || undefined;
        if (this.graph && this.diagram.graph_data) {
          this.canvasService.fromGraphData(this.diagram.graph_data);
        }
        this.cdr.markForCheck();
      }
    });

    // Suscripción a operaciones remotas
    this.subs.add(
      this.colabService.remoteOperations$.subscribe(msg => {
        this.handleRemoteOperation(msg);
      })
    );

    // Suscripción a OP_REJECTED (reversión local y aviso)
    this.subs.add(
      this.colabService.opRejected$.subscribe(({ element_id, reason }) => {
        this.revertRejectedElement(element_id);
      })
    );
  }

  @HostListener('window:resize')
  onWindowResize() {
    this.checkScreenSize();
  }

  private checkScreenSize() {
    if (typeof window !== 'undefined') {
      const isMobile = window.innerWidth < 768;
      this.isMobileViewer.set(isMobile);
      if (isMobile) {
        this.isToolboxOpen = false;
      }
    }
  }

  ngAfterViewInit() {
    this.ngZone.runOutsideAngular(() => {
      this.graph = this.canvasService.initGraph(
        this.graphContainer.nativeElement,
        this.minimapContainer.nativeElement
      );

      // Listener de cursor
      this.mouseMoveListener = (e: MouseEvent) => {
        const rect = this.graphContainer.nativeElement.getBoundingClientRect();
        this.colabService.sendCursor(e.clientX - rect.left, e.clientY - rect.top);
      };
      this.graphContainer.nativeElement.addEventListener('mousemove', this.mouseMoveListener);

      // Drag and drop toolbox
      const wrapper = this.canvasWrapper?.nativeElement || this.graphContainer.nativeElement.parentElement;
      if (wrapper) {
        this.dragOverListener = (e: DragEvent) => {
          e.preventDefault();
          if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
        };
        this.dropListener = (e: DragEvent) => {
          e.preventDefault();
          if (this.isMobileViewer()) return; // Solo lectura en móvil
          const nodeType = e.dataTransfer?.getData('application/classforge-node') as NodeType;
          if (nodeType && this.graph) {
            const localPoint = this.graph.clientToLocal(e.clientX, e.clientY);
            this.canvasService.addNode(nodeType, { x: localPoint.x, y: localPoint.y });
          }
        };
        wrapper.addEventListener('dragover', this.dragOverListener);
        wrapper.addEventListener('drop', this.dropListener);
      }

      this.bindGraphEvents();

      if (this.diagram?.graph_data) {
        this.canvasService.fromGraphData(this.diagram.graph_data);
      }

      this.resizeObserver = new ResizeObserver(() => {
        this.canvasService.resizeGraphToContainer();
        this.updateFloatingToolbarsPosition();
      });
      if (this.canvasWrapper?.nativeElement) {
        this.resizeObserver.observe(this.canvasWrapper.nativeElement);
      }
    });
  }

  private bindGraphEvents() {
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

    this.graph.on('node:removed', ({ node }) => {
      this.autoSave.markDirty();
      this.triggerCodegenPreview();
      this.closeNodeQuickToolbar();
      if (!this.isApplyingRemoteUpdate && node) {
        this.colabService.sendNodeOperation('delete', node.id, null);
      }
    });

    this.graph.on('edge:connected', ({ edge }) => {
      this.autoSave.markDirty();
      this.triggerCodegenPreview();
      this.canvasService.clearConnectionMode();
      this.graph.cleanSelection();
      this.graph.select(edge);
      this.ngZone.run(() => this.openEdgeQuickToolbar(edge));
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

      // Clic '+' en atributos
      if (relX >= node.size().width - 32 && relX <= node.size().width && relY >= headerHeight && relY <= headerHeight + 24) {
        this.canvasService.addNewAttributeToNode(node);
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        e.stopPropagation();
        return;
      }

      // Clic '+' en métodos
      if (relX >= node.size().width - 32 && relX <= node.size().width && relY >= attrDividerY && relY <= attrDividerY + 24) {
        this.canvasService.addNewMethodToNode(node);
        this.autoSave.markDirty();
        this.triggerCodegenPreview();
        e.stopPropagation();
        return;
      }

      this.ngZone.run(() => this.openNodeQuickToolbar(node));
    });

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

    this.graph.on('blank:click', () => {
      this.ngZone.run(() => {
        if (this.inlineEditingMode !== 'none') this.saveInlineEditing();
        this.closeEdgeQuickToolbar();
        this.closeNodeQuickToolbar();
      });
    });

    // Bloquear interacción si el elemento está bloqueado por otro
    this.graph.on('node:mousedown', ({ node, e }) => {
      const lockedBy = this.colabService.lockedElements().get(node.id);
      if (lockedBy && lockedBy !== this.currentUser?.id) {
        e.stopPropagation();
        const owner = this.colabService.getLockOwner(node.id);
        this.toastService.info(`El nodo está siendo editado por ${owner ? owner.name : 'otro usuario'}`);
      }
    });
  }

  // ─── Reversión ante OP_REJECTED ─────────────────────────────
  private revertRejectedElement(elementId: string) {
    if (!this.graph || !elementId) return;
    this.diagramService.getDiagram(this.diagramId).subscribe(res => {
      if (res.success && res.data?.graph_data) {
        const remoteNode = res.data.graph_data.nodes?.find(n => n.id === elementId);
        const cell = this.graph.getCellById(elementId);
        if (cell && cell.isNode() && remoteNode) {
          cell.position(remoteNode.position.x, remoteNode.position.y);
          this.canvasService.updateNodeData(cell as Node, remoteNode.data, remoteNode.type);
        }
        this.cdr.markForCheck();
      }
    });
  }

  // ─── Manejo de Operaciones Remotas ───────────────────────────
  private handleRemoteOperation(msg: any) {
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
          const existing = this.graph.getCellById(nodeId);
          if (!existing) {
            this.canvasService.addNode(data.type || 'class', data.position, nodeId, data.data, data.size, false);
          }
        } else if (op === 'move' && data) {
          const node = this.graph.getCellById(nodeId);
          if (node && node.isNode()) {
            const posX = data.position?.x ?? data.x;
            const posY = data.position?.y ?? data.y;
            if (posX !== undefined && posY !== undefined) node.position(posX, posY);
          }
        } else if (op === 'update' && data) {
          const node = this.graph.getCellById(nodeId);
          if (node && node.isNode()) {
            if (data.data) this.canvasService.updateNodeData(node as Node, data.data, data.nodeType || data.type);
            if (data.position) node.position(data.position.x, data.position.y);
            if (data.size) node.resize(data.size.width, data.size.height);
          }
        } else if (op === 'delete') {
          const node = this.graph.getCellById(nodeId);
          if (node) this.graph.removeCell(node);
        }
      } else if (isEdgeOp && edgeId) {
        if (op === 'add' && data) {
          const existing = this.graph.getCellById(edgeId);
          if (!existing && data.source && data.target) {
            const src = typeof data.source === 'object' ? data.source.cell : data.source;
            const tgt = typeof data.target === 'object' ? data.target.cell : data.target;
            this.canvasService.addRemoteEdge(edgeId, data.type || 'association', src, tgt, data.label, data.source_multiplicity, data.target_multiplicity, data.labels);
          }
        } else if (op === 'update' && data) {
          this.canvasService.updateEdgeProperties(edgeId, data.type || 'association', data.label || '', data.source_multiplicity || '', data.target_multiplicity || '');
        } else if (op === 'delete') {
          const edge = this.graph.getCellById(edgeId);
          if (edge) this.graph.removeCell(edge);
        }
      }
    } finally {
      this.isApplyingRemoteUpdate = false;
      this.triggerCodegenPreview();
      this.updateFloatingToolbarsPosition();
      this.cdr.markForCheck();
    }
  }

  // ─── Navegación por Teclado Accesible ─────────────────────────
  @HostListener('document:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent) {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;

    const ctrl = event.ctrlKey || event.metaKey;

    // Guardar
    if (ctrl && (event.key === 's' || event.key === 'S')) {
      event.preventDefault();
      this.autoSave.forceSaveNow();
      return;
    }

    // Ayuda atajos
    if (event.key === '?' || (event.shiftKey && event.key === '/')) {
      event.preventDefault();
      this.isShortcutsModalOpen = true;
      this.cdr.markForCheck();
      return;
    }

    // Tab / Shift+Tab para ciclar selección de nodos
    if (event.key === 'Tab') {
      event.preventDefault();
      this.cycleNodeSelection(event.shiftKey);
      return;
    }

    // Flechas para mover nodo seleccionado
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      if (this.selectedNodeId && !event.altKey) {
        event.preventDefault();
        this.nudgeSelectedNode(event.key, event.shiftKey ? 50 : 10);
        return;
      } else if (event.altKey && this.graph) {
        // Pan con teclado
        event.preventDefault();
        this.panCanvasWithKeyboard(event.key);
        return;
      }
    }

    // Zoom con + y -
    if ((event.key === '+' || event.key === '=') && !ctrl) {
      event.preventDefault();
      this.canvasService.zoomIn();
      return;
    }
    if ((event.key === '-' || event.key === '_') && !ctrl) {
      event.preventDefault();
      this.canvasService.zoomOut();
      return;
    }

    // Eliminar seleccionado
    if (event.key === 'Delete' || event.key === 'Backspace') {
      if (this.selectedNodeId) {
        event.preventDefault();
        this.deleteSelectedNode();
      } else if (this.selectedEdgeId) {
        event.preventDefault();
        this.deleteSelectedEdge();
      }
      return;
    }

    // Escape
    if (event.key === 'Escape') {
      this.closeNodeQuickToolbar();
      this.closeEdgeQuickToolbar();
      this.graph?.cleanSelection();
      return;
    }

    // Ajustar vista (F)
    if (!ctrl && (event.key === 'f' || event.key === 'F')) {
      event.preventDefault();
      this.canvasService.fitView();
      return;
    }
  }

  private cycleNodeSelection(reverse: boolean) {
    if (!this.graph) return;
    const nodes = this.graph.getNodes();
    if (nodes.length === 0) return;

    let currentIndex = -1;
    if (this.selectedNodeId) {
      currentIndex = nodes.findIndex(n => n.id === this.selectedNodeId);
    }

    let nextIndex = 0;
    if (currentIndex >= 0) {
      nextIndex = reverse ? (currentIndex - 1 + nodes.length) % nodes.length : (currentIndex + 1) % nodes.length;
    }

    const targetNode = nodes[nextIndex];
    this.graph.cleanSelection();
    this.graph.select(targetNode);
    this.openNodeQuickToolbar(targetNode);
  }

  private nudgeSelectedNode(key: string, step: number) {
    if (!this.selectedNodeId || !this.graph) return;
    const node = this.graph.getCellById(this.selectedNodeId);
    if (!node || !node.isNode()) return;

    const pos = node.position();
    let dx = 0;
    let dy = 0;
    if (key === 'ArrowUp') dy = -step;
    if (key === 'ArrowDown') dy = step;
    if (key === 'ArrowLeft') dx = -step;
    if (key === 'ArrowRight') dx = step;

    node.position(pos.x + dx, pos.y + dy);
    this.autoSave.markDirty();
    this.updateFloatingToolbarsPosition();
  }

  private panCanvasWithKeyboard(key: string) {
    if (!this.graph) return;
    const step = 40;
    let dx = 0;
    let dy = 0;
    if (key === 'ArrowUp') dy = step;
    if (key === 'ArrowDown') dy = -step;
    if (key === 'ArrowLeft') dx = step;
    if (key === 'ArrowRight') dx = -step;
    (this.graph as any).translateBy?.(dx, dy);
  }

  // ─── Floating Toolbars ───────────────────────────────────────
  openEdgeQuickToolbar(edge: Edge) {
    if (!edge || !this.graph) return;
    this.selectedEdgeId = edge.id;
    this.quickEdgeType = (edge.shape?.replace('uml-', '') as EdgeType) || 'association';
    const labels = edge.getLabels ? edge.getLabels() : [];
    const getLabelText = (idx: number): string => {
      const l = labels[idx];
      const attrs = l?.attrs as Record<string, any>;
      const labelObj = attrs?.['label'] || attrs?.['text'];
      return typeof labelObj?.['text'] === 'string' ? labelObj['text'] : '';
    };
    this.quickEdgeLabel = getLabelText(0);
    this.quickEdgeSourceMult = getLabelText(1);
    this.quickEdgeTargetMult = getLabelText(2);
    this.updateFloatingToolbarsPosition();
    this.cdr.markForCheck();
  }

  closeEdgeQuickToolbar() {
    this.selectedEdgeId = null;
    this.edgeToolbarPos = null;
    this.cdr.markForCheck();
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
  }

  openNodeQuickToolbar(node: Node) {
    if (!node || !this.graph) return;
    this.selectedNodeId = node.id;
    this.updateFloatingToolbarsPosition();
    this.cdr.markForCheck();
  }

  closeNodeQuickToolbar() {
    this.selectedNodeId = null;
    this.nodeToolbarPos = null;
    this.cdr.markForCheck();
  }

  deleteSelectedNode() {
    if (!this.selectedNodeId) return;
    const node = this.graph.getCellById(this.selectedNodeId);
    if (node) this.graph.removeCell(node);
    this.closeNodeQuickToolbar();
    this.autoSave.markDirty();
  }

  // ─── Inline Editing ──────────────────────────────────────────
  startInlineEditing(node: Node, mode: 'name' | 'attributes' | 'methods') {
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
      this.inlineEditorPos = { x: pixelX + 10 * zoom, y: pixelY + (hasStereotype ? 20 : 4) * zoom, width: (size.width - 20) * zoom, height: 28 * zoom };
    } else if (mode === 'attributes') {
      this.inlineEditingText = data.attributes?.map(a => `${a.visibility || '+'} ${a.name}: ${a.type || 'String'}`).join('\n') || '+ id: Long';
      this.inlineEditorPos = { x: pixelX + 6 * zoom, y: pixelY + (headerHeight + 2) * zoom, width: (size.width - 12) * zoom, height: Math.max(70, (attrDividerY - headerHeight - 4) * zoom) };
    } else if (mode === 'methods') {
      this.inlineEditingText = data.methods?.map(m => `${m.visibility || '+'} ${m.name}(${m.params || ''}): ${m.return_type || 'void'}`).join('\n') || '+ nuevoMetodo(): void';
      this.inlineEditorPos = { x: pixelX + 6 * zoom, y: pixelY + (attrDividerY + 2) * zoom, width: (size.width - 12) * zoom, height: Math.max(70, (size.height - attrDividerY - 4) * zoom) };
    }
    this.cdr.markForCheck();
  }

  saveInlineEditing() {
    if (!this.inlineEditingNodeId || this.inlineEditingMode === 'none') return;
    const node = this.graph.getCellById(this.inlineEditingNodeId);
    if (node && node.isNode()) {
      const data = (node.getData() as UMLNodeData) || { name: 'Clase', attributes: [], methods: [] };
      if (this.inlineEditingMode === 'name') {
        data.name = this.inlineEditingText.trim() || 'Clase';
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
    this.cdr.markForCheck();
  }

  updateFloatingToolbarsPosition() {
    if (!this.graph || !this.graphContainer) return;
    const containerRect = this.graphContainer.nativeElement.getBoundingClientRect();

    if (this.selectedEdgeId) {
      const edge = this.graph.getCellById(this.selectedEdgeId);
      if (edge && edge.isEdge()) {
        const bbox = (edge as any).getBBox();
        if (bbox) {
          const clientPt = this.graph.localToClient(bbox.getCenter());
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
        const clientPt = this.graph.localToClient(node.position());
        this.nodeToolbarPos = {
          x: Math.max(16, clientPt.x - containerRect.left),
          y: Math.max(16, clientPt.y - containerRect.top - 38)
        };
      }
    }
  }

  // ─── Manejo de Paneles & Modales ─────────────────────────────
  toggleToolbox() {
    this.isToolboxOpen = !this.isToolboxOpen;
    setTimeout(() => this.canvasService.resizeGraphToContainer(), 250);
  }

  startToolboxResize(event: MouseEvent) {
    event.preventDefault();
    this.isResizingToolbox = true;
    this.resizeStartX = event.clientX;
    this.resizeStartWidth = this.toolboxWidth;
  }

  @HostListener('document:mousemove', ['$event'])
  onDocMouseMove(event: MouseEvent) {
    if (this.isResizingToolbox) {
      const delta = event.clientX - this.resizeStartX;
      this.toolboxWidth = Math.max(180, Math.min(400, this.resizeStartWidth + delta));
      this.canvasService.resizeGraphToContainer();
    }
  }

  @HostListener('document:mouseup')
  onDocMouseUp() {
    this.isResizingToolbox = false;
  }

  openNodeEditModal(cellOrNode?: Node | Cell | null) {
    const node = (cellOrNode?.isNode() ? cellOrNode : (this.selectedNodeId ? this.graph?.getCellById(this.selectedNodeId) : this.graph?.getNodes()[0])) as Node;
    if (!node) {
      this.toastService.info('Selecciona una clase o elemento en el lienzo para editar sus propiedades');
      return;
    }
    this.editingNodeId = node.id;
    this.editingNodeData = (node.getData() || { name: 'Clase', attributes: [], methods: [] }) as UMLNodeData;
    this.editingNodeType = (node.prop('nodeType') || 'class') as NodeType;
    this.isNodeEditModalOpen = true;
    this.cdr.markForCheck();
  }

  onSaveNodeEdit({ data, type }: { data: UMLNodeData; type: NodeType }) {
    if (this.editingNodeId && this.graph) {
      this.canvasService.updateNodeData(this.editingNodeId, data, type);
      this.autoSave.markDirty();
      this.triggerCodegenPreview();
      this.isNodeEditModalOpen = false;
      this.editingNodeId = null;
      this.cdr.markForCheck();
    }
  }

  onVersionRestored(newDiagram: Diagram) {
    this.diagram = newDiagram;
    if (newDiagram.graph_data) {
      this.canvasService.fromGraphData(newDiagram.graph_data);
    }
    this.cdr.markForCheck();
  }

  onDiagramUpdated(updated: { name: string; description?: string; image_url: string | null }) {
    if (this.diagram) {
      this.diagram.name = updated.name;
      this.diagram.description = updated.description ?? '';
      this.diagram.image_url = updated.image_url;
      this.cdr.markForCheck();
    }
  }

  onParticipantsUpdated(ids: string[]) {
    if (this.diagram) {
      this.diagram.member_ids = ids;
      this.cdr.markForCheck();
    }
  }

  triggerCodegenPreview() {
    clearTimeout(this.codegenTimeout);
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
    }, 400);
  }

  goBack() {
    if (this.diagram?.project_id) {
      this.router.navigate(['/projects', this.diagram.project_id, 'diagramas']);
    } else {
      this.router.navigate(['/diagrams']);
    }
  }

  // ─── Cleanup Total Libre de Fugas ─────────────────────────────
  ngOnDestroy() {
    this.subs.unsubscribe();
    clearTimeout(this.codegenTimeout);

    if (this.mouseMoveListener && this.graphContainer?.nativeElement) {
      this.graphContainer.nativeElement.removeEventListener('mousemove', this.mouseMoveListener);
    }
    const wrapper = this.canvasWrapper?.nativeElement;
    if (wrapper) {
      if (this.dragOverListener) wrapper.removeEventListener('dragover', this.dragOverListener);
      if (this.dropListener) wrapper.removeEventListener('drop', this.dropListener);
    }

    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }

    this.colabService.disconnect();
    this.autoSave.destroy();

    if (this.graph) {
      this.graph.dispose();
    }
  }
}
