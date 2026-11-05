import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/api-response.model';
import { Diagram, GraphData, CreateDiagramDto, UpdateDiagramDto, DiagramParticipantsResponse } from '../models/diagram.model';

export interface DiagramFilters {
  project_id?: string;
  status?: string;
}

@Injectable({ providedIn: 'root' })
export class DiagramService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/diagrams`;
  private versions = new Map<string, number>();

  getDiagram(id: string): Observable<ApiResponse<Diagram>> {
    return this.http.get<ApiResponse<Diagram>>(`${this.apiUrl}/${id}`).pipe(
      tap(res => { if (res.data?.version) this.versions.set(id, res.data.version); })
    );
  }

  getDiagrams(filters?: DiagramFilters): Observable<ApiResponse<Diagram[]>> {
    let params: any = {};
    if (filters?.project_id) params.project_id = filters.project_id;
    if (filters?.status) params.status = filters.status;
    return this.http.get<ApiResponse<Diagram[]>>(this.apiUrl, { params });
  }

  createDiagram(data: CreateDiagramDto): Observable<ApiResponse<Diagram>> {
    return this.http.post<ApiResponse<Diagram>>(this.apiUrl, data);
  }

  saveGraph(id: string, graphData: GraphData, comment?: string): Observable<ApiResponse<Diagram>> {
    return this.http.put<ApiResponse<Diagram>>(`${this.apiUrl}/${id}/graph`, {
      graph_data: graphData, comment, base_version: this.versions.get(id)
    }).pipe(tap(res => { if (res.data?.version) this.versions.set(id, res.data.version); }));
  }

  updateDiagram(id: string, data: UpdateDiagramDto): Observable<ApiResponse<Diagram>> {
    return this.http.put<ApiResponse<Diagram>>(`${this.apiUrl}/${id}`, data);
  }

  deleteDiagram(id: string): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.apiUrl}/${id}`);
  }

  getParticipants(id: string): Observable<ApiResponse<DiagramParticipantsResponse>> {
    return this.http.get<ApiResponse<DiagramParticipantsResponse>>(`${this.apiUrl}/${id}/participants`);
  }

  updateParticipants(id: string, memberIds: string[]): Observable<ApiResponse<DiagramParticipantsResponse>> {
    return this.http.put<ApiResponse<DiagramParticipantsResponse>>(`${this.apiUrl}/${id}/participants`, { member_ids: memberIds });
  }

  exportXmi(id: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${id}/export/xmi`, { responseType: 'blob' });
  }

  exportJson(id: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${id}/export/json`, { responseType: 'blob' });
  }

  importXmi(id: string, file: File): Observable<ApiResponse<Diagram>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ApiResponse<Diagram>>(`${this.apiUrl}/${id}/import/xmi`, formData).pipe(
      tap(res => { if (res.data?.version) this.versions.set(id, res.data.version); })
    );
  }

  getHistory(id: string): Observable<ApiResponse<any[]>> {
    return this.http.get<ApiResponse<any[]>>(`${this.apiUrl}/${id}/history`);
  }

  restoreVersion(id: string, version: number): Observable<ApiResponse<Diagram>> {
    return this.http.post<ApiResponse<Diagram>>(`${this.apiUrl}/${id}/history/${version}/restore`, {}).pipe(
      tap(res => { if (res.data?.version) this.versions.set(id, res.data.version); })
    );
  }

  getWsToken(id: string): Observable<ApiResponse<{token: string}>> {
    return this.http.get<ApiResponse<{token: string}>>(`${this.apiUrl}/${id}/ws-token`);
  }

  autoLayout(id: string, baseVersion?: number): Observable<ApiResponse<Diagram>> {
    const version = baseVersion ?? this.versions.get(id);
    return this.http.post<ApiResponse<Diagram>>(`${this.apiUrl}/${id}/layout`, {
      base_version: version
    }).pipe(
      tap(res => { if (res.data?.version) this.versions.set(id, res.data.version); })
    );
  }

  getNormalization(id: string): Observable<ApiResponse<{ diagram_id: string; version: number; total_findings: number; findings: any[] }>> {
    return this.http.get<ApiResponse<{ diagram_id: string; version: number; total_findings: number; findings: any[] }>>(`${this.apiUrl}/${id}/normalization`);
  }

  applyNormalization(id: string, rules?: string[], baseVersion?: number, comment?: string): Observable<ApiResponse<Diagram>> {
    const version = baseVersion ?? this.versions.get(id);
    return this.http.post<ApiResponse<Diagram>>(`${this.apiUrl}/${id}/normalization/apply`, {
      base_version: version,
      rules,
      comment
    }).pipe(
      tap(res => { if (res.data?.version) this.versions.set(id, res.data.version); })
    );
  }
}
