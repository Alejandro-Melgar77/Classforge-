import { Injectable, computed, signal, inject, OnDestroy } from '@angular/core';
import { DiagramService } from './diagram.service';
import { GraphData } from '../models/diagram.model';
import { ToastService } from '../../../core/services/toast.service';

export type SaveStatus = 'saving' | 'unsaved' | 'saved' | 'error';

@Injectable({ providedIn: 'root' })
export class AutoSaveService implements OnDestroy {
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);
  private saveTimer: any;
  private retryTimer: any;

  private isDirty = signal(false);
  private isSaving = signal(false);
  private hasError = signal(false);
  private retryCount = 0;
  private readonly maxRetries = 3;

  readonly saveStatus = computed<SaveStatus>(() => {
    if (this.hasError()) return 'error';
    if (this.isSaving()) return 'saving';
    if (this.isDirty()) return 'unsaved';
    return 'saved';
  });

  private currentDiagramId: string | null = null;
  private currentGraphData: () => GraphData | null = () => null;

  private beforeUnloadListener = (e: BeforeUnloadEvent) => {
    if (this.isDirty()) {
      e.preventDefault();
      e.returnValue = 'Tienes cambios sin guardar en el lienzo.';
      return e.returnValue;
    }
  };

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', this.beforeUnloadListener);
    }
  }

  init(diagramId: string, graphDataGetter: () => GraphData) {
    this.currentDiagramId = diagramId;
    this.currentGraphData = graphDataGetter;
    this.isDirty.set(false);
    this.hasError.set(false);
    this.isSaving.set(false);
    this.retryCount = 0;
    clearTimeout(this.saveTimer);
    clearTimeout(this.retryTimer);
  }

  markDirty(): void {
    if (!this.currentDiagramId) return;
    this.hasError.set(false);
    this.isDirty.set(true);
    this.saveLocalDraft();
    this.scheduleAutoSave();
  }

  private saveLocalDraft(): void {
    if (!this.currentDiagramId || typeof localStorage === 'undefined') return;
    try {
      const data = this.currentGraphData();
      if (data) {
        localStorage.setItem(`cf_draft_diagram_${this.currentDiagramId}`, JSON.stringify({
          saved_at: new Date().toISOString(),
          graph_data: data
        }));
      }
    } catch {
      // Ignorar cuota de localStorage excedida
    }
  }

  private scheduleAutoSave(): void {
    clearTimeout(this.saveTimer);
    // Debounce de 5 segundos tras última edición
    this.saveTimer = setTimeout(() => this.executeSave(), 5000);
  }

  async executeSave(isRetry = false): Promise<void> {
    if (!this.currentDiagramId || (!this.isDirty() && !isRetry)) return;

    const data = this.currentGraphData();
    if (!data) return;

    this.isSaving.set(true);
    this.hasError.set(false);

    try {
      await this.diagramService.saveGraph(this.currentDiagramId, data, 'Auto-save').toPromise();
      this.isDirty.set(false);
      this.hasError.set(false);
      this.retryCount = 0;
    } catch (e) {
      console.error('Auto-save falló', e);
      if (this.retryCount < this.maxRetries) {
        this.retryCount++;
        const backoffMs = Math.pow(2, this.retryCount - 1) * 1000; // 1s, 2s, 4s
        clearTimeout(this.retryTimer);
        this.retryTimer = setTimeout(() => this.executeSave(true), backoffMs);
      } else {
        this.hasError.set(true);
        this.toastService.error('Error al guardar en el servidor. Los cambios están respaldados localmente en tu navegador.');
      }
    } finally {
      this.isSaving.set(false);
    }
  }

  forceSaveNow(): Promise<void> {
    clearTimeout(this.saveTimer);
    clearTimeout(this.retryTimer);
    this.retryCount = 0;
    return this.executeSave();
  }

  destroy(): void {
    clearTimeout(this.saveTimer);
    clearTimeout(this.retryTimer);
    this.currentDiagramId = null;
    this.currentGraphData = () => null;
  }

  ngOnDestroy(): void {
    this.destroy();
    if (typeof window !== 'undefined') {
      window.removeEventListener('beforeunload', this.beforeUnloadListener);
    }
  }
}
