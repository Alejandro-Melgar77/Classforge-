import { TestBed, fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { of } from 'rxjs';
import { AiTeamApiService } from './ai-team.api';
import { AiTeamSocketService } from './ai-team.socket';
import { WsServerEvent } from './ai-team.models';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  readyState = 0; // CONNECTING
  onopen: ((ev: any) => any) | null = null;
  onmessage: ((ev: any) => any) | null = null;
  onerror: ((ev: any) => any) | null = null;
  onclose: ((ev: any) => any) | null = null;
  sentMessages: string[] = [];

  static readonly OPEN = 1;
  static readonly CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sentMessages.push(data);
  }

  close(code = 1000, reason = ''): void {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code, reason } as CloseEvent);
    }
  }

  simulateOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen({} as Event);
    }
  }

  simulateMessage(data: any): void {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) } as MessageEvent);
    }
  }
}

describe('AiTeamSocketService', () => {
  let service: AiTeamSocketService;
  let apiSpy: jasmine.SpyObj<AiTeamApiService>;
  let originalWebSocket: any;

  beforeEach(() => {
    MockWebSocket.instances = [];
    originalWebSocket = (window as any).WebSocket;
    (window as any).WebSocket = MockWebSocket;

    apiSpy = jasmine.createSpyObj('AiTeamApiService', ['getWsToken']);

    TestBed.configureTestingModule({
      providers: [
        AiTeamSocketService,
        { provide: AiTeamApiService, useValue: apiSpy }
      ]
    });

    service = TestBed.inject(AiTeamSocketService);
  });

  afterEach(() => {
    service.disconnect();
    (window as any).WebSocket = originalWebSocket;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
    expect(service.currentStatus).toBe('disconnected');
  });

  it('should request a fresh token on connect and establish WebSocket', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-fresh-1', expires_at: '2026-11-01T12:00:00Z' }
    }));

    service.connect('proj-1');
    expect(apiSpy.getWsToken).toHaveBeenCalledWith('proj-1');
    expect(MockWebSocket.instances.length).toBe(1);

    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain('token=token-fresh-1');

    ws.simulateOpen();
    expect(service.currentStatus).toBe('connected');

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should request a brand new token on every reconnection attempt with backoff', fakeAsync(() => {
    let callCount = 0;
    apiSpy.getWsToken.and.callFake(() => {
      callCount++;
      return of({
        success: true,
        message: 'Token generated',
        data: { token: `token-attempt-${callCount}`, expires_at: '2026-11-01T12:00:00Z' }
      });
    });

    service.connect('proj-1');
    expect(apiSpy.getWsToken).toHaveBeenCalledTimes(1);

    const ws1 = MockWebSocket.instances[0];
    ws1.simulateOpen();
    expect(service.currentStatus).toBe('connected');

    // Simulate accidental socket close
    ws1.close(1006, 'Abnormal closure');
    expect(service.currentStatus).toBe('reconnecting');

    // Advance through first backoff delay (~1000ms + jitter)
    tick(2000);

    // Second connection attempt must have requested token-attempt-2
    expect(apiSpy.getWsToken).toHaveBeenCalledTimes(2);
    expect(MockWebSocket.instances.length).toBe(2);
    expect(MockWebSocket.instances[1].url).toContain('token=token-attempt-2');

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should send periodic heartbeat PING and maintain connection', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-ping', expires_at: '2026-11-01T12:00:00Z' }
    }));

    service.connect('proj-1');
    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    // Advance 25 seconds for heartbeat
    tick(25100);

    expect(ws.sentMessages.length).toBe(1);
    expect(JSON.parse(ws.sentMessages[0])).toEqual({ type: 'PING' });

    // Simulate PONG response from server
    ws.simulateMessage({ type: 'PONG' });

    // Advance another 25 seconds
    tick(25100);
    expect(ws.sentMessages.length).toBe(2);
    expect(JSON.parse(ws.sentMessages[1])).toEqual({ type: 'PING' });

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should dispatch server events to events$ and track lastTimestamp', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-events', expires_at: '2026-11-01T12:00:00Z' }
    }));

    const receivedEvents: WsServerEvent[] = [];
    service.events$.subscribe(e => receivedEvents.push(e));

    service.connect('proj-1');
    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    const mockMsgEvent = {
      type: 'AI_MESSAGE_CREATED',
      message: {
        id: 'msg-real-1',
        content: 'Hola equipo',
        created_at: '2026-11-01T12:30:00Z',
        status: 'ok'
      }
    };
    ws.simulateMessage(mockMsgEvent);

    expect(receivedEvents.length).toBe(1);
    expect(receivedEvents[0].type).toBe('AI_MESSAGE_CREATED');
    expect(service.getLastTimestamp()).toBe('2026-11-01T12:30:00Z');

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should emit resume$ with lastTimestamp after reconnecting', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-resume', expires_at: '2026-11-01T12:00:00Z' }
    }));

    service.setLastTimestamp('2026-11-01T11:55:00Z');

    let resumedTimestamp = '';
    service.resume$.subscribe(ts => {
      resumedTimestamp = ts || '';
    });

    service.connect('proj-1');
    const ws1 = MockWebSocket.instances[0];
    ws1.simulateOpen();

    // Trigger unexpected close
    ws1.close(1006, 'Conn reset');
    expect(service.currentStatus).toBe('reconnecting');

    // Wait for backoff
    tick(2000);

    const ws2 = MockWebSocket.instances[1];
    ws2.simulateOpen();

    expect(resumedTimestamp).toBe('2026-11-01T11:55:00Z');

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should transition to polling_fallback when reconnection attempts exceed maximum', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-fail', expires_at: '2026-11-01T12:00:00Z' }
    }));

    service.connect('proj-1');
    let currentWs = MockWebSocket.instances[0];

    // Close 6 times to exceed maxReconnectAttempts (5)
    for (let i = 0; i < 6; i++) {
      currentWs.close(1006, 'Drop');
      tick(35000);
      currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    }

    expect(service.currentStatus).toBe('polling_fallback');

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should not reconnect when server closes with code 4003 (forbidden/not member)', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-forbidden', expires_at: '2026-11-01T12:00:00Z' }
    }));

    service.connect('proj-1');
    const ws = MockWebSocket.instances[0];
    ws.close(4003, 'Forbidden');

    expect(service.currentStatus).toBe('disconnected');
    tick(5000);
    // No further connection attempts
    expect(MockWebSocket.instances.length).toBe(1);

    service.disconnect();
    discardPeriodicTasks();
  }));

  it('should send typing state when requested', fakeAsync(() => {
    apiSpy.getWsToken.and.returnValue(of({
      success: true,
      message: 'Token generated',
      data: { token: 'token-type', expires_at: '2026-11-01T12:00:00Z' }
    }));

    service.connect('proj-1');
    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    service.sendTyping(true);
    expect(ws.sentMessages.length).toBe(1);
    expect(JSON.parse(ws.sentMessages[0])).toEqual({ type: 'TYPING', is_typing: true });

    service.sendTyping(false);
    expect(ws.sentMessages.length).toBe(2);
    expect(JSON.parse(ws.sentMessages[1])).toEqual({ type: 'TYPING', is_typing: false });

    service.disconnect();
    discardPeriodicTasks();
  }));
});
