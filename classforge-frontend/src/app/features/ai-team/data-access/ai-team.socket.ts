import { Injectable, OnDestroy, inject } from '@angular/core';
import { BehaviorSubject, Observable, Subject, Subscription } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AiTeamApiService } from './ai-team.api';
import { ConnectionStatus, WsServerEvent } from './ai-team.models';

@Injectable({
  providedIn: 'root'
})
export class AiTeamSocketService implements OnDestroy {
  private api = inject(AiTeamApiService);

  private socket: WebSocket | null = null;
  private currentProjectId: string | null = null;
  private isExplicitDisconnect = false;
  private isReconnecting = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: any = null;

  // Heartbeat settings
  private heartbeatInterval = 25000;
  private heartbeatTimeout = 10000;
  private heartbeatTimer: any = null;
  private heartbeatResponseTimer: any = null;

  // Timestamp of the last received message for resume (?after=)
  private lastTimestamp: string | null = null;

  private statusSubject = new BehaviorSubject<ConnectionStatus>('disconnected');
  public status$: Observable<ConnectionStatus> = this.statusSubject.asObservable();

  private eventsSubject = new Subject<WsServerEvent>();
  public events$: Observable<WsServerEvent> = this.eventsSubject.asObservable();

  private resumeSubject = new Subject<string | null>();
  public resume$: Observable<string | null> = this.resumeSubject.asObservable();

  private tokenSubscription: Subscription | null = null;

  public get currentStatus(): ConnectionStatus {
    return this.statusSubject.value;
  }

  public getLastTimestamp(): string | null {
    return this.lastTimestamp;
  }

  public setLastTimestamp(ts: string | null): void {
    if (ts) {
      this.lastTimestamp = ts;
    }
  }

  public connect(projectId: string): void {
    if (!projectId) return;

    // If already connected to the same project, do nothing
    if (
      this.currentProjectId === projectId &&
      (this.currentStatus === 'connected' || this.currentStatus === 'connecting')
    ) {
      return;
    }

    this.disconnect();
    this.currentProjectId = projectId;
    this.isExplicitDisconnect = false;
    this.reconnectAttempts = 0;
    this.initiateConnection();
  }

  private initiateConnection(): void {
    if (!this.currentProjectId || this.isExplicitDisconnect) return;

    const isRetry = this.reconnectAttempts > 0;
    this.statusSubject.next(isRetry ? 'reconnecting' : 'connecting');

    // Rule: Request a fresh single-use token on every connection/reconnection attempt
    if (this.tokenSubscription) {
      this.tokenSubscription.unsubscribe();
    }

    this.tokenSubscription = this.api.getWsToken(this.currentProjectId).subscribe({
      next: (res) => {
        if (!res?.data?.token) {
          this.handleConnectionFailure('No se recibió un token de WebSocket válido');
          return;
        }
        this.openSocket(res.data.token);
      },
      error: (err) => {
        // If 403 Forbidden or not authorized, fail permanently without retrying
        if (err?.status === 403) {
          this.statusSubject.next('disconnected');
          return;
        }
        this.handleConnectionFailure('Error al obtener token de WebSocket');
      }
    });
  }

  private getWebSocketUrl(token: string): string {
    const wsBase = (environment.wsUrl || environment.apiUrl.replace(/^http/, 'ws')).replace(/\/$/, '');
    return `${wsBase}/projects/${this.currentProjectId}?token=${encodeURIComponent(token)}`;
  }

  private openSocket(token: string): void {
    try {
      const url = this.getWebSocketUrl(token);
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        this.statusSubject.next('connected');
        this.reconnectAttempts = 0;
        this.startHeartbeat();

        if (this.isReconnecting) {
          this.resumeSubject.next(this.lastTimestamp);
          this.isReconnecting = false;
        }
      };

      this.socket.onmessage = (event: MessageEvent) => {
        this.handleIncomingMessage(event.data);
      };

      this.socket.onerror = () => {
        // Error will trigger onclose where reconnect logic lives
      };

      this.socket.onclose = (event: CloseEvent) => {
        this.cleanupSocket();

        // 4003: User is not a member of the project or forbidden -> Do not retry
        if (event.code === 4003) {
          this.statusSubject.next('disconnected');
          return;
        }

        if (this.isExplicitDisconnect) {
          this.statusSubject.next('disconnected');
          return;
        }

        // Automatic reconnection with exponential backoff
        this.handleConnectionFailure(`Socket cerrado con código ${event.code}`);
      };
    } catch {
      this.handleConnectionFailure('Error al inicializar WebSocket');
    }
  }

  private handleIncomingMessage(rawData: string): void {
    this.resetHeartbeatResponseTimer();
    try {
      const data: WsServerEvent = JSON.parse(rawData);

      if (data.type === 'PONG') {
        return;
      }

      // Track last timestamp for resume strategy
      if (data.type === 'AI_MESSAGE_CREATED' || data.type === 'AI_MESSAGE_UPDATED') {
        const msg = data.message;
        const ts = msg?.created_at || msg?.timestamp;
        if (ts) {
          this.lastTimestamp = ts;
        }
      }

      this.eventsSubject.next(data);
    } catch {
      // Ignore malformed message frames
    }
  }

  private handleConnectionFailure(_reason: string): void {
    this.cleanupSocket();
    if (this.isExplicitDisconnect) return;

    this.reconnectAttempts++;
    this.isReconnecting = true;

    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      // Reconnection limit reached: fallback to polling
      this.setPollingFallback();
      return;
    }

    this.statusSubject.next('reconnecting');
    // Exponential backoff: min(1000 * 2^attempts, 30000) + random jitter (0-500ms)
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000) + Math.floor(Math.random() * 500);

    this.reconnectTimer = setTimeout(() => {
      this.initiateConnection();
    }, delay);
  }

  public setPollingFallback(): void {
    this.cleanupSocket();
    this.stopReconnectTimer();
    this.statusSubject.next('polling_fallback');
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.sendPing();
      this.heartbeatResponseTimer = setTimeout(() => {
        // Did not receive PONG or activity in time: terminate socket to trigger reconnect
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          try {
            this.socket.close(4000, 'Heartbeat timeout');
          } catch {
            // Ignore close error
          }
        }
      }, this.heartbeatTimeout);
    }, this.heartbeatInterval);
  }

  private resetHeartbeatResponseTimer(): void {
    if (this.heartbeatResponseTimer) {
      clearTimeout(this.heartbeatResponseTimer);
      this.heartbeatResponseTimer = null;
    }
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.resetHeartbeatResponseTimer();
  }

  private stopReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  public sendPing(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify({ type: 'PING' }));
      } catch {
        // Send failure will trigger onclose
      }
    }
  }

  public sendTyping(isTyping: boolean): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify({ type: 'TYPING', is_typing: isTyping }));
      } catch {
        // Send failure
      }
    }
  }

  private cleanupSocket(): void {
    this.stopHeartbeat();
    if (this.tokenSubscription) {
      this.tokenSubscription.unsubscribe();
      this.tokenSubscription = null;
    }
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
        try {
          this.socket.close();
        } catch {
          // Ignore
        }
      }
      this.socket = null;
    }
  }

  public disconnect(): void {
    this.isExplicitDisconnect = true;
    this.isReconnecting = false;
    this.reconnectAttempts = 0;
    this.stopReconnectTimer();
    this.cleanupSocket();
    this.statusSubject.next('disconnected');
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
