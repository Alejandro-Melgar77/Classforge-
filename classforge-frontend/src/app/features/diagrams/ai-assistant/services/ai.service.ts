import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of, catchError, map, timeout } from 'rxjs';
import { NluParserService } from './nlu-parser.service';
import { UMLCommandResponse, UMLClassCommand, UMLRelationCommand } from '../models/ai-command.model';
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

  processImage(
    imageBase64: string,
    mimeType: string = 'image/jpeg',
    promptText?: string,
    diagramId?: string
  ): Observable<UMLCommandResponse> {
    if (!imageBase64 || !imageBase64.trim()) {
      return of({
        action: 'unknown',
        classes: [],
        relations: [],
        deleted_elements: [],
        explanation: 'Imagen no proporcionada.',
        source: 'heuristic'
      });
    }

    let cleanBase64 = imageBase64.trim();
    if (cleanBase64.includes(',')) {
      cleanBase64 = cleanBase64.split(',')[1];
    }

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

    let headers = new HttpHeaders();
    if (apiKey) {
      headers = headers.set('X-Gemini-Key', apiKey);
    }

    const url = `${environment.apiUrl}/ai/generate-from-image`;
    const payload: any = {
      image_base64: cleanBase64,
      mime_type: mimeType || 'image/jpeg',
      api_key: apiKey,
      model: model
    };

    if (diagramId) {
      payload.diagram_id = diagramId;
    }
    if (promptText && promptText.trim()) {
      payload.prompt = promptText.trim();
    }

    return this.http.post<any>(url, payload, { headers }).pipe(
      timeout(45000),
      map((res) => {
        const data = res?.data || res;
        const semantics = data?.semantics || data;
        const classes = semantics?.classes || [];
        const relationships = semantics?.relationships || semantics?.relations || [];
        const summary = semantics?.summary || data?.summary || res?.message || 'Diagrama UML interpretado desde imagen.';

        const mappedClasses: UMLClassCommand[] = classes.map((c: any) => ({
          name: c.name || 'ClaseSinNombre',
          stereotype: c.stereotype || (c.isInterface ? 'interface' : (c.isAbstract ? 'abstract' : undefined)),
          is_abstract: !!c.isAbstract || !!c.is_abstract || c.stereotype === 'abstract',
          attributes: (c.attributes || []).map((a: any) => ({
            name: a.name,
            type: a.type || 'String',
            visibility: a.visibility || '+',
            is_derived: !!a.is_derived,
            multiplicity: a.multiplicity || null,
            default_value: a.default_value || null,
            is_static: !!a.is_static
          })),
          methods: (c.methods || []).map((m: any) => ({
            name: m.name,
            params: m.parameters || m.params || '',
            return_type: m.returnType || m.return_type || 'void',
            visibility: m.visibility || '+',
            is_static: !!m.is_static,
            is_abstract: !!m.is_abstract
          }))
        }));

        const mappedRelations: UMLRelationCommand[] = relationships.map((r: any) => ({
          source: r.source,
          target: r.target,
          type: r.type || 'association',
          label: r.label || undefined,
          sourceMultiplicity: r.sourceMultiplicity || r.source_multiplicity || undefined,
          targetMultiplicity: r.targetMultiplicity || r.target_multiplicity || undefined,
          sourceRole: r.sourceRole || r.source_role || undefined,
          targetRole: r.targetRole || r.target_role || undefined
        }));

        return {
          action: 'generate_system',
          classes: mappedClasses,
          relations: mappedRelations,
          deleted_elements: [],
          explanation: summary,
          source: 'gemini' as const
        };
      }),
      catchError((err) => {
        console.error('[AiService] Error generating UML from image:', err);
        const errMsg = err?.error?.detail || err?.message || 'Error al procesar la imagen con Gemini Vision.';
        return of({
          action: 'unknown',
          classes: [],
          relations: [],
          deleted_elements: [],
          explanation: `Error en análisis de imagen: ${errMsg}`,
          source: 'gemini' as const
        });
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
