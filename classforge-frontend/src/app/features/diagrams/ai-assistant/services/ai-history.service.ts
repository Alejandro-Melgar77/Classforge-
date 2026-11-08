import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../../../core/services/auth.service';
import { AiHistoryEntry, UMLCommandResponse } from '../models/ai-command.model';
import { environment } from '../../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AiHistoryService {
  private http = inject(HttpClient);
  private authService = inject(AuthService);

  public history = signal<AiHistoryEntry[]>([]);

  constructor() {
    this.reloadHistory();
  }

  private getStorageKey(): string {
    const user = this.authService.getCurrentUser();
    const userId = user?.id || user?.email || 'anonymous';
    return `cf_ai_history_${userId}`;
  }

  private getDiagramStorageKey(diagramId?: string): string {
    if (diagramId) {
      return `cf_ai_diagram_history_${diagramId}`;
    }
    return this.getStorageKey();
  }

  public reloadHistory(diagramId?: string): AiHistoryEntry[] {
    const key = this.getDiagramStorageKey(diagramId);
    let localEntries: AiHistoryEntry[] = [];
    if (typeof localStorage !== 'undefined') {
      try {
        const stored = localStorage.getItem(key);
        localEntries = stored ? JSON.parse(stored) : [];
        const filtered = diagramId ? localEntries.filter(item => !item.diagramId || item.diagramId === diagramId) : localEntries;
        this.history.set(filtered);
      } catch {
        this.history.set([]);
      }
    }

    // Si contamos con diagramId, consultamos el backend para sincronizar el historial grupal del equipo
    if (diagramId) {
      this.http.get<any>(`${environment.apiUrl}/diagrams/${diagramId}/ai-history`).subscribe({
        next: (res) => {
          if (res?.success && Array.isArray(res.data)) {
            const remoteEntries: AiHistoryEntry[] = res.data;
            this.history.set(remoteEntries);
            if (typeof localStorage !== 'undefined') {
              try {
                localStorage.setItem(key, JSON.stringify(remoteEntries.slice(0, 100)));
              } catch {}
            }
          }
        },
        error: (err) => {
          console.warn('[AiHistoryService] Error al sincronizar historial de IA grupal desde el backend:', err);
        }
      });
    }

    return this.history();
  }

  public addEntry(
    prompt: string,
    inputType: 'voice' | 'text' | 'image',
    command?: UMLCommandResponse,
    status: 'applied' | 'discarded' | 'failed' = 'applied',
    diagramId?: string
  ): AiHistoryEntry {
    const user = this.authService.getCurrentUser();
    const userId = user?.id || user?.email || 'anonymous';
    const userName = user?.name || user?.email || 'Usuario';
    const userRole = user?.role || 'dev';
    const userEmail = user?.email || '';

    let summary = '';
    if (command) {
      if (command.classes && command.classes.length > 0) {
        summary += `Clases: ${command.classes.map(c => c.name).join(', ')}`;
      }
      if (command.relations && command.relations.length > 0) {
        summary += `${summary ? ' | ' : ''}Relaciones: ${command.relations.map(r => `${r.source} -> ${r.target}`).join(', ')}`;
      }
      if (command.deleted_elements && command.deleted_elements.length > 0) {
        summary += `${summary ? ' | ' : ''}Eliminado: ${command.deleted_elements.join(', ')}`;
      }
    }

    const entry: AiHistoryEntry = {
      id: `ai_hist_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      userId,
      userName,
      userRole,
      userEmail,
      diagramId,
      timestamp: new Date().toISOString(),
      prompt,
      inputType,
      status,
      command,
      resultSummary: summary || command?.explanation || ''
    };

    // 1. Guardado inmediato en cache local de este diagrama
    if (typeof localStorage !== 'undefined') {
      const key = this.getDiagramStorageKey(diagramId);
      try {
        const stored = localStorage.getItem(key);
        const list: AiHistoryEntry[] = stored ? JSON.parse(stored) : [];
        list.unshift(entry);
        const capped = list.slice(0, 100);
        localStorage.setItem(key, JSON.stringify(capped));
      } catch (e) {
        console.warn('Failed to save AI history in storage:', e);
      }
    }

    this.history.update(current => [entry, ...current.filter(e => e.id !== entry.id)]);

    // 2. Persistencia remota en MongoDB para que todo el equipo lo vea
    if (diagramId) {
      this.http.post<any>(`${environment.apiUrl}/diagrams/${diagramId}/ai-history`, {
        prompt: entry.prompt,
        inputType: entry.inputType,
        status: entry.status,
        source: command?.source || 'heuristic',
        resultSummary: entry.resultSummary,
        command: entry.command
      }).subscribe({
        next: (res) => {
          if (res?.success && res.data?.id) {
            this.history.update(current => 
              current.map(item => item.id === entry.id ? { ...item, id: res.data.id } : item)
            );
          }
        },
        error: (err) => {
          console.warn('[AiHistoryService] Error al guardar orden en backend compartido:', err);
        }
      });
    }

    return entry;
  }

  public updateStatus(id: string, status: 'applied' | 'discarded' | 'failed'): void {
    if (typeof localStorage === 'undefined') return;
    const key = this.getStorageKey();
    try {
      const stored = localStorage.getItem(key);
      if (!stored) return;
      const list: AiHistoryEntry[] = JSON.parse(stored);
      const found = list.find(item => item.id === id);
      if (found) {
        found.status = status;
        localStorage.setItem(key, JSON.stringify(list));
        this.history.update(current => current.map(item => item.id === id ? { ...item, status } : item));
      }
    } catch {}
  }

  public clearUserHistory(diagramId?: string): void {
    const key = this.getDiagramStorageKey(diagramId);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(key);
    }
    this.history.set([]);

    if (diagramId) {
      this.http.delete(`${environment.apiUrl}/diagrams/${diagramId}/ai-history`).subscribe({
        error: (err) => console.warn('[AiHistoryService] Error al borrar historial en backend:', err)
      });
    }
  }
}