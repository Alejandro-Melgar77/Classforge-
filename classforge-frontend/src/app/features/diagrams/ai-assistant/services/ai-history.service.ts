import { Injectable, inject, signal } from '@angular/core';
import { AuthService } from '../../../../core/services/auth.service';
import { AiHistoryEntry, UMLCommandResponse } from '../models/ai-command.model';

@Injectable({
  providedIn: 'root'
})
export class AiHistoryService {
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

  public reloadHistory(diagramId?: string): AiHistoryEntry[] {
    if (typeof localStorage === 'undefined') return [];
    const key = this.getStorageKey();
    try {
      const stored = localStorage.getItem(key);
      const list: AiHistoryEntry[] = stored ? JSON.parse(stored) : [];
      const filtered = diagramId ? list.filter(item => !item.diagramId || item.diagramId === diagramId) : list;
      this.history.set(filtered);
      return filtered;
    } catch {
      this.history.set([]);
      return [];
    }
  }

  public addEntry(
    prompt: string,
    inputType: 'voice' | 'text',
    command?: UMLCommandResponse,
    status: 'applied' | 'discarded' | 'failed' = 'applied',
    diagramId?: string
  ): AiHistoryEntry {
    const user = this.authService.getCurrentUser();
    const userId = user?.id || user?.email || 'anonymous';

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
      diagramId,
      timestamp: new Date().toISOString(),
      prompt,
      inputType,
      status,
      command,
      resultSummary: summary || command?.explanation || ''
    };

    if (typeof localStorage !== 'undefined') {
      const key = this.getStorageKey();
      try {
        const stored = localStorage.getItem(key);
        const list: AiHistoryEntry[] = stored ? JSON.parse(stored) : [];
        list.unshift(entry);
        // Keep last 100 entries per user
        const capped = list.slice(0, 100);
        localStorage.setItem(key, JSON.stringify(capped));
      } catch (e) {
        console.warn('Failed to save AI history in storage:', e);
      }
    }

    this.reloadHistory(diagramId);
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
    if (typeof localStorage === 'undefined') return;
    const key = this.getStorageKey();
    if (diagramId) {
      try {
        const stored = localStorage.getItem(key);
        if (stored) {
          const list: AiHistoryEntry[] = JSON.parse(stored);
          const remaining = list.filter(item => item.diagramId && item.diagramId !== diagramId);
          localStorage.setItem(key, JSON.stringify(remaining));
        }
      } catch {}
    } else {
      localStorage.removeItem(key);
    }
    this.history.set([]);
  }
}