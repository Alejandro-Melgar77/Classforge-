import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../../core/models/api-response.model';

export interface UserAdmin {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'scrum_master' | 'dev';
  avatar_url?: string | null;
  team_ids: string[];
  is_active: boolean;
  created_at?: string;
  last_activity?: string;
}

export interface CreateUserAdminDto {
  name: string;
  email: string;
  password: string;
  role: 'admin' | 'scrum_master' | 'dev';
  team_ids?: string[];
}

export interface UpdateUserAdminDto {
  name?: string;
  email?: string;
  role?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class UsersAdminService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/users`;

  getUsers(): Observable<ApiResponse<UserAdmin[]>> {
    return this.http.get<ApiResponse<UserAdmin[]>>(this.apiUrl);
  }

  getUser(id: string): Observable<ApiResponse<UserAdmin>> {
    return this.http.get<ApiResponse<UserAdmin>>(`${this.apiUrl}/${id}`);
  }

  createUser(data: CreateUserAdminDto): Observable<ApiResponse<{ id: string }>> {
    return this.http.post<ApiResponse<{ id: string }>>(this.apiUrl, data);
  }

  updateUser(id: string, data: UpdateUserAdminDto): Observable<ApiResponse<void>> {
    return this.http.put<ApiResponse<void>>(`${this.apiUrl}/${id}`, data);
  }

  changeRole(id: string, role: string): Observable<ApiResponse<void>> {
    return this.http.put<ApiResponse<void>>(`${this.apiUrl}/${id}/role`, { role });
  }

  deleteUser(id: string): Observable<ApiResponse<void>> {
    return this.http.delete<ApiResponse<void>>(`${this.apiUrl}/${id}`);
  }
}
