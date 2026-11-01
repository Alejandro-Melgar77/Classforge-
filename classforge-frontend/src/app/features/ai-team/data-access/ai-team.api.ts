import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  AiHealthResponse,
  AiHistoryResponse,
  AiMessage,
  AiProjectState,
  AiRole,
  AiRoleAutonomy,
  AiSendMessageResponse,
  AiTask,
  HistoryQueryParams,
  ProposalStatus,
  WsTokenResponse
} from './ai-team.models';

export const GEMINI_BYOK_STORAGE_KEY = 'classforge_gemini_api_key';

@Injectable({
  providedIn: 'root'
})
export class AiTeamApiService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/ai-chat`;

  private getCustomHeaders(): HttpHeaders {
    let headers = new HttpHeaders();
    if (typeof sessionStorage !== 'undefined') {
      const byok = sessionStorage.getItem(GEMINI_BYOK_STORAGE_KEY);
      if (byok && byok.trim()) {
        headers = headers.set('X-Gemini-Key', byok.trim());
      }
    }
    return headers;
  }

  public sendMessage(
    projectId: string,
    req: {
      content: string;
      client_id: string;
      ai_role?: string;
      diagram_id?: string;
      reply_to?: string;
      model?: string;
    }
  ): Observable<AiSendMessageResponse> {
    const url = `${this.baseUrl}/projects/${projectId}/messages`;
    return this.http.post<AiSendMessageResponse>(url, req, {
      headers: this.getCustomHeaders()
    });
  }

  public retryMessage(projectId: string, messageId: string): Observable<AiSendMessageResponse> {
    const url = `${this.baseUrl}/projects/${projectId}/messages/${messageId}/retry`;
    return this.http.post<AiSendMessageResponse>(url, {}, {
      headers: this.getCustomHeaders()
    });
  }

  public getHistory(projectId: string, params?: HistoryQueryParams): Observable<AiHistoryResponse> {
    const url = `${this.baseUrl}/projects/${projectId}/history`;
    let httpParams = new HttpParams();
    if (params?.before) httpParams = httpParams.set('before', params.before);
    if (params?.after) httpParams = httpParams.set('after', params.after);
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());
    if (params?.member) httpParams = httpParams.set('member', params.member);
    if (params?.role) httpParams = httpParams.set('role', params.role);

    return this.http.get<AiHistoryResponse>(url, { params: httpParams });
  }

  public getMyHistory(
    projectId: string,
    params?: { before?: string; after?: string; limit?: number }
  ): Observable<AiHistoryResponse> {
    const url = `${this.baseUrl}/projects/${projectId}/history/mine`;
    let httpParams = new HttpParams();
    if (params?.before) httpParams = httpParams.set('before', params.before);
    if (params?.after) httpParams = httpParams.set('after', params.after);
    if (params?.limit) httpParams = httpParams.set('limit', params.limit.toString());

    return this.http.get<AiHistoryResponse>(url, { params: httpParams });
  }

  public getState(projectId: string): Observable<AiProjectState> {
    const url = `${this.baseUrl}/projects/${projectId}/state`;
    return this.http.get<AiProjectState>(url);
  }

  public updateState(
    projectId: string,
    body: {
      participative?: { enabled: boolean };
      roles?: Array<{ role_id: string; enabled?: boolean; autonomy?: AiRoleAutonomy }>;
      local_only?: boolean;
    }
  ): Observable<AiProjectState> {
    const url = `${this.baseUrl}/projects/${projectId}/state`;
    return this.http.put<AiProjectState>(url, body);
  }

  public setRole(
    projectId: string,
    roleId: string,
    active: boolean,
    autonomy?: AiRoleAutonomy
  ): Observable<{ project_id: string; active_ai_roles: string[] }> {
    const url = `${this.baseUrl}/projects/${projectId}/roles`;
    return this.http.put<{ project_id: string; active_ai_roles: string[] }>(url, {
      role_id: roleId,
      active,
      autonomy
    });
  }

  public getRoles(projectId: string): Observable<AiRole[]> {
    const url = `${this.baseUrl}/projects/${projectId}/roles`;
    return this.http.get<AiRole[]>(url);
  }

  public getAllRoles(): Observable<any[]> {
    const url = `${this.baseUrl}/roles`;
    return this.http.get<any[]>(url);
  }

  public setProposalState(
    projectId: string,
    messageId: string,
    proposalId: string,
    status: ProposalStatus
  ): Observable<{ message: AiMessage; proposal_id: string; status: string }> {
    const url = `${this.baseUrl}/projects/${projectId}/messages/${messageId}/proposals/${proposalId}/state`;
    return this.http.post<{ message: AiMessage; proposal_id: string; status: string }>(url, {
      status
    });
  }

  public listTasks(projectId: string): Observable<{ project_id: string; tasks: AiTask[]; total: number }> {
    const url = `${this.baseUrl}/projects/${projectId}/tasks`;
    return this.http.get<{ project_id: string; tasks: AiTask[]; total: number }>(url);
  }

  public createTask(
    projectId: string,
    task: {
      ai_role: string;
      title: string;
      description: string;
      diagram_id?: string;
    }
  ): Observable<{ task_id: string; status: string; message: string }> {
    const url = `${this.baseUrl}/projects/${projectId}/tasks`;
    return this.http.post<{ task_id: string; status: string; message: string }>(url, task);
  }

  public updateTask(
    projectId: string,
    taskId: string,
    updates: Partial<{
      title: string;
      description: string;
      ai_role: string;
      status: string;
      diagram_id?: string;
    }>
  ): Observable<AiTask> {
    const url = `${this.baseUrl}/projects/${projectId}/tasks/${taskId}`;
    return this.http.patch<AiTask>(url, updates);
  }

  public deleteTask(projectId: string, taskId: string): Observable<{ success: boolean; message: string }> {
    const url = `${this.baseUrl}/projects/${projectId}/tasks/${taskId}`;
    return this.http.delete<{ success: boolean; message: string }>(url);
  }

  public executeTask(projectId: string, taskId: string): Observable<any> {
    const url = `${this.baseUrl}/projects/${projectId}/tasks/${taskId}/execute`;
    return this.http.patch<any>(url, {});
  }

  public getWsToken(projectId: string): Observable<WsTokenResponse> {
    const url = `${this.baseUrl}/projects/${projectId}/ws-token`;
    return this.http.get<WsTokenResponse>(url);
  }

  public getAiHealth(): Observable<AiHealthResponse> {
    const url = `${environment.apiUrl}/ai/health`;
    return this.http.get<AiHealthResponse>(url);
  }
}
