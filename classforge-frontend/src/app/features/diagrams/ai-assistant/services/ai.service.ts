import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, catchError, map, timeout } from 'rxjs';
import { NluParserService } from './nlu-parser.service';
import { UMLCommandResponse } from '../models/ai-command.model';
import { environment } from '../../../../../environments/environment';

export interface AiHealthResponse {
  provider: string;
  models: string[];
  has_server_key: boolean;
  local_available: boolean;
  local_model: string;
  local_latency_ms?: number | null;
  routing?: Record<string, string[]>;
  ollama_available?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AiService {
  private http = inject(HttpClient);
  private nluParser = inject(NluParserService);

  checkHealth(): Observable<AiHealthResponse> {
    const url = `${environment.apiUrl}/ai/health`;
    return this.http.get<any>(url).pipe(
      map(res => res as AiHealthResponse),
      catchError(err => {
        console.warn('[AiService] Failed to check AI health:', err);
        return of({
          provider: 'gemini',
          models: ['gemini-3.8-flash'],
          has_server_key: false,
          local_available: false,
          local_model: 'qwen2.5:1.5b'
        });
      })
    );
  }

  processInput(
    text: string,
    diagramContext?: any,
    preferredProvider: 'auto' | 'gemini' | 'local' = 'auto',
    localOnly: boolean = false
  ): Observable<UMLCommandResponse> {
    const trimmed = text.trim();
    if (!trimmed) {
      return of({
        action: 'unknown',
        classes: [],
        relations: [],
        deleted_elements: [],
        explanation: 'Consulta vacía.',
        source: 'heuristic'
      });
    }

    // Retrieve configured Gemini API Key from sessionStorage and Model preference
    let apiKey: string | undefined = undefined;
    let model: string = 'gemini-3.8-flash';
    if (typeof sessionStorage !== 'undefined') {
      const storedKey = sessionStorage.getItem('classforge_gemini_api_key');
      if (storedKey && storedKey.trim()) {
        apiKey = storedKey.trim();
      }
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('classforge_gemini_api_key');
      const storedModel = localStorage.getItem('classforge_gemini_model');
      if (storedModel && storedModel.trim()) {
        model = storedModel.trim();
      }
    }

    // Purpose-based routing with local LLM and Gemini support
    const url = `${environment.apiUrl}/ai/generate`;
    const payload: any = {
      prompt: trimmed,
      diagram_context: diagramContext,
      api_key: apiKey,
      model: model,
      local_only: localOnly
    };

    if (preferredProvider && preferredProvider !== 'auto') {
      payload.preferred_provider = preferredProvider;
    }

    return this.http.post<any>(url, payload).pipe(
      timeout(28000),
      map(res => {
        const data: UMLCommandResponse = res.data || res;
        if (data && (data.classes?.length > 0 || data.relations?.length > 0 || (data.action && data.action !== 'unknown'))) {
          data.source = (data.source as any) || 'heuristic';
          return data;
        }
        // Fallback if backend returned empty
        return this.fallbackToLocalNlu(trimmed);
      }),
      catchError((err) => {
        console.warn('[AiService] Backend AI call failed, falling back to local deterministic NLU:', err);
        return of(this.fallbackToLocalNlu(trimmed));
      })
    );
  }

  private fallbackToLocalNlu(text: string): UMLCommandResponse {
    const parsed = this.nluParser.parse(text);
    if (parsed && parsed.action !== 'unknown') {
      parsed.source = 'heuristic';
      return parsed;
    }
    return {
      action: 'unknown',
      classes: [],
      relations: [],
      deleted_elements: [],
      explanation: 'No se pudo interpretar el comando con el motor local ni con la IA.',
      source: 'heuristic'
    };
  }
}
