export interface WsMessage<T = any> {
  type: string;
  payload: T;
  sender_id?: string;
  timestamp?: number;
}

export interface Collaborator {
  user_id: string;
  name: string;
  role: string;
  color: string;
  status: 'online' | 'away' | 'busy';
  cursor?: { x: number; y: number };
  active_lock?: string;
}

export interface ChatMessage {
  id: string;
  user_id: string;
  user_name: string;
  user_color: string;
  content: string;
  timestamp: string;
}

export interface CollaborationState {
  connectedUsers: Collaborator[];
  lockedElements: Map<string, string>;
  connectionStatus: 'connected' | 'connecting' | 'disconnected';
  chatMessages: ChatMessage[];
}
