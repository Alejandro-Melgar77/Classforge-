import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { ApiResponse } from '../../../core/models/api-response.model';
import {
  ProjectReview,
  ReviewDocument,
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
