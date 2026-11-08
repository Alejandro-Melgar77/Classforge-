export type VerdictType = 'APROBADO' | 'RECHAZADO' | 'INFORMACION_INSUFICIENTE';
export type ReviewStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type RecommendationPriority = 'HIGH' | 'MEDIUM' | 'LOW';

export interface CriterionScore {
  criterion_code: string;
  name: string;
  weight: number;
  score: number;
  weighted_score: number;
  strengths: string[];
  weaknesses: string[];
  observations: string;
  citations: number[];
  evidence_quotes: string[];
}

export interface Recommendation {
  priority: RecommendationPriority;
  criterion_code: string;
  title: string;
  description: string;
  action_plan: string;
}

export interface ComponentSpec {
  name: string;
  role: string;
  technology: string;
  description: string;
}

export interface EndpointSpec {
  method: string;
  path: string;
  description: string;
  request_body?: string;
  response_body?: string;
}

export interface DataModelEntity {
  name: string;
  attributes: string[];
  relationships: string[];
}

export interface TechnicalSpecification {
  title: string;
  overview: string;
  functional_scope: string[];
  system_architecture: string;
  components: ComponentSpec[];
  api_endpoints: EndpointSpec[];
  data_model: DataModelEntity[];
  non_functional_requirements: string[];
  deployment_and_security: string[];
}

export interface ReviewDocument {
  id: string;
  project_id: string;
  filename: string;
  file_size_bytes: number;
  content_hash: string;
  page_count: number;
  has_sufficient_text: boolean;
  detected_sections: string[];
  uploaded_by: string;
  uploaded_at: string;
}

export interface ProjectReview {
  id: string;
  project_id: string;
  review_number: number;
  document_id: string;
  document_filename: string;
  rubric_code: string;
  rubric_version: string;
  status: ReviewStatus;
  verdict?: VerdictType;
  total_score?: number;
  passing_score: number;
  summary?: string;
  criteria_scores: CriterionScore[];
  recommendations: Recommendation[];
  technical_specification?: TechnicalSpecification;
  evaluated_by_model?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  created_by: string;
}

export interface LocalAiStatus {
  online: boolean;
  model: string;
  latency_ms?: number;
  installed_models: string[];
  is_classforge_local_active: boolean;
  url: string;
  status: 'connected' | 'disconnected';
  error?: string;
}

export interface LocalAiChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface LocalAiChatRequest {
  diagram_id?: string;
  message: string;
  session_history: LocalAiChatMessage[];
  tunnel_url?: string;
}

export interface LocalAiChatResponse {
  verdict: VerdictType;
  total_score: number;
  passing_score: number;
  summary: string;
  criteria_scores: CriterionScore[];
  technical_specification?: TechnicalSpecification;
  required_improvements: string[];
  assistant_message: string;
  evaluated_by_model: string;
  latency_ms?: number;
  diagram_id?: string;
  diagram_name?: string;
}

export interface LocalAiUiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  evaluation?: LocalAiChatResponse;
}
