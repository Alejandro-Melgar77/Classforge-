export interface UMLAttribute {
  name: string;
  type: string;
  visibility: string;
}

export interface UMLMethod {
  name: string;
  params: string;
  return_type: string;
  visibility: string;
}

export interface UMLClassCommand {
  name: string;
  attributes: UMLAttribute[];
  methods: UMLMethod[];
  stereotype?: string;
}

export interface UMLRelationCommand {
  source: string;
  target: string;
  type: string;
  label?: string;
  sourceMultiplicity?: string;
  targetMultiplicity?: string;
}

export interface UMLCommandResponse {
  action: string;
  classes: UMLClassCommand[];
  relations: UMLRelationCommand[];
  deleted_elements: string[];
  explanation: string;
  source: 'offline_nlu' | 'backend_ai';
}

export interface AiHistoryEntry {
  id: string;
  userId: string;
  diagramId?: string;
  timestamp: string;
  prompt: string;
  inputType: 'voice' | 'text';
  status: 'applied' | 'discarded' | 'failed';
  command?: UMLCommandResponse;
  resultSummary?: string;
}
