import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { ApiResponse } from '../../../../core/models/api-response.model';
import { CodegenPreviewResponse, GeneratedFiles, FrontendPromptRequest, FrontendPromptResponse } from '../models/codegen.model';

@Injectable({
  providedIn: 'root'
})
export class CodegenService {
  private http = inject(HttpClient);
  
  generatedFiles = signal<GeneratedFiles>({});
  selectedFilePath = signal<string>('pom.xml');
  isLoading = signal<boolean>(false);
  
  selectedFileContent = computed(() => {
    return this.generatedFiles()[this.selectedFilePath()] || '';
  });

  getPreview(diagramId: string, graphData: any = {}): Observable<ApiResponse<CodegenPreviewResponse>> {
    return this.http.post<ApiResponse<CodegenPreviewResponse>>(
      `${environment.apiUrl}/codegen/${diagramId}/preview`,
      { graph_data: graphData }
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
    this.http.get(`${environment.apiUrl}/codegen/${diagramId}/download`, {
      responseType: 'blob'
    }).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }
}
