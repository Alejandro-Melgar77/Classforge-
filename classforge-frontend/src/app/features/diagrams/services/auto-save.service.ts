import { Injectable, computed, signal, inject } from '@angular/core';
import { DiagramService } from './diagram.service';
import { GraphData } from '../models/diagram.model';

export type SaveStatus = 'saving' | 'unsaved' | 'saved' | 'error';

@Injectable({ providedIn: 'root' })
export class AutoSaveService {
  private diagramService = inject(DiagramService);
  private saveTimer: any;
  
  private isDirty = signal(false);
  private isSaving = signal(false);
  private hasError = signal(false);
  
  readonly saveStatus = computed<SaveStatus>(() => {
    if (this.hasError()) return 'error';
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
    this.hasError.set(false);
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
    this.hasError.set(false);
    try {
      await this.diagramService.saveGraph(this.currentDiagramId, data, 'Auto-save').toPromise();
      this.isDirty.set(false);
    } catch (e) {
      console.error('Auto-save failed', e);
      this.hasError.set(true);
    } finally {
      this.isSaving.set(false);
    }
  }

  forceSaveNow(): Promise<void> {
    clearTimeout(this.saveTimer);
    return this.executeSave();
  }
}
