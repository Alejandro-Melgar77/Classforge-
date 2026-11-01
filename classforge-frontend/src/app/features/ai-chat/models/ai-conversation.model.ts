/** Represents a proposal produced by an AI role. */
export interface ProposalItem {
  id: string;
  kind: 'uml_command' | 'task' | 'note';
  title: string;
  rationale: string;
  severity: 'info' | 'warn' | 'critical';
  command?: Record<string, unknown> | null;
  target_element_ids?: string[];
}

/** Structured output contract from AI Team roles. */
export interface AiTeamResponse {
  reply_markdown: string;
  proposals: ProposalItem[];
  questions: string[];
  needs_context: boolean;
}

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
  proposals?: ProposalItem[];
  questions?: string[];
  needs_context?: boolean;
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
export type AiRoleId = 'architect' | 'qa' | 'tech_lead' | 'mentor' | 'dba' | 'security' | 'analyst';

/** UI skin configuration for an AI role. */
export interface AiRoleSkin {
  accent: string;
  bg: string;
  border: string;
  text: string;
  icon: string;
  bubble_shape: string;
  typing_text: string;
  avatar_style: string;
}

/** Status configuration for an AI role. */
export interface AiRoleStatus {
  role_id: AiRoleId;
  label: string;
  emoji: string;
  description: string;
  is_active: boolean;
  skin?: AiRoleSkin;
  triggers?: string[];
}

/** UI theme/skin configuration for an AI role. */
export interface AiRoleTheme {
  emoji: string;
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  description: string;
  icon?: string;
  bubbleShape?: string;
}

/** Map of role themes for consistent UI presentation. */
export const AI_ROLE_THEMES: Record<AiRoleId, AiRoleTheme> = {
  architect: {
    emoji: '🏛️',
    label: 'Arquitecto IA',
    bgColor: '#0F172A',
    textColor: '#93C5FD',
    borderColor: '#2563EB',
    description: 'Diseña y valida la arquitectura del sistema',
    icon: 'landmark',
    bubbleShape: 'bubble-rounded-bl',
  },
  qa: {
    emoji: '🔬',
    label: 'QA IA',
    bgColor: '#064E3B',
    textColor: '#A7F3D0',
    borderColor: '#059669',
    description: 'Detecta inconsistencias y errores en el modelo',
    icon: 'shield-check',
    bubbleShape: 'bubble-angular',
  },
  tech_lead: {
    emoji: '⚡',
    label: 'Tech Lead IA',
    bgColor: '#451A03',
    textColor: '#FDE68A',
    borderColor: '#D97706',
    description: 'Guía decisiones técnicas y estándares de código',
    icon: 'terminal',
    bubbleShape: 'bubble-rounded-tr',
  },
  mentor: {
    emoji: '📚',
    label: 'Mentor IA',
    bgColor: '#2E1065',
    textColor: '#DDD6FE',
    borderColor: '#7C3AED',
    description: 'Explica conceptos y enseña buenas prácticas',
    icon: 'sparkles',
    bubbleShape: 'bubble-pill',
  },
  dba: {
    emoji: '💾',
    label: 'DBA IA',
    bgColor: '#164E63',
    textColor: '#A5F3FC',
    borderColor: '#0891B2',
    description: 'Optimiza persistencia, normalización 3FN y claves',
    icon: 'database',
    bubbleShape: 'bubble-cut-corner',
  },
  security: {
    emoji: '🛡️',
    label: 'Seguridad IA',
    bgColor: '#450A0A',
    textColor: '#FECACA',
    borderColor: '#DC2626',
    description: 'Audita OWASP, contraseñas y control de accesos',
    icon: 'shield-alert',
    bubbleShape: 'bubble-sharp-bl',
  },
  analyst: {
    emoji: '📋',
    label: 'Analista IA',
    bgColor: '#134E4A',
    textColor: '#99F6E4',
    borderColor: '#0D9488',
    description: 'Mapea requisitos e historias de usuario a clases',
    icon: 'file-text',
    bubbleShape: 'bubble-card',
  },
};

/** Response from the AI role chat endpoint. */
export interface AiRoleChatResponse {
  ai_message: AiMessage;
  has_diagram_changes: boolean;
  diagram_changes_json?: unknown;
  role_label: string;
  role_emoji: string;
  structured_response?: AiTeamResponse;
  proposals?: ProposalItem[];
  questions?: string[];
  needs_context?: boolean;
}
