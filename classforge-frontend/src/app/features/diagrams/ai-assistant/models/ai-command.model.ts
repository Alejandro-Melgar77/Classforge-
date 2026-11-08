export interface UMLAttribute {
  name: string;
  type: string;
  visibility: string;
  is_derived?: boolean;
  multiplicity?: string | null;
  default_value?: string | null;
  is_static?: boolean;
}

export interface UMLMethod {
  name: string;
  params: string;
  return_type: string;
  visibility: string;
  is_static?: boolean;
  is_abstract?: boolean;
}

export interface UMLClassCommand {
  name: string;
  attributes: UMLAttribute[];
  methods: UMLMethod[];
  stereotype?: string;
  is_abstract?: boolean;
}

export interface UMLRelationCommand {
  source: string;
  target: string;
  type: string;
  label?: string;
  sourceMultiplicity?: string;
  targetMultiplicity?: string;
  source_multiplicity?: string;
  target_multiplicity?: string;
  sourceRole?: string;
  targetRole?: string;
  source_role?: string;
  target_role?: string;
}

export interface UMLCommandResponse {
  action: string;
  classes: UMLClassCommand[];
  relations: UMLRelationCommand[];
  deleted_elements: string[];
  explanation: string;
  source: 'offline_nlu' | 'backend_ai' | 'local' | 'gemini' | 'heuristic';
}

export interface AiHistoryEntry {
  id: string;
  userId: string;
  userName?: string;
  userRole?: string;
  userEmail?: string;
  diagramId?: string;
  timestamp: string;
  prompt: string;
  inputType: 'voice' | 'text' | 'image';
  status: 'applied' | 'discarded' | 'failed';
  command?: UMLCommandResponse;
  resultSummary?: string;
  imageThumbnail?: string;
}
