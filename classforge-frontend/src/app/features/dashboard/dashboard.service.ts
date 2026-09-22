import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../core/models/api-response.model';
import { ProjectStatus } from '../../shared/components/status-badge/status-badge.component';

export interface DashboardStats {
  total_projects: number;
  completed_projects: number;
  active_projects: number;
  total_teams: number;
  recent_projects: {
    id: string;
    name: string;
    team_name: string | null;
    status: ProjectStatus;
    updated_at: string;
  }[];
  recent_activity: {
    id: string;
    user_name: string;
    action: string;
    target_name: string;
    created_at: string;
  }[];
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/dashboard`;

  getStats(): Observable<ApiResponse<DashboardStats>> {
    return this.http.get<ApiResponse<DashboardStats>>(`${this.apiUrl}/stats`);
  }
}
