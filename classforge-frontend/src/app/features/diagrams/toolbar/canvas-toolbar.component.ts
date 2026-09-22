import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule, Undo, Redo, Trash2, Copy, ClipboardPaste, Maximize, ZoomIn, ZoomOut, Download, Upload, LayoutGrid, FileJson, FileCode } from 'lucide-angular';
import { CanvasService } from '../services/canvas.service';
import { DiagramService } from '../services/diagram.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'canvas-toolbar',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  templateUrl: './canvas-toolbar.component.html',
})
export class CanvasToolbarComponent {
  private canvasService = inject(CanvasService);
  private diagramService = inject(DiagramService);
  private route = inject(ActivatedRoute);

  exportMenuOpen = false;

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
    if (graph) graph.copy(graph.getSelectedCells());
  }

  paste() {
    const graph = this.canvasService.getGraph();
    if (graph) graph.paste();
  }

  toggleExportMenu() {
    this.exportMenuOpen = !this.exportMenuOpen;
  }

  async exportPng() {
    this.exportMenuOpen = false;
    await this.canvasService.exportPng();
  }

  async exportPdf() {
    this.exportMenuOpen = false;
    await this.canvasService.exportPdf('classforge-diagram');
  }

  exportXmi() {
    this.exportMenuOpen = false;
    if (!this.diagramId) return;
    this.diagramService.exportXmi(this.diagramId).subscribe(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `diagram_${this.diagramId}.xmi`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  exportJson() {
    this.exportMenuOpen = false;
    if (!this.diagramId) return;
    this.diagramService.exportJson(this.diagramId).subscribe(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `diagram_${this.diagramId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  importXmi(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0 || !this.diagramId) return;
    const file = input.files[0];
    this.diagramService.importXmi(this.diagramId, file).subscribe(res => {
      if (res.success && res.data?.graph_data) {
        this.canvasService.fromGraphData(res.data.graph_data);
      }
    });
    input.value = ''; // reset file input
  }
}
