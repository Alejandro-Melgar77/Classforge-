import { UMLCommandResponse } from '../../diagrams/ai-assistant/models/ai-command.model';

export type ProposalKind = 'uml_command' | 'task' | 'note';
export type ProposalSeverity = 'info' | 'warn' | 'critical';
export type ProposalStatus = 'applied' | 'dismissed';

export interface ProposalStateRecord {
  status: ProposalStatus;
  by?: string;
  at?: string;
}

export interface Proposal {
  id: string;
  kind: ProposalKind;
  title: string;
  rationale: string;
  severity: ProposalSeverity;
  command?: UMLCommandResponse;
  target_element_ids?: string[];
}

export interface RoleSkin {
  accent: string;
  bg: string;
  border: string;
  text: string;
  icon: string;
  bubble_shape: string;
  typing_text: string;
  avatar_style: string;
}

export type AiRoleId =
  | 'architect'
  | 'qa'
  | 'tech_lead'
  | 'mentor'
  | 'dba'
  | 'security'
  | 'analyst';

export type AiRoleAutonomy = 'off' | 'suggest' | 'apply';

export interface AiRole {
  role_id: string;
  label: string;
  emoji: string;
  description: string;
  is_active: boolean;
  autonomy?: AiRoleAutonomy;
  skin?: RoleSkin;
  triggers?: string[];
}

export type MessageStatus = 'ok' | 'pending' | 'error' | 'sending' | 'failed';
export type MessageAuthorType = 'user' | 'ai';
export type MessageThread = 'personal' | 'project';

export interface AiMessage {
  id: string;
  project_id?: string;
  thread: MessageThread;
  owner_id?: string | null;
  author_type: MessageAuthorType;
  author_id?: string | null;
  author_name: string;
  author_role_label?: string;
  ai_role?: string | null;
  content: string;
  content_format?: 'markdown';
  timestamp?: string;
  created_at?: string;
  updated_at?: string;
  visible_to_all?: boolean;
  diagram_snapshot?: Record<string, unknown> | null;
  has_diagram_changes?: boolean;
  proposals?: Proposal[];
  proposal_state?: Record<string, ProposalStateRecord>;
  mentions?: string[];
  reply_to?: string | null;
  client_id?: string | null;
  trigger?: string | null;
  status: MessageStatus;
  error_code?: string | null;
  model?: string | null;
  questions?: string[] | null;
  needs_context?: boolean | null;
}

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'needs_input'
  | 'cancelled'
  | 'deleted';

export interface AiTask {
  id: string;
  project_id: string;
  diagram_id?: string | null;
  assigned_by?: string | null;
  created_by?: string | null;
  assignee_type: 'ai_role' | 'user';
  assignee_id?: string | null;
  ai_role: string;
  title: string;
  description: string;
  status: TaskStatus;
  attempts?: number;
  result?: string | null;
  result_message_id?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
  updated_at?: string | null;
}

export interface ParticipativeConfig {
  enabled: boolean;
  updated_by?: string | null;
  updated_at?: string | null;
}

export interface RoleAutonomyConfig {
  role_id: string;
  enabled: boolean;
  autonomy: AiRoleAutonomy;
}

export interface ProjectDigest {
  text: string;
  tokens: number;
  covers_until?: string | null;
  updated_at?: string | null;
}

export interface AiProjectState {
  project_id: string;
  participative: ParticipativeConfig;
  roles: RoleAutonomyConfig[];
  digest: ProjectDigest;
  local_only?: boolean;
  updated_at?: string | null;
}

export interface AiPendingRole {
  role: string;
  message_id: string;
}

export interface AiSendMessageResponse {
  message: AiMessage;
  ai_pending: AiPendingRole[];
  ai_message?: AiMessage | null;
  has_diagram_changes?: boolean;
  proposals?: Proposal[];
  questions?: string[];
  needs_context?: boolean;
}

export interface AiHistoryResponse {
  project_id: string;
  messages: AiMessage[];
  total: number;
  next_cursor?: string | null;
}

export interface AiHealthResponse {
  provider: string;
  models: string[];
  has_server_key: boolean;
  local_available?: boolean;
  local_model?: string;
  local_latency_ms?: number | null;
  ollama_available: boolean;
  model: string;
}

export interface WsTokenResponse {
  success: boolean;
  message: string;
  data: {
    token: string;
    expires_at: string;
  };
}

export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'polling_fallback';

export interface WsPresenceMember {
  user_id: string;
  user_name: string;
  role: string;
  status: 'online' | string;
}

export interface WsTypingEvent {
  role: string;
  state: 'start' | 'stop';
  user_name?: string;
}

export interface HistoryFilters {
  member?: string;
  role?: string;
  onlyProposals?: boolean;
}

export interface HistoryQueryParams {
  before?: string;
  after?: string;
  limit?: number;
  member?: string;
  role?: string;
}

export type WsServerEvent =
  | { type: 'PRESENCE'; members: WsPresenceMember[] }
  | { type: 'AI_TYPING'; role: string; state: 'start' | 'stop'; user_name?: string }
  | { type: 'AI_MESSAGE_CREATED'; message: AiMessage }
  | { type: 'AI_MESSAGE_UPDATED'; message: AiMessage }
  | { type: 'AI_STATE_CHANGED'; state: AiProjectState }
  | { type: 'AI_TASK_UPDATED'; task: AiTask }
  | { type: 'PONG' };
