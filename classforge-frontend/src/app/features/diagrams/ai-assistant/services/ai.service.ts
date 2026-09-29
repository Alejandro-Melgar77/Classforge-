import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, catchError, map, timeout } from 'rxjs';
import { NluParserService } from './nlu-parser.service';
import { UMLCommandResponse } from '../models/ai-command.model';
import { environment } from '../../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AiService {
  private http = inject(HttpClient);
  private nluParser = inject(NluParserService);

  processInput(text: string, diagramContext?: any): Observable<UMLCommandResponse> {
    const trimmed = text.trim();
    if (!trimmed) {
      return of({
        action: 'unknown',
        classes: [],
        relations: [],
        deleted_elements: [],
        explanation: 'Consulta vacía.',
        source: 'offline_nlu'
      });
    }

    // Retrieve configured Gemini API Key and Model (defaults to gemini-3.7-flash)
    let apiKey: string | undefined = undefined;
    let model: string = 'gemini-3.7-flash';
    if (typeof localStorage !== 'undefined') {
      const storedKey = localStorage.getItem('classforge_gemini_api_key');
      if (storedKey && storedKey.trim()) {
        apiKey = storedKey.trim();
      }
      const storedModel = localStorage.getItem('classforge_gemini_model');
      if (storedModel && storedModel.trim()) {
        model = storedModel.trim();
      }
    }

    // 1. Primary Engine: Google Gemini 3.7 Flash Semantic UML Generator via Backend
    const url = `${environment.apiUrl}/ai/generate`;
    const payload = {
      prompt: trimmed,
      diagram_context: diagramContext,
      api_key: apiKey,
      model: model
    };

    return this.http.post<any>(url, payload).pipe(
      timeout(25000),
      map(res => {
        const data: UMLCommandResponse = res.data || res;
        if (data && (data.classes?.length > 0 || data.relations?.length > 0 || (data.action && data.action !== 'unknown'))) {
          data.source = (data.source as any) || 'backend_ai';
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
      parsed.source = 'offline_nlu';
      return parsed;
    }
    return {
      action: 'unknown',
      classes: [],
      relations: [],
      deleted_elements: [],
      explanation: 'No se pudo interpretar el comando con el motor local ni con la IA.',
      source: 'offline_nlu'
    };
  }
}


