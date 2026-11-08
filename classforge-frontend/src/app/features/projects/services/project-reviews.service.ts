import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/api-response.model';
import {
  ProjectReview,
  ReviewDocument,
  LocalAiStatus,
  LocalAiChatRequest,
  LocalAiChatResponse,
} from '../models/review.model';

export interface ReviewListResponse {
  items: ProjectReview[];
  total: number;
  page: number;
  limit: number;
}

@Injectable({
  providedIn: 'root'
})
export class ProjectReviewsService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/projects`;

  uploadDocument(projectId: string, file: File): Observable<ApiResponse<ReviewDocument>> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<ApiResponse<ReviewDocument>>(
      `${this.baseUrl}/${projectId}/reviews/upload`,
      formData
    );
  }

  createReview(
    projectId: string,
    documentId: string,
    rubricCode: string = 'CF-SE-2026.1',
    evaluationNotes?: string
  ): Observable<ApiResponse<ProjectReview>> {
    return this.http.post<ApiResponse<ProjectReview>>(
      `${this.baseUrl}/${projectId}/reviews`,
      {
        document_id: documentId,
        rubric_code: rubricCode,
        evaluation_notes: evaluationNotes
      }
    );
  }

  listReviews(projectId: string, page: number = 1, limit: number = 20): Observable<ApiResponse<ReviewListResponse>> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('limit', limit.toString());
    return this.http.get<ApiResponse<ReviewListResponse>>(
      `${this.baseUrl}/${projectId}/reviews`,
      { params }
    );
  }

  getReview(projectId: string, reviewId: string): Observable<ApiResponse<ProjectReview>> {
    return this.http.get<ApiResponse<ProjectReview>>(
      `${this.baseUrl}/${projectId}/reviews/${reviewId}`
    );
  }

  cancelReview(projectId: string, reviewId: string): Observable<ApiResponse<ProjectReview>> {
    return this.http.post<ApiResponse<ProjectReview>>(
      `${this.baseUrl}/${projectId}/reviews/${reviewId}/cancel`,
      {}
    );
  }

  checkLocalStatus(tunnelUrl?: string): Observable<LocalAiStatus> {
    let headers = new HttpHeaders();
    let params = new HttpParams();
    if (tunnelUrl) {
      headers = headers.set('X-Local-AI-Url', tunnelUrl);
      params = params.set('tunnel_url', tunnelUrl);
    }
    return this.http.get<any>(`${environment.apiUrl}/ai/local-status`, { headers, params }).pipe(
      map(res => ((res && res.data) ? res.data : res) as LocalAiStatus)
    );
  }

  evaluateAndChat(
    projectId: string,
    request: LocalAiChatRequest,
    tunnelUrl?: string
  ): Observable<ApiResponse<LocalAiChatResponse>> {
    let headers = new HttpHeaders();
    const payload: LocalAiChatRequest = {
      ...request,
      tunnel_url: tunnelUrl || request.tunnel_url,
    };
    if (tunnelUrl) {
      headers = headers.set('X-Local-AI-Url', tunnelUrl);
    }
    return this.http.post<ApiResponse<LocalAiChatResponse>>(
      `${this.baseUrl}/${projectId}/local-ai/evaluate-and-chat`,
      payload,
      { headers }
    );
  }

  downloadReportPdf(projectId: string, reviewId: string): Observable<Blob> {
    return this.http.get(
      `${this.baseUrl}/${projectId}/reviews/${reviewId}/report.pdf`,
      { responseType: 'blob' }
    );
  }

  downloadSpecificationPdf(projectId: string, reviewId: string): Observable<Blob> {
    return this.http.get(
      `${this.baseUrl}/${projectId}/reviews/${reviewId}/specification.pdf`,
      { responseType: 'blob' }
    );
  }
}
