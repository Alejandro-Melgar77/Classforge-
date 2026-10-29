import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  AiRoleChatResponse,
  AiConversation,
  AiRoleStatus,
  AiRoleId
} from '../models/ai-conversation.model';
import { AiTask, AiTaskCreate, AiTaskListResponse } from '../models/ai-task.model';

@Injectable({ providedIn: 'root' })
export class AiChatService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/ai-chat`;

  /** Sends a message with an active AI role and receives the AI response. */
  sendMessage(projectId: string, message: string, aiRole: AiRoleId, diagramId?: string): Observable<AiRoleChatResponse> {
    return this.http.post<AiRoleChatResponse>(
      `${this.base}/projects/${projectId}/messages`,
      { message, ai_role: aiRole, project_id: projectId, diagram_id: diagramId }
    );
  }

  /** Retrieves the full group chat history for a project. */
  getGroupHistory(projectId: string, limit = 200): Observable<{ project_id: string; messages: AiConversation['messages']; total: number }> {
    return this.http.get<{ project_id: string; messages: AiConversation['messages']; total: number }>(
      `${this.base}/projects/${projectId}/history`,
      { params: { limit: limit.toString() } }
    );
  }

  /** Retrieves only the current user's messages and AI responses. */
  getMyHistory(projectId: string, limit = 100): Observable<{ project_id: string; messages: AiConversation['messages']; total: number }> {
    return this.http.get<{ project_id: string; messages: AiConversation['messages']; total: number }>(
      `${this.base}/projects/${projectId}/history/mine`,
      { params: { limit: limit.toString() } }
    );
  }

  /** Returns all AI roles with their active status for the project. */
  getRoles(projectId: string): Observable<AiRoleStatus[]> {
    return this.http.get<AiRoleStatus[]>(`${this.base}/projects/${projectId}/roles`);
  }

  /** Activates or deactivates an AI role for the project. */
  setRole(projectId: string, roleId: AiRoleId, active: boolean): Observable<{ project_id: string; active_ai_roles: AiRoleId[] }> {
    return this.http.put<{ project_id: string; active_ai_roles: AiRoleId[] }>(
      `${this.base}/projects/${projectId}/roles`,
      { role_id: roleId, active }
    );
  }

  /** Creates a new task assigned to an AI role. */
  createTask(projectId: string, task: AiTaskCreate): Observable<{ task_id: string; status: string; message: string }> {
    return this.http.post<{ task_id: string; status: string; message: string }>(
      `${this.base}/projects/${projectId}/tasks`,
      task
    );
  }

  /** Lists all AI tasks for a project. */
  listTasks(projectId: string): Observable<AiTaskListResponse> {
    return this.http.get<AiTaskListResponse>(`${this.base}/projects/${projectId}/tasks`);
  }

  /** Executes a pending AI task immediately. */
  executeTask(projectId: string, taskId: string): Observable<AiTask> {
    return this.http.patch<AiTask>(
      `${this.base}/projects/${projectId}/tasks/${taskId}/execute`,
      {}
    );
  }
}
