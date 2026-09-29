import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { ApiResponse } from '../../../../core/models/api-response.model';
import { CodegenPreviewResponse, GeneratedFiles, FrontendPromptRequest, FrontendPromptResponse, CodegenEngine } from '../models/codegen.model';

@Injectable({
  providedIn: 'root'
})
export class CodegenService {
  private http = inject(HttpClient);
  
  generatedFiles = signal<GeneratedFiles>({});
  selectedFilePath = signal<string>('pom.xml');
  isLoading = signal<boolean>(false);
  activeEngine = signal<CodegenEngine>('gemini');
  geminiModel = signal<string>(localStorage.getItem('classforge_gemini_model') || 'gemini-3.8-flash');
  geminiApiKey = signal<string>(localStorage.getItem('classforge_gemini_api_key') || '');
  engineUsed = signal<string>('deterministic');
  engineSummary = signal<string>('');
  
  selectedFileContent = computed(() => {
    return this.generatedFiles()[this.selectedFilePath()] || '';
  });

  setEngine(engine: CodegenEngine): void {
    this.activeEngine.set(engine);
  }

  setGeminiApiKey(key: string): void {
    this.geminiApiKey.set(key);
    localStorage.setItem('classforge_gemini_api_key', key);
  }

  setGeminiModel(model: string): void {
    this.geminiModel.set(model);
    localStorage.setItem('classforge_gemini_model', model);
  }

  getPreview(diagramId: string, graphData: any = {}): Observable<ApiResponse<CodegenPreviewResponse>> {
    const payload = {
      graph_data: graphData,
      engine: this.activeEngine(),
      gemini_api_key: this.geminiApiKey() || undefined,
      gemini_model: this.geminiModel()
    };

    return this.http.post<ApiResponse<CodegenPreviewResponse>>(
      `${environment.apiUrl}/codegen/${diagramId}/preview`,
      payload
    ).pipe(
      tap(res => {
        if (res.success && res.data) {
          if (res.data.engine_used) {
            this.engineUsed.set(res.data.engine_used);
          }
          if (res.data.summary) {
            this.engineSummary.set(res.data.summary);
          }
        }
      })
    );
  }

  getFrontendPrompt(
    diagramId: string, 
    options: FrontendPromptRequest
  ): Observable<ApiResponse<FrontendPromptResponse>> {
    return this.http.post<ApiResponse<FrontendPromptResponse>>(
      `${environment.apiUrl}/codegen/${diagramId}/frontend-prompt`,
      options
    );
  }

  downloadZip(diagramId: string, filename: string): void {
    const engine = this.activeEngine();
    const model = this.geminiModel();
    const url = `${environment.apiUrl}/codegen/${diagramId}/download?engine=${engine}&model=${model}`;

    this.http.get(url, {
      responseType: 'blob'
    }).subscribe(blob => {
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(blobUrl);
    });
  }
}

