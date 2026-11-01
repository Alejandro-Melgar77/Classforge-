import { Injectable, signal, inject, OnDestroy } from '@angular/core';
import { Subject, Observable, Subscription } from 'rxjs';
import { DiagramService } from '../../services/diagram.service';
import { Collaborator, WsMessage, ChatMessage } from '../models/collaboration.model';
import { environment } from '../../../../../environments/environment';
import { ToastService } from '../../../../core/services/toast.service';

@Injectable({ providedIn: 'root' })
export class CollaborationService implements OnDestroy {
  private diagramService = inject(DiagramService);
  private toastService = inject(ToastService);

  private ws: WebSocket | null = null;
  private tokenSub: Subscription | null = null;
  private diagramId: string | null = null;

  public connectedUsers = signal<Collaborator[]>([]);
  public lockedElements = signal<Map<string, string>>(new Map());
  public connectionStatus = signal<'connected' | 'connecting' | 'disconnected'>('disconnected');
  public remoteCursors = signal<Map<string, { x: number; y: number; name: string; color: string }>>(new Map());

  public chatMessages = signal<ChatMessage[]>([]);
  public myPresenceStatus = signal<'online' | 'away' | 'busy'>('online');

  private remoteOperationsSubj = new Subject<WsMessage>();
  public remoteOperations$: Observable<WsMessage> = this.remoteOperationsSubj.asObservable();

  private opRejectedSubj = new Subject<{ element_id: string; reason: string }>();
  public opRejected$: Observable<{ element_id: string; reason: string }> = this.opRejectedSubj.asObservable();

  private aiFocusSubj = new Subject<{ element_ids: string[]; role?: string }>();
  public aiFocus$: Observable<{ element_ids: string[]; role?: string }> = this.aiFocusSubj.asObservable();

  private reconnectAttempts = 0;
  private maxReconnects = 5;
  private reconnectTimer: any = null;
  private lastCursorSend = 0;
  private pingInterval: ReturnType<typeof setInterval> | undefined = undefined;

  // Cola local de operaciones pendientes mientras WS no esté conectado
  private offlineQueue: any[] = [];

  connect(diagramId: string): void {
    if (this.diagramId === diagramId && (this.ws?.readyState === WebSocket.OPEN || this.connectionStatus() === 'connecting')) {
      return;
    }

    this.disconnect();
    this.diagramId = diagramId;
    this.connectionStatus.set('connecting');

    this.tokenSub = this.diagramService.getWsToken(diagramId).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.initWebSocket(res.data.token);
        } else {
          this.connectionStatus.set('disconnected');
          this.toastService.warning('No se pudo autenticar la conexión de colaboración en tiempo real');
        }
      },
      error: () => {
        this.connectionStatus.set('disconnected');
      }
    });
  }

  private initWebSocket(token: string): void {
    let wsBase: string;
    if (environment.apiUrl.startsWith('http')) {
      wsBase = environment.apiUrl.replace(/^http/, 'ws');
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsBase = `${protocol}//${window.location.host}${environment.apiUrl}`;
    }
    const url = `${wsBase}/ws/diagrams/${this.diagramId}?token=${token}`;

    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      console.error('Error inicializando WebSocket:', e);
      this.connectionStatus.set('disconnected');
      return;
    }

    this.ws.onopen = () => {
      this.connectionStatus.set('connected');
      this.reconnectAttempts = 0;

      // 1. Handshake JOIN
      this.sendDirect({ type: 'JOIN' });
      // 2. Restaurar presencia
      this.setPresenceStatus(this.myPresenceStatus());

      // 3. Reenviar cola offline ordenada
      if (this.offlineQueue.length > 0) {
        const queueCopy = [...this.offlineQueue];
        this.offlineQueue = [];
        queueCopy.forEach(msg => this.sendDirect(msg));
      }

      // 4. Ping keepalive cada 30s
      clearInterval(this.pingInterval);
      this.pingInterval = setInterval(() => {
        this.sendDirect({ type: 'PING' });
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.handleMessage(msg);
      } catch (e) {
        console.error('Error procesando mensaje WebSocket:', e);
      }
    };

    this.ws.onclose = () => {
      this.connectionStatus.set('disconnected');
      clearInterval(this.pingInterval);
      this.handleReconnect();
    };

    this.ws.onerror = () => {
      this.connectionStatus.set('disconnected');
    };
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnects && this.diagramId) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => {
        if (this.diagramId) {
          this.connect(this.diagramId);
        }
      }, delay);
    }
  }

  private handleMessage(msg: any): void {
    const type = msg.type;
    switch (type) {
      case 'ROOM_STATE': {
        const users: Collaborator[] = (msg.users || []).map((u: any) => ({
          user_id: u.user_id,
          name: u.user_name || u.name || 'Usuario',
          role: u.role || 'dev',
          color: u.user_color || u.color || '#2D6BE4',
          status: u.status || 'online',
          cursor: u.cursor
        }));
        this.connectedUsers.set(users);

        if (msg.chat_history) {
          this.chatMessages.set(msg.chat_history);
        }
        break;
      }

      case 'USER_JOINED': {
        const newUser: Collaborator = {
          user_id: msg.user_id,
          name: msg.user_name || msg.name || 'Usuario',
          role: msg.role || 'dev',
          color: msg.user_color || msg.color || '#2D6BE4',
          status: msg.status || 'online'
        };
        this.connectedUsers.update(users => {
          const filtered = users.filter(u => u.user_id !== newUser.user_id);
          return [...filtered, newUser];
        });
        break;
      }

      case 'USER_LEFT': {
        const userId = msg.user_id;
        this.connectedUsers.update(users => users.filter(u => u.user_id !== userId));
        this.remoteCursors.update(map => {
          const newMap = new Map(map);
          newMap.delete(userId);
          return newMap;
        });
        break;
      }

      case 'USER_PRESENCE_UPDATED': {
        this.connectedUsers.update(users => {
          return users.map(u => {
            if (u.user_id === msg.user_id) {
              return { ...u, status: msg.status };
            }
            return u;
          });
        });
        break;
      }

      case 'CHAT_MESSAGE': {
        this.chatMessages.update(msgs => {
          const newMsg: ChatMessage = {
            id: msg.id || Date.now().toString(),
            user_id: msg.user_id,
            user_name: msg.user_name,
            user_color: msg.user_color,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString()
          };
          return [...msgs, newMsg];
        });
        break;
      }

      case 'CURSOR_UPDATE': {
        const senderId = msg.user_id;
        const user = this.connectedUsers().find(u => u.user_id === senderId);
        const name = user ? user.name : (msg.user_name || 'Colaborador');
        const color = user ? user.color : (msg.user_color || '#2D6BE4');
        this.remoteCursors.update(map => {
          const newMap = new Map(map);
          newMap.set(senderId, { x: msg.x, y: msg.y, name, color });
          return newMap;
        });
        break;
      }

      case 'LOCK_GRANTED': {
        this.lockedElements.update(map => {
          const newMap = new Map(map);
          newMap.set(msg.element_id, msg.user_id);
          return newMap;
        });
        break;
      }

      case 'LOCK_RELEASED': {
        this.lockedElements.update(map => {
          const newMap = new Map(map);
          newMap.delete(msg.element_id);
          return newMap;
        });
        break;
      }

      case 'LOCK_REJECTED': {
        const owner = this.getLockOwner(msg.element_id);
        const ownerName = owner ? owner.name : 'otro usuario';
        this.toastService.info(`El elemento ya está siendo editado por ${ownerName}.`);
        break;
      }

      case 'OP_REJECTED': {
        const elementId = msg.element_id || msg.payload?.element_id || '';
        const reason = msg.reason || msg.payload?.reason || 'locked';
        this.toastService.warning('Operación rechazada: el elemento está bloqueado por otro usuario.');
        this.opRejectedSubj.next({ element_id: elementId, reason });
        break;
      }

      case 'AI_FOCUS': {
        const elementIds = msg.element_ids || msg.payload?.element_ids || [];
        const role = msg.role || msg.payload?.role;
        this.aiFocusSubj.next({ element_ids: elementIds, role });
        break;
      }

      case 'NODE_OPERATION':
      case 'EDGE_OPERATION': {
        this.remoteOperationsSubj.next(msg);
        break;
      }

      case 'PONG':
        break;

      default:
        if (type === 'presence_update' && msg.payload?.users) {
          this.connectedUsers.set(msg.payload.users);
        }
        break;
    }
  }

  getLockOwner(elementId: string): Collaborator | undefined {
    const userId = this.lockedElements().get(elementId);
    if (!userId) return undefined;
    return this.connectedUsers().find(u => u.user_id === userId);
  }

  sendCursor(x: number, y: number): void {
    const now = Date.now();
    if (now - this.lastCursorSend < 50) return; // throttle 50ms
    this.lastCursorSend = now;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendDirect({ type: 'CURSOR_MOVE', x, y });
    }
  }

  sendNodeOperation(op: 'add' | 'update' | 'move' | 'delete', nodeId: string, data: any): void {
    this.sendWithOfflineQueue({ type: 'NODE_OPERATION', op, node_id: nodeId, data });
  }

  sendEdgeOperation(op: 'add' | 'update' | 'delete', edgeId: string, data: any): void {
    this.sendWithOfflineQueue({ type: 'EDGE_OPERATION', op, edge_id: edgeId, data });
  }

  acquireLock(elementId: string): void {
    this.sendWithOfflineQueue({ type: 'LOCK_ACQUIRE', element_id: elementId });
  }

  releaseLock(elementId: string): void {
    this.sendWithOfflineQueue({ type: 'LOCK_RELEASE', element_id: elementId });
  }

  sendChatMessage(content: string): void {
    this.sendWithOfflineQueue({ type: 'CHAT_MESSAGE', content });
  }

  setPresenceStatus(status: 'online' | 'away' | 'busy'): void {
    this.myPresenceStatus.set(status);
    this.sendDirect({ type: 'PRESENCE_STATUS', status });
  }

  private sendWithOfflineQueue(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendDirect(data);
    } else {
      // Guardar en cola local para enviar inmediatamente al reconectar
      this.offlineQueue.push(data);
    }
  }

  private sendDirect(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  /**
   * Agrega o remueve el miembro virtual de la IA en la barra de presencia (P5)
   */
  setAiMemberPresence(isActive: boolean, role: string = 'architect'): void {
    const aiId = `ai:${role}`;
    this.connectedUsers.update(users => {
      const filtered = users.filter(u => !u.is_ai);
      if (!isActive) return filtered;

      const roleLabels: Record<string, string> = {
        architect: 'Arquitecto IA',
        qa: 'QA Linter IA',
        tech_lead: 'Tech Lead IA',
        mentor: 'Mentor IA',
        dba: 'DBA IA',
        security: 'Security IA'
      };

      const aiMember: Collaborator = {
        user_id: aiId,
        name: roleLabels[role] || 'Asistente IA',
        role: role,
        color: '#8B5CF6',
        status: 'online',
        is_ai: true,
        ai_role: role
      };
      return [...filtered, aiMember];
    });
  }

  disconnect(): void {
    clearInterval(this.pingInterval);
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;

    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
    if (this.tokenSub) {
      this.tokenSub.unsubscribe();
      this.tokenSub = null;
    }
    this.connectionStatus.set('disconnected');
    this.diagramId = null;
    this.lockedElements.set(new Map());
    this.remoteCursors.set(new Map());
  }

  ngOnDestroy(): void {
    this.disconnect();
    this.remoteOperationsSubj.complete();
    this.opRejectedSubj.complete();
    this.aiFocusSubj.complete();
  }
}
