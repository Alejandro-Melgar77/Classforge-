import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { ApiResponse } from '../../../../core/models/api-response.model';
import { CodegenPreviewResponse, GeneratedFiles, FrontendPromptRequest, FrontendPromptResponse, CodegenEngine, BackendFramework } from '../models/codegen.model';

@Injectable({
  providedIn: 'root'
})
export class CodegenService {
  private http = inject(HttpClient);
  
  generatedFiles = signal<GeneratedFiles>({});
  selectedFilePath = signal<string>('pom.xml');
  isLoading = signal<boolean>(false);
  targetBackend = signal<BackendFramework>('spring_boot');
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

  setBackend(backend: BackendFramework): void {
    this.targetBackend.set(backend);
    if (backend === 'fastapi') {
      this.selectedFilePath.set('app/main.py');
    } else {
      this.selectedFilePath.set('pom.xml');
    }
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
      target_backend: this.targetBackend(),
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
          if (res.data.files) {
            this.generatedFiles.set(res.data.files);
          }
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
    const payload: FrontendPromptRequest = {
      ...options,
      engine: options.engine || this.activeEngine(),
      gemini_api_key: this.geminiApiKey() || undefined,
      gemini_model: this.geminiModel()
    };

    return this.http.post<ApiResponse<FrontendPromptResponse>>(
      `${environment.apiUrl}/codegen/${diagramId}/frontend-prompt`,
      payload
    );
  }

  downloadZip(diagramId: string, filename?: string): void {
    const backend = this.targetBackend();
    const engine = this.activeEngine();
    const model = this.geminiModel();
    const defaultFilename = backend === 'fastapi' ? 'classforge-fastapi-backend.zip' : 'classforge-springboot-backend.zip';
    const targetFilename = filename || defaultFilename;
    const url = `${environment.apiUrl}/codegen/${diagramId}/download?target_backend=${backend}&engine=${engine}&model=${model}`;

    this.http.get(url, {
      responseType: 'blob'
    }).subscribe(blob => {
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = targetFilename;
      a.click();
      window.URL.revokeObjectURL(blobUrl);
    });
  }
}
