/** Status of a task assigned to an AI role. */
export type AiTaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/** A task assigned to an AI role in ClassForge. */
export interface AiTask {
  id?: string;
  project_id: string;
  diagram_id?: string;
  assigned_by?: string;
  ai_role: string;
  title: string;
  description: string;
  status: AiTaskStatus;
  result?: string;
  created_at?: string;
  completed_at?: string;
}

/** Payload to create a new AI task. */
export interface AiTaskCreate {
  ai_role: string;
  title: string;
  description: string;
  diagram_id?: string;
}

/** Response from the tasks list endpoint. */
export interface AiTaskListResponse {
  project_id: string;
  tasks: AiTask[];
  total: number;
}
