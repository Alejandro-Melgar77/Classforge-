export type DiagramStatus = 'draft' | 'in_progress' | 'completed' | 'archived';
export type NodeType = 'class' | 'interface' | 'abstract' | 'enum' | 'note' | 'package';
export type EdgeType = 'inheritance' | 'composition' | 'aggregation' | 'association' | 'dependency' | 'realization';
export type Visibility = '+' | '-' | '#' | '~';

export interface UMLAttribute {
  visibility: Visibility;
  name: string;
  type: string;
  default_value: string | null;
  is_static: boolean;
}

export interface UMLMethod {
  visibility: Visibility;
  name: string;
  params: string;
  return_type: string;
  is_static: boolean;
  is_abstract: boolean;
}

export interface UMLNodeData {
  name: string;
  stereotype: string | null;
  attributes: UMLAttribute[];
  methods: UMLMethod[];
  notes: string | null;
}

export interface DiagramNode {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  size: { width: number; height: number };
  data: UMLNodeData;
}

export interface DiagramEdge {
  id: string;
  type: EdgeType;
  source: string;
  target: string;
  label: string | null;
  source_multiplicity: string | null;
  target_multiplicity: string | null;
}

export interface GraphData {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  viewport: { x: number; y: number; zoom: number };
}

export interface Diagram {
  id: string;
  name: string;
  description: string;
  image_url?: string | null;
  project_id: string;
  team_id: string | null;
  team_name?: string | null;
  member_ids?: string[];
  status: DiagramStatus;
  graph_data: GraphData;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDiagramDto {
  name: string;
  description?: string;
  image_url?: string | null;
  project_id?: string;
  team_id?: string | null;
  member_ids?: string[];
}

export interface UpdateDiagramDto {
  name?: string;
  description?: string;
  image_url?: string | null;
  team_id?: string | null;
  member_ids?: string[];
  status?: DiagramStatus;
}

export interface ParticipantItem {
  id: string;
  name: string;
  email: string;
  role: string;
  is_assigned: boolean;
}

export interface DiagramParticipantsResponse {
  diagram_id: string;
  team_id?: string | null;
  team_name?: string | null;
  assigned_member_ids: string[];
  available_members: ParticipantItem[];
}

export interface UpdateParticipantsDto {
  member_ids: string[];
}
