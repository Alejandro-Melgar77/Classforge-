import { Injectable, signal, inject, OnDestroy } from '@angular/core';
import { Subject, Observable, Subscription } from 'rxjs';
import { DiagramService } from '../../services/diagram.service';
import { Collaborator, WsMessage, ChatMessage } from '../models/collaboration.model';
import { environment } from '../../../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class CollaborationService implements OnDestroy {
  private diagramService = inject(DiagramService);
  
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

  private reconnectAttempts = 0;
  private maxReconnects = 5;
  private lastCursorSend = 0;
  private pingInterval: ReturnType<typeof setInterval> | undefined = undefined;

  connect(diagramId: string): void {
    this.diagramId = diagramId;
    this.connectionStatus.set('connecting');
    this.tokenSub = this.diagramService.getWsToken(diagramId).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.initWebSocket(res.data.token);
        } else {
          this.connectionStatus.set('disconnected');
        }
      },
      error: () => this.connectionStatus.set('disconnected')
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
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.connectionStatus.set('connected');
      this.reconnectAttempts = 0;
      // Send handshake JOIN message
      this.sendRaw({ type: 'JOIN' });
      // Restore my presence on reconnect
      this.setPresenceStatus(this.myPresenceStatus());
      
      // Keepalive ping every 30s
      clearInterval(this.pingInterval);
      this.pingInterval = setInterval(() => {
        this.sendRaw({ type: 'PING' });
      }, 30000);
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.handleMessage(msg);
      } catch (e) {
        console.error('WebSocket parse error:', e);
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
      setTimeout(() => this.connect(this.diagramId!), delay);
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

  sendCursor(x: number, y: number): void {
    const now = Date.now();
    if (now - this.lastCursorSend < 50) return; // throttle 50ms
    this.lastCursorSend = now;
    this.sendRaw({ type: 'CURSOR_MOVE', x, y });
  }

  sendNodeOperation(op: 'add' | 'update' | 'move' | 'delete', nodeId: string, data: any): void {
    this.sendRaw({ type: 'NODE_OPERATION', op, node_id: nodeId, data });
  }

  sendEdgeOperation(op: 'add' | 'update' | 'delete', edgeId: string, data: any): void {
    this.sendRaw({ type: 'EDGE_OPERATION', op, edge_id: edgeId, data });
  }

  acquireLock(elementId: string): void {
    this.sendRaw({ type: 'LOCK_ACQUIRE', element_id: elementId });
  }

  releaseLock(elementId: string): void {
    this.sendRaw({ type: 'LOCK_RELEASE', element_id: elementId });
  }
  
  sendChatMessage(content: string): void {
    this.sendRaw({ type: 'CHAT_MESSAGE', content });
  }
  
  setPresenceStatus(status: 'online' | 'away' | 'busy'): void {
    this.myPresenceStatus.set(status);
    this.sendRaw({ type: 'PRESENCE_STATUS', status });
  }

  private sendRaw(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect(): void {
    clearInterval(this.pingInterval);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.tokenSub) {
      this.tokenSub.unsubscribe();
    }
    this.connectionStatus.set('disconnected');
    this.diagramId = null;
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
