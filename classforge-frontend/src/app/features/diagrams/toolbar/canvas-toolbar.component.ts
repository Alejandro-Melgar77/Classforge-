import { Component, inject, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { 
  LucideAngularModule, 
  LUCIDE_ICONS, 
  LucideIconProvider, 
  Undo, Redo, Trash2, Copy, ClipboardPaste, 
  Maximize, ZoomIn, ZoomOut, Download, Upload, 
  LayoutGrid, HelpCircle, RefreshCw 
} from 'lucide-angular';
import { CanvasService } from '../services/canvas.service';
import { DiagramService } from '../services/diagram.service';
import { AutoSaveService } from '../services/auto-save.service';
import { ToastService } from '../../../core/services/toast.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'canvas-toolbar',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Undo, Redo, Trash2, Copy, ClipboardPaste,
        Maximize, ZoomIn, ZoomOut, Download, Upload,
        LayoutGrid, HelpCircle, RefreshCw
      })
    }
  ],
  templateUrl: './canvas-toolbar.component.html',
})
export class CanvasToolbarComponent {
  private canvasService = inject(CanvasService);
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);
  public autoSave = inject(AutoSaveService);
  private route = inject(ActivatedRoute);

  @Output() openShortcuts = new EventEmitter<void>();

  exportMenuOpen = false;
  isExporting = false;
  isImporting = false;

  get diagramId(): string {
    return this.route.snapshot.paramMap.get('id') || '';
  }

  // Actions
  undo() { this.canvasService.undo(); }
  redo() { this.canvasService.redo(); }
  deleteSelected() { this.canvasService.deleteSelected(); }
  fitView() { this.canvasService.fitView(); }
  autoLayout() { this.canvasService.autoLayout(); }
  zoomIn() { this.canvasService.zoomIn(); }
  zoomOut() { this.canvasService.zoomOut(); }

  copy() {
    const graph = this.canvasService.getGraph();
    if (graph) {
      const selected = graph.getSelectedCells();
      if (selected.length > 0) {
        graph.copy(selected);
        this.toastService.info('Elementos copiados al portapapeles');
      }
    }
  }

  paste() {
    const graph = this.canvasService.getGraph();
    if (graph) {
      graph.paste();
      this.autoSave.markDirty();
    }
  }

  toggleExportMenu() {
    this.exportMenuOpen = !this.exportMenuOpen;
  }

  async exportPng() {
    this.exportMenuOpen = false;
    this.isExporting = true;
    try {
      await this.canvasService.exportPng();
      this.toastService.success('Imagen PNG generada correctamente');
    } catch {
      this.toastService.error('Error al exportar PNG');
    } finally {
      this.isExporting = false;
    }
  }

  async exportPdf() {
    this.exportMenuOpen = false;
    this.isExporting = true;
    try {
      await this.canvasService.exportPdf('classforge-diagram');
      this.toastService.success('Documento PDF generado correctamente');
    } catch {
      this.toastService.error('Error al exportar PDF');
    } finally {
      this.isExporting = false;
    }
  }

  exportXmi() {
    this.exportMenuOpen = false;
    if (!this.diagramId) return;
    this.isExporting = true;
    this.diagramService.exportXmi(this.diagramId).subscribe({
      next: (blob) => {
        this.isExporting = false;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `diagram_${this.diagramId}.xmi`;
        a.click();
        URL.revokeObjectURL(url);
        this.toastService.success('Archivo XMI exportado con éxito');
      },
      error: () => {
        this.isExporting = false;
        this.toastService.error('Error al exportar archivo XMI');
      }
    });
  }

  exportJson() {
    this.exportMenuOpen = false;
    if (!this.diagramId) return;
    this.isExporting = true;
    this.diagramService.exportJson(this.diagramId).subscribe({
      next: (blob) => {
        this.isExporting = false;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `diagram_${this.diagramId}.json`;
        a.click();
        URL.revokeObjectURL(url);
        this.toastService.success('Archivo JSON exportado con éxito');
      },
      error: () => {
        this.isExporting = false;
        this.toastService.error('Error al exportar archivo JSON');
      }
    });
  }

  importXmi(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0 || !this.diagramId) return;
    const file = input.files[0];

    // Validación de extensión
    const validExtensions = ['.xmi', '.xml'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));
    if (!isValid) {
      this.toastService.warning('Formato no válido. Debe ser un archivo .xmi o .xml');
      input.value = '';
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.toastService.warning('El archivo supera el límite de 10 MB');
      input.value = '';
      return;
    }

    this.isImporting = true;
    this.toastService.info('Importando archivo XMI...');

    this.diagramService.importXmi(this.diagramId, file).subscribe({
      next: (res) => {
        this.isImporting = false;
        if (res.success && res.data?.graph_data) {
          this.canvasService.fromGraphData(res.data.graph_data);
          this.autoSave.markDirty();
          this.toastService.success('XMI importado exitosamente');
        } else {
          this.toastService.error(res.message || 'Error al procesar XMI');
        }
      },
      error: (err) => {
        this.isImporting = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al procesar archivo XMI');
      }
    });
    input.value = '';
  }

  importJson(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];

    if (!file.name.toLowerCase().endsWith('.json')) {
      this.toastService.warning('El archivo debe tener extensión .json');
      input.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result as string);
        const graphData = parsed.graph_data || parsed;
        if (graphData && (Array.isArray(graphData.nodes) || Array.isArray(graphData.edges))) {
          this.canvasService.fromGraphData(graphData);
          this.autoSave.markDirty();
          this.toastService.success('Estructura JSON cargada en el lienzo');
        } else {
          this.toastService.warning('El archivo JSON no contiene un esquema de diagrama UML compatible');
        }
      } catch {
        this.toastService.error('El archivo JSON contiene errores de sintaxis');
      }
    };
    reader.readAsText(file);
    input.value = '';
  }

  retrySave() {
    this.autoSave.forceSaveNow();
  }
}
