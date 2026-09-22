import { Injectable, computed, signal, inject } from '@angular/core';
import { DiagramService } from './diagram.service';
import { GraphData } from '../models/diagram.model';

@Injectable({ providedIn: 'root' })
export class AutoSaveService {
  private diagramService = inject(DiagramService);
  private saveTimer: any;
  
  private isDirty = signal(false);
  private isSaving = signal(false);
  
  readonly saveStatus = computed(() => {
    if (this.isSaving()) return 'saving';
    if (this.isDirty()) return 'unsaved';
    return 'saved';
  });

  private currentDiagramId: string | null = null;
  private currentGraphData: () => GraphData | null = () => null;

  init(diagramId: string, graphDataGetter: () => GraphData) {
    this.currentDiagramId = diagramId;
    this.currentGraphData = graphDataGetter;
  }

  markDirty(): void {
    if (!this.currentDiagramId) return;
    this.isDirty.set(true);
    this.scheduleAutoSave();
  }

  private scheduleAutoSave(): void {
    clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => this.executeSave(), 30_000);
  }

  async executeSave(): Promise<void> {
    if (!this.currentDiagramId || !this.isDirty()) return;
    
    const data = this.currentGraphData();
    if (!data) return;

    this.isSaving.set(true);
    try {
      await this.diagramService.saveGraph(this.currentDiagramId, data, 'Auto-save').toPromise();
      this.isDirty.set(false);
    } catch (e) {
      console.error('Auto-save failed', e);
    } finally {
      this.isSaving.set(false);
    }
  }

  forceSaveNow(): Promise<void> {
    clearTimeout(this.saveTimer);
    return this.executeSave();
  }
}
