/** Represents a message in the AI group chat. */
export interface AiMessage {
  id: string;
  author_type: 'user' | 'ai';
  author_id?: string;
  author_name: string;
  author_role_label: string;
  ai_role?: AiRoleId;
  content: string;
  timestamp: string;
  visible_to_all: boolean;
  has_diagram_changes?: boolean;
  diagram_snapshot?: Record<string, unknown>;
}

/** Represents the full conversation document for a project. */
export interface AiConversation {
  id?: string;
  project_id: string;
  messages: AiMessage[];
  active_ai_roles: AiRoleId[];
  created_at?: string;
  updated_at?: string;
}

/** Valid AI role identifiers. */
export type AiRoleId = 'architect' | 'qa' | 'tech_lead' | 'mentor';

/** Status configuration for an AI role. */
export interface AiRoleStatus {
  role_id: AiRoleId;
  label: string;
  emoji: string;
  description: string;
  is_active: boolean;
}

/** UI theme/skin configuration for an AI role. */
export interface AiRoleTheme {
  emoji: string;
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  description: string;
}

/** Map of role themes for consistent UI presentation. */
export const AI_ROLE_THEMES: Record<AiRoleId, AiRoleTheme> = {
  architect: {
    emoji: '🏛️',
    label: 'Arquitecto IA',
    bgColor: '#1E3A5F',
    textColor: '#7EB3FF',
    borderColor: '#2D6BE4',
    description: 'Diseña y valida la arquitectura del sistema'
  },
  qa: {
    emoji: '🔬',
    label: 'QA IA',
    bgColor: '#1A3C2F',
    textColor: '#4ADE80',
    borderColor: '#00C896',
    description: 'Detecta inconsistencias y errores en el modelo'
  },
  tech_lead: {
    emoji: '⚡',
    label: 'Tech Lead IA',
    bgColor: '#5C2E00',
    textColor: '#FBBF24',
    borderColor: '#F5A623',
    description: 'Guía decisiones técnicas y estándares de código'
  },
  mentor: {
    emoji: '📚',
    label: 'Mentor IA',
    bgColor: '#2D1B69',
    textColor: '#C4B5FD',
    borderColor: '#9B51E0',
    description: 'Explica conceptos y enseña buenas prácticas'
  }
};

/** Response from the AI role chat endpoint. */
export interface AiRoleChatResponse {
  ai_message: AiMessage;
  has_diagram_changes: boolean;
  diagram_changes_json?: unknown;
  role_label: string;
  role_emoji: string;
}
