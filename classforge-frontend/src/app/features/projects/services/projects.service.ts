import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../../core/models/api-response.model';
import { Project, ProjectStatus } from '../models/project.model';

export interface ProjectFilters {
  status?: string;
  team_id?: string;
  search?: string;
  folder_id?: string;
}

export interface CreateProjectDto {
  name: string;
  description: string;
  team_id?: string;
  color_tag?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ProjectsService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/projects`;

  getProjects(filters?: ProjectFilters): Observable<ApiResponse<Project[]>> {
    let params = new HttpParams();
    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.team_id) params = params.set('team_id', filters.team_id);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.folder_id) params = params.set('folder_id', filters.folder_id);
    }
    return this.http.get<ApiResponse<Project[]>>(this.apiUrl, { params });
  }

  createProject(data: CreateProjectDto): Observable<ApiResponse<Project>> {
    return this.http.post<ApiResponse<Project>>(this.apiUrl, data);
  }

  updateProjectStatus(id: string, status: ProjectStatus): Observable<ApiResponse<Project>> {
    return this.http.patch<ApiResponse<Project>>(`${this.apiUrl}/${id}/status`, { status });
  }
}
