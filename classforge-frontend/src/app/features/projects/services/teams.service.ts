import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../../core/models/api-response.model';
import { Team, CreateTeamDto, UpdateTeamDto } from '../models/team.model';

@Injectable({
  providedIn: 'root'
})
export class TeamsService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/teams`;

  getTeams(): Observable<ApiResponse<Team[]>> {
    return this.http.get<ApiResponse<Team[]>>(this.apiUrl);
  }

  getTeam(id: string): Observable<ApiResponse<Team>> {
    return this.http.get<ApiResponse<Team>>(`${this.apiUrl}/${id}`);
  }

  createTeam(data: CreateTeamDto): Observable<ApiResponse<Team>> {
    return this.http.post<ApiResponse<Team>>(this.apiUrl, data);
  }

  updateTeam(id: string, data: UpdateTeamDto): Observable<ApiResponse<Team>> {
    return this.http.put<ApiResponse<Team>>(`${this.apiUrl}/${id}`, data);
  }

  addMember(teamId: string, userId: string): Observable<ApiResponse<void>> {
    return this.http.post<ApiResponse<void>>(`${this.apiUrl}/${teamId}/members`, { user_id: userId });
  }

  removeMember(teamId: string, userId: string): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.apiUrl}/${teamId}/members/${userId}`);
  }

  deleteTeam(teamId: string): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.apiUrl}/${teamId}`);
  }
}
