import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, catchError, map } from 'rxjs';
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
    // 1. Instant deterministic Offline NLU execution
    const parsed = this.nluParser.parse(text);
    if (parsed && parsed.action !== 'unknown') {
      return of(parsed);
    }

    // 2. Optional backend fallback (still offline on localhost if server is running)
    const url = `${environment.apiUrl}/ai/generate`;
    return this.http.post<any>(url, { prompt: text, diagram_context: diagramContext }).pipe(
      map(res => {
        const data: UMLCommandResponse = res.data || res;
        data.source = 'backend_ai';
        return data;
      }),
      catchError(() => {
        // Safe offline fallback
        return of(parsed || {
          action: 'unknown',
          classes: [],
          relations: [],
          deleted_elements: [],
          explanation: 'No se pudo interpretar el comando.',
          source: 'offline_nlu'
        } as UMLCommandResponse);
      })
    );
  }
}

